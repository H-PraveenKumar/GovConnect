"""
LLM service for OpenRouter API integration
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import httpx
from datetime import datetime
import re

from ..config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for OpenRouter API integration"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.prompt_template = settings.llm_prompt_template
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),  # 60 seconds timeout
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def extract_eligibility_rules(self, scheme_text: str, scheme_name: str = "") -> Dict[str, Any]:
        """
        Extract eligibility rules from scheme text using OpenRouter API
        
        Args:
            scheme_text: Extracted text from PDF
            scheme_name: Name of the scheme (optional)
        
        Returns:
            Dict containing extracted rules or error information
        """
        try:
            # Prepare the prompt
            prompt = self.prompt_template.format(scheme_text=scheme_text)
            
            # Add scheme name context if available
            if scheme_name:
                prompt = f"Scheme Name: {scheme_name}\n\n" + prompt
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Low temperature for consistent output
                "max_tokens": 4000,  # Sufficient tokens for structured output
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            logger.info(f"Sending request to OpenRouter API with model: {self.model}")
            
            # Make the API request
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code != 200:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }
            
            # Parse the response
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response
            extracted_rules = self._extract_json_from_response(content)
            
            if extracted_rules:
                logger.info("Successfully extracted eligibility rules from LLM response")
                return {
                    "success": True,
                    "rules": extracted_rules,
                    "raw_response": content,
                    "model_used": self.model,
                    "tokens_used": response_data.get("usage", {}).get("total_tokens", 0)
                }
            else:
                logger.warning("Failed to extract valid JSON from LLM response")
                return {
                    "success": False,
                    "error": "Failed to extract valid JSON from LLM response",
                    "raw_response": content,
                    "model_used": self.model
                }
                
        except httpx.TimeoutException:
            error_msg = "OpenRouter API request timed out"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "status_code": 408
            }
            
        except httpx.RequestError as e:
            error_msg = f"OpenRouter API request failed: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "status_code": 500
            }
            
        except Exception as e:
            error_msg = f"Unexpected error in LLM service: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "status_code": 500
            }
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response content
        
        Args:
            content: Raw response content from LLM
        
        Returns:
            Parsed JSON dict or None if extraction fails
        """
        try:
            # Try to find JSON in the response
            # Look for content between ```json and ``` markers
            json_match = None
            
            # Pattern 1: ```json ... ```
            json_block_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_block_match:
                json_match = json_block_match.group(1)
            
            # Pattern 2: ``` ... ``` (without json specifier)
            if not json_match:
                block_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                if block_match:
                    json_match = block_match.group(1)
            
            # Pattern 3: Look for content that starts with { and ends with }
            if not json_match:
                brace_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if brace_match:
                    json_match = brace_match.group(1)
            
            # If we found potential JSON content, try to parse it
            if json_match:
                # Clean up the extracted content
                json_match = json_match.strip()
                
                # Try to parse as JSON
                try:
                    parsed_json = json.loads(json_match)
                    
                    # Validate the structure
                    if self._validate_rules_structure(parsed_json):
                        return parsed_json
                    else:
                        logger.warning("Extracted JSON doesn't match expected structure")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse extracted JSON: {e}")
                    return None
            
            logger.warning("No JSON content found in LLM response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from response: {e}")
            return None
    
    def _validate_rules_structure(self, rules: Dict[str, Any]) -> bool:
        """
        Validate that extracted rules have the expected structure
        
        Args:
            rules: Parsed rules dictionary
        
        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Check required top-level fields
            required_fields = ["scheme_id", "scheme_name", "eligibility", "required_inputs"]
            for field in required_fields:
                if field not in rules:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Check eligibility structure
            eligibility = rules.get("eligibility", {})
            if not isinstance(eligibility, dict):
                logger.warning("Eligibility field must be a dictionary")
                return False
            
            # Check required_inputs is a list
            if not isinstance(rules.get("required_inputs"), list):
                logger.warning("required_inputs must be a list")
                return False
            
            # Basic validation passed
            return True
            
        except Exception as e:
            logger.error(f"Error validating rules structure: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenRouter API connection"""
        try:
            # Simple test request
            test_payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, please respond with 'OK' only."
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.0
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=test_payload
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "OpenRouter API connection successful",
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {e}"
            }
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get information about available models"""
        return {
            "current_model": self.model,
            "recommended_models": [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "meta-llama/llama-3.1-8b-instruct",
                "google/gemini-pro-1.5"
            ],
            "model_features": {
                "claude-3.5-sonnet": "Excellent for structured output, good reasoning",
                "gpt-4o": "Strong reasoning, good for complex tasks",
                "llama-3.1": "Good performance, cost-effective"
            }
        }


# Global LLM service instance
llm_service = LLMService()
