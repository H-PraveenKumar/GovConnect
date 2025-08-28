"""
Minimal test to isolate OpenAPI schema generation issue
"""
from fastapi import FastAPI
from pydantic import BaseModel

# Simple test model
class TestModel(BaseModel):
    name: str
    value: int

# Create minimal app
app = FastAPI(title="Test App")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test", response_model=TestModel)
async def test():
    return TestModel(name="test", value=42)

if __name__ == "__main__":
    print("Testing minimal app...")
    try:
        schema = app.openapi()
        print("✅ OpenAPI schema generated successfully!")
        print(f"Schema has {len(schema.get('paths', {}))} endpoints")
    except Exception as e:
        print(f"❌ OpenAPI schema generation failed: {e}")
        print(f"Error type: {type(e).__name__}")
