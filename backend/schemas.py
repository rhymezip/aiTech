from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    login: str
    password: str
    ad: str
    soyad: str
    role: str
    hoca_kodu: Optional[str] = None
    dil: Optional[str] = "tr"


class DersRequest(BaseModel):
    tema: str
    icerik: Optional[str] = None


class DersUpdateRequest(BaseModel):
    tema: Optional[str] = None
    icerik: Optional[str] = None


class SoruRequest(BaseModel):
    ders_id: int
    soru: str


class AnladiRequest(BaseModel):
    soru_id: int
    anladi: bool


class AiMessageRequest(BaseModel):
    message: str
    context: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    ozel_kod: str
    new_password: str


class AddTeacherRequest(BaseModel):
    hoca_kodu: str


class LanguageRequest(BaseModel):
    dil: str