# 🚀 Quick Start Guide

## 🎯 What This System Does

This is a **Government Schemes Eligibility System** that:

1. **Stores PDFs** of government schemes in MongoDB
2. **Extracts text** from PDFs using PyMuPDF/pdfminer
3. **Uses AI (OpenRouter API)** to convert text into structured eligibility rules
4. **Checks user eligibility** against all schemes in real-time
5. **Returns detailed results** with reasons and required documents

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
# Copy the environment template
cp env.example .env

# Edit .env and add your OpenRouter API key
# Get one from: https://openrouter.ai/
```

### 3. Start MongoDB
```bash
docker-compose up -d
```

### 4. Run the Application
```bash
uvicorn app.main:app --reload
```

### 5. Visit the API Docs
Open: http://localhost:8000/docs

## 🔄 How It Works

### Step 1: Upload a Scheme PDF
```bash
curl -X POST "http://localhost:8000/api/v1/upload/scheme" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_scheme.pdf"
```

### Step 2: AI Processes the PDF
- System extracts text from PDF
- Sends text to OpenRouter API with this prompt:
```
You are an AI assistant helping to simplify government schemes.
Extract eligibility criteria and output in JSON format with this structure:
{
  "scheme_id": "unique_name",
  "scheme_name": "official_name",
  "eligibility": {
    "all": [{"attribute": "age", "op": ">=", "value": 18}],
    "any": [],
    "disqualifiers": []
  },
  "required_inputs": ["age", "gender", "income"],
  "required_documents": ["aadhaar", "income_certificate"],
  "benefit_outline": "summary",
  "next_steps": "how to apply"
}
```

### Step 3: Check User Eligibility
```bash
curl -X POST "http://localhost:8000/api/v1/eligibility/check" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "age": 25,
      "gender": "female",
      "occupation": "student",
      "is_student": true,
      "income": 50000,
      "caste": "OBC",
      "state": "KA"
    }
  }'
```

## 📊 Example Response

```json
{
  "total_schemes_checked": 5,
  "eligible_schemes": 3,
  "results": [
    {
      "scheme_id": "pm_kisan",
      "scheme_name": "PM-KISAN Scheme",
      "is_eligible": true,
      "reasons": ["Age requirement met", "Farmer status confirmed"],
      "required_documents": ["aadhaar", "land_record"],
      "benefit_outline": "₹6000 annual income support",
      "next_steps": "Apply via PM-KISAN portal",
      "score": 95.0
    }
  ]
}
```

## 🛠️ Key Features

- **Automatic PDF Processing**: Upload PDFs and get structured rules
- **AI-Powered Extraction**: Uses Claude/GPT to understand eligibility criteria
- **Real-time Checking**: Instant eligibility results for any user profile
- **Comprehensive Coverage**: Check against all schemes at once
- **Detailed Explanations**: Why eligible/ineligible with specific reasons
- **Document Requirements**: Lists all documents needed for application

## 🔧 Configuration

### OpenRouter API Models
The system works with any model from OpenRouter:
- `anthropic/claude-3.5-sonnet` (recommended)
- `openai/gpt-4o`
- `meta-llama/llama-3.1-8b-instruct`
- `google/gemini-pro-1.5`

### Supported Operators
- **Comparison**: `==`, `!=`, `>`, `>=`, `<`, `<=`
- **Boolean**: `truthy`, `falsy`
- **Membership**: `in`, `not_in`
- **Range**: `between`

## 📁 Project Structure

```
schemes-eligibility-system/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   ├── routes/              # API endpoints
│   └── utils/               # Helper functions
├── docker-compose.yml       # MongoDB setup
├── requirements.txt         # Dependencies
└── start.py                # Startup script
```

## 🧪 Testing

Run the basic test:
```bash
python test_basic.py
```

Or use the startup script:
```bash
python start.py
```

## 🚨 Common Issues

### "OpenRouter API key not set"
- Edit `.env` file and add your API key
- Get one from: https://openrouter.ai/

### "MongoDB connection failed"
- Make sure Docker is running
- Run: `docker-compose up -d`

### "PDF processing failed"
- Check if PDF is text-based (not image-only)
- Ensure PDF is under 10MB limit

## 🔗 API Endpoints

- **`POST /api/v1/upload/scheme`** - Upload scheme PDF
- **`GET /api/v1/schemes/`** - List all schemes
- **`POST /api/v1/eligibility/check`** - Check eligibility
- **`GET /api/v1/eligibility/summary`** - Get eligibility summary
- **`GET /api/v1/schemes/{id}/rules`** - Get scheme rules

## 📚 Next Steps

1. **Upload your first scheme PDF**
2. **Wait for AI processing** (2-5 minutes)
3. **Test with different user profiles**
4. **Customize the LLM prompt** for better extraction
5. **Add more validation rules** as needed

## 🆘 Need Help?

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **System Info**: http://localhost:8000/info

---

**🎉 You're all set! Start uploading schemes and checking eligibility!**
