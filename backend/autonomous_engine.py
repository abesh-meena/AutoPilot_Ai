"""
Autonomous Execution Engine for AutoPilot AI

The core autonomous agent that executes high-level goals end-to-end.
This is the main engine that powers Update 4 - True Autonomous Agent Mode.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from goal_engine import Goal, TaskGraph, Subgoal, goal_interpreter, subgoal_decomposer
from goal_checker import goal_checker
from llm_planner import plan_actions
from autonomous_executor import AutonomousExecutor
import json

logger = logging.getLogger(__name__)

class AutonomousEngine:
    """Main autonomous execution engine for goal-driven tasks."""
    
    def __init__(self, max_execution_time: int = 300, max_subgoals: int = 10):
        self.max_execution_time = timedelta(seconds=max_execution_time)
        self.max_subgoals = max_subgoals
        self.executor = AutonomousExecutor()
        self.execution_history = []
        
    async def execute_goal(self, user_command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a high-level goal autonomously from start to finish.
        
        Args:
            user_command: The user's natural language command
            context: Optional execution context
            
        Returns:
            Dict containing the final result and execution details
        """
        start_time = datetime.utcnow()
        context = context or {}
        
        try:
            # Step 1: Extract and interpret the goal
            logger.info(f"Interpreting goal from command: {user_command}")
            goal = goal_interpreter.extract_goal(user_command)
            logger.info(f"Goal extracted: {goal.goal_statement}")
            
            # Step 2: Decompose goal into subgoals
            logger.info("Decomposing goal into subgoals...")
            subgoals = subgoal_decomposer.decompose_goal(goal)
            
            # Limit subgoals if too many
            if len(subgoals) > self.max_subgoals:
                subgoals = subgoals[:self.max_subgoals]
                logger.warning(f"Limited subgoals to {self.max_subgoals}")
            
            # Step 3: Create task execution graph
            task_graph = TaskGraph(subgoals)
            logger.info(f"Created task graph with {len(subgoals)} subgoals")
            
            # Step 4: Execute autonomous loop
            execution_state = await self._run_autonomous_loop(goal, task_graph, context, start_time)
            
            # Step 5: Check goal completion
            completion_check = goal_checker.check_goal_completion(goal, task_graph, execution_state)
            
            # Step 6: Generate final output
            final_output = self._generate_final_output(goal, completion_check, execution_state)
            
            # Record execution
            execution_record = {
                "goal": goal.goal_statement,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.utcnow() - start_time).total_seconds(),
                "completed": completion_check["completed"],
                "subgoals_completed  ": len(task_graph.completed),
                "total_subgoals": len(subgoals)
            }
            self.execution_history.append(execution_record)
            
            return final_output
            
        except Exception as e:
            logger.error(f"Autonomous execution failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "goal": user_command,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _run_autonomous_loop(self, goal: Goal, task_graph: TaskGraph, 
                             context: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """Run the main autonomous execution loop."""
        execution_state = {
            "collected_data": [],
            "results": [],
            "dom_state": {},
            "total_actions": 0,
            "errors_encountered": 0,
            "retry_attempts": 0,
            "subgoal_results": {}
        }
        
        while not task_graph.is_complete():
            # Check timeout
            if datetime.utcnow() - start_time > self.max_execution_time:
                logger.warning("Execution timeout reached")
                break
            
            # Get next subgoal to execute
            current_subgoal = task_graph.get_next_subgoal()
            if not current_subgoal:
                logger.warning("No more subgoals to execute")
                break
            
            logger.info(f"Executing subgoal: {current_subgoal.description}")
            
            # Execute subgoal
            subgoal_result = await self._execute_subgoal(
                current_subgoal, 
                goal, 
                context, 
                execution_state
            )
            
            # Store subgoal result
            execution_state["subgoal_results"][current_subgoal.id] = subgoal_result
            
            # Check if subgoal was completed successfully
            subgoal_completion = goal_checker.check_subgoal_completion(
                current_subgoal, 
                execution_state
            )
            
            if subgoal_completion["completed"]:
                task_graph.mark_completed(current_subgoal.id)
                logger.info(f"Subgoal {current_subgoal.id} completed successfully")
                
                # Collect any data from this subgoal
                if "data" in subgoal_result:
                    execution_state["collected_data"].extend(subgoal_result["data"])
            else:
                task_graph.mark_failed(current_subgoal.id)
                logger.warning(f"Subgoal {current_subgoal.id} failed: {subgoal_completion['reason']}")
                
                # Decide whether to continue or abort
                if not self._should_continue_on_failure(current_subgoal, task_graph):
                    logger.error("Critical subgoal failed, aborting execution")
                    break
            
            # Update progress
            progress = task_graph.get_progress()
            logger.info(f"Progress: {progress['progress_percentage']:.1f}% ({progress['completed']}/{progress['total_subgoals']})")
        
        # Calculate execution time
        execution_state["execution_time"] = (datetime.utcnow() - start_time).total_seconds()
        
        return execution_state
    
    async def _execute_subgoal(self, subgoal: Subgoal, goal: Goal, 
                             context: Dict[str, Any], execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single subgoal using the planner and executor."""
        subgoal_context = context.copy()
        subgoal_context.update({
            "current_subgoal": subgoal.description,
            "subgoal_id": subgoal.id,
            "goal": goal.goal_statement,
            "success_criteria": subgoal.success_criteria
        })
        
        # Generate plan for this subgoal
        subgoal_command = f"{subgoal.description} for {goal.goal_statement}"
        
        # Execute the subgoal using the autonomous executor
        result = await self.executor.execute_goal(subgoal_command, subgoal_context)
        
        # Update execution state
        execution_state["total_actions"] += result.get("total_actions", 0)
        execution_state["errors_encountered"] += result.get("errors_encountered", 0)
        execution_state["retry_attempts"] += result.get("retry_attempts", 0)
        
        # Extract any data from the result
        if "result" in result and isinstance(result["result"], dict):
            if "data" in result["result"]:
                execution_state["results"].append(result["result"]["data"])
            if "dom_observation" in result["result"]:
                execution_state["dom_state"] = result["result"]["dom_observation"]
        
        return result
    
    def _should_continue_on_failure(self, failed_subgoal: Subgoal, task_graph: TaskGraph) -> bool:
        """Determine if execution should continue after a subgoal failure."""
        # Critical subgoals that should abort execution
        critical_patterns = ["navigate", "search", "access"]
        
        failed_description = failed_subgoal.description.lower()
        
        # If critical subgoal failed, don't continue
        if any(pattern in failed_description for pattern in critical_patterns):
            return False
        
        # If more than 50% of subgoals have failed, don't continue
        progress = task_graph.get_progress()
        if progress["failed"] > progress["total_subgoals"] * 0.5:
            return False
        
        # Otherwise, continue with remaining subgoals
        return True
    
    def _generate_final_output(self, goal: Goal, completion_check: Dict[str, Any], 
                             execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final structured output."""
        base_output = {
            "status": "success" if completion_check["completed"] else "partial",
            "goal": goal.goal_statement,
            "original_command": goal.original_command,
            "success_condition": goal.success_condition,
            "timestamp": datetime.utcnow().isoformat(),
            "completion_check": completion_check
        }
        
        if completion_check["completed"]:
            # Successful completion
            base_output.update({
                "results": execution_state.get("collected_data", []),
                "execution_summary": completion_check.get("execution_summary", {}),
                "quality_score": completion_check.get("quality_score", 0),
                "message": "Goal completed successfully"
            })
        else:
            # Partial or failed completion
            base_output.update({
                "partial_results": execution_state.get("collected_data", []),
                "reason": completion_check.get("reason", "Goal not completed"),
                "progress": completion_check.get("progress", {}),
                "message": "Goal partially completed or failed"
            })
        
        # Add execution statistics
        base_output["statistics"] = {
            "total_actions": execution_state.get("total_actions", 0),
            "execution_time": execution_state.get("execution_time", 0),
            "errors_encountered": execution_state.get("errors_encountered", 0),
            "retry_attempts": execution_state.get("retry_attempts", 0),
            "subgoals_completed": len(completion_check.get("progress", {}).get("completed", []))
        }
        
        return base_output
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get statistics about all executions."""
        if not self.execution_history:
            return {"total_executions": 0}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history if record["completed"])
        
        avg_duration = sum(record["duration"] for record in self.execution_history) / total_executions
        avg_subgoals = sum(record["total_subgoals"] for record in self.execution_history) / total_executions
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (successful_executions / total_executions) * 100,
            "average_duration": avg_duration,
            "average_subgoals": avg_subgoals,
            "recent_executions": self.execution_history[-5:]  # Last 5 executions
        }

# Global instance
autonomous_engine = AutonomousEngine()
