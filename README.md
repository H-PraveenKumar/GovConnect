# 🏛️ Government Schemes Eligibility System

A comprehensive system to automatically determine eligibility for government schemes by extracting rules from PDFs and matching user profiles.

## 🎯 **Project Overview**

This system consists of two main modules:
1. **PolicyPal** - PDF processing and rule extraction
2. **GovMatch** - User eligibility checking

## 🔄 **High-Level Workflow**

### 1. **PDF Storage & Processing**
- Store government scheme PDFs in MongoDB GridFS
- Extract text using PyMuPDF/pdfminer.six
- Send extracted text to OpenRouter API for rule extraction
- Store structured JSON rules in MongoDB

### 2. **User Eligibility Checking**
- User provides profile information (age, gender, occupation, etc.)
- System iterates through all scheme rules
- Returns list of eligible schemes with reasons and required documents

## 🏗️ **Project Structure**

```
schemes-eligibility-system/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── models/                 # Pydantic models
│   │   ├── __init__.py
│   │   ├── scheme.py          # Scheme and rule models
│   │   └── user.py            # User profile models
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── pdf_service.py     # PDF processing
│   │   ├── llm_service.py     # OpenRouter API integration
│   │   ├── eligibility_service.py # Eligibility checking logic
│   │   └── mongo_service.py   # Database operations
│   ├── routes/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── schemes.py         # Scheme management endpoints
│   │   ├── eligibility.py     # Eligibility checking endpoints
│   │   └── upload.py          # PDF upload endpoints
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       └── validators.py      # Input validation helpers
├── tests/                      # Test files
├── data/                       # Sample PDFs and test data
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── docker-compose.yml         # MongoDB setup
```

## 🚀 **Quick Start**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenRouter API key and MongoDB connection
   ```

3. **Start MongoDB:**
   ```bash
   docker-compose up -d
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🔑 **Key Features**

- **Automatic PDF Processing**: Extract text and convert to structured rules
- **LLM-Powered Rule Extraction**: Use OpenRouter API for intelligent rule parsing
- **Real-time Eligibility Checking**: Match user profiles against all schemes
- **MongoDB Integration**: Scalable storage for PDFs and structured data
- **RESTful API**: Clean endpoints for all operations

## 📚 **API Endpoints**

### Schemes Management
- `POST /schemes/upload` - Upload new scheme PDF
- `GET /schemes/` - List all schemes
- `GET /schemes/{scheme_id}` - Get specific scheme details

### Eligibility Checking
- `POST /eligibility/check` - Check user eligibility for all schemes
- `GET /eligibility/user/{user_id}` - Get user's eligible schemes

## 🧠 **LLM Prompt for Rule Extraction**

The system uses a carefully crafted prompt sent to OpenRouter API to extract eligibility criteria from PDF text and convert them to structured JSON format.

## 🔧 **Technologies Used**

- **FastAPI** - Modern Python web framework
- **MongoDB** - Document database with GridFS for PDF storage
- **PyMuPDF** - PDF text extraction
- **OpenRouter API** - LLM integration for rule extraction
- **Pydantic** - Data validation and serialization
- **Docker** - MongoDB containerization

## 📝 **License**

MIT License

