from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, Ders, Soru, Bildirim, OgrenciHoca
from schemas import DersRequest, DersUpdateRequest, SoruRequest, AnladiRequest, AddTeacherRequest, LanguageRequest
from utils import encrypt_data, decrypt_data, create_jwt
from errors import get_error, ALL_ERRORS, LANG_NAMES
from datetime import datetime
import os
import re
import json
import httpx

router = APIRouter()

API_KEY = os.getenv("API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
AI_MODEL = os.getenv("MODEL", "openai/gpt-oss-20b:free")
SECRET_KEY = os.getenv("SECRET_KEY", "b27a2885fc06b4c1057899a151d038a48b5f6cc98ae9148d173332579d9383d1")


def get_user_lang(user) -> str:
    return getattr(user, 'dil', None) or "tr"


def get_current_user_fast(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    from jose import jwt
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        uid = int(payload["sub"])
    except:
        raise HTTPException(status_code=401, detail=get_error("invalid_token"))
    
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail=get_error("user_not_found"))
    return user


def check_notification_threshold(db, ders_id, hoca_id):
    total = db.query(Soru).filter(Soru.ders_id == ders_id, Soru.anladi_mi != None).count()
    if total < 3:
        return
    anlamadi = db.query(Soru).filter(Soru.ders_id == ders_id, Soru.anladi_mi == False).count()
    yuzde = int(anlamadi / total * 100)
    if yuzde < 15:
        return
    
    ders = db.query(Ders).filter(Ders.id == ders_id).first()
    if not ders:
        return
    
    from errors import ERROR_MSGS
    existing = db.query(Bildirim).filter(
        Bildirim.hoca_id == hoca_id,
        Bildirim.konu_encrypted == ders.tema_encrypted
    ).first()
    
    if existing:
        existing.yuzde = yuzde
        existing.goruldu = False
        existing.timestamp = datetime.utcnow()
    else:
        db.add(Bildirim(hoca_id=hoca_id, konu_encrypted=ders.tema_encrypted, yuzde=yuzde))
    db.commit()


lessons_router = APIRouter(prefix="/api", tags=["Lessons & Students"])


@lessons_router.get("/lessons")
def get_lessons(db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    lessons = db.query(Ders).filter(Ders.hoca_id == cu.id).order_by(Ders.olusturma_tarihi.desc()).all()
    result = []
    for l in lessons:
        total = db.query(Soru).filter(Soru.ders_id == l.id, Soru.anladi_mi != None).count()
        anlamadi = db.query(Soru).filter(Soru.ders_id == l.id, Soru.anladi_mi == False).count()
        toplam_soru = db.query(Soru).filter(Soru.ders_id == l.id).count()
        result.append({
            "id": l.id,
            "tema": decrypt_data(l.tema_encrypted),
            "icerik": decrypt_data(l.icerik_encrypted) if l.icerik_encrypted else None,
            "olusturma_tarihi": l.olusturma_tarihi.isoformat(),
            "toplam_soru": toplam_soru,
            "anlamadi_yuzde": int(anlamadi / total * 100) if total else 0
        })
    return {"lessons": result}


@lessons_router.post("/lessons")
def create_lesson(data: DersRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    lesson = Ders(
        hoca_id=cu.id,
        tema_encrypted=encrypt_data(data.tema.strip()),
        icerik_encrypted=encrypt_data(data.icerik.strip()) if data.icerik else None
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return {"message": get_error("lesson_created", lang), "id": lesson.id}


@lessons_router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    lesson = db.query(Ders).filter(Ders.id == lesson_id, Ders.hoca_id == cu.id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail=get_error("lesson_not_found", lang))
    db.delete(lesson)
    db.commit()
    return {"message": get_error("lesson_deleted", lang)}


@lessons_router.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, data: DersUpdateRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    lesson = db.query(Ders).filter(Ders.id == lesson_id, Ders.hoca_id == cu.id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail=get_error("lesson_not_found", lang))
    
    if data.tema is not None:
        lesson.tema_encrypted = encrypt_data(data.tema.strip())
    if data.icerik is not None:
        lesson.icerik_encrypted = encrypt_data(data.icerik.strip()) if data.icerik.strip() else None
    
    db.commit()
    return {"message": get_error("lesson_updated", lang)}


@lessons_router.get("/notifications")
def get_notifications(db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    notifs = db.query(Bildirim).filter(Bildirim.hoca_id == cu.id).order_by(Bildirim.timestamp.asc()).all()
    return {
        "notifications": [{
            "id": n.id,
            "konu": decrypt_data(n.konu_encrypted),
            "yuzde": n.yuzde,
            "goruldu": n.goruldu,
            "timestamp": n.timestamp.isoformat()
        } for n in notifs]
    }


@lessons_router.patch("/notifications/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    n = db.query(Bildirim).filter(Bildirim.id == notif_id, Bildirim.hoca_id == cu.id).first()
    if not n:
        raise HTTPException(status_code=404, detail=get_error("not_found", lang))
    n.goruldu = True
    db.commit()
    return {"message": get_error("marked_as_read", lang)}


@lessons_router.get("/teacher/stats")
def teacher_stats(db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    ogrenciler = db.query(OgrenciHoca).filter(OgrenciHoca.hoca_id == cu.id).count()
    if ogrenciler == 0:
        ogrenciler = db.query(User).filter(User.hoca_id == cu.id, User.role == "student").count()
    dersler = db.query(Ders).filter(Ders.hoca_id == cu.id).count()
    sorular = db.query(Soru).join(Ders, Ders.id == Soru.ders_id).filter(Ders.hoca_id == cu.id).count()
    return {
        "ogrenci_sayisi": ogrenciler,
        "ders_sayisi": dersler,
        "soru_sayisi": sorular,
        "hoca_kodu": cu.kendi_hoca_kodu
    }


@lessons_router.get("/students/teachers")
def get_my_teachers(db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    rows = db.query(OgrenciHoca).filter(OgrenciHoca.ogrenci_id == cu.id).all()
    result = []
    for row in rows:
        hoca = db.query(User).filter(User.id == row.hoca_id).first()
        if not hoca:
            continue
        ders_sayisi = db.query(Ders).filter(Ders.hoca_id == hoca.id).count()
        result.append({
            "id": hoca.id,
            "ad": decrypt_data(hoca.ad_encrypted),
            "soyad": decrypt_data(hoca.soyad_encrypted),
            "ders_sayisi": ders_sayisi
        })
    return {"teachers": result}


@lessons_router.post("/students/add-teacher")
def add_teacher(data: AddTeacherRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    hoca_kodu = data.hoca_kodu.strip().upper()
    if not hoca_kodu:
        raise HTTPException(status_code=400, detail=get_error("code_required", lang))
    
    hoca = db.query(User).filter(User.kendi_hoca_kodu == hoca_kodu, User.role == "teacher").first()
    if not hoca:
        raise HTTPException(status_code=404, detail=get_error("invalid_code", lang))
    
    already = db.query(OgrenciHoca).filter(
        OgrenciHoca.ogrenci_id == cu.id,
        OgrenciHoca.hoca_id == hoca.id
    ).first()
    if already:
        raise HTTPException(status_code=400, detail=get_error("teacher_already_added", lang))
    
    db.add(OgrenciHoca(ogrenci_id=cu.id, hoca_id=hoca.id))
    cu.hoca_id = hoca.id
    db.commit()
    
    return {
        "message": get_error("teacher_added", lang),
        "hoca": {
            "id": hoca.id,
            "ad": decrypt_data(hoca.ad_encrypted),
            "soyad": decrypt_data(hoca.soyad_encrypted)
        }
    }


@lessons_router.delete("/students/teacher/{hoca_id}")
def remove_teacher(hoca_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    relation = db.query(OgrenciHoca).filter(
        OgrenciHoca.ogrenci_id == cu.id,
        OgrenciHoca.hoca_id == hoca_id
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail=get_error("teacher_not_found", lang))
    
    db.delete(relation)
    if cu.hoca_id == hoca_id:
        cu.hoca_id = None
    db.commit()
    
    return {"message": get_error("teacher_removed", lang)}


@lessons_router.get("/students/lessons/{hoca_id}")
def get_teacher_lessons_for_student(hoca_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    relation = db.query(OgrenciHoca).filter(
        OgrenciHoca.ogrenci_id == cu.id,
        OgrenciHoca.hoca_id == hoca_id
    ).first()
    if not relation:
        raise HTTPException(status_code=403, detail=get_error("no_teacher_access", lang))
    
    lessons = db.query(Ders).filter(Ders.hoca_id == hoca_id).order_by(Ders.olusturma_tarihi.desc()).all()
    return {
        "lessons": [{
            "id": l.id,
            "tema": decrypt_data(l.tema_encrypted),
            "icerik": decrypt_data(l.icerik_encrypted) if l.icerik_encrypted else None,
            "olusturma_tarihi": l.olusturma_tarihi.isoformat()
        } for l in lessons]
    }


@lessons_router.post("/students/anladi")
def set_anladi(data: AnladiRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    soru = db.query(Soru).filter(Soru.id == data.soru_id, Soru.ogrenci_id == cu.id).first()
    if not soru:
        raise HTTPException(status_code=404, detail=get_error("question_not_found", lang))
    
    soru.anladi_mi = data.anladi
    soru.ai_tahmin = False
    db.commit()
    
    lesson = db.query(Ders).filter(Ders.id == soru.ders_id).first()
    if lesson:
        check_notification_threshold(db, soru.ders_id, lesson.hoca_id)
    
    return {"message": get_error("saved", lang)}


@lessons_router.get("/students/history/{ders_id}")
def get_history(ders_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    sorular = db.query(Soru).filter(Soru.ders_id == ders_id, Soru.ogrenci_id == cu.id).order_by(Soru.timestamp.asc()).all()
    return {
        "history": [{
            "id": s.id,
            "soru": decrypt_data(s.soru_encrypted),
            "cevap": decrypt_data(s.ai_cevap_encrypted) if s.ai_cevap_encrypted else "",
            "anladi_mi": s.anladi_mi,
            "ai_tahmin": s.ai_tahmin,
            "timestamp": s.timestamp.isoformat()
        } for s in sorular]
    }


@lessons_router.post("/user/dil")
def set_language(data: LanguageRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if not data.dil:
        raise HTTPException(status_code=400, detail=get_error("language_code_required", lang))
    cu.dil = data.dil
    db.commit()
    return {"message": get_error("language_updated", lang)}


@lessons_router.get("/teacher/students")
def get_teacher_students(db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    rows = db.query(OgrenciHoca).filter(OgrenciHoca.hoca_id == cu.id).all()
    seen_ids = set()
    result = []
    for row in rows:
        if row.ogrenci_id in seen_ids:
            continue
        seen_ids.add(row.ogrenci_id)
        ogr = db.query(User).filter(User.id == row.ogrenci_id).first()
        if not ogr:
            continue
        try:
            ad = decrypt_data(ogr.ad_encrypted)
            soyad = decrypt_data(ogr.soyad_encrypted)
        except Exception as e:
            print(f"[WARN] decrypt failed for user {ogr.id}: {e}")
            ad = "???"
            soyad = "???"
        sorular = db.query(Soru).filter(Soru.ogrenci_id == ogr.id).count()
        anlamadi = db.query(Soru).filter(Soru.ogrenci_id == ogr.id, Soru.anladi_mi == False).count()
        result.append({
            "id": ogr.id,
            "ad": ad,
            "soyad": soyad,
            "telefon": ogr.telefon,
            "toplam_soru": sorular,
            "anlamadi_sayi": anlamadi,
            "kayit_tarihi": ogr.olusturma_tarihi.isoformat() if ogr.olusturma_tarihi else None
        })
    return {"students": result}


@lessons_router.delete("/teacher/students/{ogr_id}")
def delete_student(ogr_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))
    
    relation = db.query(OgrenciHoca).filter(
        OgrenciHoca.hoca_id == cu.id,
        OgrenciHoca.ogrenci_id == ogr_id
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail=get_error("student_not_found", lang))
    
    db.query(Soru).filter(Soru.ogrenci_id == ogr_id).delete()
    db.query(OgrenciHoca).filter(
        OgrenciHoca.hoca_id == cu.id,
        OgrenciHoca.ogrenci_id == ogr_id
    ).delete()
    db.commit()
    return {"message": get_error("student_deleted", lang)}