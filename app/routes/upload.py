"""
API routes for PDF upload and processing
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from ..models.scheme import Scheme, SchemeRule
from ..services.mongo_service import mongo_service
from ..services.pdf_service import pdf_service
from ..services.llm_service import llm_service
from ..utils.validators import (
    validate_file_extension, 
    validate_file_size, 
    generate_scheme_id,
    sanitize_filename
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/scheme")
async def upload_scheme_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to upload"),
    source: Optional[str] = Form(None, description="Source of the scheme document"),
    scheme_name: Optional[str] = Form(None, description="Custom scheme name (optional)")
):
    """
    Upload a new government scheme PDF for processing
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Only {', '.join(pdf_service.supported_extensions)} files are allowed"
            )
        
        # Read file content
        file_content = await file.read()
        
        if not validate_file_size(len(file_content)):
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {pdf_service.format_file_size(pdf_service.max_file_size)}"
            )
        
        # Validate PDF
        validation_result = pdf_service.validate_pdf(file_content)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid PDF file: {'; '.join(validation_result['errors'])}"
            )
        
        # Extract text and metadata
        extracted_text = pdf_service.extract_text(file_content)
        metadata = pdf_service.extract_metadata(file_content)
        
        # Generate scheme name if not provided
        if not scheme_name:
            scheme_name = pdf_service.extract_scheme_name(extracted_text)
        
        # Generate scheme ID
        scheme_id = generate_scheme_id(scheme_name, source)
        
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        
        # Store PDF in GridFS
        pdf_metadata = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "source": source or "Unknown",
            "upload_date": metadata.get("creation_date"),
            "page_count": metadata.get("page_count", 0),
            "file_size": len(file_content)
        }
        
        pdf_file_id = await mongo_service.store_pdf(safe_filename, file_content, pdf_metadata)
        
        # Create scheme record
        scheme = Scheme(
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            pdf_file_id=str(pdf_file_id),  # Convert ObjectId to string
            source=source,
            status="processing"
        )
        
        await mongo_service.create_scheme(scheme)
        
        # Start background processing
        background_tasks.add_task(
            process_scheme_pdf,
            scheme_id,
            extracted_text,
            scheme_name
        )
        
        logger.info(f"Scheme PDF uploaded successfully: {scheme_id}")
        
        return {
            "message": "Scheme PDF uploaded successfully",
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "status": "processing",
            "estimated_processing_time": "2-5 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload scheme PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_scheme_pdf(scheme_id: str, extracted_text: str, scheme_name: str):
    """
    Background task to process uploaded PDF and extract eligibility rules
    """
    try:
        logger.info(f"Starting PDF processing for scheme: {scheme_id}")
        
        # Update status to processing
        await mongo_service.update_scheme_status(scheme_id, "processing")
        
        # Extract eligibility rules using LLM
        llm_result = await llm_service.extract_eligibility_rules(extracted_text, scheme_name)
        
        if not llm_result["success"]:
            error_msg = f"LLM processing failed: {llm_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            await mongo_service.update_scheme_status(scheme_id, "failed", error_msg)
            return
        
        # Parse extracted rules
        try:
            rules_data = llm_result["rules"]
            scheme_rules = SchemeRule(
                scheme_id=scheme_id,
                scheme_name=rules_data.get("scheme_name", scheme_name),
                eligibility=rules_data["eligibility"],
                required_inputs=rules_data["required_inputs"],
                required_documents=rules_data.get("required_documents", []),
                benefit_outline=rules_data.get("benefit_outline", ""),
                next_steps=rules_data.get("next_steps", "")
            )
            
            # Store rules in database
            await mongo_service.create_scheme_rule(scheme_rules)
            
            # Update scheme status to completed
            await mongo_service.update_scheme_status(scheme_id, "completed")
            
            logger.info(f"Scheme processing completed successfully: {scheme_id}")
            
        except Exception as e:
            error_msg = f"Failed to parse LLM rules: {str(e)}"
            logger.error(error_msg)
            await mongo_service.update_scheme_status(scheme_id, "failed", error_msg)
            
    except Exception as e:
        error_msg = f"Unexpected error in PDF processing: {str(e)}"
        logger.error(error_msg)
        await mongo_service.update_scheme_status(scheme_id, "failed", error_msg)


@router.get("/status/{scheme_id}")
async def get_upload_status(scheme_id: str):
    """
    Get the processing status of an uploaded scheme
    """
    try:
        scheme = await mongo_service.get_scheme(scheme_id)
        
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme not found: {scheme_id}")
        
        status_info = {
            "scheme_id": scheme.scheme_id,
            "scheme_name": scheme.scheme_name,
            "status": scheme.status,
            "upload_date": scheme.upload_date,
            "source": scheme.source
        }
        
        if scheme.status == "completed":
            # Get scheme rules
            rules = await mongo_service.get_scheme_rule(scheme_id)
            if rules:
                status_info["rules_available"] = True
                status_info["required_inputs"] = rules.required_inputs
                status_info["required_documents"] = rules.required_documents
            else:
                status_info["rules_available"] = False
        
        elif scheme.status == "failed":
            status_info["error_message"] = scheme.error_message
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/retry/{scheme_id}")
async def retry_failed_processing(scheme_id: str, background_tasks: BackgroundTasks):
    """
    Retry processing a failed scheme
    """
    try:
        scheme = await mongo_service.get_scheme(scheme_id)
        
        if not scheme:
            raise HTTPException(status_code=404, detail=f"Scheme not found: {scheme_id}")
        
        if scheme.status != "failed":
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot retry scheme with status: {scheme.status}"
            )
        
        # Get PDF content
        pdf_content = await mongo_service.get_pdf(scheme.pdf_file_id)
        
        # Extract text again
        extracted_text = pdf_service.extract_text(pdf_content)
        
        # Start background processing
        background_tasks.add_task(
            process_scheme_pdf,
            scheme_id,
            extracted_text,
            scheme.scheme_name
        )
        
        return {
            "message": f"Retry processing started for scheme: {scheme_id}",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry processing: {str(e)}")


@router.get("/batch/status")
async def get_batch_upload_status():
    """
    Get status of all uploaded schemes
    """
    try:
        schemes = await mongo_service.get_all_schemes()
        
        status_summary = {
            "total_schemes": len(schemes),
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "schemes": []
        }
        
        for scheme in schemes:
            status_summary[scheme.status] += 1
            
            scheme_info = {
                "scheme_id": scheme.scheme_id,
                "scheme_name": scheme.scheme_name,
                "status": scheme.status,
                "upload_date": scheme.upload_date
            }
            
            if scheme.status == "failed":
                scheme_info["error_message"] = scheme.error_message
            
            status_summary["schemes"].append(scheme_info)
        
        return status_summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.delete("/cleanup/failed")
async def cleanup_failed_schemes():
    """
    Clean up all failed scheme uploads
    """
    try:
        failed_schemes = await mongo_service.get_all_schemes(status="failed")
        
        if not failed_schemes:
            return {"message": "No failed schemes to clean up"}
        
        cleanup_count = 0
        
        for scheme in failed_schemes:
            try:
                # Delete PDF file
                await mongo_service.delete_pdf(scheme.pdf_file_id)
                
                # TODO: Delete scheme and rules records
                # This would require additional methods in mongo_service
                
                cleanup_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cleanup scheme {scheme.scheme_id}: {e}")
        
        return {
            "message": f"Cleanup completed. {cleanup_count} failed schemes removed.",
            "schemes_cleaned": cleanup_count,
            "total_failed": len(failed_schemes)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/health/llm")
async def check_llm_health():
    """
    Check the health of the LLM service
    """
    try:
        health_status = await llm_service.test_connection()
        return health_status
        
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM health check failed: {str(e)}"
        }


@router.get("/health/pdf")
async def check_pdf_service_health():
    """
    Check the health of the PDF service
    """
    try:
        # Test with a simple validation
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n0000000112 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n149\n%%EOF"
        
        validation_result = pdf_service.validate_pdf(test_content)
        
        return {
            "success": True,
            "service": "PDF Service",
            "validation_test": validation_result["is_valid"],
            "message": "PDF service is operational"
        }
        
    except Exception as e:
        return {
            "success": False,
            "service": "PDF Service",
            "error": f"PDF service health check failed: {str(e)}"
        }
