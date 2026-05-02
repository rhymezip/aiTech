# AiTech — Project Specification

## 🏢 About the Project

| Field | Detail |
|-------|--------|
| **Name** | AiTech |
| **Type** | Web Application (SPA) |
| **Purpose** | Education-focused, AI-powered teacher–student platform |
| **Language** | Multilingual (TR, TK, EN, ZH, KO, JA, PT, RU, FR) |

---

## 👥 User Types

### Teacher (`role: teacher`)
- Creates an account (first name, last name, username, password)
- A unique `ozel_kod` (recovery code) and `kendi_hoca_kodu` (teacher invite code) are generated at registration
- Creates lessons (topic required, content optional)
- Can edit (PUT) or delete (DELETE) lessons
- Views student list; can remove individual students
- Dashboard statistics: student count, lesson count, total question count, teacher code
- Notifications tab: automatic alerts when a lesson's "didn't understand" rate exceeds 15%
- Can chat with AI (`/api/teacher/ai`)

### Student (`role: student`)
- Registers with a teacher's invite code (`hoca_kodu`) to be linked to a teacher
- Can add additional teachers after registration (`/api/students/add-teacher`)
- Can remove a teacher (`DELETE /api/students/teacher/{hoca_id}`)
- Lists linked teachers and their lesson counts
- Views lessons from a selected teacher
- Asks AI questions within a lesson; AI responds
- Sends "Understood" / "Didn't Understand" feedback for each answer
- Views question history per lesson

---

## 🔐 Security

| Feature | Detail |
|---------|--------|
| Authentication | Username + Password → JWT (valid 7 days, HS256) |
| Password hashing | bcrypt (passlib) |
| Data encryption | XOR + base64 (SHA-256 derived key from MASTER_KEY) — PII fields stored encrypted in DB |
| Failed login | 5 failed attempts → 5-minute account lockout |
| Password reset | Via `ozel_kod` (unique 8-character code); 3 failed attempts → 24-hour lockout (spec note) |
| Brute force protection | Cooldown system via `failed_attempts` + `locked_until` DB fields |
| Username check | Real-time availability check (`/api/auth/check-username/{username}`) |
| CORS | Configurable via environment variables (`CORS_ORIGINS`, `CORS_ALLOW_ALL`) |

---

## 📊 Data Models

### User
```python
id: int (PK)
login: str (unique, lowercase)
password_hash: str (bcrypt)
role: str  # "teacher" | "student"
ad_encrypted: str  # XOR+base64 (first name)
soyad_encrypted: str  # XOR+base64 (last name)
dil: str (nullable)  # preferred UI language
ozel_kod: str (unique, 8 char)  # password recovery code
hoca_kodu: str (nullable)  # teacher code the student registered with
hoca_id: int (FK → users.id, nullable)
kendi_hoca_kodu: str (unique, nullable)  # teachers only
failed_attempts: int (default=0)
locked_until: datetime (nullable)
olusturma_tarihi: datetime  # created_at
```

### Lesson (Ders)
```python
id: int (PK)
hoca_id: int (FK → users.id)
tema_encrypted: str  # XOR+base64 (topic)
icerik_encrypted: str (nullable)  # XOR+base64 (content)
olusturma_tarihi: datetime  # created_at
aktif: bool (default=True)
```

### Question (Soru)
```python
id: int (PK)
ders_id: int (FK → lessons.id)
ogrenci_id: int (FK → users.id)
soru_encrypted: Text  # XOR+base64 (question text)
ai_cevap_encrypted: Text (nullable)  # XOR+base64 (AI answer)
anladi_mi: bool (nullable)  # None=pending, True=understood, False=didn't understand
ai_tahmin: bool (default=False)  # True if AI-predicted, False if user-submitted
timestamp: datetime
```

### Notification (Bildirim)
```python
id: int (PK)
hoca_id: int (FK → users.id)
konu_encrypted: str  # XOR+base64 (lesson topic)
yuzde: int  # "didn't understand" percentage
goruldu: bool (default=False)  # read status
timestamp: datetime
```

### StudentTeacher / OgrenciHoca (Many-to-Many bridge)
```python
id: int (PK)
ogrenci_id: int (FK → users.id)
hoca_id: int (FK → users.id)
olusturma_tarihi: datetime  # created_at
```

---

## 🔔 Notification System

- **Trigger:** "Didn't understand" rate ≥ 15% among answered questions (`anladi_mi != None`) for a lesson, with at least 3 answered questions
- **Update:** If a notification already exists for the same lesson, the percentage and timestamp are updated; `goruldu` is reset to False
- **Privacy:** Teacher only sees aggregate statistics — individual student responses are never shown
- **Ordering:** Ascending by timestamp (oldest alert first)
- **Mark as read:** `PATCH /api/notifications/{id}/read`

---

## 🤖 AI Integration

| Field | Detail |
|-------|--------|
| Provider | OpenRouter (`https://openrouter.ai/api/v1/chat/completions`) |
| Default model | `openai/gpt-oss-20b:free` (overridable via `MODEL` env variable) |
| Student questions | Answered in context of lesson topic + content; markdown is stripped from responses |
| Teacher AI chat | Free-form chat with a personalized system prompt including teacher name and role |
| AI prediction | Infers "understood?" from question text (`ai_tahmin: true`) |
| Error handling | Language-specific messages for 401, timeout, quota, and generic errors |
| Multilingual | System prompts available in TR, EN, ZH, KO, JA, PT, RU, FR, TK |

---

## 🌐 Multilingual Support

Supported languages: Turkish (`tr`), Turkmen (`tk`), English (`en`), Chinese (`zh`), Korean (`ko`), Japanese (`ja`), Portuguese (`pt`), Russian (`ru`), French (`fr`)

- **Frontend:** Svelte store-based i18n; auto-detects browser language; preference saved in localStorage
- **Backend:** Error messages and AI system prompts selected based on the user's `dil` field
- **Language switching:** `POST /api/user/dil`

---

## 📡 API Endpoint Catalogue

### Auth — `/api/auth`
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/login` | Log in → returns JWT | — |
| POST | `/register` | Register new account | — |
| POST | `/reset-password` | Reset password using recovery code | — |
| GET | `/check-username/{username}` | Real-time username availability check | — |

### Teacher — `/api`
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lessons` | List teacher's lessons (with question/didn't-understand stats) |
| POST | `/lessons` | Create a new lesson |
| PUT | `/lessons/{id}` | Update a lesson |
| DELETE | `/lessons/{id}` | Delete a lesson |
| GET | `/notifications` | List notifications |
| PATCH | `/notifications/{id}/read` | Mark notification as read |
| GET | `/teacher/stats` | Overview stats + teacher invite code |
| GET | `/teacher/students` | Student list (with question & didn't-understand counts) |
| DELETE | `/teacher/students/{ogr_id}` | Remove a student |
| POST | `/teacher/ai` | Teacher AI chat |

### Student — `/api/students`
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/teachers` | List linked teachers |
| POST | `/students/add-teacher` | Add a teacher by invite code |
| DELETE | `/students/teacher/{hoca_id}` | Remove a linked teacher |
| GET | `/students/lessons/{hoca_id}` | View a teacher's lessons |
| POST | `/students/ask` | Ask a question to AI |
| POST | `/students/anladi` | Submit Understood / Didn't Understand |
| GET | `/students/history/{ders_id}` | Question history for a lesson |

### General
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System and AI status check |
| POST | `/api/user/dil` | Update user UI language |

---

## 📦 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Svelte + Vite | Svelte 5, Vite 6 |
| Backend | FastAPI + Pydantic v2 | FastAPI 0.115.6 |
| ORM | SQLAlchemy | 2.0.36 |
| Database | PostgreSQL | 15 (Alpine) |
| AI | OpenRouter API | — |
| Auth | JWT (python-jose) + bcrypt | — |
| HTTP client | httpx | 0.28.1 |
| Server | nginx (frontend) + uvicorn (backend) | — |
| Containers | Docker + Docker Compose | — |

---

## 🎨 UI / UX Design Principles

- Apple-inspired minimal and modern aesthetic
- Smooth animations and transitions
- Frameless layout with generous whitespace
- Large typography, clean visual hierarchy
- Single-page application (SPA) — no routing; views managed via reactive state
- Components: `Login`, `Register`, `TeacherDashboard`, `StudentDashboard`, `LanguageSelector`

---

## 🗄️ Database & Environment

**Tables:** `users`, `dersler` (lessons), `sorular` (questions), `bildirimler` (notifications), `ogrenci_hocalar` (student-teacher links)

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key |
| `MASTER_KEY` | ✅ | PII encryption key (SHA-256 → XOR) |
| `API_KEY` / `OPENROUTER_API_KEY` | ✅ | OpenRouter API key |
| `MODEL` | ❌ | AI model (default: `openai/gpt-oss-20b:free`) |
| `DATABASE_URL` | ❌ | PostgreSQL connection URL (default: `postgresql://postgres:postgres@db:5432/aitech`) |
| `CORS_ORIGINS` | ❌ | Comma-separated list of allowed origins |
| `CORS_ALLOW_ALL` | ❌ | Set to `true` to allow all origins |
