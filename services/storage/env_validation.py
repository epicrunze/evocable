"""Environment variable validation utilities."""
import os
from typing import Optional


def get_required_env(var_name: str, description: str = None) -> str:
    """
    Get required environment variable or raise error with helpful message.
    
    Args:
        var_name: Name of the environment variable
        description: Optional description of what this variable is used for
    
    Returns:
        The environment variable value
        
    Raises:
        RuntimeError: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if value is None:
        error_msg = f"Required environment variable {var_name} is not set."
        if description:
            error_msg += f" This variable is used for: {description}"
        error_msg += "\nPlease check your .env file or environment configuration."
        raise RuntimeError(error_msg)
    return value


def get_optional_env(var_name: str, default: str, description: str = None) -> str:
    """
    Get optional environment variable with default value.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not set
        description: Optional description of what this variable is used for
    
    Returns:
        The environment variable value or default
    """
    value = os.getenv(var_name)
    if value is None:
        if description:
            print(f"Using default value for {var_name}: {default} ({description})")
        return default
    return value


def validate_critical_env_vars():
    """Validate that all critical environment variables are set."""
    critical_vars = [
        ("DATABASE_URL", "SQLite database connection string"),
        ("REDIS_URL", "Redis connection for inter-service communication"),
        ("SECRET_KEY", "JWT token signing key for authentication"),
    ]
    
    missing_vars = []
    for var_name, description in critical_vars:
        try:
            get_required_env(var_name, description)
        except RuntimeError:
            missing_vars.append(f"  - {var_name}: {description}")
    
    if missing_vars:
        error_msg = "Critical environment variables are missing:\n"
        error_msg += "\n".join(missing_vars)
        error_msg += "\n\nPlease ensure these are set in your .env file."
        raise RuntimeError(error_msg)