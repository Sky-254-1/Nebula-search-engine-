from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Text
from db.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    file_path = Column(String)
    content_type = Column(String)
    status = Column(String, default="pending")
    full_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class SearchLog(Base):
    __tablename__ = "search_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(String)
    source = Column(String)
    results_count = Column(Integer)
    timestamp = Column(DateTime, server_default=func.now())