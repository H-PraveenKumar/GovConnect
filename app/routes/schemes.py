"""
API routes for scheme management
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ..models.scheme import Scheme, SchemeRule
from ..services.mongo_service import mongo_service
from ..utils.validators import validate_scheme_name

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("/", response_model=List[Scheme])
async def get_schemes(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of schemes to return"),
    offset: int = Query(0, ge=0, description="Number of schemes to skip")
):
    """
    Get all schemes with optional filtering
    """
    try:
        schemes = await mongo_service.get_all_schemes(status=status)
        
        # Apply pagination
        schemes = schemes[offset:offset + limit]
        
        return schemes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve schemes: {str(e)}")


@router.get("/{scheme_id}", response_model=Scheme)
async def get_scheme(scheme_id: str):
    """
    Get a specific scheme by ID
    """
    try:
        scheme = await mongo_service.get_scheme(scheme_id)
        
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme not found: {scheme_id}")
        
        return scheme
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scheme: {str(e)}")


@router.get("/{scheme_id}/rules", response_model=SchemeRule)
async def get_scheme_rules(scheme_id: str):
    """
    Get eligibility rules for a specific scheme
    """
    try:
        rules = await mongo_service.get_scheme_rule(scheme_id)
        
        if not rules:
            raise HTTPException(status_code=404, detail=f"Scheme rules not found: {scheme_id}")
        
        return rules
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scheme rules: {str(e)}")


@router.get("/{scheme_id}/pdf")
async def download_scheme_pdf(scheme_id: str):
    """
    Download the PDF file for a specific scheme
    """
    try:
        # Get scheme to find PDF file ID
        scheme = await mongo_service.get_scheme(scheme_id)
        
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme not found: {scheme_id}")
        
        if scheme.status != "completed":
            raise HTTPException(status_code=400, detail=f"Scheme PDF not ready. Status: {scheme.status}")
        
        # Get PDF content
        pdf_content = await mongo_service.get_pdf(scheme.pdf_file_id)
        
        # Return PDF file
        return JSONResponse(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={scheme.scheme_name}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")


@router.delete("/{scheme_id}")
async def delete_scheme(scheme_id: str):
    """
    Delete a scheme and its associated files
    """
    try:
        # Get scheme to find PDF file ID
        scheme = await mongo_service.get_scheme(scheme_id)
        
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme not found: {scheme_id}")
        
        # Delete PDF file from GridFS
        pdf_deleted = await mongo_service.delete_pdf(scheme.pdf_file_id)
        
        # TODO: Delete scheme and rules from collections
        # This would require additional methods in mongo_service
        
        if pdf_deleted:
            return {"message": f"Scheme {scheme_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete scheme files")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scheme: {str(e)}")


@router.get("/stats/overview")
async def get_schemes_overview():
    """
    Get overview statistics for schemes
    """
    try:
        stats = await mongo_service.get_database_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@router.get("/search/")
async def search_schemes(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results")
):
    """
    Search schemes by name or description
    """
    try:
        # Get all schemes and filter by search query
        all_schemes = await mongo_service.get_all_schemes()
        
        # Simple text search (could be enhanced with full-text search)
        query_lower = query.lower()
        matching_schemes = []
        
        for scheme in all_schemes:
            if (query_lower in scheme.scheme_name.lower() or
                (scheme.source and query_lower in scheme.source.lower())):
                matching_schemes.append(scheme)
        
        # Apply limit
        matching_schemes = matching_schemes[:limit]
        
        return {
            "query": query,
            "total_results": len(matching_schemes),
            "schemes": matching_schemes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/categories/")
async def get_scheme_categories():
    """
    Get available scheme categories
    """
    try:
        # Get all schemes to analyze categories
        all_schemes = await mongo_service.get_all_schemes()
        
        categories = {}
        
        for scheme in all_schemes:
            # Simple categorization based on scheme name
            category = "General"
            
            scheme_name_lower = scheme.scheme_name.lower()
            
            if any(keyword in scheme_name_lower for keyword in ["farmer", "agriculture", "kisan", "land"]):
                category = "Agriculture"
            elif any(keyword in scheme_name_lower for keyword in ["student", "education", "scholarship", "fellowship"]):
                category = "Education"
            elif any(keyword in scheme_name_lower for keyword in ["income", "financial", "loan", "credit"]):
                category = "Financial"
            elif any(keyword in scheme_name_lower for keyword in ["health", "medical", "hospital", "insurance"]):
                category = "Healthcare"
            elif any(keyword in scheme_name_lower for keyword in ["women", "girl", "female"]):
                category = "Women Empowerment"
            elif any(keyword in scheme_name_lower for keyword in ["disability", "handicap", "special"]):
                category = "Disability Support"
            elif any(keyword in scheme_name_lower for keyword in ["startup", "business", "entrepreneur"]):
                category = "Business & Startup"
            
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        # Convert to list format
        category_list = [
            {"name": name, "count": count}
            for name, count in categories.items()
        ]
        
        # Sort by count
        category_list.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "categories": category_list,
            "total_schemes": len(all_schemes)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve categories: {str(e)}")
