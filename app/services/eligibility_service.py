"""
Eligibility service for checking user eligibility against scheme rules
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from ..models.scheme import SchemeRule, EligibilityRule, DisqualifierRule
from ..models.user import UserProfile, EligibilityResult, EligibilityResponse
from ..services.mongo_service import mongo_service

logger = logging.getLogger(__name__)


class EligibilityService:
    """Service for checking user eligibility against scheme rules"""
    
    def __init__(self):
        self.operators = {
            '==': self._eq,
            '!=': self._ne,
            '>': self._gt,
            '>=': self._gte,
            '<': self._lt,
            '<=': self._lte,
            'truthy': self._truthy,
            'falsy': self._falsy,
            'in': self._in,
            'not_in': self._not_in,
            'between': self._between
        }
    
    async def check_eligibility(
        self, 
        user_profile: UserProfile, 
        scheme_ids: Optional[List[str]] = None
    ) -> EligibilityResponse:
        """
        Check user eligibility for schemes
        
        Args:
            user_profile: User's profile information
            scheme_ids: Specific schemes to check (if None, check all)
        
        Returns:
            EligibilityResponse with results
        """
        start_time = time.time()
        
        try:
            # Get scheme rules to check
            if scheme_ids:
                scheme_rules = []
                for scheme_id in scheme_ids:
                    rule = await mongo_service.get_scheme_rule(scheme_id)
                    if rule:
                        scheme_rules.append(rule)
            else:
                scheme_rules = await mongo_service.get_all_scheme_rules()
            
            if not scheme_rules:
                return EligibilityResponse(
                    total_schemes_checked=0,
                    eligible_schemes=0,
                    results=[],
                    checked_at=datetime.now(datetime.timezone.utc)
                )
            
            # Check eligibility for each scheme
            results = []
            eligible_count = 0
            
            for scheme_rule in scheme_rules:
                result = await self._check_single_scheme(user_profile, scheme_rule)
                results.append(result)
                
                if result.is_eligible:
                    eligible_count += 1
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create response
            response = EligibilityResponse(
                total_schemes_checked=len(scheme_rules),
                eligible_schemes=eligible_count,
                results=results,
                checked_at=datetime.now(datetime.timezone.utc),
                processing_time_ms=processing_time
            )
            
            logger.info(f"Eligibility check completed: {eligible_count}/{len(scheme_rules)} schemes eligible")
            return response
            
        except Exception as e:
            logger.error(f"Error in eligibility check: {e}")
            raise
    
    async def _check_single_scheme(
        self, 
        user_profile: UserProfile, 
        scheme_rule: SchemeRule
    ) -> EligibilityResult:
        """
        Check eligibility for a single scheme
        
        Args:
            user_profile: User's profile
            scheme_rule: Scheme rules to check against
        
        Returns:
            EligibilityResult for the scheme
        """
        try:
            reasons = []
            required_documents = scheme_rule.required_documents.copy()
            
            # Check disqualifiers first
            for disqualifier in scheme_rule.eligibility.disqualifiers:
                if self._evaluate_rule(user_profile, disqualifier):
                    return EligibilityResult(
                        scheme_id=scheme_rule.scheme_id,
                        scheme_name=scheme_rule.scheme_name,
                        is_eligible=False,
                        reasons=[f"Disqualified: {disqualifier.reason}"],
                        required_documents=required_documents,
                        benefit_outline=scheme_rule.benefit_outline,
                        next_steps=scheme_rule.next_steps,
                        score=0.0
                    )
            
            # Check 'all' rules (all must pass)
            for rule in scheme_rule.eligibility.all:
                if not self._evaluate_rule(user_profile, rule):
                    reasons.append(f"Failed: {rule.reason_if_fail}")
                else:
                    reasons.append(f"Passed: {rule.attribute} requirement met")
            
            # Check 'any' rules (at least one must pass)
            any_rules_passed = False
            if scheme_rule.eligibility.any:
                for rule in scheme_rule.eligibility.any:
                    if self._evaluate_rule(user_profile, rule):
                        any_rules_passed = True
                        reasons.append(f"Passed: {rule.attribute} requirement met")
                        break
                if not any_rules_passed:
                    reasons.append("Failed: None of the 'any' rules passed")
            else:
                any_rules_passed = True  # No 'any' rules means this check passes
            
            # Determine eligibility
            all_rules_passed = all(
                self._evaluate_rule(user_profile, rule) 
                for rule in scheme_rule.eligibility.all
            )
            
            is_eligible = all_rules_passed and any_rules_passed
            
            # Calculate score
            score = self._calculate_eligibility_score(
                scheme_rule, user_profile, all_rules_passed, any_rules_passed
            )
            
            # Update reasons based on final result
            if is_eligible:
                if not reasons:
                    reasons.append("All eligibility criteria met")
            else:
                # Add specific failure reasons
                failed_rules = []
                for rule in scheme_rule.eligibility.all:
                    if not self._evaluate_rule(user_profile, rule):
                        failed_rules.append(rule.reason_if_fail)
                
                if failed_rules:
                    reasons = [f"Failed: {reason}" for reason in failed_rules]
                
                if scheme_rule.eligibility.any and not any_rules_passed:
                    reasons.append("Failed: None of the alternative criteria met")
            
            return EligibilityResult(
                scheme_id=scheme_rule.scheme_id,
                scheme_name=scheme_rule.scheme_name,
                is_eligible=is_eligible,
                reasons=reasons,
                required_documents=required_documents,
                benefit_outline=scheme_rule.benefit_outline,
                next_steps=scheme_rule.next_steps,
                score=score
            )
            
        except Exception as e:
            logger.error(f"Error checking eligibility for scheme {scheme_rule.scheme_id}: {e}")
            return EligibilityResult(
                scheme_id=scheme_rule.scheme_id,
                scheme_name=scheme_rule.scheme_name,
                is_eligible=False,
                reasons=[f"Error during eligibility check: {str(e)}"],
                required_documents=scheme_rule.required_documents,
                score=0.0
            )
    
    def _evaluate_rule(self, user_profile: UserProfile, rule: EligibilityRule) -> bool:
        """
        Evaluate a single eligibility rule against user profile
        
        Args:
            user_profile: User's profile
            rule: Rule to evaluate
        
        Returns:
            True if rule passes, False otherwise
        """
        try:
            # Get the attribute value from user profile
            attribute_value = getattr(user_profile, rule.attribute, None)
            
            # Handle None values
            if attribute_value is None:
                return False
            
            # Get the operator function
            op_func = self.operators.get(rule.op)
            if not op_func:
                logger.warning(f"Unknown operator: {rule.op}")
                return False
            
            # Evaluate the rule
            return op_func(attribute_value, rule.value)
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.attribute} {rule.op} {rule.value}: {e}")
            return False
    
    def _evaluate_disqualifier(self, user_profile: UserProfile, rule: DisqualifierRule) -> bool:
        """
        Evaluate a disqualifier rule
        
        Args:
            user_profile: User's profile
            rule: Disqualifier rule to evaluate
        
        Returns:
            True if user is disqualified, False otherwise
        """
        try:
            # Get the attribute value from user profile
            attribute_value = getattr(user_profile, rule.attribute, None)
            
            # Handle None values
            if attribute_value is None:
                return False
            
            # Get the operator function
            op_func = self.operators.get(rule.op)
            if not op_func:
                logger.warning(f"Unknown operator: {rule.op}")
                return False
            
            # Evaluate the rule
            return op_func(attribute_value, rule.value)
            
        except Exception as e:
            logger.error(f"Error evaluating disqualifier rule {rule.attribute} {rule.op} {rule.value}: {e}")
            return False
    
    def _calculate_eligibility_score(
        self, 
        scheme_rule: SchemeRule, 
        user_profile: UserProfile,
        all_rules_passed: bool,
        any_rules_passed: bool
    ) -> float:
        """
        Calculate eligibility score (0-100)
        
        Args:
            scheme_rule: Scheme rules
            user_profile: User's profile
            all_rules_passed: Whether all required rules passed
            any_rules_passed: Whether any alternative rules passed
        
        Returns:
            Score between 0 and 100
        """
        if not all_rules_passed or not any_rules_passed:
            return 0.0
        
        try:
            total_rules = len(scheme_rule.eligibility.all) + len(scheme_rule.eligibility.any)
            if total_rules == 0:
                return 100.0
            
            passed_rules = 0
            
            # Count passed 'all' rules
            for rule in scheme_rule.eligibility.all:
                if self._evaluate_rule(user_profile, rule):
                    passed_rules += 1
            
            # Count passed 'any' rules (only count 1 if any pass)
            if scheme_rule.eligibility.any:
                any_passed = any(
                    self._evaluate_rule(user_profile, rule) 
                    for rule in scheme_rule.eligibility.any
                )
                if any_passed:
                    passed_rules += 1
            
            # Calculate percentage
            score = (passed_rules / total_rules) * 100
            
            # Round to 1 decimal place
            return round(score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating eligibility score: {e}")
            return 0.0
    
    # Operator functions
    def _eq(self, a, b):
        """Equal operator"""
        return a == b
    
    def _ne(self, a, b):
        """Not equal operator"""
        return a != b
    
    def _gt(self, a, b):
        """Greater than operator"""
        try:
            return float(a) > float(b)
        except (ValueError, TypeError):
            return False
    
    def _gte(self, a, b):
        """Greater than or equal operator"""
        try:
            return float(a) >= float(b)
        except (ValueError, TypeError):
            return False
    
    def _lt(self, a, b):
        """Less than operator"""
        try:
            return float(a) < float(b)
        except (ValueError, TypeError):
            return False
    
    def _lte(self, a, b):
        """Less than or equal operator"""
        try:
            return float(a) <= float(b)
        except (ValueError, TypeError):
            return False
    
    def _truthy(self, a, b):
        """Truthy operator"""
        return bool(a)
    
    def _falsy(self, a, b):
        """Falsy operator"""
        return not bool(a)
    
    def _in(self, a, b):
        """In operator"""
        if isinstance(b, (list, tuple)):
            return a in b
        return str(a) in str(b)
    
    def _not_in(self, a, b):
        """Not in operator"""
        if isinstance(b, (list, tuple)):
            return a not in b
        return str(a) not in str(b)
    
    def _between(self, a, b):
        """Between operator - b should be a list/tuple with [min, max]"""
        try:
            if isinstance(b, (list, tuple)) and len(b) == 2:
                min_val, max_val = float(b[0]), float(b[1])
                a_val = float(a)
                return min_val <= a_val <= max_val
            return False
        except (ValueError, TypeError):
            return False
    
    async def get_eligibility_summary(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        Get a summary of eligibility across all schemes
        
        Args:
            user_profile: User's profile
        
        Returns:
            Summary statistics
        """
        try:
            # Get all scheme rules
            scheme_rules = await mongo_service.get_all_scheme_rules()
            
            if not scheme_rules:
                return {
                    "total_schemes": 0,
                    "eligible_schemes": 0,
                    "partially_eligible": 0,
                    "ineligible_schemes": 0,
                    "top_categories": [],
                    "recommendations": []
                }
            
            # Analyze each scheme
            eligible_count = 0
            partially_eligible = 0
            ineligible_count = 0
            category_scores = {}
            
            for scheme_rule in scheme_rules:
                result = await self._check_single_scheme(user_profile, scheme_rule)
                
                if result.is_eligible:
                    eligible_count += 1
                elif result.score > 50:
                    partially_eligible += 1
                else:
                    ineligible_count += 1
                
                # Track category performance
                # This is a simple example - you could implement more sophisticated categorization
                if result.score > 0:
                    category = "General"
                    if "farmer" in scheme_rule.scheme_name.lower():
                        category = "Agriculture"
                    elif "student" in scheme_rule.scheme_name.lower():
                        category = "Education"
                    elif "income" in scheme_rule.scheme_name.lower():
                        category = "Financial"
                    
                    if category not in category_scores:
                        category_scores[category] = []
                    category_scores[category].append(result.score)
            
            # Calculate top categories
            top_categories = []
            for category, scores in category_scores.items():
                avg_score = sum(scores) / len(scores)
                top_categories.append({
                    "category": category,
                    "average_score": round(avg_score, 1),
                    "scheme_count": len(scores)
                })
            
            # Sort by average score
            top_categories.sort(key=lambda x: x["average_score"], reverse=True)
            
            # Generate recommendations
            recommendations = []
            if eligible_count == 0:
                recommendations.append("Consider updating your profile information for better matches")
            if partially_eligible > 0:
                recommendations.append("Some schemes are partially eligible - check specific requirements")
            
            return {
                "total_schemes": len(scheme_rules),
                "eligible_schemes": eligible_count,
                "partially_eligible": partially_eligible,
                "ineligible_schemes": ineligible_count,
                "top_categories": top_categories[:5],  # Top 5 categories
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error generating eligibility summary: {e}")
            return {
                "error": str(e)
            }


# Global eligibility service instance
eligibility_service = EligibilityService()
