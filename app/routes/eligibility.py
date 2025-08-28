"""
API routes for eligibility checking
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from ..models.user import (
    UserProfile, 
    EligibilityRequest, 
    EligibilityResponse,
    EligibilityResult
)
from ..services.eligibility_service import eligibility_service
from ..services.mongo_service import mongo_service
from ..utils.validators import validate_user_profile_data

router = APIRouter(prefix="/eligibility", tags=["eligibility"])


@router.post("/check", response_model=EligibilityResponse)
async def check_eligibility(request: EligibilityRequest):
    """
    Check user eligibility for government schemes
    """
    try:
        # Validate user profile data
        validation_errors = validate_user_profile_data(request.user_profile.model_dump())
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid user profile data: {'; '.join(validation_errors)}"
            )
        
        # Check eligibility
        response = await eligibility_service.check_eligibility(
            user_profile=request.user_profile,
            scheme_ids=request.scheme_ids
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check eligibility: {str(e)}"
        )


@router.post("/check/batch", response_model=List[EligibilityResult])
async def check_eligibility_batch(
    user_profile: UserProfile,
    scheme_ids: List[str]
):
    """
    Check eligibility for multiple specific schemes
    """
    try:
        # Validate user profile data
        validation_errors = validate_user_profile_data(user_profile.model_dump())
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid user profile data: {'; '.join(validation_errors)}"
            )
        
        # Check eligibility for specific schemes
        response = await eligibility_service.check_eligibility(
            user_profile=user_profile,
            scheme_ids=scheme_ids
        )
        
        return response.results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check eligibility: {str(e)}"
        )


@router.get("/summary")
async def get_eligibility_summary(
    age: int = Query(..., ge=0, le=150, description="User's age"),
    gender: str = Query(..., description="User's gender"),
    occupation: str = Query(..., description="User's occupation"),
    is_student: bool = Query(False, description="Whether user is a student"),
    income: Optional[float] = Query(None, ge=0, description="Annual household income"),
    caste: Optional[str] = Query(None, description="User's caste category"),
    state: Optional[str] = Query(None, description="User's state of residence"),
    district: Optional[str] = Query(None, description="User's district"),
    is_farmer: Optional[bool] = Query(None, description="Whether user is a farmer"),
    land_size_acres: Optional[float] = Query(None, ge=0, description="Land size in acres"),
    education_level: Optional[str] = Query(None, description="Highest education level"),
    disability: Optional[bool] = Query(None, description="Whether user has disability"),
    family_size: Optional[int] = Query(None, ge=1, description="Family size"),
    bank_account: Optional[bool] = Query(None, description="Whether user has bank account"),
    aadhaar: Optional[bool] = Query(None, description="Whether user has Aadhaar")
):
    """
    Get eligibility summary for a user profile
    """
    try:
        # Create user profile from query parameters
        user_profile = UserProfile(
            age=age,
            gender=gender,
            occupation=occupation,
            is_student=is_student,
            income=income,
            caste=caste,
            state=state,
            district=district,
            is_farmer=is_farmer,
            land_size_acres=land_size_acres,
            education_level=education_level,
            disability=disability,
            family_size=family_size,
            bank_account=bank_account,
            aadhaar=aadhaar
        )
        
        # Get eligibility summary
        summary = await eligibility_service.get_eligibility_summary(user_profile)
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate eligibility summary: {str(e)}"
        )


@router.get("/user/{user_id}/history")
async def get_user_eligibility_history(user_id: str):
    """
    Get user's eligibility check history
    """
    try:
        history = await mongo_service.get_user_eligibility_history(user_id)
        
        if not history:
            return {
                "user_id": user_id,
                "total_checks": 0,
                "history": []
            }
        
        # Group by scheme and get latest results
        scheme_results = {}
        for record in history:
            scheme_id = record["scheme_id"]
            if scheme_id not in scheme_results or record["checked_at"] > scheme_results[scheme_id]["checked_at"]:
                scheme_results[scheme_id] = record
        
        # Convert to list and sort by check date
        history_list = list(scheme_results.values())
        history_list.sort(key=lambda x: x["checked_at"], reverse=True)
        
        return {
            "user_id": user_id,
            "total_checks": len(history_list),
            "history": history_list
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve eligibility history: {str(e)}"
        )


@router.get("/user/{user_id}/eligible")
async def get_user_eligible_schemes(user_id: str):
    """
    Get schemes where user is currently eligible
    """
    try:
        # Get user profile
        user_data = await mongo_service.get_user(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
        
        user_profile = UserProfile(**user_data["profile"])
        
        # Check eligibility for all schemes
        response = await eligibility_service.check_eligibility(user_profile)
        
        # Filter only eligible schemes
        eligible_schemes = [
            result for result in response.results 
            if result.is_eligible
        ]
        
        return {
            "user_id": user_id,
            "total_eligible": len(eligible_schemes),
            "eligible_schemes": eligible_schemes,
            "checked_at": response.checked_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get eligible schemes: {str(e)}"
        )


@router.get("/scheme/{scheme_id}/requirements")
async def get_scheme_requirements(scheme_id: str):
    """
    Get detailed requirements for a specific scheme
    """
    try:
        # Get scheme rules
        rules = await mongo_service.get_scheme_rule(scheme_id)
        
        if not rules:
            raise HTTPException(status_code=404, detail=f"Scheme rules not found: {scheme_id}")
        
        # Extract requirements information
        requirements = {
            "scheme_id": rules.scheme_id,
            "scheme_name": rules.scheme_name,
            "eligibility_criteria": {
                "all_required": [
                    {
                        "attribute": rule.attribute,
                        "operator": rule.op,
                        "value": rule.value,
                        "description": rule.reason_if_fail
                    }
                    for rule in rules.eligibility.all
                ],
                "any_required": [
                    {
                        "attribute": rule.attribute,
                        "operator": rule.op,
                        "value": rule.value,
                        "description": rule.reason_if_fail
                    }
                    for rule in rules.eligibility.any
                ],
                "disqualifiers": [
                    {
                        "attribute": rule.attribute,
                        "operator": rule.op,
                        "value": rule.value,
                        "reason": rule.reason
                    }
                    for rule in rules.eligibility.disqualifiers
                ]
            },
            "required_inputs": rules.required_inputs,
            "required_documents": rules.required_documents,
            "benefit_outline": rules.benefit_outline,
            "next_steps": rules.next_steps
        }
        
        return requirements
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get scheme requirements: {str(e)}"
        )


@router.get("/compare/")
async def compare_eligibility(
    scheme_ids: List[str] = Query(..., description="List of scheme IDs to compare"),
    age: int = Query(..., ge=0, le=150, description="User's age"),
    gender: str = Query(..., description="User's gender"),
    occupation: str = Query(..., description="User's occupation"),
    is_student: bool = Query(False, description="Whether user is a student"),
    income: Optional[float] = Query(None, ge=0, description="Annual household income"),
    caste: Optional[str] = Query(None, description="User's caste category"),
    state: Optional[str] = Query(None, description="User's state of residence")
):
    """
    Compare eligibility across multiple schemes
    """
    try:
        if len(scheme_ids) < 2:
            raise HTTPException(
                status_code=400, 
                detail="At least 2 scheme IDs required for comparison"
            )
        
        if len(scheme_ids) > 10:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 10 schemes can be compared at once"
            )
        
        # Create user profile
        user_profile = UserProfile(
            age=age,
            gender=gender,
            occupation=occupation,
            is_student=is_student,
            income=income,
            caste=caste,
            state=state
        )
        
        # Check eligibility for specific schemes
        response = await eligibility_service.check_eligibility(
            user_profile=user_profile,
            scheme_ids=scheme_ids
        )
        
        # Create comparison matrix
        comparison = {
            "user_profile": {
                "age": age,
                "gender": gender,
                "occupation": occupation,
                "is_student": is_student,
                "income": income,
                "caste": caste,
                "state": state
            },
            "schemes_compared": len(scheme_ids),
            "results": response.results,
            "summary": {
                "total_eligible": response.eligible_schemes,
                "eligibility_rate": f"{(response.eligible_schemes / len(scheme_ids)) * 100:.1f}%",
                "best_match": max(response.results, key=lambda x: x.score) if response.results else None,
                "checked_at": response.checked_at
            }
        }
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to compare eligibility: {str(e)}"
        )
