"""
Pydantic models for schemes and eligibility rules
"""
from datetime import datetime, timezone
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


def get_current_utc_time():
    """Get current UTC time for default values"""
    return datetime.now(timezone.utc)


class EligibilityRule(BaseModel):
    """Individual eligibility rule"""
    attribute: str = Field(..., description="Field name to check")
    op: str = Field(..., description="Comparison operator")
    value: Union[str, int, float, bool, List] = Field(..., description="Expected value")
    reason_if_fail: str = Field(..., description="Explanation if rule fails")
    
    @field_validator('op')
    @classmethod
    def validate_operator(cls, v):
        valid_ops = ['==', '!=', '>', '>=', '<', '<=', 'truthy', 'falsy', 'in', 'not_in', 'between']
        if v not in valid_ops:
            raise ValueError(f'Operator must be one of: {valid_ops}')
        return v


class DisqualifierRule(BaseModel):
    """Rule that disqualifies a user"""
    attribute: str = Field(..., description="Field name to check")
    op: str = Field(..., description="Comparison operator")
    value: Union[str, int, float, bool, List] = Field(..., description="Value that disqualifies")
    reason: str = Field(..., description="Reason for disqualification")


class EligibilityCriteria(BaseModel):
    """Complete eligibility criteria for a scheme"""
    all: List[EligibilityRule] = Field(default_factory=list, description="All rules must pass")
    any: List[EligibilityRule] = Field(default_factory=list, description="At least one rule must pass")
    disqualifiers: List[DisqualifierRule] = Field(default_factory=list, description="Rules that disqualify")


class SchemeRule(BaseModel):
    """Structured scheme rules extracted from PDF"""
    scheme_id: str = Field(..., description="Unique identifier for the scheme")
    scheme_name: str = Field(..., description="Full official name of the scheme")
    eligibility: EligibilityCriteria = Field(..., description="Eligibility criteria")
    required_inputs: List[str] = Field(..., description="User profile fields needed")
    required_documents: List[str] = Field(default_factory=list, description="Documents needed for application")
    benefit_outline: str = Field(..., description="Short summary of benefits")
    next_steps: str = Field(..., description="Application process or link")
    created_at: datetime = Field(default_factory=get_current_utc_time)
    updated_at: datetime = Field(default_factory=get_current_utc_time)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scheme_id": "pm_kisan",
                "scheme_name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
                "eligibility": {
                    "all": [
                        {
                            "attribute": "is_farmer",
                            "op": "truthy",
                            "value": True,
                            "reason_if_fail": "Applicant must be a farmer"
                        },
                        {
                            "attribute": "age",
                            "op": ">=",
                            "value": 18,
                            "reason_if_fail": "Applicant must be 18 or older"
                        }
                    ],
                    "any": [],
                    "disqualifiers": [
                        {
                            "attribute": "income",
                            "op": ">",
                            "value": 1200000,
                            "reason": "Household income exceeds ₹12 lakh"
                        }
                    ]
                },
                "required_inputs": ["age", "is_farmer", "income"],
                "required_documents": ["aadhaar", "land_record"],
                "benefit_outline": "Provides ₹6000 annual income support to farmers in 3 installments.",
                "next_steps": "Apply via PM-KISAN official portal"
            }
        }
    )


class Scheme(BaseModel):
    """Scheme metadata stored in MongoDB"""
    id: Optional[str] = Field(default=None, alias="_id", pattern=r"^[0-9a-fA-F]{24}$")
    scheme_id: str = Field(..., description="Unique identifier for the scheme")
    scheme_name: str = Field(..., description="Name of the scheme")
    pdf_file_id: str = Field(..., description="GridFS file ID for the PDF", pattern=r"^[0-9a-fA-F]{24}$")
    upload_date: datetime = Field(default_factory=get_current_utc_time)
    source: Optional[str] = Field(None, description="Source of the scheme document")
    status: Literal["processing", "completed", "failed"] = Field(default="processing")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    @field_validator('id', 'pdf_file_id')
    @classmethod
    def validate_object_id(cls, v):
        if v is not None and not re.match(r"^[0-9a-fA-F]{24}$", v):
            raise ValueError("Invalid ObjectId format")
        return v
    
    model_config = ConfigDict(
        validate_by_name=True,
        json_schema_extra={
            "example": {
                "scheme_id": "pm_kisan",
                "scheme_name": "PM-KISAN Scheme",
                "pdf_file_id": "507f1f77bcf86cd799439011",
                "source": "Government Portal",
                "status": "completed"
            }
        }
    )
