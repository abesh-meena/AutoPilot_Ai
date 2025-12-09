"""
Enhanced Task Executor for AutoPilot AI

Handles execution of tasks with context management and command analysis.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

from .action_schema import Action, ActionType
from .context_manager import context_manager, CommandContext, BrowserTabState
from .command_analyzer import command_analyzer, CommandComplexity

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class TaskStep:
    """Represents a single step in a task."""
    action: Action
    status: TaskStatus = TaskStatus.PENDING
    attempt: int = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    depends_on: List[int] = field(default_factory=list)

@dataclass
class TaskResult:
    """Result of a completed task."""
    task_id: str
    status: TaskStatus
    steps_completed: int
    total_steps: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class EnhancedTaskExecutor:
    """Executes tasks with context management and command analysis."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.tasks: Dict[str, List[TaskStep]] = {}
        self.execution_hooks: Dict[str, Callable[[Action, CommandContext], Awaitable[Dict]]] = {}
        
        # Register default action handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default handlers for common action types."""
        # Basic actions
        self.register_handler(ActionType.OPEN_URL, self._handle_open_url)
        self.register_handler(ActionType.TYPE_TEXT, self._handle_type_text)
        self.register_handler(ActionType.CLICK_ELEMENT, self._handle_click_element)
        self.register_handler(ActionType.KEY_PRESS, self._handle_key_press)
        self.register_handler(ActionType.WAIT_FOR_ELEMENT, self._handle_wait_for_element)
        
        # Phase 4 action handlers
        self.register_handler(ActionType.PLAY_VIDEO, self._handle_play_video)
        self.register_handler(ActionType.PAUSE_VIDEO, self._handle_pause_video)
        self.register_handler(ActionType.OPEN_SETTINGS_MENU, self._handle_open_settings_menu)
        self.register_handler(ActionType.SET_QUALITY, self._handle_set_quality)
        self.register_handler(ActionType.CREATE_PLAYLIST, self._handle_create_playlist)
        self.register_handler(ActionType.ADD_TO_PLAYLIST, self._handle_add_to_playlist)
        self.register_handler(ActionType.SAVE_PLAYLIST, self._handle_save_playlist)
        self.register_handler(ActionType.OPEN_PLAYLIST, self._handle_open_playlist)
        self.register_handler(ActionType.PLAY_PLAYLIST, self._handle_play_playlist)
        self.register_handler(ActionType.WAIT_FOR_NAVIGATION, self._handle_wait_for_navigation)
        self.register_handler(ActionType.RETRY_ACTION, self._handle_retry_action)
        self.register_handler(ActionType.SCROLL_UNTIL_FOUND, self._handle_scroll_until_found)
    
    def register_handler(self, action_type: Union[str, ActionType], 
                        handler: Callable[[Action, CommandContext], Awaitable[Dict]]):
        """Register a handler for a specific action type."""
        if isinstance(action_type, ActionType):
            action_type = action_type.value
        self.execution_hooks[action_type] = handler
    
    async def execute_command(self, session_id: str, command: str) -> TaskResult:
        """
        Execute a natural language command with context management.
        
        This is the main entry point for executing commands. It will:
        1. Analyze the command complexity
        2. Break it down into sub-tasks if needed
        3. Execute each sub-task in order
        4. Maintain context between sub-tasks
        """
        # Load or create session context
        try:
            context = context_manager.load_context(session_id)
        except Exception as e:
            logger.error(f"Error loading context for session {session_id}: {e}")
            context = context_manager.create_session(session_id)
        
        # Analyze command complexity
        complexity = command_analyzer.analyze_complexity(command)
        logger.info(f"Command complexity: {complexity}")
        
        # Create a task ID
        task_id = f"{session_id}_{int(datetime.utcnow().timestamp())}"
        
        if complexity == CommandComplexity.SIMPLE:
            # For simple commands, execute directly
            actions = await self._plan_actions(command, context)
            return await self._execute_task(task_id, actions, context)
        else:
            # For complex commands, break them down
            subtasks = command_analyzer.split_into_subtasks(command)
            logger.info(f"Command broken down into {len(subtasks)} sub-tasks")
            
            all_actions = []
            for i, subtask in enumerate(subtasks, 1):
                logger.info(f"Planning sub-task {i}/{len(subtasks)}: {subtask['command']}")
                actions = await self._plan_actions(subtask["command"], context)
                all_actions.extend(actions)
                
                # Update context with the planned actions
                for action in actions:
                    context_manager.add_action(action.dict())
            
            # Execute all actions as a single task
            return await self._execute_task(task_id, all_actions, context)
    
    async def _plan_actions(self, command: str, context: CommandContext) -> List[Action]:
        """Convert a command into a list of actions."""
        # TODO: Integrate with your existing LLM planner
        # For now, return a simple action
        from .llm_planner import plan_actions  # Import here to avoid circular imports
        return [Action(**action) for action in plan_actions(command)]
    
    async def _execute_task(self, task_id: str, actions: List[Action], 
                          context: CommandContext) -> TaskResult:
        """Execute a list of actions as a task."""
        task_steps = [TaskStep(action=action) for action in actions]
        self.tasks[task_id] = task_steps
        
        results = []
        
        for i, step in enumerate(task_steps, 1):
            step.status = TaskStatus.RUNNING
            
            # Check dependencies
            for dep_idx in step.depends_on:
                if dep_idx >= 0 and dep_idx < len(task_steps):
                    dep_step = task_steps[dep_idx]
                    if dep_step.status != TaskStatus.COMPLETED:
                        error_msg = f"Dependency {dep_idx} not completed for step {i}"
                        logger.error(error_msg)
                        step.status = TaskStatus.FAILED
                        step.error = error_msg
                        
                        return TaskResult(
                            task_id=task_id,
                            status=TaskStatus.FAILED,
                            steps_completed=i-1,
                            total_steps=len(task_steps),
                            error=error_msg
                        )
            
            # Execute the step with retries
            while step.attempt < self.max_retries:
                try:
                    logger.info(f"Executing step {i}/{len(task_steps)}: {step.action.action}")
                    
                    # Get the appropriate handler
                    action_type = step.action.action
                    handler = self.execution_hooks.get(action_type.value)
                    
                    if not handler:
                        raise ValueError(f"No handler registered for action type: {action_type}")
                    
                    # Execute the handler with context
                    result = await handler(step.action, context)
                    
                    # Update step status and context
                    step.status = TaskStatus.COMPLETED
                    step.result = result
                    results.append(result)
                    
                    # Update context with the completed action
                    context_manager.add_action(step.action.dict(), result)
                    
                    # Save context after successful step
                    context_manager.save_context()
                    
                    break
                    
                except Exception as e:
                    step.attempt += 1
                    step.error = str(e)
                    
                    if step.attempt >= self.max_retries:
                        step.status = TaskStatus.FAILED
                        logger.error(f"Step {i} failed after {self.max_retries} attempts: {e}")
                        
                        # Save context before failing
                        context_manager.save_context()
                        
                        return TaskResult(
                            task_id=task_id,
                            status=TaskStatus.FAILED,
                            steps_completed=i-1,
                            total_steps=len(task_steps),
                            error=f"Step {i} failed: {e}",
                            result={"steps": [s.__dict__ for s in task_steps]}
                        )
                    
                    # Wait before retrying
                    step.status = TaskStatus.RETRYING
                    logger.warning(f"Step {i} failed (attempt {step.attempt}/{self.max_retries}), retrying...")
                    await asyncio.sleep(self.retry_delay)
        
        # All steps completed successfully
        context_manager.save_context()
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            steps_completed=len(task_steps),
            total_steps=len(task_steps),
            result={"steps": [s.__dict__ for s in task_steps]}
        )
    
    # Handler implementations
    async def _handle_open_url(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Opening URL: {action.url}")
        # TODO: Implement actual URL opening logic
        context_manager.update_tab_state(action.url, "Loading...")
        return {"status": "success", "url": action.url}
    
    async def _handle_type_text(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Typing text: {action.text}")
        # TODO: Implement actual text typing logic
        return {"status": "success", "text_entered": action.text}
    
    async def _handle_click_element(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Clicking element: {action.selector}")
        # TODO: Implement actual element clicking logic
        return {"status": "success", "element_clicked": action.selector}
    
    async def _handle_key_press(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Pressing key: {action.key}")
        # TODO: Implement actual key press logic
        return {"status": "success", "key_pressed": action.key}
    
    async def _handle_wait_for_element(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Waiting for element: {action.selector}")
        # TODO: Implement actual wait logic
        await asyncio.sleep(action.timeout_ms / 1000)
        return {"status": "success", "element_found": True}
    
    # Phase 4 action handlers - implement these with actual logic
    async def _handle_play_video(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Playing video")
        return {"status": "success", "action": "play_video"}
    
    async def _handle_pause_video(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Pausing video")
        return {"status": "success", "action": "pause_video"}
    
    async def _handle_open_settings_menu(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Opening settings menu")
        return {"status": "success", "action": "open_settings_menu"}
    
    async def _handle_set_quality(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Setting video quality to: {action.quality}")
        return {"status": "success", "action": "set_quality", "quality": action.quality}
    
    async def _handle_create_playlist(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Creating playlist: {action.playlist_name}")
        return {"status": "success", "action": "create_playlist", "name": action.playlist_name}
    
    async def _handle_add_to_playlist(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Adding to playlist: {action.playlist_name}")
        return {"status": "success", "action": "add_to_playlist", "item": action.playlist_item}
    
    async def _handle_save_playlist(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Saving playlist")
        return {"status": "success", "action": "save_playlist"}
    
    async def _handle_open_playlist(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Opening playlist: {action.playlist_name}")
        return {"status": "success", "action": "open_playlist", "name": action.playlist_name}
    
    async def _handle_play_playlist(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Playing playlist: {action.playlist_name}")
        return {"status": "success", "action": "play_playlist", "name": action.playlist_name}
    
    async def _handle_wait_for_navigation(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Waiting for navigation to complete")
        await asyncio.sleep(2)  # Simulate waiting
        return {"status": "success", "action": "wait_for_navigation"}
    
    async def _handle_retry_action(self, action: Action, context: CommandContext) -> Dict:
        logger.info("Retrying previous action")
        return {"status": "success", "action": "retry_action"}
    
    async def _handle_scroll_until_found(self, action: Action, context: CommandContext) -> Dict:
        logger.info(f"Scrolling until element is found: {action.selector}")
        return {"status": "success", "action": "scroll_until_found", "selector": action.selector}

# Global task executor instance
task_executor = EnhancedTaskExecutor()
