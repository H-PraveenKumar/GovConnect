import logging
from typing import Any, Dict, List, Tuple, Union
from app.models import UserProfile, EligibilityCondition, EligibilityRules

logger = logging.getLogger(__name__)


class RulesEvaluator:
    """Evaluates user profiles against scheme eligibility rules"""
    
    SUPPORTED_OPERATORS = {
        "==", "!=", ">", ">=", "<", "<=", 
        "truthy", "falsy", "in", "not_in", "between"
    }
    
    @staticmethod
    def _coerce_value(value: Any, target_type: type = None) -> Any:
        """Coerce string values to appropriate types"""
        if isinstance(value, str) and value.isdigit():
            logger.warning(f"Coercing string '{value}' to integer")
            return int(value)
        return value
    
    @staticmethod
    def _get_profile_value(profile: UserProfile, attribute: str) -> Any:
        """Get value from user profile, handling missing attributes"""
        profile_dict = profile.dict()
        return profile_dict.get(attribute)
    
    @staticmethod
    def _evaluate_condition(profile: UserProfile, condition: EligibilityCondition) -> Tuple[bool, str]:
        """
        Evaluate a single condition against user profile
        Returns: (passed, reason_message)
        """
        attribute = condition.attribute
        op = condition.op
        expected_value = condition.value
        
        if op not in RulesEvaluator.SUPPORTED_OPERATORS:
            return False, f"Unsupported operator: {op}"
        
        profile_value = RulesEvaluator._get_profile_value(profile, attribute)
        
        # Handle missing attributes
        if profile_value is None:
            return False, f"missing: {attribute}"
        
        # Coerce values if needed
        profile_value = RulesEvaluator._coerce_value(profile_value)
        
        try:
            # Evaluate based on operator
            if op == "==":
                passed = profile_value == expected_value
            elif op == "!=":
                passed = profile_value != expected_value
            elif op == ">":
                passed = profile_value > expected_value
            elif op == ">=":
                passed = profile_value >= expected_value
            elif op == "<":
                passed = profile_value < expected_value
            elif op == "<=":
                passed = profile_value <= expected_value
            elif op == "truthy":
                passed = bool(profile_value)
            elif op == "falsy":
                passed = not bool(profile_value)
            elif op == "in":
                if isinstance(expected_value, list):
                    passed = profile_value in expected_value
                elif isinstance(expected_value, str):
                    # Handle comma-delimited strings
                    values = [v.strip() for v in expected_value.split(",")]
                    passed = profile_value in values
                else:
                    passed = False
            elif op == "not_in":
                if isinstance(expected_value, list):
                    passed = profile_value not in expected_value
                elif isinstance(expected_value, str):
                    values = [v.strip() for v in expected_value.split(",")]
                    passed = profile_value not in values
                else:
                    passed = True
            elif op == "between":
                if isinstance(expected_value, dict) and "min" in expected_value and "max" in expected_value:
                    min_val = expected_value["min"]
                    max_val = expected_value["max"]
                    passed = min_val <= profile_value <= max_val
                else:
                    return False, f"Invalid 'between' value format for {attribute}"
            else:
                return False, f"Unhandled operator: {op}"
            
            if passed:
                return True, f"{attribute} {op} {expected_value} ✓"
            else:
                reason = condition.reason_if_fail or condition.reason or f"{attribute} {op} {expected_value} failed"
                return False, reason
                
        except Exception as e:
            logger.error(f"Error evaluating condition {attribute} {op} {expected_value}: {e}")
            return False, f"evaluation error: {attribute}"
    
    @staticmethod
    def evaluate_scheme(profile: UserProfile, rules: EligibilityRules) -> Tuple[bool, List[str], List[str]]:
        """
        Evaluate user profile against scheme rules
        Returns: (eligible, failed_conditions, passed_conditions)
        """
        failed_conditions = []
        passed_conditions = []
        
        # Check disqualifiers first (fail fast)
        for disqualifier in rules.disqualifiers:
            passed, reason = RulesEvaluator._evaluate_condition(profile, disqualifier)
            if passed:
                # If disqualifier condition passes, user is disqualified
                disqualify_reason = disqualifier.reason or f"Disqualified: {reason}"
                failed_conditions.append(disqualify_reason)
                return False, failed_conditions, passed_conditions
        
        # Check all conditions (must all pass)
        for condition in rules.all:
            passed, reason = RulesEvaluator._evaluate_condition(profile, condition)
            if passed:
                passed_conditions.append(reason)
            else:
                failed_conditions.append(reason)
        
        # Check any conditions (at least one must pass if any exist)
        if rules.any:
            any_passed = False
            any_reasons = []
            
            for condition in rules.any:
                passed, reason = RulesEvaluator._evaluate_condition(profile, condition)
                if passed:
                    any_passed = True
                    passed_conditions.append(f"(any) {reason}")
                else:
                    any_reasons.append(reason)
            
            if not any_passed:
                failed_conditions.extend([f"None of required alternatives met: {', '.join(any_reasons)}"])
        
        # Determine final eligibility
        eligible = len(failed_conditions) == 0
        
        return eligible, failed_conditions, passed_conditions
    
    @staticmethod
    def validate_rules_json(rules_data: dict) -> Tuple[bool, str]:
        """Validate rules JSON structure"""
        try:
            # Check required top-level keys
            required_keys = ["scheme_id", "scheme_name", "eligibility"]
            for key in required_keys:
                if key not in rules_data:
                    return False, f"Missing required key: {key}"
            
            eligibility = rules_data["eligibility"]
            
            # Validate eligibility structure
            if not isinstance(eligibility, dict):
                return False, "eligibility must be a dictionary"
            
            # Check condition lists
            for condition_type in ["all", "any", "disqualifiers"]:
                if condition_type in eligibility:
                    conditions = eligibility[condition_type]
                    if not isinstance(conditions, list):
                        return False, f"eligibility.{condition_type} must be a list"
                    
                    for i, condition in enumerate(conditions):
                        if not isinstance(condition, dict):
                            return False, f"eligibility.{condition_type}[{i}] must be a dictionary"
                        
                        # Check required condition fields
                        if "attribute" not in condition:
                            return False, f"eligibility.{condition_type}[{i}] missing 'attribute'"
                        if "op" not in condition:
                            return False, f"eligibility.{condition_type}[{i}] missing 'op'"
                        if "value" not in condition:
                            return False, f"eligibility.{condition_type}[{i}] missing 'value'"
                        
                        # Validate operator
                        op = condition["op"]
                        if op not in RulesEvaluator.SUPPORTED_OPERATORS:
                            return False, f"Unsupported operator '{op}' in {condition_type}[{i}]"
                        
                        # Validate 'between' operator value format
                        if op == "between":
                            value = condition["value"]
                            if not isinstance(value, dict) or "min" not in value or "max" not in value:
                                return False, f"'between' operator requires value with 'min' and 'max' keys in {condition_type}[{i}]"
            
            return True, "Valid rules JSON"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
