"""
Models package for the Government Schemes Eligibility System
"""

from .scheme import (
    Scheme,
    SchemeRule,
    EligibilityCriteria,
    EligibilityRule,
    DisqualifierRule
)

from .user import (
    UserProfile,
    EligibilityRequest,
    EligibilityResult,
    EligibilityResponse
)

__all__ = [
    # Scheme models
    "Scheme",
    "SchemeRule", 
    "EligibilityCriteria",
    "EligibilityRule",
    "DisqualifierRule",
    
    # User models
    "UserProfile",
    "EligibilityRequest",
    "EligibilityResult",
    "EligibilityResponse"
]
