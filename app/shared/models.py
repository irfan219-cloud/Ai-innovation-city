# app/shared/models.py - User Models & Database Schemas (Pydantic v2 Compatible)
from datetime import datetime
from typing import List, Optional, Dict, Any, Annotated
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from bson import ObjectId
import re

# Custom ObjectId type for MongoDB (Pydantic v2 compatible)
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

# ===================
# LOCATION MODELS
# ===================

class LocationModel(BaseModel):
    """Location information"""
    state: str = Field(..., min_length=2, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    city: str = Field(..., min_length=2, max_length=50)
    pincode: str = Field(..., pattern=r'^\d{6}$')
    zone: Optional[str] = Field(None, max_length=50)
    area: Optional[str] = Field(None, max_length=100)
    address: str = Field(..., min_length=10, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class WorkCoverageModel(BaseModel):
    """Worker coverage area information"""
    coverageZones: List[str] = Field(default_factory=list)
    canTravelTo: List[str] = Field(default_factory=list)
    maxTravelDistance: Optional[int] = Field(10, ge=1, le=100)  # kilometers

# ===================
# USER PROFILE MODELS
# ===================

class CitizenProfileModel(BaseModel):
    """EcoWarrior (Citizen) specific profile"""
    languagePreference: str = Field(default="en", pattern=r'^(en|hi|te|ta|bn)$')
    notificationPreferences: List[str] = Field(default=["push", "sms"])
    totalReports: int = Field(default=0, ge=0)
    totalPoints: int = Field(default=0, ge=0)
    level: str = Field(default="eco_rookie")
    badges: List[str] = Field(default_factory=list)

class WorkerProfileModel(BaseModel):
    """CleanGuard (Worker) specific profile"""
    
    # Worker Classification
    workerCategory: str = Field(..., pattern=r'^(government_employee|ngo_worker|independent_worker)$')
    workerType: str = Field(..., min_length=3, max_length=50)
    
    # Professional Details
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
    joiningDate: Optional[datetime] = None
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
    workCoverage: Optional[WorkCoverageModel] = None
    
    # Performance Metrics
    totalJobsCompleted: int = Field(default=0, ge=0)
    averageRating: float = Field(default=5.0, ge=0, le=5)
    totalEarnings: float = Field(default=0.0, ge=0)
    
    # Work Status
    isActive: bool = Field(default=True)
    canStartWorking: bool = Field(default=True)
    verificationStatus: str = Field(default="auto_approved", pattern=r'^(auto_approved|pending|verified|rejected)$')

class GovernmentProfileModel(BaseModel):
    """CityMaster (Government) specific profile"""
    
    # Government Position
    designation: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=100)
    employeeCode: Optional[str] = Field(None, max_length=50)
    
    # Jurisdiction & Authority
    officeLevel: str = Field(..., pattern=r'^(state|district|municipal|zone)$')
    jurisdiction: str = Field(..., min_length=3, max_length=200)
    currentPosting: str = Field(..., min_length=2, max_length=100)
    postingDate: Optional[datetime] = None
    
    # Office Information
    officeAddress: str = Field(..., min_length=10, max_length=500)
    officeContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    secretaryName: Optional[str] = Field(None, max_length=100)
    secretaryContact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    
    # Access Control
    accessLevel: str = Field(default="limited", pattern=r'^(limited|full)$')
    budgetAuthority: Optional[int] = Field(None, ge=0)
    areaAuthority: List[str] = Field(default_factory=list)
    
    # Approval Status
    approvalStatus: str = Field(default="pending_manual_review", pattern=r'^(pending_manual_review|approved|rejected)$')
    canAccessDashboard: bool = Field(default=False)
    approvedBy: Optional[str] = None
    approvalDate: Optional[datetime] = None

# ===================
# MAIN USER MODEL
# ===================

class UserModel(BaseModel):
    """Main User model with role-based profiles"""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Basic Authentication
    email: EmailStr = Field(..., max_length=254)
    phone: str = Field(..., pattern=r'^\+91-\d{10}$')
    passwordHash: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r'^(citizen|worker|government)$')
    
    # Basic Profile
    fullName: str = Field(..., min_length=2, max_length=100)
    location: LocationModel
    
    # Role-Specific Profiles (Only one will be populated based on role)
    citizenProfile: Optional[CitizenProfileModel] = None
    workerProfile: Optional[WorkerProfileModel] = None
    governmentProfile: Optional[GovernmentProfileModel] = None
    
    # Account Status
    isActive: bool = Field(default=True)
    isVerified: bool = Field(default=False)
    emailVerified: bool = Field(default=False)
    phoneVerified: bool = Field(default=False)
    
    # Performance & Reputation
    reputation: float = Field(default=5.0, ge=0, le=5)
    totalActivities: int = Field(default=0, ge=0)
    
    # Security & Audit
    lastLogin: Optional[datetime] = None
    loginAttempts: int = Field(default=0, ge=0)
    lockedUntil: Optional[datetime] = None
    
    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    registrationIP: Optional[str] = None
    userAgent: Optional[str] = None
    referralSource: str = Field(default="web")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r'^\+91-\d{10}$', v):
            raise ValueError('Phone must be in format +91-XXXXXXXXXX')
        return v
    
    def model_dump(self, **kwargs):
        """Custom model_dump method to handle ObjectId"""
        d = super().model_dump(**kwargs)
        if "_id" in d and d["_id"]:
            d["_id"] = str(d["_id"])
        return d

# ===================
# WORKER TYPE MODEL
# ===================

class FormFieldModel(BaseModel):
    """Dynamic form field configuration"""
    field: str
    label: str
    type: str  # text, select, multiselect, number, phone, email
    placeholder: Optional[str] = None
    required: bool = True
    options: Optional[List[str]] = None
    validation: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None

class FormSectionModel(BaseModel):
    """Form section grouping"""
    title: str
    fields: str  # References to formFields key
    icon: str
    description: Optional[str] = None

class WorkerTypeModel(BaseModel):
    """Worker type configuration for dynamic forms"""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Type Information
    category: str = Field(..., pattern=r'^(government_employee|ngo_worker|independent_worker)$')
    typeId: str = Field(..., min_length=3, max_length=50)
    displayName: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    
    # Dynamic Form Configuration
    formFields: Dict[str, List[FormFieldModel]] = Field(default_factory=dict)
    formSections: List[FormSectionModel] = Field(default_factory=list)
    
    # Requirements & Benefits
    requiredFields: List[str] = Field(default_factory=list)
    availableSpecializations: List[str] = Field(default_factory=list)
    averageEarning: str = Field(..., max_length=50)
    badge: str = Field(..., max_length=100)
    priority: str = Field(default="medium", pattern=r'^(high|medium|low)$')
    trustLevel: str = Field(default="basic", pattern=r'^(verified|community|basic)$')
    
    # Status
    isActive: bool = Field(default=True)
    displayOrder: int = Field(default=1, ge=1)
    
    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class TimelineStep(BaseModel):
    step: str
    timestamp: datetime
    ai_message: str
    details: str
    mitra_response_time: Optional[float] = None

class ServiceRequest(BaseModel):
    request_id: str
    user_id: str
    description: str
    images: List[str] = []
    location: Optional[Dict] = None
    waste_type: Optional[str] = None
    priority: str = "medium"
    status: str = "submitted"
    timeline: List[TimelineStep] = []
    ai_analysis: Optional[Dict] = None
    estimated_completion: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class UserRequests(BaseModel):
    total_requests: int = 0
    active_requests: int = 0
    completed_requests: int = 0
    request_ids: List[str] = []