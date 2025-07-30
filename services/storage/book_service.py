"""Book service layer for book management operations."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator

# Import the Book model
try:
    from main import Book, User
except ImportError:
    # For testing purposes, define minimal models
    from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    
    class User(Base):
        __tablename__ = "users"
        id = Column(String, primary_key=True)
        username = Column(String, unique=True)
        email = Column(String, unique=True)
        password_hash = Column(String)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)
    
    class Book(Base):
        __tablename__ = "books"
        id = Column(String, primary_key=True)
        title = Column(String)
        format = Column(String)
        status = Column(String)
        user_id = Column(String, ForeignKey("users.id"))
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)


class BookCreateRequest(BaseModel):
    """Request model for creating a new book."""
    title: str = Field(..., min_length=1, max_length=255, description="Book title")
    format: str = Field(..., pattern="^(pdf|epub|txt)$", description="Book format (pdf, epub, txt)")
    user_id: str = Field(..., description="User ID who owns this book")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title format."""
        if not v.strip():
            raise ValueError('Title cannot be empty or just whitespace')
        return v.strip()


class BookUpdateRequest(BaseModel):
    """Request model for updating book information."""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Book title")
    status: Optional[str] = Field(None, description="Book processing status")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title format."""
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty or just whitespace')
        return v.strip() if v else v


class BookResponse(BaseModel):
    """Response model for book data."""
    id: str
    title: str
    format: str
    status: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class BookListResponse(BaseModel):
    """Response model for book list."""
    books: List[BookResponse]
    total: int
    page: int
    per_page: int


class BookService:
    """Service class for book management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_book(self, book_data: BookCreateRequest) -> BookResponse:
        """Create a new book."""
        try:
            # Generate unique book ID
            book_id = str(uuid.uuid4())
            
            # Check if user exists
            user = self.db.query(User).filter(User.id == book_data.user_id).first()
            if not user:
                raise ValueError(f"User with ID {book_data.user_id} not found")
            
            # Create book record
            db_book = Book(
                id=book_id,
                title=book_data.title,
                format=book_data.format.lower(),
                status="pending",  # Default status
                user_id=book_data.user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(db_book)
            self.db.commit()
            self.db.refresh(db_book)
            
            return BookResponse.model_validate(db_book)
            
        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"Book with this title already exists for user")
            raise ValueError(f"Database constraint error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to create book: {str(e)}")
    
    async def get_book_by_id(self, book_id: str, user_id: str = None) -> Optional[BookResponse]:
        """Get book by ID, optionally filtered by user."""
        try:
            query = self.db.query(Book).filter(Book.id == book_id)
            
            # If user_id is provided, filter by ownership
            if user_id:
                query = query.filter(Book.user_id == user_id)
            
            book = query.first()
            if book:
                return BookResponse.model_validate(book)
            return None
            
        except Exception as e:
            raise ValueError(f"Failed to get book: {str(e)}")
    
    async def list_books(self, user_id: str = None, page: int = 1, per_page: int = 50) -> BookListResponse:
        """List books, optionally filtered by user."""
        try:
            query = self.db.query(Book)
            
            # Filter by user if specified
            if user_id:
                query = query.filter(Book.user_id == user_id)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            books = query.order_by(Book.created_at.desc()).offset(offset).limit(per_page).all()
            
            book_responses = [BookResponse.model_validate(book) for book in books]
            
            return BookListResponse(
                books=book_responses,
                total=total,
                page=page,
                per_page=per_page
            )
            
        except Exception as e:
            raise ValueError(f"Failed to list books: {str(e)}")
    
    async def update_book(self, book_id: str, book_data: BookUpdateRequest, user_id: str = None) -> Optional[BookResponse]:
        """Update book information."""
        try:
            query = self.db.query(Book).filter(Book.id == book_id)
            
            # If user_id is provided, ensure ownership
            if user_id:
                query = query.filter(Book.user_id == user_id)
            
            book = query.first()
            if not book:
                return None
            
            # Update fields if provided
            if book_data.title is not None:
                book.title = book_data.title
            if book_data.status is not None:
                book.status = book_data.status
            
            book.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(book)
            
            return BookResponse.model_validate(book)
            
        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"Book with this title already exists")
            raise ValueError(f"Database constraint error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update book: {str(e)}")
    
    async def delete_book(self, book_id: str, user_id: str = None) -> bool:
        """Delete a book."""
        try:
            query = self.db.query(Book).filter(Book.id == book_id)
            
            # If user_id is provided, ensure ownership
            if user_id:
                query = query.filter(Book.user_id == user_id)
            
            book = query.first()
            if not book:
                return False
            
            self.db.delete(book)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to delete book: {str(e)}")
    
    async def update_book_status(self, book_id: str, status: str, user_id: str = None) -> Optional[BookResponse]:
        """Update book processing status."""
        try:
            query = self.db.query(Book).filter(Book.id == book_id)
            
            # If user_id is provided, ensure ownership
            if user_id:
                query = query.filter(Book.user_id == user_id)
            
            book = query.first()
            if not book:
                return None
            
            book.status = status
            book.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(book)
            
            return BookResponse.model_validate(book)
            
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update book status: {str(e)}") 