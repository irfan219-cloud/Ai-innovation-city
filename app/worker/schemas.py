# app/worker/schemas.py - CleanGuard Data Validation Schemas
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
import re

# ===================
# JOB MANAGEMENT SCHEMAS
# ===================

class JobAcceptanceSchema(BaseModel):
    """Schema for accepting a job"""
    job_id: str = Field(..., min_length=1, description="Unique job identifier")
    estimated_arrival_time: Optional[int] = Field(None, ge=5, le=120, description="ETA in minutes")
    special_equipment_needed: List[str] = Field(default_factory=list, description="Additional equipment required")
    notes: Optional[str] = Field(None, max_length=500, description="Worker notes about the job")

class JobRejectionSchema(BaseModel):
    """Schema for rejecting a job"""
    job_id: str = Field(..., min_length=1, description="Unique job identifier")
    reason: str = Field(..., min_length=3, max_length=200, description="Reason for rejection")
    category: str = Field(..., pattern=r'^(not_available|too_far|equipment_issue|safety_concern|other)$')
    alternative_time: Optional[datetime] = Field(None, description="When worker would be available")

class JobStatusUpdateSchema(BaseModel):
    """Schema for updating job status"""
    job_id: str = Field(..., min_length=1)
    status: str = Field(..., pattern=r'^(accepted|en_route|arrived|in_progress|completed|cancelled)$')
    location: Optional[Dict[str, float]] = Field(None, description="Current GPS coordinates")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, max_length=300)
    photos: List[str] = Field(default_factory=list, description="Photo URLs for documentation")

class JobCompletionSchema(BaseModel):
    """Schema for job completion data"""
    job_id: str = Field(..., min_length=1)
    completion_details: Dict[str, Any] = Field(..., description="Detailed completion data")
    waste_collected_kg: float = Field(..., ge=0, le=1000, description="Amount of waste collected")
    waste_types_collected: List[str] = Field(..., min_items=1, description="Types of waste collected")
    collection_duration_minutes: int = Field(..., ge=1, le=480, description="Time taken for collection")
    difficulty_rating: int = Field(..., ge=1, le=5, description="Job difficulty (1-5)")
    before_photos: List[str] = Field(..., min_items=1, description="Before photos URLs")
    after_photos: List[str] = Field(..., min_items=1, description="After photos URLs")
    recycling_facility: Optional[str] = Field(None, description="Where waste was taken")
    additional_notes: Optional[str] = Field(None, max_length=500)

# ===================
# WALLET & EARNINGS SCHEMAS
# ===================

class WithdrawalRequestSchema(BaseModel):
    """Schema for earnings withdrawal"""
    amount: float = Field(..., ge=100, le=50000, description="Withdrawal amount (min ₹100)")
    bank_account_number: str = Field(..., min_length=10, max_length=20, description="Bank account number")
    ifsc_code: str = Field(..., pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$', description="IFSC code")
    account_holder_name: str = Field(..., min_length=2, max_length=100, description="Account holder name")
    withdrawal_reason: Optional[str] = Field(None, max_length=200)
    
    @field_validator('bank_account_number')
    @classmethod
    def validate_account_number(cls, v):
        if not v.isdigit():
            raise ValueError('Bank account number must contain only digits')
        return v

class EarningsFilterSchema(BaseModel):
    """Schema for filtering earnings data"""
    start_date: Optional[datetime] = Field(None, description="Filter from date")
    end_date: Optional[datetime] = Field(None, description="Filter to date")
    transaction_type: Optional[str] = Field(None, pattern=r'^(earning|withdrawal|bonus|penalty)$')
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    limit: int = Field(default=50, ge=1, le=200, description="Number of records to return")

# ===================
# BIN COLLECTION SCHEMAS
# ===================

class BinCollectionSchema(BaseModel):
    """Schema for bin collection data"""
    bin_id: str = Field(..., min_length=1, description="Unique bin identifier")
    collection_time: datetime = Field(default_factory=datetime.utcnow)
    waste_collected_kg: float = Field(..., ge=0, le=500, description="Waste collected from bin")
    collection_duration_minutes: int = Field(..., ge=1, le=60, description="Collection time")
    bin_condition: str = Field(..., pattern=r'^(good|damaged|needs_maintenance|overflowing)$')
    waste_types: List[str] = Field(..., min_items=1, description="Types of waste in bin")
    collection_difficulty: str = Field(..., pattern=r'^(easy|medium|hard)$')
    notes: Optional[str] = Field(None, max_length=300)
    before_photo: Optional[str] = Field(None, description="Before collection photo")
    after_photo: Optional[str] = Field(None, description="After collection photo")

class BinRouteSchema(BaseModel):
    """Schema for bin collection route planning"""
    route_name: str = Field(..., min_length=3, max_length=100)
    bin_ids: List[str] = Field(..., min_items=1, max_items=20, description="Bins in route order")
    estimated_duration_hours: float = Field(..., ge=0.5, le=8, description="Estimated route completion time")
    vehicle_type: str = Field(..., pattern=r'^(walking|bicycle|auto|truck|van)$')
    start_location: Dict[str, float] = Field(..., description="Starting coordinates")
    notes: Optional[str] = Field(None, max_length=500)

# ===================
# WORKER PROFILE SCHEMAS
# ===================

class WorkerProfileUpdateSchema(BaseModel):
    """Schema for updating worker profile"""
    specializations: Optional[List[str]] = Field(None, description="Waste type specializations")
    equipment_access: Optional[List[str]] = Field(None, description="Available equipment")
    working_hours: Optional[Dict[str, str]] = Field(None, description="Preferred working hours")
    max_travel_distance: Optional[int] = Field(None, ge=1, le=50, description="Max travel distance in km")
    emergency_contact: Optional[str] = Field(None, pattern=r'^\+91-\d{10}$')
    language_preference: Optional[str] = Field(None, pattern=r'^(en|hi|te|ta|bn)$')
    notification_preferences: Optional[List[str]] = Field(None)

class WorkerAvailabilitySchema(BaseModel):
    """Schema for worker availability status"""
    is_available: bool = Field(..., description="Currently available for jobs")
    current_location: Optional[Dict[str, float]] = Field(None, description="Current GPS coordinates")
    availability_until: Optional[datetime] = Field(None, description="Available until this time")
    max_jobs_today: Optional[int] = Field(None, ge=1, le=20, description="Maximum jobs for today")
    preferred_job_types: Optional[List[str]] = Field(None, description="Preferred waste types")
    notes: Optional[str] = Field(None, max_length=200)

# ===================
# NOTIFICATION SCHEMAS
# ===================

class NotificationPreferenceSchema(BaseModel):
    """Schema for notification preferences"""
    job_alerts: bool = Field(default=True, description="Receive job notifications")
    payment_alerts: bool = Field(default=True, description="Receive payment notifications")
    system_updates: bool = Field(default=True, description="Receive system updates")
    marketing_messages: bool = Field(default=False, description="Receive promotional messages")
    notification_channels: List[str] = Field(default=["push", "sms"], description="Preferred channels")
    quiet_hours_start: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    quiet_hours_end: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')

# ===================
# PERFORMANCE & ANALYTICS SCHEMAS
# ===================

class PerformanceFilterSchema(BaseModel):
    """Schema for performance data filtering"""
    period: str = Field(default="month", pattern=r'^(day|week|month|quarter|year)$')
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    metric_type: Optional[str] = Field(None, pattern=r'^(earnings|efficiency|rating|jobs)$')
    comparison: bool = Field(default=False, description="Include comparison with previous period")

class WorkerFeedbackSchema(BaseModel):
    """Schema for worker feedback on jobs/system"""
    job_id: Optional[str] = Field(None, description="Related job ID")
    feedback_type: str = Field(..., pattern=r'^(job|system|payment|app|suggestion)$')
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    message: str = Field(..., min_length=10, max_length=1000, description="Detailed feedback")
    category: str = Field(..., pattern=r'^(compliment|complaint|suggestion|bug_report|other)$')
    priority: str = Field(default="medium", pattern=r'^(low|medium|high|urgent)$')
    attachments: List[str] = Field(default_factory=list, description="Photo/document URLs")

# ===================
# EMERGENCY & SAFETY SCHEMAS
# ===================

class EmergencyReportSchema(BaseModel):
    """Schema for emergency situation reporting"""
    emergency_type: str = Field(..., pattern=r'^(accident|injury|hazardous_material|equipment_failure|security|other)$')
    severity: str = Field(..., pattern=r'^(low|medium|high|critical)$')
    location: Dict[str, float] = Field(..., description="Emergency location coordinates")
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed description")
    immediate_action_taken: str = Field(..., min_length=5, max_length=500)
    assistance_needed: bool = Field(..., description="Requires immediate assistance")
    contact_emergency_services: bool = Field(default=False, description="Emergency services contacted")
    photos: List[str] = Field(default_factory=list, description="Evidence photos")
    witnesses: List[str] = Field(default_factory=list, description="Witness contact information")

class SafetyChecklistSchema(BaseModel):
    """Schema for safety checklist completion"""
    job_id: str = Field(..., min_length=1)
    checklist_items: Dict[str, bool] = Field(..., description="Safety checklist completion status")
    equipment_checked: List[str] = Field(..., description="Equipment verified")
    hazards_identified: List[str] = Field(default_factory=list, description="Identified safety hazards")
    safety_measures_taken: List[str] = Field(default_factory=list, description="Safety precautions implemented")
    completion_time: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, max_length=500)

# ===================
# LOCATION & ROUTING SCHEMAS
# ===================

class LocationUpdateSchema(BaseModel):
    """Schema for real-time location updates"""
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude")
    accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    activity: Optional[str] = Field(None, pattern=r'^(traveling|working|break|available)$')
    speed: Optional[float] = Field(None, ge=0, description="Speed in km/h")

class RouteOptimizationSchema(BaseModel):
    """Schema for route optimization requests"""
    start_location: Dict[str, float] = Field(..., description="Starting coordinates")
    destinations: List[Dict[str, Any]] = Field(..., min_items=1, max_items=20, description="Job/bin locations")
    vehicle_type: str = Field(..., pattern=r'^(walking|bicycle|auto|truck|van)$')
    max_duration_hours: float = Field(default=6, ge=1, le=12, description="Maximum route duration")
    priority_weights: Optional[Dict[str, float]] = Field(None, description="Priority factors for optimization")
    avoid_areas: List[Dict[str, float]] = Field(default_factory=list, description="Areas to avoid")
    preferred_order: Optional[List[str]] = Field(None, description="Preferred destination order")

# ===================
# RESPONSE SCHEMAS (API Responses)
# ===================

class JobResponseSchema(BaseModel):
    """Response schema for job operations"""
    success: bool
    message: str
    job_id: Optional[str] = None
    estimated_earnings: Optional[float] = None
    estimated_duration: Optional[int] = None
    next_action: Optional[str] = None
    timeline_updated: bool = Field(default=True)

class WalletResponseSchema(BaseModel):
    """Response schema for wallet operations"""
    success: bool
    message: str
    current_balance: Optional[float] = None
    transaction_id: Optional[str] = None
    processing_time: Optional[str] = None
    new_balance: Optional[float] = None

class PerformanceResponseSchema(BaseModel):
    """Response schema for performance data"""
    success: bool
    period: str
    total_earnings: float
    jobs_completed: int
    average_rating: float
    efficiency_score: float
    comparison_data: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)

# ===================
# VALIDATION HELPERS
# ===================

class CoordinatesValidator:
    """Helper class for coordinate validation"""
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> bool:
        """Validate GPS coordinates"""
        return -90 <= lat <= 90 and -180 <= lng <= 180
    
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates in km"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in km
        r = 6371
        
        return c * r

class WasteTypeValidator:
    """Helper class for waste type validation"""
    
    VALID_WASTE_TYPES = [
        "plastic", "organic", "e_waste", "paper", "metal", 
        "glass", "textile", "hazardous", "medical", "mixed"
    ]
    
    @staticmethod
    def validate_waste_types(waste_types: List[str]) -> bool:
        """Validate waste type list"""
        return all(wt in WasteTypeValidator.VALID_WASTE_TYPES for wt in waste_types)

class EarningsCalculator:
    """Helper class for earnings calculations"""
    
    BASE_RATES = {
        "plastic": 200,
        "organic": 150, 
        "e_waste": 400,
        "paper": 120,
        "metal": 300,
        "glass": 180,
        "textile": 160,
        "hazardous": 500,
        "medical": 600,
        "mixed": 180
    }
    
    @staticmethod
    def calculate_base_earnings(waste_type: str, weight_kg: float) -> float:
        """Calculate base earnings for waste collection"""
        base_rate = EarningsCalculator.BASE_RATES.get(waste_type, 180)
        return base_rate + (weight_kg * 10)  # ₹10 per kg bonus