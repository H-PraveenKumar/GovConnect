import re
import logging
from typing import Optional, Dict, List, Any
from app.models import RulesJSON, EligibilityRules, EligibilityCondition

logger = logging.getLogger(__name__)


class NLPRuleExtractor:
    """Simple NLP-based rule extraction as fallback when AI service fails"""
    
    @staticmethod
    def extract_rules_nlp(pdf_text: str, scheme_id: str = "extracted_scheme") -> Optional[Dict[str, Any]]:
        """Extract basic rules using NLP patterns and regex"""
        try:
            # Clean and normalize text
            text = pdf_text.lower().strip()
            
            # Extract scheme name (look for title patterns)
            scheme_name = NLPRuleExtractor._extract_scheme_name(pdf_text)
            if not scheme_name:
                scheme_name = scheme_id.replace("_", " ").title()
            
            # Extract eligibility conditions
            all_conditions = []
            any_conditions = []
            disqualifiers = []
            
            # Age patterns
            age_conditions = NLPRuleExtractor._extract_age_conditions(text)
            all_conditions.extend(age_conditions)
            
            # Income patterns
            income_conditions = NLPRuleExtractor._extract_income_conditions(text)
            all_conditions.extend(income_conditions)
            
            # Caste/Category patterns
            caste_conditions = NLPRuleExtractor._extract_caste_conditions(text)
            if caste_conditions:
                any_conditions.extend(caste_conditions)
            
            # Gender patterns
            gender_conditions = NLPRuleExtractor._extract_gender_conditions(text)
            if gender_conditions:
                any_conditions.extend(gender_conditions)
            
            # Occupation patterns
            occupation_conditions = NLPRuleExtractor._extract_occupation_conditions(text)
            if occupation_conditions:
                any_conditions.extend(occupation_conditions)
            
            # Extract documents
            required_documents = NLPRuleExtractor._extract_documents(text)
            
            # Extract benefits
            benefit_outline = NLPRuleExtractor._extract_benefits(pdf_text)
            
            # Create rules JSON
            rules_json = {
                "scheme_id": scheme_id,
                "scheme_name": scheme_name,
                "eligibility": {
                    "all": [cond.dict() for cond in all_conditions],
                    "any": [cond.dict() for cond in any_conditions],
                    "disqualifiers": [cond.dict() for cond in disqualifiers]
                },
                "required_inputs": ["age", "gender", "occupation", "income", "caste", "state"],
                "required_documents": required_documents,
                "benefit_outline": benefit_outline,
                "next_steps": "Apply through official government portal or nearest office"
            }
            
            logger.info(f"NLP extraction completed for scheme: {scheme_id}")
            return rules_json
            
        except Exception as e:
            logger.error(f"NLP rule extraction failed: {e}")
            return None
    
    @staticmethod
    def _extract_scheme_name(text: str) -> str:
        """Extract scheme name from document"""
        # Look for title patterns
        lines = text.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Skip common headers
                if not any(skip in line.lower() for skip in ['page', 'government', 'ministry', 'department']):
                    if any(word in line.lower() for word in ['scheme', 'yojana', 'mission', 'program']):
                        return line
        return ""
    
    @staticmethod
    def _extract_age_conditions(text: str) -> List[EligibilityCondition]:
        """Extract age-related conditions"""
        conditions = []
        
        # Pattern: "age between X and Y"
        age_between = re.findall(r'age.*?between.*?(\d+).*?(\d+)', text)
        for match in age_between:
            min_age, max_age = int(match[0]), int(match[1])
            conditions.append(EligibilityCondition(
                attribute="age",
                op="between",
                value={"min": min_age, "max": max_age},
                reason_if_fail=f"Age must be between {min_age} and {max_age}"
            ))
        
        # Pattern: "minimum age X" or "age above X"
        min_age_patterns = re.findall(r'(?:minimum age|age above|age.*?(\d+).*?year)', text)
        for match in min_age_patterns:
            if isinstance(match, tuple):
                age = int(match[0]) if match[0].isdigit() else None
            else:
                age = int(match) if match.isdigit() else None
            
            if age and 15 <= age <= 70:  # Reasonable age range
                conditions.append(EligibilityCondition(
                    attribute="age",
                    op=">=",
                    value=age,
                    reason_if_fail=f"Must be {age} years or older"
                ))
        
        return conditions
    
    @staticmethod
    def _extract_income_conditions(text: str) -> List[EligibilityCondition]:
        """Extract income-related conditions"""
        conditions = []
        
        # Pattern: income limits in rupees
        income_patterns = re.findall(r'income.*?(?:rs\.?|rupees?).*?(\d+(?:,\d+)*)', text)
        for match in income_patterns:
            income = int(match.replace(',', ''))
            if income > 1000:  # Reasonable income threshold
                conditions.append(EligibilityCondition(
                    attribute="income",
                    op="<=",
                    value=income,
                    reason_if_fail=f"Annual income must not exceed Rs. {income:,}"
                ))
        
        # Pattern: "below poverty line" or "bpl"
        if re.search(r'below poverty line|bpl', text):
            conditions.append(EligibilityCondition(
                attribute="income",
                op="<=",
                value=50000,
                reason_if_fail="Must be below poverty line"
            ))
        
        return conditions
    
    @staticmethod
    def _extract_caste_conditions(text: str) -> List[EligibilityCondition]:
        """Extract caste/category conditions"""
        conditions = []
        
        categories = []
        if re.search(r'\bsc\b|scheduled caste', text):
            categories.append("SC")
        if re.search(r'\bst\b|scheduled tribe', text):
            categories.append("ST")
        if re.search(r'\bobc\b|other backward', text):
            categories.append("OBC")
        if re.search(r'general|unreserved', text):
            categories.append("General")
        
        if categories:
            conditions.append(EligibilityCondition(
                attribute="caste",
                op="in",
                value=categories,
                reason_if_fail=f"Must belong to {', '.join(categories)} category"
            ))
        
        return conditions
    
    @staticmethod
    def _extract_gender_conditions(text: str) -> List[EligibilityCondition]:
        """Extract gender-specific conditions"""
        conditions = []
        
        if re.search(r'women|female|girl|mahila', text):
            conditions.append(EligibilityCondition(
                attribute="gender",
                op="==",
                value="female",
                reason_if_fail="Scheme is for women only"
            ))
        
        return conditions
    
    @staticmethod
    def _extract_occupation_conditions(text: str) -> List[EligibilityCondition]:
        """Extract occupation-related conditions"""
        conditions = []
        
        occupations = []
        if re.search(r'farmer|agriculture|kisan', text):
            occupations.append("farmer")
        if re.search(r'student|education', text):
            occupations.append("student")
        if re.search(r'unemployed|job.*?seeker', text):
            occupations.append("unemployed")
        
        if occupations:
            conditions.append(EligibilityCondition(
                attribute="occupation",
                op="in",
                value=occupations,
                reason_if_fail=f"Must be {', '.join(occupations)}"
            ))
        
        return conditions
    
    @staticmethod
    def _extract_documents(text: str) -> List[str]:
        """Extract required documents"""
        documents = []
        
        doc_patterns = {
            'aadhaar': r'aadhaar|aadhar',
            'income_certificate': r'income certificate|income proof',
            'caste_certificate': r'caste certificate|category certificate',
            'bank_passbook': r'bank.*?passbook|bank.*?account',
            'photo': r'photograph|photo',
            'address_proof': r'address proof|residence proof'
        }
        
        for doc_key, pattern in doc_patterns.items():
            if re.search(pattern, text):
                documents.append(doc_key)
        
        return documents if documents else ["aadhaar_card", "application_form"]
    
    @staticmethod
    def _extract_benefits(text: str) -> str:
        """Extract benefit information"""
        # Look for monetary benefits
        money_patterns = re.findall(r'(?:rs\.?|rupees?).*?(\d+(?:,\d+)*)', text)
        if money_patterns:
            amount = money_patterns[0].replace(',', '')
            return f"Financial assistance of Rs. {amount}"
        
        # Look for benefit keywords
        if re.search(r'scholarship|education', text):
            return "Educational scholarship and support"
        elif re.search(r'loan|credit', text):
            return "Financial loan assistance"
        elif re.search(r'subsidy', text):
            return "Government subsidy support"
        else:
            return "Government scheme benefits as per guidelines"
