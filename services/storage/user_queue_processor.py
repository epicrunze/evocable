"""Redis queue processor for user operations - follows TTS Worker pattern."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database_models import User
from user_service import UserService
from env_validation import get_required_env

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserOperationProcessor:
    """Processes user operations via Redis queue (following existing service patterns)."""
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
        self.user_queue_name = os.getenv("USER_QUEUE_NAME", "user_operations_queue")
        self.response_queue_name = os.getenv("USER_RESPONSE_QUEUE_NAME", "user_responses_queue")
        
        # Database setup - same as main.py
        DATABASE_URL = get_required_env("DATABASE_URL", "SQLite database connection string")
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
    async def start_processing(self):
        """Start processing user operations queue (following TTS Worker pattern)."""
        logger.info("Starting user operations queue processing")
        
        while True:
            try:
                # Same pattern as TTS/transcoder services - blocking pop with timeout
                task_data = await self.redis_client.brpop(self.user_queue_name, timeout=30)
                
                if task_data:
                    queue_name, task_json = task_data
                    logger.info(f"Processing user operation: {task_json}")
                    
                    try:
                        task = json.loads(task_json)
                        operation_id = task.get("operation_id")
                        operation = task.get("operation")
                        
                        if operation_id and operation:
                            # Process the operation
                            result = await self._process_operation(task)
                            
                            # Send response (following completion pattern)
                            response_data = {
                                "operation_id": operation_id,
                                "success": result.get("success", False),
                                "user": result.get("user"),
                                "error": result.get("error"),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            
                            await self.redis_client.lpush(
                                self.response_queue_name, 
                                json.dumps(response_data)
                            )
                            
                            if result.get("success"):
                                logger.info(f"Successfully processed user operation {operation_id}")
                            else:
                                logger.error(f"Failed to process user operation {operation_id}: {result.get('error')}")
                        
                    except Exception as e:
                        logger.error(f"Error processing user operation: {e}")
                        
                        # Send error response
                        error_response = {
                            "operation_id": task.get("operation_id", "unknown"),
                            "success": False,
                            "user": None,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        await self.redis_client.lpush(
                            self.response_queue_name,
                            json.dumps(error_response)
                        )
                        
            except Exception as e:
                logger.error(f"Error in user queue processing: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_operation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a user operation and return result."""
        operation = task.get("operation")
        user_data = task.get("user_data", {})
        
        # Create database session
        db = self.SessionLocal()
        try:
            user_service = UserService(db)
            
            if operation == "create_user":
                return await self._create_user(user_service, user_data)
            elif operation == "authenticate_user":
                return await self._authenticate_user(user_service, user_data)
            elif operation == "update_user":
                return await self._update_user(user_service, user_data)
            elif operation == "change_password":
                return await self._change_password(user_service, user_data)
            elif operation == "get_user_by_id":
                return await self._get_user_by_id(user_service, user_data)
            elif operation == "get_user_by_email":
                return await self._get_user_by_email(user_service, user_data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}",
                    "user": None
                }
                
        finally:
            db.close()
    
    async def _create_user(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        try:
            from user_service import UserCreateRequest
            
            # Validate required fields
            required_fields = ["username", "email", "password"]
            for field in required_fields:
                if field not in user_data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}",
                        "user": None
                    }
            
            logger.info(f"DEBUG: Storage _create_user - user_data: {user_data}")
            
            # Create request object
            create_request = UserCreateRequest(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"]
            )
            
            logger.info(f"DEBUG: Storage _create_user - create_request: {create_request}")
            
            # Create user via service
            user_response = user_service.create_user(create_request)
            
            logger.info(f"DEBUG: Storage _create_user - user_response: {user_response}")
            
            return {
                "success": True,
                "error": None,
                "user": {
                    "id": user_response.id,
                    "username": user_response.username,
                    "email": user_response.email,
                    "is_active": user_response.is_active,
                    "is_verified": user_response.is_verified,
                    "created_at": user_response.created_at.isoformat(),
                    "updated_at": user_response.updated_at.isoformat()
                }
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "user": None
            }
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "user": None
            }
    
    async def _authenticate_user(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user."""
        try:
            email = user_data.get("email")
            password = user_data.get("password")
            
            if not email or not password:
                return {
                    "success": False,
                    "error": "Email and password are required",
                    "user": None
                }
            
            user = user_service.authenticate_user(email, password)
            
            if user:
                return {
                    "success": True,
                    "error": None,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid email or password",
                    "user": None
                }
                
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}",
                "user": None
            }
    
    async def _update_user(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information."""
        try:
            user_id = user_data.get("user_id")
            update_data = user_data.get("update_data", {})
            
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required",
                    "user": None
                }
            
            from user_service import UserUpdateRequest
            
            # Only include fields that are actually provided
            update_fields = {}
            if "username" in update_data and update_data["username"] is not None:
                update_fields["username"] = update_data["username"]
            if "email" in update_data and update_data["email"] is not None:
                update_fields["email"] = update_data["email"]
            
            update_request = UserUpdateRequest(**update_fields)
            
            user_response = user_service.update_user(user_id, update_request)
            
            return {
                "success": True,
                "error": None,
                "user": {
                    "id": user_response.id,
                    "username": user_response.username,
                    "email": user_response.email,
                    "is_active": user_response.is_active,
                    "is_verified": user_response.is_verified,
                    "created_at": user_response.created_at.isoformat(),
                    "updated_at": user_response.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return {
                "success": False,
                "error": f"Update error: {str(e)}",
                "user": None
            }
    
    async def _change_password(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Change user password."""
        try:
            user_id = user_data.get("user_id")
            current_password = user_data.get("current_password")
            new_password = user_data.get("new_password")
            
            if not all([user_id, current_password, new_password]):
                return {
                    "success": False,
                    "error": "user_id, current_password, and new_password are required",
                    "user": None
                }
            
            success = user_service.change_password(user_id, current_password, new_password)
            
            return {
                "success": success,
                "error": None if success else "Current password is incorrect",
                "user": None
            }
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return {
                "success": False,
                "error": f"Password change error: {str(e)}",
                "user": None
            }
    
    async def _get_user_by_id(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get user by ID."""
        try:
            user_id = user_data.get("user_id")
            
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required",
                    "user": None
                }
            
            user_response = user_service.get_user_by_id(user_id)
            
            if user_response:
                return {
                    "success": True,
                    "error": None,
                    "user": {
                        "id": user_response.id,
                        "username": user_response.username,
                        "email": user_response.email,
                        "is_active": user_response.is_active,
                        "is_verified": user_response.is_verified,
                        "created_at": user_response.created_at.isoformat(),
                        "updated_at": user_response.updated_at.isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "User not found",
                    "user": None
                }
                
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return {
                "success": False,
                "error": f"Get user error: {str(e)}",
                "user": None
            }
    
    async def _get_user_by_email(self, user_service: UserService, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get user by email."""
        try:
            email = user_data.get("email")
            
            if not email:
                return {
                    "success": False,
                    "error": "email is required",
                    "user": None
                }
            
            user_response = user_service.get_user_by_email(email)
            
            if user_response:
                return {
                    "success": True,
                    "error": None,
                    "user": {
                        "id": user_response.id,
                        "username": user_response.username,
                        "email": user_response.email,
                        "is_active": user_response.is_active,
                        "is_verified": user_response.is_verified
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "User not found",
                    "user": None
                }
                
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return {
                "success": False,
                "error": f"Get user error: {str(e)}",
                "user": None
            }


# Global processor instance
user_processor = UserOperationProcessor()


async def start_user_queue_processing():
    """Start the user queue processing (called from main.py)."""
    await user_processor.start_processing()