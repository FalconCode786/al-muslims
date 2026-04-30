import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    """Application configuration"""
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production-please')
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Cache Configuration
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    
    # Application Settings
    APP_NAME = 'Almuslim'
    APP_VERSION = '1.0.0'
    DEBUG = os.getenv('FLASK_ENV', 'production') == 'development'
    TESTING = False
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    
    # Logging
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'False').lower() == 'true'