"""
Goal Completion Checker for AutoPilot AI

Determines when high-level goals have been achieved.
Provides intelligent assessment of task completion.
"""

import logging
from typing import Dict, Any, List, Optional
from goal_engine import Goal, TaskGraph, Subgoal
import re
import json

logger = logging.getLogger(__name__)

class GoalCompletionChecker:
    """Checks if goals and subgoals have been completed successfully."""
    
    def __init__(self):
        self.completion_patterns = {
            "search": [
                r"search\s+results?\s+found",
                r"results?\s+extracted",
                r"listings?\s+obtained",
                r"items?\s+found"
            ],
            "extraction": [
                r"data\s+extracted",
                r"information\s+collected",
                r"details?\s+obtained",
                r"content\s+gathered"
            ],
            "comparison": [
                r"comparison\s+completed",
                r"best\s+option\s+identified",
                r"analysis\s+performed",
                r"winner\s+selected"
            ],
            "navigation": [
                r"page\s+loaded",
                r"navigation\s+complete",
                r"target\s+reached",
                r"section\s+accessed"
            ]
        }
    
    def check_goal_completion(self, goal: Goal, task_graph: TaskGraph, 
                            execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the overall goal has been completed.
        
        Args:
            goal: The high-level goal to check
            task_graph: Current state of the task graph
            execution_state: Current execution context and results
            
        Returns:
            Dict containing completion status and details
        """
        # Check if all subgoals are completed
        if not task_graph.is_complete():
            return {
                "completed": False,
                "reason": "Not all subgoals completed",
                "progress": task_graph.get_progress()
            }
        
        # Check success condition
        success_check = self._evaluate_success_condition(
            goal.success_condition, 
            execution_state
        )
        
        if not success_check["met"]:
            return {
                "completed": False,
                "reason": f"Success condition not met: {success_check['reason']}",
                "progress": task_graph.get_progress()
            }
        
        # Validate result quality
        quality_check = self._validate_result_quality(goal, execution_state)
        
        return {
            "completed": True,
            "reason": "Goal completed successfully",
            "quality_score": quality_check["score"],
            "quality_details": quality_check["details"],
            "progress": task_graph.get_progress(),
            "execution_summary": self._generate_execution_summary(task_graph, execution_state)
        }
    
    def check_subgoal_completion(self, subgoal: Subgoal, 
                               execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a specific subgoal has been completed.
        
        Args:
            subgoal: The subgoal to check
            execution_state: Current execution context
            
        Returns:
            Dict containing completion status and details
        """
        # Evaluate success criteria
        criteria_check = self._evaluate_success_criteria(
            subgoal.success_criteria,
            execution_state
        )
        
        if not criteria_check["met"]:
            return {
                "completed": False,
                "reason": criteria_check["reason"],
                "suggestions": criteria_check["suggestions"]
            }
        
        # Check for expected data/results
        data_check = self._validate_subgoal_data(subgoal, execution_state)
        
        return {
            "completed": True,
            "reason": criteria_check["reason"],
            "data_valid": data_check["valid"],
            "data_details": data_check["details"]
        }
    
    def _evaluate_success_condition(self, condition: str, 
                                  execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if the success condition has been met."""
        # Extract numerical requirements from condition
        numerical_requirements = self._extract_numerical_requirements(condition)
        
        # Check against collected data
        collected_data = execution_state.get("collected_data", [])
        results = execution_state.get("results", [])
        
        for req_type, req_value in numerical_requirements.items():
            if req_type == "count":
                actual_count = len(collected_data) + len(results)
                if actual_count < req_value:
                    return {
                        "met": False,
                        "reason": f"Required {req_value} items, only found {actual_count}"
                    }
            elif req_type == "top":
                if len(results) < req_value:
                    return {
                        "met": False,
                        "reason": f"Required top {req_value} results, only found {len(results)}"
                    }
        
        # Check for qualitative requirements
        qualitative_check = self._check_qualitative_requirements(condition, execution_state)
        
        if not qualitative_check["met"]:
            return qualitative_check
        
        return {
            "met": True,
            "reason": "All success conditions met"
        }
    
    def _evaluate_success_criteria(self, criteria: str, 
                                 execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate success criteria for a subgoal."""
        # Similar to success condition evaluation but more specific
        dom_state = execution_state.get("dom_state", {})
        last_action_result = execution_state.get("last_action_result", {})
        
        # Check if the action was successful
        if not last_action_result.get("ok", False):
            return {
                "met": False,
                "reason": f"Last action failed: {last_action_result.get('error', 'Unknown error')}",
                "suggestions": ["Retry the action", "Try alternative approach"]
            }
        
        # Check for expected elements in DOM
        if "navigate" in criteria.lower():
            if dom_state.get("url") and dom_state["url"] != "about:blank":
                return {
                    "met": True,
                    "reason": "Navigation successful"
                }
            else:
                return {
                    "met": False,
                    "reason": "Navigation not completed",
                    "suggestions": ["Wait for page to load", "Check network connection"]
                }
        
        elif "search" in criteria.lower():
            if dom_state.get("specialElements", {}).get("searchInputs"):
                return {
                    "met": True,
                    "reason": "Search functionality found"
                }
            else:
                return {
                    "met": False,
                    "reason": "Search functionality not found",
                    "suggestions": ["Try alternative search selectors", "Scroll to find search bar"]
                }
        
        elif "extract" in criteria.lower():
            extracted_data = execution_state.get("extracted_data", [])
            if extracted_data:
                return {
                    "met": True,
                    "reason": f"Extracted {len(extracted_data)} items"
                }
            else:
                return {
                    "met": False,
                    "reason": "No data extracted",
                    "suggestions": ["Check element selectors", "Wait for content to load"]
                }
        
        # Default success
        return {
            "met": True,
            "reason": "Subgoal completed successfully"
        }
    
    def _extract_numerical_requirements(self, condition: str) -> Dict[str, int]:
        """Extract numerical requirements from success condition."""
        requirements = {}
        
        # Extract "top N" patterns
        top_match = re.search(r'top\s+(\d+)', condition.lower())
        if top_match:
            requirements["top"] = int(top_match.group(1))
        
        # Extract count patterns
        count_patterns = [
            r'(\d+)\s+items?',
            r'(\d+)\s+results?',
            r'(\d+)\s+listings?',
            r'at\s+least\s+(\d+)',
            r'minimum\s+(\d+)'
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, condition.lower())
            if match:
                requirements["count"] = int(match.group(1))
                break
        
        return requirements
    
    def _check_qualitative_requirements(self, condition: str, 
                                     execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check qualitative requirements in success condition."""
        condition_lower = condition.lower()
        
        # Check for relevance
        if "relevant" in condition_lower:
            # Simple relevance check based on content length and keywords
            collected_data = execution_state.get("collected_data", [])
            if not collected_data or all(len(str(data)) < 10 for data in collected_data):
                return {
                    "met": False,
                    "reason": "Results lack sufficient content for relevance assessment"
                }
        
        # Check for completeness
        if "complete" in condition_lower or "comprehensive" in condition_lower:
            # Basic completeness check
            results = execution_state.get("results", [])
            if len(results) < 3:  # Arbitrary threshold for completeness
                return {
                    "met": False,
                    "reason": "Results may not be comprehensive enough"
                }
        
        return {
            "met": True,
            "reason": "Qualitative requirements met"
        }
    
    def _validate_result_quality(self, goal: Goal, 
                              execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of the results."""
        collected_data = execution_state.get("collected_data", [])
        results = execution_state.get("results", [])
        
        quality_score = 0
        details = []
        
        # Check data volume
        total_items = len(collected_data) + len(results)
        if total_items >= 5:
            quality_score += 25
            details.append("Good data volume")
        elif total_items >= 2:
            quality_score += 15
            details.append("Moderate data volume")
        else:
            details.append("Low data volume")
        
        # Check data richness
        if collected_data:
            rich_data = sum(1 for item in collected_data if len(str(item)) > 50)
            if rich_data >= len(collected_data) * 0.7:
                quality_score += 25
                details.append("Rich data content")
            else:
                quality_score += 10
                details.append("Moderate data content")
        
        # Check goal alignment
        goal_keywords = set(goal.goal_statement.lower().split())
        if goal_keywords.intersection(set(str(results).lower())):
            quality_score += 25
            details.append("Good goal alignment")
        else:
            details.append("Limited goal alignment")
        
        # Check execution efficiency
        total_actions = execution_state.get("total_actions", 0)
        if total_actions <= goal.estimated_steps * 1.5:
            quality_score += 25
            details.append("Efficient execution")
        else:
            quality_score += 10
            details.append("Execution could be more efficient")
        
        return {
            "score": min(quality_score, 100),
            "details": details
        }
    
    def _validate_subgoal_data(self, subgoal: Subgoal, 
                             execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for a specific subgoal."""
        last_action_result = execution_state.get("last_action_result", {})
        
        if "extract" in subgoal.description.lower():
            extracted_data = last_action_result.get("data", [])
            if extracted_data:
                return {
                    "valid": True,
                    "details": f"Extracted {len(extracted_data)} items"
                }
            else:
                return {
                    "valid": False,
                    "details": "No data extracted"
                }
        
        elif "navigate" in subgoal.description.lower():
            dom_state = execution_state.get("dom_state", {})
            if dom_state.get("url"):
                return {
                    "valid": True,
                    "details": f"Navigation to {dom_state['url']} successful"
                }
            else:
                return {
                    "valid": False,
                    "details": "Navigation not confirmed"
                }
        
        # Default validation
        return {
            "valid": last_action_result.get("ok", False),
            "details": "Action completed successfully" if last_action_result.get("ok") else "Action failed"
        }
    
    def _generate_execution_summary(self, task_graph: TaskGraph, 
                                  execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the execution."""
        progress = task_graph.get_progress()
        
        return {
            "total_subgoals": progress["total_subgoals"],
            "completed_subgoals": progress["completed"],
            "failed_subgoals": progress["failed"],
            "success_rate": (progress["completed"] / progress["total_subgoals"]) * 100 if progress["total_subgoals"] > 0 else 0,
            "total_actions": execution_state.get("total_actions", 0),
            "execution_time": execution_state.get("execution_time", 0),
            "errors_encountered": execution_state.get("errors_encountered", 0),
            "retry_attempts": execution_state.get("retry_attempts", 0)
        }

# Global instance
goal_checker = GoalCompletionChecker()
