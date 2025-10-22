# app/auth/schemas.py - Registration Request/Response Schemas (Pydantic v2 Compatible)
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
import re

# ===================
# LOCATION SCHEMAS
# ===================

class LocationCreateSchema(BaseModel):
    """Location information for registration"""
    state: str = Field(..., min_length=2, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    city: str = Field(..., min_length=2, max_length=50)
    pincode: str = Field(..., pattern=r'^\d{6}$')
    zone: Optional[str] = Field(None, max_length=50)
    area: Optional[str] = Field(None, max_length=100)
    address: str = Field(..., min_length=10, max_length=500)

class WorkCoverageCreateSchema(BaseModel):
    """Worker coverage area for registration"""
    coverageZones: List[str] = Field(default_factory=list)
    canTravelTo: List[str] = Field(default_factory=list)
    maxTravelDistance: Optional[int] = Field(10, ge=1, le=100)

# ===================
# BASE REGISTRATION SCHEMAS
# ===================

class BaseRegistrationSchema(BaseModel):
    """Base registration fields for all users"""
    fullName: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., max_length=254)
    phone: str = Field(..., pattern=r'^\+91-\d{10}')
    password: str = Field(..., min_length=6, max_length=100)
    location: LocationCreateSchema
    termsAccepted: bool = Field(True)
    privacyAccepted: bool = Field(True)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r'^\+91-\d{10}$', v):
            raise ValueError('Phone must be in format +91-XXXXXXXXXX')
        return v
    
    @field_validator('termsAccepted', 'privacyAccepted')
    @classmethod
    def validate_agreements(cls, v):
        if not v:
            raise ValueError('Terms and privacy policy must be accepted')
        return v

# ===================
# CITIZEN REGISTRATION
# ===================

class CitizenRegistrationSchema(BaseRegistrationSchema):
    """EcoWarrior (Citizen) registration schema"""
    role: str = Field(default="citizen", pattern=r'^citizen$')
    languagePreference: str = Field(default="en", pattern=r'^(en|hi|te|ta|bn)$')
    notificationPreferences: List[str] = Field(default=["push", "sms"])

# ===================
# WORKER REGISTRATION
# ===================

class WorkerRegistrationSchema(BaseRegistrationSchema):
    """CleanGuard (Worker) registration schema"""
    role: str = Field(default="worker", pattern=r'^worker$')
    
    # Worker Classification
    workerCategory: str = Field(..., pattern=r'^(government_employee|ngo_worker|independent_worker)$')
    workerType: str = Field(..., min_length=3, max_length=50)
    
    # Professional Details (Optional - will be populated dynamically)
    employeeId: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    workingArea: Optional[str] = Field(None, max_length=200)
    shiftTiming: Optional[str] = Field("flexible", pattern=r'^(morning|evening|night|flexible)$')
    
    # Organization Information
    organizationName: str = Field(..., min_length=3, max_length=200)
    organizationAddress: Optional[str] = Field(None, max_length=500)
    organizationContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    supervisorName: Optional[str] = Field(None, max_length=100)
    supervisorContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    
    # Work Authorization
    workPermitNumber: Optional[str] = Field(None, max_length=50)
    joiningDate: Optional[str] = Field(None)  # Will be converted to datetime
    currentSalary: Optional[int] = Field(None, ge=0)
    workExperience: int = Field(0, ge=0, le=50)
    
    # Skills & Equipment
    specializations: List[str] = Field(default_factory=list)
    equipmentAccess: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    
    # Banking Details
    bankAccountNumber: str = Field(..., min_length=10, max_length=20)
    ifscCode: str = Field(..., pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$')
    accountHolderName: str = Field(..., min_length=2, max_length=100)
    
    # Work Coverage
    workCoverage: Optional[WorkCoverageCreateSchema] = None
    
    # NGO Specific Fields
    ngoName: Optional[str] = Field(None, max_length=200)
    ngoRegistrationNumber: Optional[str] = Field(None, max_length=50)
    roleInNGO: Optional[str] = Field(None, max_length=100)
    
    # Independent Worker Fields
    previousWorkType: Optional[str] = Field(None, max_length=100)
    skillAreas: Optional[List[str]] = Field(default_factory=list)
    ownEquipment: Optional[List[str]] = Field(default_factory=list)
    equipmentDetails: Optional[str] = Field(None, max_length=500)
    availableTimings: Optional[List[str]] = Field(default_factory=list)
    transportationMode: Optional[str] = Field("walking", pattern=r'^(walking|bicycle|motorcycle|auto|public_transport)$')

# ===================
# GOVERNMENT REGISTRATION
# ===================

class GovernmentRegistrationSchema(BaseRegistrationSchema):
    """CityMaster (Government) registration schema"""
    role: str = Field(default="government", pattern=r'^government$')
    
    # Use official email for government
    officialEmail: EmailStr = Field(..., max_length=254)
    personalEmail: Optional[EmailStr] = Field(None, max_length=254)
    
    # Government Position
    designation: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=100)
    employeeCode: Optional[str] = Field(None, max_length=50)
    
    # Jurisdiction & Authority
    officeLevel: str = Field(..., pattern=r'^(state|district|municipal|zone)$')
    jurisdiction: str = Field(..., min_length=3, max_length=200)
    currentPosting: str = Field(..., min_length=2, max_length=100)
    postingDate: Optional[str] = Field(None)  # Will be converted to datetime
    
    # Office Information
    officeAddress: str = Field(..., min_length=10, max_length=500)
    officeContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    secretaryName: Optional[str] = Field(None, max_length=100)
    secretaryContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')

# ===================
# DYNAMIC REGISTRATION SCHEMA
# ===================

class DynamicRegistrationSchema(BaseModel):
    """Dynamic registration schema for flexible form handling"""
    model_config = ConfigDict(extra="allow")  # Allow additional fields for dynamic forms
    
    role: str = Field(..., pattern=r'^(citizen|worker|government)$')
    workerType: Optional[str] = Field(None)  # Required only for workers
    formData: Dict[str, Any] = Field(...)  # Dynamic form data

# ===================
# VERIFICATION SCHEMAS
# ===================

class PhoneVerificationSchema(BaseModel):
    """Phone OTP verification schema"""
    phone: str = Field(..., pattern=r'^\+91-\d{10}$')
    otp: str = Field(..., min_length=4, max_length=6)

class EmailVerificationSchema(BaseModel):
    """Email verification schema"""
    token: str = Field(..., min_length=10)

class ResendOTPSchema(BaseModel):
    """Resend OTP schema"""
    phone: str = Field(..., pattern=r'^\+91-\d{10}$')

# ===================
# RESPONSE SCHEMAS
# ===================

class RegistrationResponseSchema(BaseModel):
    """Registration success response"""
    success: bool = True
    message: str
    userId: str
    userRole: str
    requiresVerification: bool = True
    verificationMethods: List[str] = ["phone", "email"]
    dashboardUrl: str

class UserProfileResponseSchema(BaseModel):
    """User profile response"""
    id: str
    fullName: str
    email: str
    phone: str
    role: str
    location: Dict[str, Any]
    isVerified: bool
    reputation: float
    createdAt: datetime
    profileData: Optional[Dict[str, Any]] = None

class WorkerTypeResponseSchema(BaseModel):
    """Worker type configuration response"""
    category: str
    typeId: str
    displayName: str
    description: str
    formFields: Dict[str, List[Dict[str, Any]]]
    formSections: List[Dict[str, Any]]
    averageEarning: str
    badge: str
    priority: str
    availableSpecializations: List[str]

class FormConfigResponseSchema(BaseModel):
    """Dynamic form configuration response"""
    role: str
    workerType: Optional[str] = None
    formFields: Dict[str, List[Dict[str, Any]]]
    formSections: List[Dict[str, Any]]
    requiredFields: List[str]
    validationRules: Dict[str, Any]

class LocationOptionsResponseSchema(BaseModel):
    """Location options for dropdowns"""
    states: List[str]
    cities: Dict[str, List[str]]
    zones: Dict[str, List[str]]
    areas: Dict[str, List[str]]

class ErrorResponseSchema(BaseModel):
    """Error response schema"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    errorCode: Optional[str] = None

# ===================
# LOGIN SCHEMAS
# ===================

class LoginSchema(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r'^(citizen|worker|government)$')
    rememberMe: bool = Field(default=False)

class LoginResponseSchema(BaseModel):
    """Login response schema"""
    success: bool = True
    message: str
    accessToken: str
    refreshToken: str
    user: UserProfileResponseSchema
    dashboardUrl: str
    expiresIn: int  # seconds

class RefreshTokenSchema(BaseModel):
    """Refresh token request"""
    refreshToken: str = Field(..., min_length=10)

# ===================
# PASSWORD SCHEMAS
# ===================

class ForgotPasswordSchema(BaseModel):
    """Forgot password request"""
    email: EmailStr = Field(..., max_length=254)

class ResetPasswordSchema(BaseModel):
    """Reset password request"""
    token: str = Field(..., min_length=10)
    newPassword: str = Field(..., min_length=6, max_length=100)
    confirmPassword: str = Field(..., min_length=6, max_length=100)
    
    @field_validator('confirmPassword')
    @classmethod
    def passwords_match(cls, v, info):
        if 'newPassword' in info.data and v != info.data['newPassword']:
            raise ValueError('Passwords do not match')
        return v

class ChangePasswordSchema(BaseModel):
    """Change password request (authenticated user)"""
    currentPassword: str = Field(..., min_length=6)
    newPassword: str = Field(..., min_length=6, max_length=100)
    confirmPassword: str = Field(..., min_length=6, max_length=100)
    
    @field_validator('confirmPassword')
    @classmethod
    def passwords_match(cls, v, info):
        if 'newPassword' in info.data and v != info.data['newPassword']:
            raise ValueError('Passwords do not match')
        return v