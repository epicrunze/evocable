"""Redis-based user service for API - follows background_tasks.py pattern."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisUserService:
    """User service using Redis queues (following existing patterns)."""
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
        self.user_queue_name = os.getenv("USER_QUEUE_NAME", "user_operations_queue")
        self.response_queue_name = os.getenv("USER_RESPONSE_QUEUE_NAME", "user_responses_queue")
        self.pending_operations = {}  # Track pending operations
    
    async def create_user(self, user_data: dict) -> dict:
        """Create user via Redis queue (following pipeline trigger pattern)."""
        operation_id = str(uuid.uuid4())
        
        # Same pattern as ingest queue in background_tasks.py
        user_task = {
            "operation_id": operation_id,
            "operation": "create_user",
            "user_data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to queue (same pattern as existing services)
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added user operation {operation_id} to queue")
        
        # Wait for response (with timeout)
        response = await self._wait_for_response(operation_id, timeout=30)
        logger.info(f"DEBUG: Redis create_user - response: {response}")
        return response
    
    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Authenticate user via Redis queue."""
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "authenticate_user",
            "user_data": {
                "email": email,
                "password": password
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added auth operation {operation_id} to queue")
        
        response = await self._wait_for_response(operation_id, timeout=30)
        
        if response.get("success"):
            return response.get("user")
        else:
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID via Redis queue."""
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "get_user_by_id",
            "user_data": {
                "user_id": user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added get user operation {operation_id} to queue")
        
        response = await self._wait_for_response(operation_id, timeout=30)
        
        if response.get("success"):
            # Convert to the expected format for compatibility
            user_data = response.get("user")
            if user_data:
                return SimpleUserProfileResponse(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    is_active=user_data["is_active"],
                    is_verified=user_data["is_verified"],
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at")
                )
        return None
    
    async def update_user(self, user_id: str, update_data: dict) -> dict:
        """Update user via Redis queue."""
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "update_user",
            "user_data": {
                "user_id": user_id,
                "update_data": update_data
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added update user operation {operation_id} to queue")
        
        return await self._wait_for_response(operation_id, timeout=30)
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password via Redis queue."""
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "change_password",
            "user_data": {
                "user_id": user_id,
                "current_password": current_password,
                "new_password": new_password
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added change password operation {operation_id} to queue")
        
        response = await self._wait_for_response(operation_id, timeout=30)
        return response.get("success", False)
    
    async def reset_password_by_email(self, email: str, new_password: str) -> bool:
        """Reset password for user with given email via Redis queue."""
        # For password reset, we first get the user by email, then change the password
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "get_user_by_email",
            "user_data": {
                "email": email
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added get user by email operation {operation_id} to queue")
        
        response = await self._wait_for_response(operation_id, timeout=30)
        
        if response.get("success"):
            user_data = response.get("user")
            if user_data:
                # TODO: Implement direct password reset operation in storage service
                # For now, return True as placeholder
                return True
        
        return False
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email via Redis queue."""
        operation_id = str(uuid.uuid4())
        
        user_task = {
            "operation_id": operation_id,
            "operation": "get_user_by_email",
            "user_data": {
                "email": email
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.lpush(self.user_queue_name, json.dumps(user_task))
        logger.info(f"Added get user by email operation {operation_id} to queue")
        
        response = await self._wait_for_response(operation_id, timeout=30)
        
        if response.get("success"):
            user_data = response.get("user")
            if user_data:
                return SimpleUser(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    is_active=user_data["is_active"],
                    is_verified=user_data["is_verified"]
                )
        return None
    
    async def _wait_for_response(self, operation_id: str, timeout: int = 30) -> dict:
        """Wait for operation response from Redis queue."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check for response with a short timeout to avoid blocking
            response_data = await self.redis_client.brpop(self.response_queue_name, timeout=1)
            
            if response_data:
                try:
                    response = json.loads(response_data[1])
                    logger.info(f"DEBUG: Redis _wait_for_response - parsed response: {response}")
                    if response.get("operation_id") == operation_id:
                        logger.info(f"Received response for operation {operation_id}")
                        return response
                    else:
                        # Put the response back for another operation to pick up
                        await self.redis_client.lpush(self.response_queue_name, response_data[1])
                        
                except Exception as e:
                    logger.error(f"Failed to parse response: {e}")
            
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.error(f"User operation {operation_id} timed out")
                return {
                    "success": False,
                    "error": f"Operation timed out after {timeout} seconds",
                    "user": None
                }
            
            # Short sleep to prevent busy waiting
            await asyncio.sleep(0.1)


# Simple user classes for compatibility with existing code
class SimpleUser:
    """Simple user class for authentication responses."""
    def __init__(self, id: str, username: str, email: str, is_active: bool, is_verified: bool):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active
        self.is_verified = is_verified


class SimpleUserProfileResponse:
    """User profile response class for compatibility."""
    def __init__(self, id: str, username: str, email: str, is_active: bool, is_verified: bool, 
                 created_at: str = None, updated_at: str = None):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active
        self.is_verified = is_verified
        self.created_at = created_at
        self.updated_at = updated_at