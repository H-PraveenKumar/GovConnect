"""
Test script to verify all imports work correctly
"""
import sys
import traceback

def test_imports():
    """Test all critical imports"""
    print("Testing imports...")
    
    try:
        # Test basic imports
        print("✓ Testing basic imports...")
        import fastapi
        import uvicorn
        import pydantic
        import pydantic_settings
        print("  ✓ Basic packages imported successfully")
        
        # Test MongoDB imports
        print("✓ Testing MongoDB imports...")
        import motor
        import pymongo
        from bson import ObjectId
        print("  ✓ MongoDB packages imported successfully")
        
        # Test PDF processing imports
        print("✓ Testing PDF processing imports...")
        import fitz  # PyMuPDF
        import pdfminer
        print("  ✓ PDF processing packages imported successfully")
        
        # Test HTTP client imports
        print("✓ Testing HTTP client imports...")
        import httpx
        print("  ✓ HTTP client packages imported successfully")
        
        # Test app imports
        print("✓ Testing app imports...")
        from app.config import settings
        print("  ✓ Config imported successfully")
        
        from app.models.scheme import Scheme, SchemeRule, EligibilityRule
        print("  ✓ Scheme models imported successfully")
        
        from app.models.user import UserProfile, EligibilityResult
        print("  ✓ User models imported successfully")
        
        from app.services.mongo_service import mongo_service
        print("  ✓ MongoDB service imported successfully")
        
        from app.services.llm_service import llm_service
        print("  ✓ LLM service imported successfully")
        
        print("\n🎉 All imports successful! The app should work correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
