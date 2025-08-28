import base64
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.database import get_database, get_gridfs_bucket
from app.models import SchemeRulesDoc, RulesJSON, UserProfile, EligibleScheme, NearMiss, SchemeInfo
from app.pdf_extractor import PDFExtractor
from app.openrouter_client import OpenRouterClient
from app.rules_evaluator import RulesEvaluator
from app.nlp_extractor import NLPRuleExtractor

logger = logging.getLogger(__name__)


class SchemeService:
    """Service layer for scheme management and evaluation"""
    
    @staticmethod
    async def upload_scheme_pdf(scheme_id: str, title: str, pdf_base64: str, force: bool = False) -> Tuple[bool, str]:
        """
        Upload scheme PDF and extract rules with NLP fallback
        Returns: (success, message)
        """
        try:
            # Decode PDF
            pdf_bytes = base64.b64decode(pdf_base64)
            pdf_sha256 = PDFExtractor.compute_sha256(pdf_bytes)
            
            db = get_database()
            gridfs = get_gridfs_bucket()
            
            # Check for existing rules with same hash (idempotency)
            if not force:
                existing_rule = await db.schemes_rules.find_one({
                    "pdf_sha256": pdf_sha256,
                    "status": "ready"
                })
                if existing_rule:
                    logger.info(f"Reusing cached rules for PDF hash {pdf_sha256}")
                    if existing_rule["scheme_id"] != scheme_id:
                        await db.schemes_rules.update_one(
                            {"_id": existing_rule["_id"]},
                            {"$set": {"scheme_id": scheme_id, "scheme_name": title}}
                        )
                    return True, f"Rules already exist for this PDF (reused cached version)"
            
            # Extract text from PDF
            extracted_text, _ = PDFExtractor.extract_text(pdf_bytes)
            if not extracted_text:
                return False, "Failed to extract text from PDF"
            
            # Store PDF in GridFS
            pdf_file_id = await gridfs.upload_from_stream(
                f"{scheme_id}.pdf",
                pdf_bytes,
                metadata={
                    "scheme_id": scheme_id,
                    "title": title,
                    "uploaded_at": datetime.utcnow(),
                    "sha256": pdf_sha256
                }
            )
            
            # Try OpenRouter first, then NLP fallback
            rules_data = await OpenRouterClient.extract_rules(extracted_text)
            extraction_method = "openrouter"
            
            if not rules_data:
                logger.warning("OpenRouter extraction failed, using NLP fallback")
                rules_data = NLPRuleExtractor.extract_rules_nlp(extracted_text, scheme_id)
                extraction_method = "nlp"
                
                if not rules_data:
                    return False, "Failed to extract rules using both AI and NLP methods"
            
            # Validate rules JSON
            is_valid, validation_message = RulesEvaluator.validate_rules_json(rules_data)
            if not is_valid:
                logger.error(f"Invalid rules JSON: {validation_message}")
                await db.schemes_rules.insert_one({
                    "scheme_id": scheme_id,
                    "scheme_name": title,
                    "pdf_file_id": pdf_file_id,
                    "pdf_sha256": pdf_sha256,
                    "rules_json": {},
                    "extracted_at": datetime.utcnow(),
                    "model_id": extraction_method,
                    "status": "error",
                    "error_message": validation_message
                })
                return False, f"Invalid rules JSON: {validation_message}"
            
            # Create RulesJSON model
            rules_json = RulesJSON(**rules_data)
            
            # Store rules in database
            rules_doc = {
                "scheme_id": scheme_id,
                "scheme_name": title,
                "pdf_file_id": pdf_file_id,
                "pdf_sha256": pdf_sha256,
                "rules_json": rules_json.dict(),
                "extracted_at": datetime.utcnow(),
                "model_id": extraction_method,
                "status": "ready",
                "error_message": None
            }
            
            # Upsert rules document
            await db.schemes_rules.replace_one(
                {"scheme_id": scheme_id},
                rules_doc,
                upsert=True
            )
            
            logger.info(f"Successfully processed scheme {scheme_id} using {extraction_method}")
            return True, f"Scheme uploaded and rules extracted successfully using {extraction_method}"
            
        except Exception as e:
            logger.error(f"Error uploading scheme {scheme_id}: {e}")
            return False, f"Error processing scheme: {str(e)}"
    
    @staticmethod
    async def get_all_schemes() -> List[SchemeInfo]:
        """Get all schemes with metadata"""
        try:
            db = get_database()
            cursor = db.schemes_rules.find({})
            schemes = []
            
            async for doc in cursor:
                scheme_info = SchemeInfo(
                    scheme_id=doc["scheme_id"],
                    scheme_name=doc["scheme_name"],
                    last_updated=doc["extracted_at"],
                    has_rules=(doc["status"] == "ready")
                )
                schemes.append(scheme_info)
            
            return schemes
            
        except Exception as e:
            logger.error(f"Error fetching schemes: {e}")
            return []
    
    @staticmethod
    async def check_eligibility(profile: UserProfile) -> Tuple[List[EligibleScheme], List[NearMiss]]:
        """Check user eligibility against all schemes"""
        try:
            db = get_database()
            cursor = db.schemes_rules.find({"status": "ready"})
            
            eligible_schemes = []
            near_misses = []
            
            async for rules_doc in cursor:
                try:
                    rules_json_data = rules_doc["rules_json"]
                    rules_json = RulesJSON(**rules_json_data)
                    
                    eligible, failed_conditions, passed_conditions = RulesEvaluator.evaluate_scheme(
                        profile, rules_json.eligibility
                    )
                    
                    if eligible:
                        eligible_scheme = EligibleScheme(
                            scheme_id=rules_json.scheme_id,
                            scheme_name=rules_json.scheme_name,
                            eligible=True,
                            reasons=passed_conditions,
                            required_documents=rules_json.required_documents,
                            next_steps=rules_json.next_steps
                        )
                        eligible_schemes.append(eligible_scheme)
                    else:
                        if len(failed_conditions) <= 2:
                            near_miss = NearMiss(
                                scheme_id=rules_json.scheme_id,
                                failed_conditions=failed_conditions
                            )
                            near_misses.append(near_miss)
                
                except Exception as e:
                    logger.error(f"Error evaluating scheme {rules_doc.get('scheme_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Found {len(eligible_schemes)} eligible schemes and {len(near_misses)} near misses")
            return eligible_schemes, near_misses
            
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return [], []
    
    @staticmethod
    async def rebuild_rules(scheme_id: str) -> Tuple[bool, str]:
        """Force rebuild rules for a specific scheme"""
        try:
            db = get_database()
            gridfs = get_gridfs_bucket()
            
            rules_doc = await db.schemes_rules.find_one({"scheme_id": scheme_id})
            if not rules_doc:
                return False, "Scheme not found"
            
            pdf_file_id = rules_doc["pdf_file_id"]
            pdf_stream = await gridfs.open_download_stream(ObjectId(pdf_file_id))
            pdf_bytes = await pdf_stream.read()
            
            extracted_text, pdf_sha256 = PDFExtractor.extract_text(pdf_bytes)
            if not extracted_text:
                return False, "Failed to extract text from PDF"
            
            # Try OpenRouter first, then NLP fallback
            rules_data = await OpenRouterClient.extract_rules(extracted_text)
            extraction_method = "openrouter"
            
            if not rules_data:
                logger.warning("OpenRouter extraction failed, using NLP fallback")
                rules_data = NLPRuleExtractor.extract_rules_nlp(extracted_text, scheme_id)
                extraction_method = "nlp"
                
                if not rules_data:
                    return False, "Failed to extract rules using both AI and NLP methods"
            
            is_valid, validation_message = RulesEvaluator.validate_rules_json(rules_data)
            if not is_valid:
                await db.schemes_rules.update_one(
                    {"scheme_id": scheme_id},
                    {"$set": {
                        "status": "error",
                        "error_message": validation_message,
                        "extracted_at": datetime.utcnow()
                    }}
                )
                return False, f"Invalid rules JSON: {validation_message}"
            
            rules_json = RulesJSON(**rules_data)
            await db.schemes_rules.update_one(
                {"scheme_id": scheme_id},
                {"$set": {
                    "rules_json": rules_json.dict(),
                    "extracted_at": datetime.utcnow(),
                    "status": "ready",
                    "error_message": None,
                    "pdf_sha256": pdf_sha256,
                    "model_id": extraction_method
                }}
            )
            
            return True, f"Rules rebuilt successfully using {extraction_method}"
            
        except Exception as e:
            logger.error(f"Error rebuilding rules for {scheme_id}: {e}")
            return False, f"Error rebuilding rules: {str(e)}"
