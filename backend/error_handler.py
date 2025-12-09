"""
Error Handler for AutoPilot AI Self-Correction System

Provides intelligent error detection, analysis, and recovery strategies.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorType(str, Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    ELEMENT_DISABLED = "element_disabled"
    TIMEOUT = "timeout"
    PAGE_NOT_LOADED = "page_not_loaded"
    SELECTOR_INVALID = "selector_invalid"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"

class RecoveryStrategy(str, Enum):
    RETRY_WITH_ALTERNATIVES = "retry_with_alternatives"
    WAIT_AND_RETRY = "wait_and_retry"
    SCROLL_AND_RETRY = "scroll_and_retry"
    FALLBACK_SELECTOR = "fallback_selector"
    REPLAN = "replan"
    ABORT = "abort"

# Alternative selectors for common elements
ALTERNATIVE_SELECTORS = {
    "search": [
        "input[type='search']",
        "input[type='text']",
        "input[name='q']",
        "input[name='query']",
        "input[id*='search']",
        "input[class*='search']",
        "[role='searchbox']",
        "textarea[name='q']",
        "input[placeholder*='search' i]",
        "input[aria-label*='search' i]"
    ],
    "submit": [
        "button[type='submit']",
        "input[type='submit']",
        "button[type='button']",
        "button:has([class*='submit'])",
        "button:has([class*='search'])",
        "button[class*='submit']",
        "button[class*='search']",
        "button[id*='submit']",
        "button[id*='search']",
        "[role='button'][class*='submit']",
        "[role='button'][class*='search']"
    ],
    "login": [
        "button[type='submit']",
        "input[type='submit']",
        "button:has([class*='login'])",
        "button:has([class*='signin'])",
        "button[class*='login']",
        "button[class*='signin']",
        "a[class*='login']",
        "a[class*='signin']",
        "button[id*='login']",
        "button[id*='signin']"
    ],
    "play": [
        "button[aria-label*='play' i]",
        "button[class*='play']",
        "button[id*='play']",
        "[role='button'][aria-label*='play' i]",
        "button:has([class*='play'])",
        ".play-button",
        ".ytp-play-button"
    ],
    "accept": [
        "button:has([class*='accept'])",
        "button:has([class*='agree'])",
        "button[class*='accept']",
        "button[class*='agree']",
        "button[id*='accept']",
        "button[id*='agree']",
        "button[aria-label*='accept' i]",
        "button[aria-label*='agree' i]"
    ]
}

class ErrorHandler:
    """Handles error detection and recovery strategies."""
    
    def __init__(self):
        self.error_history = []
        self.max_retries = 3
        
    def classify_error(self, error_result: Dict[str, Any]) -> ErrorType:
        """Classify the type of error from the result."""
        error_msg = error_result.get("error", "").lower()
        
        if "not found" in error_msg or "element not found" in error_msg:
            return ErrorType.ELEMENT_NOT_FOUND
        elif "not visible" in error_msg or "element not visible" in error_msg:
            return ErrorType.ELEMENT_NOT_VISIBLE
        elif "disabled" in error_msg or "element is disabled" in error_msg:
            return ErrorType.ELEMENT_DISABLED
        elif "timeout" in error_msg or "timed out" in error_msg:
            return ErrorType.TIMEOUT
        elif "page not loaded" in error_msg or "loading" in error_msg:
            return ErrorType.PAGE_NOT_LOADED
        elif "invalid selector" in error_msg or "selector" in error_msg and "invalid" in error_msg:
            return ErrorType.SELECTOR_INVALID
        elif "network" in error_msg or "connection" in error_msg:
            return ErrorType.NETWORK_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def get_recovery_strategy(self, error_type: ErrorType, action: Dict[str, Any], 
                            attempt_count: int = 0) -> RecoveryStrategy:
        """Determine the best recovery strategy based on error type and context."""
        
        if attempt_count >= self.max_retries:
            return RecoveryStrategy.REPLAN
        
        # Strategy mapping based on error type
        strategy_map = {
            ErrorType.ELEMENT_NOT_FOUND: self._handle_element_not_found,
            ErrorType.ELEMENT_NOT_VISIBLE: RecoveryStrategy.SCROLL_AND_RETRY,
            ErrorType.ELEMENT_DISABLED: RecoveryStrategy.REPLAN,
            ErrorType.TIMEOUT: RecoveryStrategy.WAIT_AND_RETRY,
            ErrorType.PAGE_NOT_LOADED: RecoveryStrategy.WAIT_AND_RETRY,
            ErrorType.SELECTOR_INVALID: RecoveryStrategy.FALLBACK_SELECTOR,
            ErrorType.NETWORK_ERROR: RecoveryStrategy.WAIT_AND_RETRY,
            ErrorType.UNKNOWN_ERROR: RecoveryStrategy.RETRY_WITH_ALTERNATIVES
        }
        
        base_strategy = strategy_map.get(error_type, RecoveryStrategy.RETRY_WITH_ALTERNATIVES)
        
        # Special handling for element not found
        if error_type == ErrorType.ELEMENT_NOT_FOUND:
            return self._handle_element_not_found(action, attempt_count)
        
        return base_strategy
    
    def _handle_element_not_found(self, action: Dict[str, Any], attempt_count: int) -> RecoveryStrategy:
        """Handle element not found errors with intelligent fallback."""
        selector = action.get("selector", "")
        action_type = action.get("action", "")
        
        # First attempt: try alternative selectors
        if attempt_count == 0:
            if self._has_alternative_selectors(selector, action_type):
                return RecoveryStrategy.FALLBACK_SELECTOR
            else:
                return RecoveryStrategy.SCROLL_AND_RETRY
        
        # Second attempt: scroll and wait
        elif attempt_count == 1:
            return RecoveryStrategy.SCROLL_AND_RETRY
        
        # Third attempt: wait and retry
        elif attempt_count == 2:
            return RecoveryStrategy.WAIT_AND_RETRY
        
        # Final fallback: replan
        return RecoveryStrategy.REPLAN
    
    def _has_alternative_selectors(self, selector: str, action_type: str) -> bool:
        """Check if we have alternative selectors for this element."""
        selector_lower = selector.lower()
        
        # Check if selector matches any of our known patterns
        for category, alternatives in ALTERNATIVE_SELECTORS.items():
            if any(keyword in selector_lower for keyword in [category, "search", "submit", "login", "play", "accept"]):
                return True
        
        # Check action-specific alternatives
        if action_type == "typeText" and ("input" in selector_lower or "textarea" in selector_lower):
            return True
        elif action_type == "clickElement" and ("button" in selector_lower or "a" in selector_lower):
            return True
        
        return False
    
    def generate_correction(self, action: Dict[str, Any], error_result: Dict[str, Any], 
                          attempt_count: int = 0) -> Dict[str, Any]:
        """Generate a corrected action based on the error and strategy."""
        
        error_type = self.classify_error(error_result)
        strategy = self.get_recovery_strategy(error_type, action, attempt_count)
        
        logger.info(f"Error: {error_type}, Strategy: {strategy}, Attempt: {attempt_count}")
        
        # Record error for learning
        self.error_history.append({
            "error_type": error_type,
            "strategy": strategy,
            "action": action,
            "error_result": error_result,
            "attempt_count": attempt_count
        })
        
        # Generate corrected action based on strategy
        if strategy == RecoveryStrategy.FALLBACK_SELECTOR:
            return self._apply_fallback_selector(action)
        elif strategy == RecoveryStrategy.SCROLL_AND_RETRY:
            return self._apply_scroll_and_retry(action)
        elif strategy == RecoveryStrategy.WAIT_AND_RETRY:
            return self._apply_wait_and_retry(action)
        elif strategy == RecoveryStrategy.RETRY_WITH_ALTERNATIVES:
            return self._apply_retry_with_alternatives(action)
        elif strategy == RecoveryStrategy.REPLAN:
            return self._trigger_replan(action, error_result)
        else:
            return action  # Return original action as fallback
    
    def _apply_fallback_selector(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply alternative selector to the action."""
        original_selector = action.get("selector", "")
        action_type = action.get("action", "")
        
        # Find appropriate alternative selectors
        alternatives = self._get_alternative_selectors(original_selector, action_type)
        
        if alternatives:
            # Try the first alternative
            new_action = action.copy()
            new_action["selector"] = alternatives[0]
            new_action["fallback_selectors"] = alternatives[1:]  # Store remaining alternatives
            new_action["original_selector"] = original_selector
            new_action["recovery_reason"] = "Using alternative selector"
            return new_action
        
        return action
    
    def _apply_scroll_and_retry(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Add scroll action before retrying the original action."""
        return {
            "action": "scrollPage",
            "direction": "down",
            "amount": 500,
            "recovery_reason": "Scrolling to find element",
            "followed_by": action
        }
    
    def _apply_wait_and_retry(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Add wait action before retrying the original action."""
        return {
            "action": "wait",
            "duration": 2000,  # 2 seconds
            "recovery_reason": "Waiting for element to load",
            "followed_by": action
        }
    
    def _apply_retry_with_alternatives(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Retry the action with enhanced timeout and fallback options."""
        new_action = action.copy()
        new_action["timeout"] = (action.get("timeout", 10000) * 1.5)  # Increase timeout by 50%
        new_action["recovery_reason"] = "Retrying with increased timeout"
        return new_action
    
    def _trigger_replan(self, action: Dict[str, Any], error_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a replan using LLM based on the current context."""
        return {
            "action": "replan",
            "original_action": action,
            "error_result": error_result,
            "recovery_reason": "Replanning due to persistent failure",
            "requires_llm": True
        }
    
    def _get_alternative_selectors(self, selector: str, action_type: str) -> List[str]:
        """Get alternative selectors for a given selector and action type."""
        selector_lower = selector.lower()
        
        # Check against known patterns
        for category, alternatives in ALTERNATIVE_SELECTORS.items():
            if category in selector_lower:
                return alternatives
        
        # Action-specific alternatives
        if action_type == "typeText":
            return ALTERNATIVE_SELECTORS.get("search", [])
        elif action_type == "clickElement":
            # Determine which category based on selector content
            if "submit" in selector_lower:
                return ALTERNATIVE_SELECTORS.get("submit", [])
            elif "login" in selector_lower or "signin" in selector_lower:
                return ALTERNATIVE_SELECTORS.get("login", [])
            elif "play" in selector_lower:
                return ALTERNATIVE_SELECTORS.get("play", [])
            elif "accept" in selector_lower or "agree" in selector_lower:
                return ALTERNATIVE_SELECTORS.get("accept", [])
        
        return []
    
    def should_abort(self, error_result: Dict[str, Any], attempt_count: int) -> bool:
        """Determine if the task should be aborted due to persistent errors."""
        error_type = self.classify_error(error_result)
        
        # Abort if we've exceeded max retries for certain error types
        if attempt_count >= self.max_retries:
            if error_type in [ErrorType.ELEMENT_DISABLED, ErrorType.SELECTOR_INVALID]:
                return True
        
        # Abort on network errors after 2 attempts
        if error_type == ErrorType.NETWORK_ERROR and attempt_count >= 2:
            return True
        
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of errors encountered for learning purposes."""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_counts = {}
        strategy_counts = {}
        
        for error in self.error_history:
            error_type = error["error_type"]
            strategy = error["strategy"]
            
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_counts,
            "strategies_used": strategy_counts,
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of error recovery attempts."""
        if not self.error_history:
            return 0.0
        
        # Count successful recoveries (errors that didn't lead to abort/replan)
        successful_recoveries = 0
        for error in self.error_history:
            if error["strategy"] not in [RecoveryStrategy.REPLAN, RecoveryStrategy.ABORT]:
                successful_recoveries += 1
        
        return (successful_recoveries / len(self.error_history)) * 100

# Global error handler instance
error_handler = ErrorHandler()
