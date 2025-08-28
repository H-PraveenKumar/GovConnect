#!/usr/bin/env python3
"""
Startup script for the Government Schemes Eligibility System
"""
import os
import subprocess
import sys
from pathlib import Path

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_path = Path(".env")
    if not env_path.exists():
        print("📝 Creating .env file...")
        
        env_content = """# MongoDB Configuration
MONGODB_URL=mongodb://admin:password123@localhost:27017
MONGODB_DB_NAME=schemes_db

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Application Configuration
APP_NAME=Government Schemes Eligibility System
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO

# File Upload Configuration
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=pdf

# API Configuration
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Security
SECRET_KEY=your_secret_key_here_change_this_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=30
"""
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print("✅ .env file created successfully!")
        print("⚠️  Please edit .env file and add your OpenRouter API key")
    else:
        print("✅ .env file already exists")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import motor
        import fitz
        import httpx
        print("✅ All Python dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Please install dependencies using: pip install -r requirements.txt")
        return False

def start_mongodb():
    """Start MongoDB using Docker Compose"""
    print("🐳 Starting MongoDB...")
    
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not running. Please start Docker first.")
            return False
        
        # Start MongoDB
        result = subprocess.run(['docker-compose', 'up', '-d'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ MongoDB started successfully")
            return True
        else:
            print(f"❌ Failed to start MongoDB: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Docker Compose not found. Please install Docker and Docker Compose.")
        return False

def run_tests():
    """Run basic tests"""
    print("🧪 Running basic tests...")
    
    try:
        result = subprocess.run([sys.executable, 'test_basic.py'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Tests passed successfully")
            return True
        else:
            print(f"❌ Tests failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting the application...")
    
    try:
        # Start the application
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000', 
            '--reload'
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def main():
    """Main startup function"""
    print("🏛️  Government Schemes Eligibility System")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Please run this script from the schemes-eligibility-system directory")
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Check dependencies
    if not check_dependencies():
        print("\n📦 Please install dependencies first:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Start MongoDB
    if not start_mongodb():
        print("\n⚠️  MongoDB startup failed. You can still run the application")
        print("   if MongoDB is running elsewhere.")
    
    # Run tests
    if not run_tests():
        print("\n⚠️  Some tests failed. The application may not work correctly.")
    
    print("\n🎯 System is ready!")
    print("\n📚 Next steps:")
    print("1. Edit .env file and add your OpenRouter API key")
    print("2. Visit http://localhost:8000/docs for API documentation")
    print("3. Upload PDFs using the upload endpoints")
    print("4. Check eligibility using the eligibility endpoints")
    
    # Ask if user wants to start the application
    response = input("\n🚀 Start the application now? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        start_application()
    else:
        print("\n💡 To start the application later, run:")
        print("   uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()
