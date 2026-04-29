# AiTech - Proje Spesifikasyonu

## 🏢 Proje Hakkında
- **İsim**: AiTech
- **Açıklama**: Eğitim odaklı AI destekli platform
- **Tür**: Web Uygulaması (SPA)

---

## 👥 Kullanıcı Türleri

### Öğretmen
- Hesap oluştur (login, şifre, captcha)
- Ders oluştur (tema + opsiyonel içerik/metın)
- Öğrenci ekleme kodu üret
- Dashboard: İstatistikleri gör (konu bazlı % anlamadım)
- AI'dan yardım al
- Bildirimler (zamana göre sıralı)

### Öğrenci
- Hesap oluştur (hoca kodu ile)
- Öğretmenlerin derslerini gör
- Ders seç → Soru sor → AI cevaplar
- "Anladım" / "Anlamadım" seçeneği

---

## 🔐 Güvenlik

| Özellik | Detay |
|---------|-------|
| Giriş | Login + Şifre + |
| Hatalı giriş | 5 başarısız → 5 dakika bekleme |
| Özel kod | 8 haneli, benzersiz (kayıt sırasında bir kez gösterilir) |
| Şifre unutma | Özel kod ile sıfırlama |
| Şifre unutma deneme | 3 başarısız → 24 saat kilit |
| Brute force koruma | Cooldown sistemi |

---

## 📊 Veri Modelleri

### User
```python
id: int
login: str (unique)
password_hash: str
role: str (teacher/student)
ad: str
soyad: str
okul_no: str (optional)
sinif: str (optional)
ozel_kod: str (unique, 8 char)
hoca_kodu: str (öğrenci için)
olusturma_tarihi: datetime
```

### Ders
```python
id: int
hoca_id: int (foreign key)
tema: str (zorunlu)
icerik: str (opsiyonel)
olusturma_tarihi: datetime
aktif: bool
```

### Soru
```python
id: int
ders_id: int
ogrenci_id: int
soru_metni: str
ai_cevap: str
anladi_mi: bool (optional)
timestamp: datetime
```

### Bildirim
```python
id: int
hoca_id: int
konu: str
yuzde: int
timestamp: datetime
```

---

## 🔔 Bildirim Sistemi
- Eşik: %15 öğrenci "anlamadım" dediğinde
- Hoca sadece istatistik görür (kim sorduğu GÖRÜLMEZ)
- Zamana göre sıralı (en eski konudan yeniye)

---

## 📦 Teknoloji Stack

| Katman | Teknoloji |
|--------|----------|
| Frontend | Svelte + Vite |
| Backend | FastAPI + Pydantic v2 |
| DB | PostgreSQL |
| AI | Qwen2.5-7B (Open Router) |
| Docker | nginx + uvicorn |

---

## 🎨 UI Tasarım
- Apple eskisi şıklıkta
- Minimal, modern
- Yumuşak animasyonlar
- Frameless tasarım
- Büyük tipografi