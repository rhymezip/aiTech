# AiTech — Eğitim Odaklı AI Platformu

## Hızlı Kurulum (Ubuntu Server)

### 1. Gereksinimler
```bash
# Docker & Docker Compose kurulu olmalı
docker --version
docker compose version
```

### 2. Projeyi kopyala ve .env oluştur
```bash
git clone <repo> aitech
cd aitech
cp .env.example .env
nano .env   # OPENROUTER_API_KEY ve diğer değerleri gir
```

### 3. Başlat
```bash
docker compose up -d --build
```

Uygulama `http://sunucu-ip` adresinde çalışır.

---

## .env Değişkenleri

| Değişken | Açıklama | Zorunlu |
|----------|----------|---------|
| `SECRET_KEY` | JWT imzalama anahtarı | ✅ |
| `MASTER_KEY` | Veri şifreleme anahtarı | ✅ |
| `OPENROUTER_API_KEY` | OpenRouter API key | ✅ (AI için) |
| `MODEL` | AI modeli (varsayılan: qwen/qwen-2.5-7b-instruct) | ❌ |

> **OpenRouter API key almak için:** https://openrouter.ai → Sign up → Keys

---

## API Endpoint Özeti

### Auth
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/auth/login` | Giriş yap |
| POST | `/api/auth/register` | Kayıt ol |

### Öğretmen
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/lessons` | Dersleri listele |
| POST | `/api/lessons` | Ders oluştur |
| DELETE | `/api/lessons/{id}` | Ders sil |
| GET | `/api/notifications` | Bildirimleri al |
| PATCH | `/api/notifications/{id}/read` | Bildirimi okundu işaretle |
| GET | `/api/teacher/stats` | İstatistikler + hoca_kodu |
| POST | `/api/teacher/ai` | AI ile sohbet |

### Öğrenci
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/students/teachers` | Öğretmeni gör |
| GET | `/api/students/lessons/{hoca_id}` | Dersleri gör |
| POST | `/api/students/ask` | AI'ya soru sor |
| POST | `/api/students/anladi` | Anladım/Anlamadım gönder |
| GET | `/api/students/history/{ders_id}` | Soru geçmişi |

---

## Kullanıcı Akışı

1. **Öğretmen** → Kayıt ol → Dashboard'da `🔑 HOCA_KODU` görünür → Öğrencilere paylaş
2. **Öğrenci** → Kayıt ol (öğretmen kodunu gir) → Dersler → Soru sor → Anladım/Anlamadım
3. **Öğretmen** → Bildirimler sekmesi → %15+ anlamadım uyarısı → AI ile analiz

---

## Logs & Hata Ayıklama

```bash
docker compose logs backend -f    # Backend logları
docker compose logs frontend -f   # Nginx logları
docker compose ps                 # Konteyner durumları
```
