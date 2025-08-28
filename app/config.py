"""
Configuration settings for the Government Schemes Eligibility System
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db_name: str = Field(default="schemes_db", env="MONGODB_DB_NAME")
    
    # OpenRouter API Configuration
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", 
        env="OPENROUTER_BASE_URL"
    )
    openrouter_model: str = Field(
        default="anthropic/claude-3.5-sonnet", 
        env="OPENROUTER_MODEL"
    )
    
    # Application Configuration
    app_name: str = Field(default="Government Schemes Eligibility System", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # File Upload Configuration
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_extensions: str = Field(default="pdf", env="ALLOWED_EXTENSIONS")
    
    # API Configuration
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080", 
        env="CORS_ORIGINS"
    )
    
    # Security
    secret_key: str = Field(default="your_secret_key_here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # LLM Prompt Template
    llm_prompt_template: str = Field(
        default="""You are an AI assistant helping to simplify government schemes.

I will provide the text of a government scheme. 
Your task is to extract and output the **eligibility criteria** in a clean JSON format.

The JSON must follow this structure:

{
  "scheme_id": "<unique_name_generated_from_title>",
  "scheme_name": "<full official name of the scheme>",
  "eligibility": {
    "all": [
      {"attribute": "<field_name>", "op": "<operator>", "value": <expected_value>, "reason_if_fail": "<explanation>"}
    ],
    "any": [],
    "disqualifiers": [
      {"attribute": "<field_name>", "op": "<operator>", "value": <value>, "reason": "<why disqualified>"}
    ]
  },
  "required_inputs": ["age", "gender", "occupation", "is_student", "income", "caste", "state"],
  "required_documents": ["aadhaar", "income_certificate"],
  "benefit_outline": "<short summary of benefits>",
  "next_steps": "<application process or link>"
}

Operators you may use: ==, !=, >, >=, <, <=, truthy, falsy, in, not_in, between.

Only output JSON. Do not include explanations.

Here is the scheme text to analyze:

{scheme_text}""",
        env="LLM_PROMPT_TEMPLATE"
    )
    
    def get_allowed_extensions_list(self) -> List[str]:
        """Get allowed extensions as a list"""
        if ',' in self.allowed_extensions:
            return [ext.strip() for ext in self.allowed_extensions.split(',')]
        return [self.allowed_extensions.strip()]
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if ',' in self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(',')]
        return [self.cors_origins.strip()]
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Create global settings instance
settings = Settings()

# Validate required settings
if not settings.openrouter_api_key or settings.openrouter_api_key == "your_openrouter_api_key_here":
    raise ValueError(
        "OPENROUTER_API_KEY must be set in environment variables or .env file"
    )
