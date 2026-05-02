from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import LoginRequest, RegisterRequest, ResetPasswordRequest
from utils import encrypt_data, decrypt_data, hash_password, verify_password, create_jwt, generate_unique_kod
from errors import get_error, get_error_with_params, USERNAME_MSGS

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def get_user_lang(user) -> str:
    return getattr(user, 'dil', None) or "tr"


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail=get_error("user_not_found"))

    from datetime import datetime, timedelta
    if user.locked_until and user.locked_until > datetime.utcnow():
        kalan = int((user.locked_until - datetime.utcnow()).total_seconds()/60)
        lang = get_user_lang(user)
        raise HTTPException(status_code=429, detail=get_error_with_params("account_locked_wait", lang, minutes=kalan))

    if not verify_password(data.password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=5)
            user.failed_attempts = 0
        db.commit()
        lang = get_user_lang(user)
        raise HTTPException(status_code=401, detail=get_error("wrong_password", lang))

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    return {
        "token": create_jwt(user.id),
        "user": {
            "id": user.id,
            "role": user.role,
            "ad": decrypt_data(user.ad_encrypted),
            "soyad": decrypt_data(user.soyad_encrypted),
            "kendi_hoca_kodu": user.kendi_hoca_kodu
        }
    }


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    login_clean = (data.login or "").strip().lower()
    ozel_kod = data.ozel_kod.strip()
    new_password = data.new_password

    if not login_clean or not ozel_kod or not new_password:
        raise HTTPException(status_code=400, detail=get_error("code_and_password_required"))

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail=get_error("password_min_length"))

    user = db.query(User).filter(
        User.login == login_clean,
        User.ozel_kod == ozel_kod
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail=get_error("invalid_ozel_kod"))

    user.password_hash = hash_password(new_password)
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    return {"message": get_error("password_reset_success"), "login": user.login}


@router.get("/check-username/{username}")
def check_username(username: str, lang: str = "en", db: Session = Depends(get_db)):
    login_clean = username.strip().lower()
    msgs = USERNAME_MSGS.get(lang, USERNAME_MSGS["tr"])

    if not login_clean:
        return {"available": False, "reason": "empty", "message": msgs["empty"]}
    if len(login_clean) < 3:
        return {"available": False, "reason": "short", "message": msgs["short"]}

    import re
    if not re.match(r"^[a-zA-Z0-9_]+$", login_clean):
        return {"available": False, "reason": "invalid_chars", "message": msgs["invalid_chars"]}
    if re.match(r"^[0-9]+$", login_clean):
        return {"available": False, "reason": "only_numbers", "message": msgs["only_numbers"]}

    existing = db.query(User).filter(User.login == login_clean).first()
    if existing:
        return {"available": False, "reason": "taken", "message": msgs["taken"]}
    return {"available": True, "reason": "ok", "message": msgs["ok"]}


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    login_clean = data.login.strip().lower()
    lang = data.dil or "tr"

    if db.query(User).filter(User.login == login_clean).first():
        raise HTTPException(status_code=400, detail=get_error("username_taken", lang))

    hoca = None
    if data.role == "student" and data.hoca_kodu:
        hoca = db.query(User).filter(User.kendi_hoca_kodu == data.hoca_kodu.strip().upper(), User.role == "teacher").first()
        if not hoca:
            raise HTTPException(status_code=400, detail=get_error("invalid_code", lang))

    ozel_kod = generate_unique_kod(db, User, User.ozel_kod)

    kendi_hoca_kodu = None
    if data.role == "teacher":
        kendi_hoca_kodu = generate_unique_kod(db, User, User.kendi_hoca_kodu)

    from models import OgrenciHoca
    user = User(
        login=login_clean,
        password_hash=hash_password(data.password),
        role=data.role,
        ad_encrypted=encrypt_data(data.ad.strip()),
        soyad_encrypted=encrypt_data(data.soyad.strip()),
        ozel_kod=ozel_kod,
        hoca_kodu=data.hoca_kodu.strip().upper() if data.hoca_kodu else None,
        hoca_id=hoca.id if hoca else None,
        kendi_hoca_kodu=kendi_hoca_kodu,
        dil=lang
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if hoca:
        db.add(OgrenciHoca(ogrenci_id=user.id, hoca_id=hoca.id))
        db.commit()

    return {"message": get_error("registration_success", lang), "ozel_kod": ozel_kod}