"""
Autonomous Task Executor

Handles the execution loop for autonomous task completion.
"""
from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AutonomousExecutor:
    """Manages the autonomous execution loop."""
    
    def __init__(self, max_steps: int = 20, timeout_seconds: int = 300):
        self.max_steps = max_steps
        self.timeout = timedelta(seconds=timeout_seconds)
        self.start_time = None
        
    async def execute_goal(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Execute a command with autonomous planning and execution."""
        from .llm_planner import plan_actions
        
        self.start_time = datetime.now()
        context = context or {}
        context.setdefault("execution_history", [])
        
        while not self._should_stop(context):
            # Get next action from planner
            plan_result = plan_actions(command, context)
            
            if plan_result["status"] == "completed":
                return {
                    "status": "completed",
                    "context": context,
                    "message": "Goal completed successfully"
                }
                
            if plan_result["status"] == "error":
                return {
                    "status": "error",
                    "context": context,
                    "message": plan_result.get("message", "Unknown error")
                }
                
            # Execute the next action
            action = plan_result["next_action"]
            execution_result = await self._execute_action(action, context)
            
            # Update context with execution result
            context["last_action"] = action
            context["last_result"] = execution_result
            context["last_observation"] = execution_result.get("observation", {})
            context["execution_history"].append({
                "action": action,
                "result": execution_result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update step counter
            context["current_step"] = context.get("current_step", 0) + 1
            
        return {
            "status": "timeout" if self._is_timed_out() else "max_steps_reached",
            "context": context,
            "message": "Execution stopped"
        }
        
    async def _execute_action(self, action: Dict, context: Dict) -> Dict[str, Any]:
        """Execute a single action and return the result."""
        from .task_executor import task_executor
        from .retry_manager import retry_manager
        
        try:
            # Add context to action
            action["context"] = {
                "current_url": context.get("current_url"),
                "session_id": context.get("session_id"),
                "task_id": context.get("task_id")
            }
            
            # Execute the action with retry logic
            retry_result = await retry_manager.execute_with_retry(action, task_executor.execute)
            
            if retry_result.get("ok", False):
                # Success - update context and get observation
                result = retry_result["result"]
                
                # Update context with new URL if navigation occurred
                if "url" in result and result["url"] != context.get("current_url"):
                    context["current_url"] = result["url"]
                    
                # Wait for DOM observation
                await asyncio.sleep(1)  # Give time for DOM to update
                
                # Get DOM observation
                dom_observation = await self._get_dom_observation(context.get("task_id"))
                
                return {
                    "success": True,
                    **result,
                    "observation": dom_observation,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_attempts": retry_result.get("attempts", 1)
                }
            else:
                # All retries failed
                if retry_result.get("requires_replan"):
                    # Trigger replan
                    context["requires_replan"] = True
                    context["replan_reason"] = retry_result.get("error", "Replan required")
                    context["failed_action"] = retry_result.get("original_action")
                    context["error_result"] = retry_result.get("error_result")
                
                return {
                    "success": False,
                    "error": retry_result.get("error", "Action failed after retries"),
                    "action": action,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_attempts": retry_result.get("attempts", 1),
                    "max_retries_exceeded": retry_result.get("max_retries_exceeded", False)
                }
            
        except Exception as e:
            logger.error(f"Error executing action {action}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_dom_observation(self, task_id: str) -> Dict:
        """Get DOM observation from the browser extension."""
        # This would send a message to the extension to get DOM snapshot
        # For now, return a placeholder
        # In a real implementation, you'd use websockets or another communication method
        return {
            "url": context.get("current_url", ""),
            "title": "Page Title",
            "text": "",
            "buttons": [],
            "inputs": [],
            "links": [],
            "specialElements": {},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _should_stop(self, context: Dict) -> bool:
        """Determine if execution should stop."""
        if context.get("status") in ["completed", "error"]:
            return True
            
        if self._is_timed_out():
            return True
            
        current_step = context.get("current_step", 0)
        return current_step >= self.max_steps
    
    def _is_timed_out(self) -> bool:
        """Check if execution has timed out."""
        if not self.start_time:
            return False
        return (datetime.now() - self.start_time) > self.timeout
