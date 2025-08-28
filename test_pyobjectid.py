"""
Test PyObjectId class specifically
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re

class TestModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id", pattern=r"^[0-9a-fA-F]{24}$")
    name: str
    
    @field_validator('id')
    @classmethod
    def validate_object_id(cls, v):
        if v is not None and not re.match(r"^[0-9a-fA-F]{24}$", v):
            raise ValueError("Invalid ObjectId format")
        return v

app = FastAPI(title="Test ObjectId")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test", response_model=TestModel)
async def test():
    return TestModel(name="test")

if __name__ == "__main__":
    print("Testing simplified ObjectId...")
    try:
        schema = app.openapi()
        print("✅ OpenAPI schema generated successfully!")
        print(f"Schema has {len(schema.get('paths', {}))} endpoints")
    except Exception as e:
        print(f"❌ OpenAPI schema generation failed: {e}")
        print(f"Error type: {type(e).__name__}")
