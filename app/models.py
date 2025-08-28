from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    is_student: Optional[bool] = None
    income: Optional[int] = None
    caste: Optional[str] = None
    state: Optional[str] = None
    # Land and farming related
    has_land: Optional[bool] = None
    land_size_acres: Optional[float] = None
    is_farmer: Optional[bool] = None
    is_marginal_farmer: Optional[bool] = None
    # Employment and benefits
    has_government_job: Optional[bool] = None
    is_unemployed: Optional[bool] = None
    has_bank_account: Optional[bool] = None
    # Family and social
    is_married: Optional[bool] = None
    family_size: Optional[int] = None
    is_widow: Optional[bool] = None
    is_disabled: Optional[bool] = None
    # Location specific
    is_rural: Optional[bool] = None
    district: Optional[str] = None


class EligibilityCondition(BaseModel):
    attribute: str
    op: str  # ==, !=, >, >=, <, <=, truthy, falsy, in, not_in, between
    value: Any
    reason_if_fail: Optional[str] = None
    reason: Optional[str] = None  # for disqualifiers


class EligibilityRules(BaseModel):
    all: List[EligibilityCondition] = []
    any: List[EligibilityCondition] = []
    disqualifiers: List[EligibilityCondition] = []


class RulesJSON(BaseModel):
    scheme_id: str
    scheme_name: str
    eligibility: EligibilityRules
    required_inputs: List[str] = []
    required_documents: List[str] = []
    benefit_outline: str = ""
    next_steps: str = ""


class SchemeRulesDoc(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    scheme_id: str
    scheme_name: str
    pdf_file_id: PyObjectId
    pdf_sha256: str
    rules_json: RulesJSON
    extracted_at: datetime
    model_id: str
    status: str  # ready, error
    error_message: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class EligibleScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    eligible: bool
    reasons: List[str] = []
    required_documents: List[str] = []
    next_steps: str = ""


class NearMiss(BaseModel):
    scheme_id: str
    failed_conditions: List[str] = []


class CheckResponse(BaseModel):
    eligible_schemes: List[EligibleScheme] = []
    near_misses: List[NearMiss] = []


class SchemeInfo(BaseModel):
    scheme_id: str
    scheme_name: str
    last_updated: datetime
    has_rules: bool


class UploadSchemeRequest(BaseModel):
    scheme_id: str
    title: str
    pdf_base64: Optional[str] = None


class UploadSchemeResponse(BaseModel):
    scheme_id: str
    rules_saved: bool
