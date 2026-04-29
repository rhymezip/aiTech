from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    ad_encrypted = Column(String)
    soyad_encrypted = Column(String)
    dil = Column(String, nullable=True)
    ozel_kod = Column(String, unique=True)
    hoca_kodu = Column(String, nullable=True)
    hoca_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    kendi_hoca_kodu = Column(String, unique=True, nullable=True)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)

    # Self-referential: bir öğretmenin öğrencileri
    teacher_students = relationship(
        "User",
        foreign_keys=[hoca_id],
        primaryjoin="User.hoca_id == User.id",
        back_populates="teacher",
    )
    # Self-referential: öğrencinin öğretmeni (many-to-one tarafı → remote_side zorunlu)
    teacher = relationship(
        "User",
        foreign_keys=[hoca_id],
        primaryjoin="User.hoca_id == User.id",
        back_populates="teacher_students",
        remote_side="User.id",
    )

    dersler = relationship("Ders", back_populates="hoca")
    sorular = relationship("Soru", back_populates="ogrenci")
    bildirimler = relationship("Bildirim", back_populates="hoca")
    ogrenci_hoca_baglantisi = relationship(
        "OgrenciHoca", foreign_keys="OgrenciHoca.ogrenci_id", back_populates="ogrenci"
    )
    hoca_baglantisi = relationship(
        "OgrenciHoca", foreign_keys="OgrenciHoca.hoca_id", back_populates="hoca"
    )


class Ders(Base):
    __tablename__ = "dersler"
    id = Column(Integer, primary_key=True, index=True)
    hoca_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tema_encrypted = Column(String)
    icerik_encrypted = Column(String, nullable=True)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)
    aktif = Column(Boolean, default=True)

    hoca = relationship("User", back_populates="dersler")
    sorular = relationship("Soru", back_populates="ders")


class Soru(Base):
    __tablename__ = "sorular"
    id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("dersler.id"), nullable=False)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    soru_encrypted = Column(Text)
    ai_cevap_encrypted = Column(Text, nullable=True)
    anladi_mi = Column(Boolean, nullable=True)
    ai_tahmin = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    ders = relationship("Ders", back_populates="sorular")
    ogrenci = relationship("User", back_populates="sorular")


class Bildirim(Base):
    __tablename__ = "bildirimler"
    id = Column(Integer, primary_key=True, index=True)
    hoca_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    konu_encrypted = Column(String)
    yuzde = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    goruldu = Column(Boolean, default=False)

    hoca = relationship("User", back_populates="bildirimler")


class OgrenciHoca(Base):
    __tablename__ = "ogrenci_hocalar"
    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hoca_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)

    ogrenci = relationship(
        "User", foreign_keys=[ogrenci_id], back_populates="ogrenci_hoca_baglantisi"
    )
    hoca = relationship(
        "User", foreign_keys=[hoca_id], back_populates="hoca_baglantisi"
    )
