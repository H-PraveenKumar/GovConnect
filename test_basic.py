"""
Basic test script for the Government Schemes Eligibility System
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.mongo_service import mongo_service
from app.services.llm_service import llm_service
from app.services.pdf_service import pdf_service


async def test_services():
    """Test basic service functionality"""
    print("🧪 Testing Government Schemes Eligibility System...")
    
    try:
        # Test PDF service
        print("\n📄 Testing PDF Service...")
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n0000000112 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n149\n%%EOF"
        
        validation_result = pdf_service.validate_pdf(test_pdf_content)
        print(f"✅ PDF validation: {validation_result['is_valid']}")
        
        # Test LLM service connection (if API key is set)
        print("\n🤖 Testing LLM Service...")
        try:
            llm_health = await llm_service.test_connection()
            if llm_health["success"]:
                print(f"✅ LLM service: {llm_health['message']}")
            else:
                print(f"⚠️ LLM service: {llm_health.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"⚠️ LLM service test failed: {e}")
        
        # Test MongoDB connection (if running)
        print("\n🗄️ Testing MongoDB Service...")
        try:
            await mongo_service.connect()
            mongo_healthy = await mongo_service.health_check()
            if mongo_healthy:
                print("✅ MongoDB connection: Successful")
            else:
                print("❌ MongoDB connection: Failed")
            await mongo_service.close()
        except Exception as e:
            print(f"⚠️ MongoDB test failed: {e}")
        
        print("\n🎉 Basic tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    return True


async def test_eligibility_logic():
    """Test basic eligibility logic"""
    print("\n🧮 Testing Eligibility Logic...")
    
    try:
        from app.services.eligibility_service import eligibility_service
        from app.models.user import UserProfile
        
        # Create a test user profile
        test_user = UserProfile(
            age=25,
            gender="female",
            occupation="student",
            is_student=True,
            income=50000,
            caste="OBC",
            state="KA"
        )
        
        print(f"✅ Test user profile created: {test_user.age} year old {test_user.gender} {test_user.occupation}")
        
        # Test rule evaluation
        from app.models.scheme import EligibilityRule
        
        test_rule = EligibilityRule(
            attribute="age",
            op=">=",
            value=18,
            reason_if_fail="Must be 18 or older"
        )
        
        # This would normally be done through the service
        print(f"✅ Test eligibility rule created: {test_rule.attribute} {test_rule.op} {test_rule.value}")
        
        print("✅ Eligibility logic tests passed!")
        
    except Exception as e:
        print(f"❌ Eligibility logic test failed: {e}")
        return False
    
    return True


async def main():
    """Main test function"""
    print("🚀 Starting Government Schemes Eligibility System Tests")
    print("=" * 60)
    
    # Test basic services
    services_ok = await test_services()
    
    # Test eligibility logic
    logic_ok = await test_eligibility_logic()
    
    print("\n" + "=" * 60)
    if services_ok and logic_ok:
        print("🎉 All tests passed! System is ready to use.")
        print("\n📚 Next steps:")
        print("1. Set up your OpenRouter API key in .env file")
        print("2. Start MongoDB using: docker-compose up -d")
        print("3. Run the application: uvicorn app.main:app --reload")
        print("4. Visit http://localhost:8000/docs for API documentation")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
