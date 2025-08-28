"""
Dynamic Field Discovery System
Analyzes scheme rules to identify what user profile fields are actually needed
"""
import logging
from typing import Dict, List, Set, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class FieldAnalyzer:
    """Analyzes scheme rules to discover required user profile fields"""
    
    @staticmethod
    def analyze_scheme_requirements(rules_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a scheme's rules to extract required user profile fields
        Returns field requirements with metadata
        """
        required_fields = {}
        field_usage = defaultdict(list)
        
        # Analyze eligibility conditions
        eligibility = rules_json.get('eligibility', [])
        for condition in eligibility:
            if isinstance(condition, dict):
                field_name = condition.get('attribute')
                operator = condition.get('op')
                value = condition.get('value')
                reason = condition.get('reason_if_fail', '')
                
                if field_name:
                    field_info = {
                        'field': field_name,
                        'operator': operator,
                        'value': value,
                        'reason': reason,
                        'required': True,
                        'context': 'eligibility'
                    }
                    field_usage[field_name].append(field_info)
        
        # Convert to required fields format
        for field_name, usages in field_usage.items():
            required_fields[field_name] = {
                'required': True,
                'usages': usages,
                'field_type': FieldAnalyzer._infer_field_type(field_name, usages),
                'description': FieldAnalyzer._generate_field_description(field_name, usages)
            }
        
        return required_fields
    
    @staticmethod
    def _infer_field_type(field_name: str, usages: List[Dict]) -> str:
        """Infer the data type of a field based on its usage"""
        if not usages:
            return 'unknown'
        
        # Check common field patterns
        if 'age' in field_name.lower():
            return 'integer'
        elif 'income' in field_name.lower():
            return 'integer'
        elif 'land' in field_name.lower() and 'size' in field_name.lower():
            return 'float'
        elif field_name.lower() in ['gender', 'caste', 'state', 'occupation']:
            return 'string'
        elif 'is_' in field_name.lower() or 'has_' in field_name.lower():
            return 'boolean'
        
        # Infer from operators used
        operators = [usage.get('operator') for usage in usages]
        if any(op in ['>', '>=', '<', '<=', 'between'] for op in operators):
            return 'number'
        elif any(op in ['truthy', 'falsy'] for op in operators):
            return 'boolean'
        else:
            return 'string'
    
    @staticmethod
    def _generate_field_description(field_name: str, usages: List[Dict]) -> str:
        """Generate human-readable description for a field"""
        descriptions = {
            'age': 'Your current age in years',
            'gender': 'Your gender (male/female/other)',
            'income': 'Your annual income in rupees',
            'caste': 'Your caste category (General/SC/ST/OBC)',
            'state': 'Your state of residence',
            'has_land': 'Do you own any agricultural land?',
            'land_size_acres': 'Size of your land in acres',
            'is_farmer': 'Are you engaged in farming?',
            'is_marginal_farmer': 'Are you a marginal farmer (less than 2.5 acres)?',
            'occupation': 'Your primary occupation',
            'is_student': 'Are you currently a student?',
            'is_unemployed': 'Are you currently unemployed?',
            'has_government_job': 'Do you have a government job?',
            'is_married': 'Are you married?',
            'is_widow': 'Are you a widow?',
            'is_disabled': 'Do you have any disability?',
            'is_rural': 'Do you live in a rural area?',
            'family_size': 'Number of people in your family',
            'district': 'Your district of residence'
        }
        
        if field_name in descriptions:
            return descriptions[field_name]
        
        # Generate description from usage context
        reasons = [usage.get('reason', '') for usage in usages if usage.get('reason')]
        if reasons:
            return f"Required for: {', '.join(reasons[:2])}"
        
        return f"Information about your {field_name.replace('_', ' ')}"

class SchemeFieldDiscovery:
    """Service to discover and manage required fields across all schemes"""
    
    @staticmethod
    async def get_all_required_fields(db) -> Dict[str, Any]:
        """
        Analyze all schemes to get comprehensive list of required fields
        Returns aggregated field requirements
        """
        try:
            cursor = db.schemes_rules.find({"status": "ready"})
            all_fields = {}
            field_frequency = defaultdict(int)
            
            async for scheme_doc in cursor:
                rules_json = scheme_doc.get('rules_json', {})
                scheme_fields = FieldAnalyzer.analyze_scheme_requirements(rules_json)
                
                for field_name, field_info in scheme_fields.items():
                    field_frequency[field_name] += 1
                    
                    if field_name not in all_fields:
                        all_fields[field_name] = field_info
                    else:
                        # Merge usage information
                        all_fields[field_name]['usages'].extend(field_info['usages'])
            
            # Add frequency information
            for field_name in all_fields:
                all_fields[field_name]['frequency'] = field_frequency[field_name]
                all_fields[field_name]['priority'] = 'high' if field_frequency[field_name] > 2 else 'medium'
            
            return all_fields
            
        except Exception as e:
            logger.error(f"Error analyzing scheme fields: {e}")
            return {}
    
    @staticmethod
    async def get_minimal_profile_fields(db) -> List[str]:
        """Get the most commonly required fields for a minimal user profile"""
        all_fields = await SchemeFieldDiscovery.get_all_required_fields(db)
        
        # Sort by frequency and return top fields
        sorted_fields = sorted(
            all_fields.items(),
            key=lambda x: x[1].get('frequency', 0),
            reverse=True
        )
        
        # Return top 8-10 most common fields
        return [field_name for field_name, _ in sorted_fields[:10]]
    
    @staticmethod
    async def get_adaptive_questions(db, partial_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate adaptive questions based on what schemes the user might be eligible for
        """
        try:
            all_fields = await SchemeFieldDiscovery.get_all_required_fields(db)
            questions = []
            
            # Prioritize fields not yet provided
            missing_fields = {
                field_name: field_info 
                for field_name, field_info in all_fields.items()
                if field_name not in partial_profile or partial_profile[field_name] is None
            }
            
            # Sort by priority and frequency
            sorted_missing = sorted(
                missing_fields.items(),
                key=lambda x: (
                    x[1].get('priority') == 'high',
                    x[1].get('frequency', 0)
                ),
                reverse=True
            )
            
            # Generate questions for top missing fields
            for field_name, field_info in sorted_missing[:5]:  # Top 5 questions
                question = {
                    'field': field_name,
                    'question': field_info.get('description', f'What is your {field_name}?'),
                    'type': field_info.get('field_type', 'string'),
                    'required': field_info.get('required', False),
                    'priority': field_info.get('priority', 'medium')
                }
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating adaptive questions: {e}")
            return []
