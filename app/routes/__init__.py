"""
API routes for the Government Schemes Eligibility System
"""

from .schemes import router as schemes_router
from .eligibility import router as eligibility_router
from .upload import router as upload_router

__all__ = [
    "schemes_router",
    "eligibility_router", 
    "upload_router"
]
