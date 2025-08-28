"""
Main FastAPI application for the Government Schemes Eligibility System
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .routes import schemes_router, eligibility_router, upload_router
from .services.mongo_service import mongo_service
from .services.llm_service import llm_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Government Schemes Eligibility System...")
    
    try:
        # Connect to MongoDB
        await mongo_service.connect()
        logger.info("MongoDB connection established")
        
        # Test LLM service connection
        llm_health = await llm_service.test_connection()
        if llm_health["success"]:
            logger.info("LLM service connection established")
        else:
            logger.warning(f"LLM service connection issue: {llm_health.get('error', 'Unknown error')}")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Government Schemes Eligibility System...")
    
    try:
        # Close MongoDB connection
        await mongo_service.close()
        logger.info("MongoDB connection closed")
        
        # Close LLM service connection
        await llm_service.close()
        logger.info("LLM service connection closed")
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Application shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="""
    A comprehensive system to automatically determine eligibility for government schemes 
    by extracting rules from PDFs and matching user profiles.
    
    ## Features
    
    * **PDF Processing**: Upload and process government scheme PDFs
    * **Rule Extraction**: Use AI to extract eligibility criteria from PDFs
    * **Eligibility Checking**: Check user eligibility against all schemes
    * **Real-time Results**: Get instant eligibility results with detailed explanations
    
    ## API Endpoints
    
    * **Schemes**: Manage government schemes and their rules
    * **Eligibility**: Check user eligibility for schemes
    * **Upload**: Upload and process new scheme PDFs
    
    ## Getting Started
    
    1. Upload government scheme PDFs using the upload endpoints
    2. Wait for AI processing to extract eligibility rules
    3. Use eligibility endpoints to check user eligibility
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schemes_router, prefix=settings.api_prefix)
app.include_router(eligibility_router, prefix=settings.api_prefix)
app.include_router(upload_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Welcome to Government Schemes Eligibility System",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """System health check endpoint"""
    try:
        # Check MongoDB health
        mongo_healthy = await mongo_service.health_check()
        
        # Check LLM service health
        llm_healthy = await llm_service.test_connection()
        
        health_status = {
            "status": "healthy" if mongo_healthy and llm_healthy["success"] else "unhealthy",
            "timestamp": "2024-01-15T10:30:00Z",  # This should be dynamic
            "services": {
                "mongodb": {
                    "status": "healthy" if mongo_healthy else "unhealthy",
                    "message": "MongoDB connection is working" if mongo_healthy else "MongoDB connection failed"
                },
                "llm_service": {
                    "status": "healthy" if llm_healthy["success"] else "unhealthy",
                    "message": llm_healthy.get("message", "LLM service is working") if llm_healthy["success"] else llm_healthy.get("error", "LLM service failed")
                }
            }
        }
        
        if health_status["status"] == "healthy":
            return health_status
        else:
            return JSONResponse(
                content=health_status,
                status_code=503
            )
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-15T10:30:00Z"
            },
            status_code=503
        )


@app.get("/info", tags=["info"])
async def system_info():
    """Get system information and configuration"""
    return {
        "system_name": settings.app_name,
        "version": "1.0.0",
        "debug_mode": settings.debug,
        "api_prefix": settings.api_prefix,
        "max_file_size": f"{settings.max_file_size / (1024*1024):.1f} MB",
        "allowed_extensions": settings.get_allowed_extensions_list(),
        "llm_model": settings.openrouter_model,
        "mongodb_database": settings.mongodb_db_name
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "status_code": 500,
            "path": request.url.path
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
