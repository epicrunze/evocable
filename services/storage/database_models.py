"""Shared database models for the storage service."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Shared Base for all models
Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to books
    books = relationship("Book", back_populates="user")


class Book(Base):
    """Book model for storing book information."""
    __tablename__ = "books"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    format = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending')
    percent_complete = Column(Float, default=0.0)
    error_message = Column(Text)
    file_path = Column(Text)
    total_chunks = Column(Integer, default=0)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = relationship("User", back_populates="books")


class AudioChunk(Base):
    """Audio chunk model for storing audio segment information."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(String, ForeignKey('books.id'), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    duration_s = Column(Float, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to book
    book = relationship("Book", back_populates="chunks")


# Add back-references
User.books = relationship("Book", back_populates="user")
Book.chunks = relationship("AudioChunk", back_populates="book")