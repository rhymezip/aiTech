# AiTech — AI-Powered Education Platform

A multilingual platform where teachers create lessons, students ask AI-powered questions, and comprehension feedback drives intelligent notifications.

---

## Quick Setup (Ubuntu Server)

### 1. Requirements

```bash
# Docker and Docker Compose must be installed
docker --version
docker compose version
```

### 2. Clone the repo and create `.env`

```bash
git clone <repo> aitech
cd aitech
cp .env.example .env
nano .env   # Fill in API_KEY and other values
```

### 3. Start

```bash
docker compose up -d --build
```

The app runs at `http://server-ip`. The backend API is available at `http://server-ip:8000`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key |
| `MASTER_KEY` | ✅ | PII data encryption key |
| `API_KEY` | ✅ | OpenRouter API key |
| `MODEL` | ❌ | AI model (default: `openai/gpt-oss-20b:free`) |
| `DATABASE_URL` | ❌ | PostgreSQL URL (default: `postgresql://postgres:postgres@db:5432/aitech`) |
| `CORS_ORIGINS` | ❌ | Comma-separated list of allowed origins |
| `CORS_ALLOW_ALL` | ❌ | Set to `true` to allow all origins |

> To get an OpenRouter API key: https://openrouter.ai → Sign up → Keys

---

## User Flow

**Teacher:**
1. Register → `TEACHER_CODE` appears on dashboard → Share with students
2. Create lessons (topic required, content optional)
3. Monitor the Notifications tab for lessons with 15%+ "didn't understand" rate
4. Use AI chat to analyze lesson comprehension

**Student:**
1. Register with a teacher's invite code → Automatically linked
2. Can add more teachers later, or remove existing ones
3. Select a lesson → Ask AI questions → Submit Understood / Didn't Understand
4. View question history per lesson

---

## API Endpoint Summary

### Auth — `/api/auth`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Log in → returns JWT |
| POST | `/register` | Register new account |
| POST | `/reset-password` | Reset password via recovery code |
| GET | `/check-username/{username}` | Real-time username availability check |

### Teacher — `/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lessons` | List lessons (with stats) |
| POST | `/lessons` | Create a lesson |
| PUT | `/lessons/{id}` | Update a lesson |
| DELETE | `/lessons/{id}` | Delete a lesson |
| GET | `/notifications` | List notifications |
| PATCH | `/notifications/{id}/read` | Mark notification as read |
| GET | `/teacher/stats` | Overview stats + teacher invite code |
| GET | `/teacher/students` | Student list |
| DELETE | `/teacher/students/{ogr_id}` | Remove a student |
| POST | `/teacher/ai` | AI chat |

### Student — `/api/students`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/teachers` | List linked teachers |
| POST | `/students/add-teacher` | Add teacher by invite code |
| DELETE | `/students/teacher/{hoca_id}` | Remove a teacher |
| GET | `/students/lessons/{hoca_id}` | View teacher's lessons |
| POST | `/students/ask` | Ask AI a question |
| POST | `/students/anladi` | Submit Understood / Didn't Understand |
| GET | `/students/history/{ders_id}` | Question history for a lesson |

### General

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System and AI status |
| POST | `/api/user/dil` | Update UI language |

---

## Supported Languages

🇹🇷 Turkish · 🇹🇲 Turkmen · 🇬🇧 English · 🇨🇳 Chinese · 🇰🇷 Korean · 🇯🇵 Japanese · 🇧🇷 Portuguese · 🇷🇺 Russian · 🇫🇷 French

The system auto-detects the browser language. Users can switch at any time.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Svelte 5 + Vite 6 |
| Backend | FastAPI 0.115.6 + Pydantic v2 |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| AI | OpenRouter API |
| Auth | JWT (python-jose) + bcrypt |
| Server | nginx + uvicorn |
| Containers | Docker + Docker Compose |

---

## Services (Docker)

| Service | Port | Description |
|---------|------|-------------|
| `aitech-frontend` | 80, 443 | Svelte SPA served via nginx |
| `aitech-backend` | 8000 | FastAPI running via uvicorn |
| `aitech-db` | 5432 | PostgreSQL 15 |

---

## Security Features

- Personal data (names, lesson content, questions, answers) stored encrypted in the database
- 5 failed login attempts → 5-minute account lockout
- Password reset only possible with the unique 8-character `ozel_kod` recovery code
- JWT tokens are valid for 7 days
- Teachers cannot see individual student question history — only aggregate statistics

---

## Logs & Debugging

```bash
docker compose logs backend -f     # Backend logs
docker compose logs frontend -f    # Nginx logs
docker compose ps                  # Container status
docker compose restart backend     # Restart backend
```

Health check:

```bash
curl http://localhost:8000/api/health
# {"status": "ok", "ai_configured": true}
```

---

## Project Structure

```
aiTech/
├── docker-compose.yml
├── .env
├── backend/
│   ├── main.py           # FastAPI app entry, CORS, router registration
│   ├── database.py       # SQLAlchemy engine, session, init_db
│   ├── models.py         # User, Ders, Soru, Bildirim, OgrenciHoca
│   ├── schemas.py        # Pydantic request models
│   ├── utils.py          # Encryption, JWT, code generation, bcrypt
│   ├── errors.py         # Multilingual error messages
│   ├── requirements.txt
│   ├── Dockerfile
│   └── api/
│       ├── auth.py       # Login, register, password reset, username check
│       ├── lessons.py    # Lesson CRUD, notifications, student management
│       └── ai.py         # Student Q&A, AI prediction, teacher AI chat
└── frontend/
    ├── src/
    │   ├── App.svelte
    │   ├── main.js
    │   ├── styles.css
    │   ├── components/
    │   │   ├── Login.svelte
    │   │   ├── Register.svelte
    │   │   ├── TeacherDashboard.svelte
    │   │   ├── StudentDashboard.svelte
    │   │   └── LanguageSelector.svelte
    │   └── stores/
    │       ├── auth.js
    │       ├── i18n.js
    │       └── languages/  # tr, tk, en, zh, ko, ja, pt, ru, fr
    ├── package.json
    ├── vite.config.js
    ├── svelte.config.js
    ├── nginx.conf
    └── Dockerfile
```
