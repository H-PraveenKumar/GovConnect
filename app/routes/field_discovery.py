"""
Field Discovery API Routes
Provides endpoints to discover what user profile fields are needed
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging

from app.database import get_database
from app.field_analyzer import SchemeFieldDiscovery

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/required_fields")
async def get_required_fields() -> Dict[str, Any]:
    """
    Get all required user profile fields based on uploaded schemes
    Returns field requirements with descriptions and priorities
    """
    try:
        db = get_database()
        fields = await SchemeFieldDiscovery.get_all_required_fields(db)
        
        return {
            "success": True,
            "required_fields": fields,
            "total_fields": len(fields),
            "message": "Required fields discovered from uploaded schemes"
        }
    except Exception as e:
        logger.error(f"Error getting required fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/minimal_profile")
async def get_minimal_profile_fields() -> Dict[str, Any]:
    """
    Get the most commonly required fields for a minimal user profile
    """
    try:
        db = get_database()
        fields = await SchemeFieldDiscovery.get_minimal_profile_fields(db)
        
        return {
            "success": True,
            "minimal_fields": fields,
            "message": "Top required fields for basic eligibility checking"
        }
    except Exception as e:
        logger.error(f"Error getting minimal profile fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adaptive_questions")
async def get_adaptive_questions(partial_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get adaptive questions based on partial user profile
    Suggests what additional information to collect
    """
    try:
        db = get_database()
        questions = await SchemeFieldDiscovery.get_adaptive_questions(db, partial_profile)
        
        return {
            "success": True,
            "questions": questions,
            "total_questions": len(questions),
            "message": "Adaptive questions generated based on your profile"
        }
    except Exception as e:
        logger.error(f"Error generating adaptive questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
