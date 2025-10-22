# app/shared/config.py - Application Configuration
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    app_name: str = Field(default="Meri Dharani API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Database
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    database_name: str = Field(default="meri_dharani", env="DATABASE_NAME")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Firebase (all optional for development)
    firebase_project_id: Optional[str] = Field(default=None, env="FIREBASE_PROJECT_ID")
    firebase_private_key_id: Optional[str] = Field(default=None, env="FIREBASE_PRIVATE_KEY_ID")
    firebase_private_key: Optional[str] = Field(default=None, env="FIREBASE_PRIVATE_KEY")
    firebase_client_email: Optional[str] = Field(default=None, env="FIREBASE_CLIENT_EMAIL")
    firebase_client_id: Optional[str] = Field(default=None, env="FIREBASE_CLIENT_ID")
    
    # File Storage (optional)
    cloudinary_cloud_name: Optional[str] = Field(default=None, env="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: Optional[str] = Field(default=None, env="CLOUDINARY_API_KEY")
    cloudinary_api_secret: Optional[str] = Field(default=None, env="CLOUDINARY_API_SECRET")
    
    # Communication (optional)
    twilio_account_sid: Optional[str] = Field(default=None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, env="TWILIO_PHONE_NUMBER")
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    from_email: Optional[str] = Field(default="noreply@meridharani.com", env="FROM_EMAIL")
    
    # External APIs (optional)
    google_maps_api_key: Optional[str] = Field(default=None, env="GOOGLE_MAPS_API_KEY")
    
    # URLs
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", env="BACKEND_URL")
    
    # CORS
    allowed_origins: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"], env="ALLOWED_ORIGINS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of raising errors

# Global settings instance
settings = Settings()

# Firebase configuration dictionary (only if Firebase is configured)
def get_firebase_config():
    """Get Firebase configuration if available"""
    if not all([
        settings.firebase_project_id,
        settings.firebase_private_key_id, 
        settings.firebase_private_key,
        settings.firebase_client_email,
        settings.firebase_client_id
    ]):
        return None
    
    return {
        "type": "service_account",
        "project_id": settings.firebase_project_id,
        "private_key_id": settings.firebase_private_key_id,
        "private_key": settings.firebase_private_key.replace('\\n', '\n'),
        "client_email": settings.firebase_client_email,
        "client_id": settings.firebase_client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.firebase_client_email}"
    }

# Predefined data for the application
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal"
]

WASTE_TYPES = [
    {"id": "plastic", "name": "Plastic Waste", "icon": "♻️"},
    {"id": "organic", "name": "Organic Waste", "icon": "🍃"},
    {"id": "e_waste", "name": "Electronic Waste", "icon": "📱"},
    {"id": "paper", "name": "Paper Waste", "icon": "📄"},
    {"id": "metal", "name": "Metal Waste", "icon": "🔩"},
    {"id": "glass", "name": "Glass Waste", "icon": "🍶"},
    {"id": "textile", "name": "Textile Waste", "icon": "👕"},
    {"id": "hazardous", "name": "Hazardous Waste", "icon": "⚠️"},
    {"id": "mixed", "name": "Mixed Waste", "icon": "🗑️"}
]

URGENCY_LEVELS = [
    {"id": "low", "name": "Low", "color": "green", "response_time": "24-48 hours"},
    {"id": "medium", "name": "Medium", "color": "yellow", "response_time": "4-8 hours"},
    {"id": "high", "name": "High", "color": "orange", "response_time": "1-2 hours"},
    {"id": "critical", "name": "Critical", "color": "red", "response_time": "30 minutes"}
]