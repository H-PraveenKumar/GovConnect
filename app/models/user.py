"""
Pydantic models for user profiles and eligibility requests
"""
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


def get_current_utc_time():
    """Get current UTC time for default values"""
    return datetime.now(timezone.utc)


class UserProfile(BaseModel):
    """User profile information for eligibility checking"""
    age: int = Field(..., ge=0, le=150, description="User's age")
    gender: str = Field(..., description="User's gender")
    occupation: str = Field(..., description="User's occupation")
    is_student: bool = Field(False, description="Whether user is a student")
    income: Optional[float] = Field(None, ge=0, description="Annual household income")
    caste: Optional[str] = Field(None, description="User's caste category")
    state: Optional[str] = Field(None, description="User's state of residence")
    district: Optional[str] = Field(None, description="User's district")
    is_farmer: Optional[bool] = Field(None, description="Whether user is a farmer")
    land_size_acres: Optional[float] = Field(None, ge=0, description="Land size in acres")
    education_level: Optional[str] = Field(None, description="Highest education level")
    disability: Optional[bool] = Field(None, description="Whether user has disability")
    family_size: Optional[int] = Field(None, ge=1, description="Family size")
    bank_account: Optional[bool] = Field(None, description="Whether user has bank account")
    aadhaar: Optional[bool] = Field(None, description="Whether user has Aadhaar")
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
        if v.lower() not in valid_genders:
            raise ValueError(f'Gender must be one of: {valid_genders}')
        return v.lower()
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        if v:
            # Add validation for Indian state codes if needed
            return v.upper()
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 25,
                "gender": "female",
                "occupation": "student",
                "is_student": True,
                "income": 50000,
                "caste": "OBC",
                "state": "KA",
                "district": "Bangalore",
                "education_level": "bachelor",
                "family_size": 4,
                "bank_account": True,
                "aadhaar": True
            }
        }
    )


class EligibilityRequest(BaseModel):
    """Request to check eligibility for schemes"""
    user_profile: UserProfile = Field(..., description="User's profile information")
    scheme_ids: Optional[List[str]] = Field(None, description="Specific schemes to check (if None, check all)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_profile": {
                    "age": 25,
                    "gender": "female",
                    "occupation": "student",
                    "is_student": True,
                    "income": 50000,
                    "caste": "OBC",
                    "state": "KA"
                },
                "scheme_ids": ["pm_kisan", "pm_fellowship"]
            }
        }
    )


class EligibilityResult(BaseModel):
    """Result of eligibility check for a single scheme"""
    scheme_id: str = Field(..., description="Scheme identifier")
    scheme_name: str = Field(..., description="Scheme name")
    is_eligible: bool = Field(..., description="Whether user is eligible")
    reasons: List[str] = Field(default_factory=list, description="Reasons for eligibility/ineligibility")
    required_documents: List[str] = Field(default_factory=list, description="Documents needed for application")
    benefit_outline: Optional[str] = Field(None, description="Summary of benefits")
    next_steps: Optional[str] = Field(None, description="Application process")
    score: Optional[float] = Field(None, ge=0, le=100, description="Eligibility score (0-100)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scheme_id": "pm_kisan",
                "scheme_name": "PM-KISAN Scheme",
                "is_eligible": True,
                "reasons": ["Age requirement met", "Farmer status confirmed"],
                "required_documents": ["aadhaar", "land_record"],
                "benefit_outline": "₹6000 annual income support",
                "next_steps": "Apply via PM-KISAN portal",
                "score": 95.0
            }
        }
    )


class EligibilityResponse(BaseModel):
    """Complete eligibility response for a user"""
    user_id: Optional[str] = Field(None, description="User identifier")
    total_schemes_checked: int = Field(..., description="Total number of schemes checked")
    eligible_schemes: int = Field(..., description="Number of eligible schemes")
    results: List[EligibilityResult] = Field(..., description="Detailed results for each scheme")
    checked_at: datetime = Field(default_factory=get_current_utc_time)
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process request")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_schemes_checked": 5,
                "eligible_schemes": 3,
                "results": [
                    {
                        "scheme_id": "pm_kisan",
                        "scheme_name": "PM-KISAN Scheme",
                        "is_eligible": True,
                        "reasons": ["Age requirement met", "Farmer status confirmed"],
                        "required_documents": ["aadhaar", "land_record"],
                        "benefit_outline": "₹6000 annual income support",
                        "next_steps": "Apply via PM-KISAN portal",
                        "score": 95.0
                    }
                ],
                "checked_at": "2024-01-15T10:30:00Z",
                "processing_time_ms": 1250.5
            }
        }
    )
