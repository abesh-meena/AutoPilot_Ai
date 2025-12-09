"""
Retry Manager for AutoPilot AI Self-Correction System

Manages the 3-attempt retry logic with intelligent error recovery.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from error_handler import error_handler, ErrorType, RecoveryStrategy

logger = logging.getLogger(__name__)

class RetryManager:
    """Manages retry logic with error recovery strategies."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_history = []
        
    async def execute_with_retry(self, action: Dict[str, Any], executor_func) -> Dict[str, Any]:
        """
        Execute an action with automatic retry and error recovery.
        
        Args:
            action: The action to execute
            executor_func: Async function that executes the action
            
        Returns:
            Dict containing the final result and retry information
        """
        original_action = action.copy()
        attempt_count = 0
        last_error = None
        
        while attempt_count < self.max_retries:
            try:
                logger.info(f"Executing action {action['action']} (attempt {attempt_count + 1}/{self.max_retries})")
                
                # Execute the action
                result = await executor_func(action)
                
                # Check if successful
                if result.get("ok", False):
                    # Success - record and return
                    self._record_retry(original_action, attempt_count, result, success=True)
                    return {
                        "ok": True,
                        "result": result,
                        "attempts": attempt_count + 1,
                        "retry_history": self.retry_history[-1] if self.retry_history else None
                    }
                
                # Failed - analyze error and apply correction
                last_error = result
                logger.warning(f"Action failed on attempt {attempt_count + 1}: {result.get('error', 'Unknown error')}")
                
                # Check if we should abort
                if error_handler.should_abort(result, attempt_count):
                    logger.error("Aborting due to persistent error")
                    break
                
                # Generate correction for next attempt
                if attempt_count < self.max_retries - 1:
                    action = error_handler.generate_correction(action, result, attempt_count)
                    
                    # Handle special recovery actions
                    if action.get("action") == "scrollPage":
                        # Execute scroll first, then retry original action
                        scroll_result = await executor_func(action)
                        if scroll_result.get("ok", False):
                            # Restore original action for retry
                            action = original_action.copy()
                            # Increase timeout for the retry
                            action["timeout"] = action.get("timeout", 10000) * 1.5
                        else:
                            # Scroll failed - continue with corrected action
                            pass
                    
                    elif action.get("action") == "wait":
                        # Execute wait first, then retry original action
                        wait_result = await executor_func(action)
                        if wait_result.get("ok", False):
                            # Restore original action for retry
                            action = original_action.copy()
                            # Increase timeout for the retry
                            action["timeout"] = action.get("timeout", 10000) * 1.5
                        else:
                            # Wait failed - continue with corrected action
                            pass
                    
                    elif action.get("action") == "replan":
                        # Trigger replan - this will be handled by the planner
                        self._record_retry(original_action, attempt_count, last_error, success=False)
                        return {
                            "ok": False,
                            "error": last_error.get("error", "Replan required"),
                            "requires_replan": True,
                            "attempts": attempt_count + 1,
                            "retry_history": self.retry_history[-1] if self.retry_history else None,
                            "original_action": original_action,
                            "error_result": last_error
                        }
                
            except Exception as e:
                logger.error(f"Exception during execution attempt {attempt_count + 1}: {str(e)}")
                last_error = {"ok": False, "error": str(e)}
                
                # Check if we should abort on exception
                if error_handler.should_abort(last_error, attempt_count):
                    break
            
            attempt_count += 1
        
        # All retries failed
        self._record_retry(original_action, attempt_count, last_error, success=False)
        return {
            "ok": False,
            "error": last_error.get("error", "All retry attempts failed"),
            "attempts": attempt_count,
            "retry_history": self.retry_history[-1] if self.retry_history else None,
            "max_retries_exceeded": True
        }
    
    def _record_retry(self, action: Dict[str, Any], attempt_count: int, result: Dict[str, Any], success: bool):
        """Record retry attempt for analysis."""
        retry_record = {
            "action": action,
            "attempts": attempt_count + 1,
            "success": success,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.retry_history.append(retry_record)
        
        # Keep only last 50 retry records to avoid memory issues
        if len(self.retry_history) > 50:
            self.retry_history = self.retry_history[-50:]
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get statistics about retry attempts."""
        if not self.retry_history:
            return {"total_retries": 0}
        
        total_retries = len(self.retry_history)
        successful_retries = sum(1 for r in self.retry_history if r["success"])
        failed_retries = total_retries - successful_retries
        
        # Calculate average attempts per action
        total_attempts = sum(r["attempts"] for r in self.retry_history)
        avg_attempts = total_attempts / total_retries if total_retries > 0 else 0
        
        # Most common error types
        error_types = {}
        for record in self.retry_history:
            if not record["success"] and "result" in record:
                error_msg = record["result"].get("error", "Unknown")
                error_types[error_msg] = error_types.get(error_msg, 0) + 1
        
        return {
            "total_retries": total_retries,
            "successful_retries": successful_retries,
            "failed_retries": failed_retries,
            "success_rate": (successful_retries / total_retries) * 100 if total_retries > 0 else 0,
            "average_attempts": avg_attempts,
            "most_common_errors": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def reset_history(self):
        """Reset retry history."""
        self.retry_history = []

# Global retry manager instance
retry_manager = RetryManager()
