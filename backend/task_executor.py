"""
Task Execution Engine for AutoPilot AI

Handles execution of multi-step tasks with error recovery and retry logic.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from pydantic import BaseModel, Field

from .action_schema import Action, ActionType, SelectorStrategy, create_action

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class TaskStep(BaseModel):
    """Represents a single step in a task."""
    action: Action
    status: TaskStatus = TaskStatus.PENDING
    attempt: int = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class TaskResult(BaseModel):
    """Result of a completed task."""
    task_id: str
    status: TaskStatus
    steps_completed: int
    total_steps: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskExecutor:
    """Executes tasks with retry and error handling."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.tasks: Dict[str, List[TaskStep]] = {}
        self.execution_hooks: Dict[str, Callable[[str, Dict], Awaitable[Dict]]] = {}
        
        # Register default action handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default handlers for common action types."""
        self.register_handler(ActionType.OPEN_URL, self._handle_open_url)
        self.register_handler(ActionType.TYPE_TEXT, self._handle_type_text)
        self.register_handler(ActionType.CLICK_ELEMENT, self._handle_click_element)
        self.register_handler(ActionType.KEY_PRESS, self._handle_key_press)
        self.register_handler(ActionType.WAIT_FOR_ELEMENT, self._handle_wait_for_element)
        
        # New Phase 4 action handlers
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
    
    def register_handler(self, action_type: Union[str, ActionType], handler: Callable):
        """Register a handler for a specific action type.
        
        Args:
            action_type: Either a string or ActionType enum value
            handler: The function to handle the action
        """
        if isinstance(action_type, ActionType):
            action_type = action_type.value
        self.execution_hooks[action_type] = handler
    
    async def execute_task(self, task_id: str, actions: List[Dict]) -> TaskResult:
        """Execute a task with the given actions."""
        if task_id in self.tasks:
            raise ValueError(f"Task with ID {task_id} already exists")
        
        # Convert dicts to Action objects
        task_steps = []
        for i, action_dict in enumerate(actions):
            try:
                action = Action(**action_dict)
                task_steps.append(TaskStep(action=action))
                logger.debug(f"Created action {i}: {action.action} with data: {action_dict}")
            except Exception as e:
                logger.error(f"Error creating action from dict: {action_dict}")
                raise ValueError(f"Invalid action at index {i}: {str(e)}")
                
        self.tasks[task_id] = task_steps
        logger.info(f"Task {task_id} created with {len(task_steps)} steps")
        
        results = []
        
        for i, step in enumerate(task_steps, 1):
            step.status = TaskStatus.RUNNING
            
            # Execute the step with retries
            while step.attempt < self.max_retries:
                try:
                    logger.info(f"Executing step {i}/{len(task_steps)}: {step.action.action}")
                    
                    # Get the appropriate handler
                    action_type = step.action.action  # This is the ActionType enum
                    logger.debug(f"Processing action: {action_type} (type: {type(action_type).__name__})")
                    
                    # Log all available handlers for debugging
                    logger.debug(f"Available handlers: {list(self.execution_hooks.keys())}")
                    
                    # Try to get the handler using the enum value
                    handler = self.execution_hooks.get(action_type.value)
                    
                    if not handler:
                        # Try to find a matching handler by string comparison as fallback
                        for key, h in self.execution_hooks.items():
                            if key.lower() == action_type.value.lower():
                                handler = h
                                logger.warning(f"Found case-insensitive match for handler: {key}")
                                break
                    
                    if not handler:
                        raise ValueError(
                            f"No handler registered for action type: {action_type} (value: {action_type.value})\n                            "f"Available handlers: {list(self.execution_hooks.keys())}"
                        )
                        
                    logger.debug(f"Found handler for action type {action_type}: {handler.__name__}")
                    
                    # Execute the handler
                    result = await handler(step.action)
                    
                    # Update step status
                    step.status = TaskStatus.COMPLETED
                    step.result = result
                    results.append(result)
                    break
                    
                except Exception as e:
                    step.attempt += 1
                    step.error = str(e)
                    
                    if step.attempt >= self.max_retries:
                        step.status = TaskStatus.FAILED
                        logger.error(f"Step {i} failed after {self.max_retries} attempts: {e}")
                        
                        # Return partial results if some steps succeeded
                        return TaskResult(
                            task_id=task_id,
                            status=TaskStatus.FAILED,
                            steps_completed=i-1,
                            total_steps=len(task_steps),
                            error=f"Step {i} failed: {e}",
                            result={"steps": [s.dict() for s in task_steps]}
                        )
                    
                    # Wait before retrying
                    step.status = TaskStatus.RETRYING
                    logger.warning(f"Step {i} failed (attempt {step.attempt}/{self.max_retries}), retrying...")
                    await asyncio.sleep(self.retry_delay)
        
        # All steps completed successfully
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            steps_completed=len(task_steps),
            total_steps=len(task_steps),
            result={"steps": [s.dict() for s in task_steps]}
        )
    
    # --- Default Action Handlers ---
    
    async def _handle_open_url(self, action: Action) -> Dict:
        # In a real implementation, this would use a browser automation library
        logger.info(f"Opening URL: {action.url}")
        return {"status": "success", "url": action.url}
    
    async def _handle_type_text(self, action: Action) -> Dict:
        logger.info(f"Typing text '{action.text}' into {action.selector}")
        return {"status": "success", "text_entered": action.text}
    
    async def _handle_click_element(self, action: Action) -> Dict:
        logger.info(f"Clicking element: {action.selector}")
        return {"status": "success", "element_clicked": action.selector}
    
    async def _handle_key_press(self, action: Action) -> Dict:
        logger.info(f"Pressing key: {action.key}")
        return {"status": "success", "key_pressed": action.key}
    
    async def _handle_wait_for_element(self, action: Action) -> Dict:
        logger.info(f"Waiting for element: {action.selector} (timeout: {action.timeout_ms}ms)")
        return {"status": "success", "element_found": action.selector}
    
    # --- Phase 4 Action Handlers ---
    
    async def _handle_play_video(self, action: Action) -> Dict:
        logger.info("Playing video")
        return {"status": "success", "action": "play_video"}
    
    async def _handle_pause_video(self, action: Action) -> Dict:
        logger.info("Pausing video")
        return {"status": "success", "action": "pause_video"}
    
    async def _handle_open_settings_menu(self, action: Action) -> Dict:
        logger.info("Opening settings menu")
        return {"status": "success", "action": "open_settings_menu"}
    
    async def _handle_set_quality(self, action: Action) -> Dict:
        quality = getattr(action, 'quality', 'auto')
        logger.info(f"Setting video quality to: {quality}")
        return {"status": "success", "action": "set_quality", "quality": quality}
    
    async def _handle_create_playlist(self, action: Action) -> Dict:
        name = getattr(action, 'name', 'New Playlist')
        logger.info(f"Creating playlist: {name}")
        return {"status": "success", "action": "create_playlist", "name": name}
    
    async def _handle_add_to_playlist(self, action: Action) -> Dict:
        item = getattr(action, 'item', 'current_video')
        playlist = getattr(action, 'playlist', 'default')
        logger.info(f"Adding {item} to playlist: {playlist}")
        return {"status": "success", "action": "add_to_playlist", "item": item, "playlist": playlist}
    
    async def _handle_save_playlist(self, action: Action) -> Dict:
        logger.info("Saving playlist")
        return {"status": "success", "action": "save_playlist"}
    
    async def _handle_open_playlist(self, action: Action) -> Dict:
        name = getattr(action, 'name', 'default')
        logger.info(f"Opening playlist: {name}")
        return {"status": "success", "action": "open_playlist", "name": name}
    
    async def _handle_play_playlist(self, action: Action) -> Dict:
        name = getattr(action, 'name', 'default')
        logger.info(f"Playing playlist: {name}")
        return {"status": "success", "action": "play_playlist", "name": name}
    
    async def _handle_wait_for_navigation(self, action: Action) -> Dict:
        timeout = getattr(action, 'timeout_ms', 10000)
        logger.info(f"Waiting for navigation (timeout: {timeout}ms)")
        return {"status": "success", "action": "wait_for_navigation", "timeout_ms": timeout}
    
    async def _handle_retry_action(self, action: Action) -> Dict:
        max_retries = getattr(action, 'max_retries', 3)
        logger.info(f"Retrying action (max_retries: {max_retries})")
        return {"status": "success", "action": "retry_action", "max_retries": max_retries}
    
    async def _handle_scroll_until_found(self, action: Action) -> Dict:
        selector = getattr(action, 'selector', '')
        logger.info(f"Scrolling until element is found: {selector}")
        return {"status": "success", "action": "scroll_until_found", "selector": selector}
