from db import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime


class Urls(Base):
    __tablename__ = 'urls'
    
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String(500), unique=True)
    shortened_url = Column(String(50),index=True)
    full_shortened_url = Column(String(250), index=True)
    custom_path = Column(String, unique=True)
    qr_code_path = Column(String(250), index=True)
    visit_count = Column(Integer, default=0)
    time = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    user = relationship("Users", back_populates="urls")

class Users(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(50), unique=True)
    username = Column(String(50), unique=True)
    hashed_password = Column(String(80))   
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    role = Column(String(50))
    
    urls = relationship("Urls", back_populates="user")