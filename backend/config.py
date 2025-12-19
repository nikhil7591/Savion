"""
Configuration settings for Savion Backend
"""
import os
from typing import List

# OpenAI Configuration for Guidance
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Add your OpenAI API key here

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Add your Gemini API key here

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./savion.db")

# CORS Configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")

# Whisper Model Configuration (for voice input)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")

# Optional: OpenAI API Key (if using OpenAI features)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# WebSocket Configuration
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # seconds
WEBSOCKET_MAX_CONNECTIONS_PER_USER = 5

# File Upload Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = ['.csv', '.xlsx', '.xls']

# Chat Configuration
MAX_CONVERSATION_HISTORY = 20
MAX_MESSAGE_LENGTH = 1000

# Gemini AI Configuration
GEMINI_MODEL_NAME = "gemini-1.5-flash"
GEMINI_MAX_TOKENS = 4096
GEMINI_TEMPERATURE = 0.7

def get_config():
    """Get configuration dictionary"""
    return {
        "gemini_api_key": GEMINI_API_KEY,
        "database_url": DATABASE_URL,
        "allowed_origins": ALLOWED_ORIGINS,
        "whisper_model_size": WHISPER_MODEL_SIZE,
        "openai_api_key": OPENAI_API_KEY,
        "websocket_heartbeat_interval": WEBSOCKET_HEARTBEAT_INTERVAL,
        "websocket_max_connections_per_user": WEBSOCKET_MAX_CONNECTIONS_PER_USER,
        "max_file_size": MAX_FILE_SIZE,
        "allowed_file_types": ALLOWED_FILE_TYPES,
        "max_conversation_history": MAX_CONVERSATION_HISTORY,
        "max_message_length": MAX_MESSAGE_LENGTH,
        "gemini_model_name": GEMINI_MODEL_NAME,
        "gemini_max_tokens": GEMINI_MAX_TOKENS,
        "gemini_temperature": GEMINI_TEMPERATURE,
    }
