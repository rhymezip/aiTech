import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from api.auth import router as auth_router
from api.lessons import lessons_router
from api.ai import router as ai_router

app = FastAPI(title="AiTech API")

cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["http://localhost:5173", "http://localhost:3000"]
if os.getenv("CORS_ALLOW_ALL", "").lower() == "true":
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(lessons_router)
app.include_router(ai_router)

@app.get("/api/health")
def health():
    import os
    API_KEY = os.getenv("API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    return {"status": "ok", "ai_configured": bool(API_KEY)}

@app.on_event("startup")
def startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)