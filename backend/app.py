"""
AutoPilot AI Backend — Phase 1

Key Features:
- Enhanced AI Task Planner with multi-selector fallback
- Support for multiple LLM providers (OpenAI, Gemini, Claude, OLLAMA, Groq)
- Hinglish language support
- 3-level selector fallback system (CSS → XPath → Text)
- Auto-wait and retry logic
"""

import os
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Literal

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from llm_planner import plan_actions, autonomous_planner

# --- Configuration ---

class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    GROQ = "groq"

# Default settings
DEFAULT_LLM_PROVIDER = LLMProvider.OPENAI
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds

# --- Models ---

class PlanRequest(BaseModel):
    command: str
    llm_provider: Optional[LLMProvider] = DEFAULT_LLM_PROVIDER
    timeout_ms: int = DEFAULT_TIMEOUT_MS


class PlanResponse(BaseModel):
    actions: List[Dict[str, Any]]
    provider: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    status: str
    phase: int = 1
    llm_providers: List[str]
    active_provider: str


class VisionRequest(BaseModel):
    image_data: str
    hint: Optional[str] = None


class VisionResponse(BaseModel):
    ok: bool = True
    elements: List[Dict[str, Any]] = []
    message: Optional[str] = None


# Update 1: Autonomous execution models
class AutonomousActionRequest(BaseModel):
    goal: str
    observation: Dict[str, Any]
    step: int = 0
    history: List[Dict[str, Any]] = []


class AutonomousActionResponse(BaseModel):
    action: Optional[Dict[str, Any]] = None
    completed: bool = False
    reasoning: Optional[str] = None
    next_step_hint: Optional[str] = None


# --- LLM Provider Interface ---

class LLMProviderClient:
    """Base class for LLM providers"""
    
    async def generate_plan(self, command: str, **kwargs) -> List[Dict[str, Any]]:
        """Generate an action plan from natural language"""
        raise NotImplementedError()


class OpenAIClient(LLMProviderClient):
    """OpenAI API client"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            logger.warning("OPENAI_API_KEY not set. Using fallback planner.")
            raise ValueError("OPENAI_API_KEY not configured. Please update the .env file.")
    
    async def generate_plan(self, command: str, **kwargs):
        # In a real implementation, this would call the OpenAI API
        # For now, we'll use the heuristic planner as a fallback
        return plan_actions(command)


class GeminiClient(LLMProviderClient):
    """Google Gemini API client"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY not set. Using fallback planner.")
            raise ValueError("GEMINI_API_KEY not configured. Please update the .env file.")
    
    async def generate_plan(self, command: str, **kwargs):
        # Placeholder for Gemini API integration
        return plan_actions(command)


# Provider factory
async def get_llm_provider(provider: LLMProvider = DEFAULT_LLM_PROVIDER) -> LLMProviderClient:
    """Get the appropriate LLM provider client"""
    try:
        if provider == LLMProvider.OPENAI:
            try:
                return OpenAIClient()
            except ValueError as e:
                logger.warning(f"Falling back to HeuristicPlanner: {str(e)}")
                return HeuristicPlannerClient()
                
        elif provider == LLMProvider.GEMINI:
            try:
                return GeminiClient()
            except ValueError as e:
                logger.warning(f"Falling back to HeuristicPlanner: {str(e)}")
                return HeuristicPlannerClient()
                
        # Default to heuristic planner if provider not implemented
        return HeuristicPlannerClient()
        
    except Exception as e:
        logger.error(f"Error initializing {provider.value} client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize {provider.value} client: {str(e)}"
        )


# Fallback to heuristic planner
class HeuristicPlannerClient(LLMProviderClient):
    """Fallback to heuristic planner"""
    
    async def generate_plan(self, command: str, **kwargs):
        return plan_actions(command)


# --- FastAPI App ---

app = FastAPI(
    title="AutoPilot AI Backend — Phase 1",
    description="Enhanced AI Task Planner with multi-LLM support",
    version="1.0.0"
)


# --- API Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "phase": 1,
        "llm_providers": [p.value for p in LLMProvider],
        "active_provider": DEFAULT_LLM_PROVIDER.value
    }


@app.post("/plan", response_model=PlanResponse)
async def plan(
    request: PlanRequest,
    llm_provider: LLMProviderClient = Depends(get_llm_provider)
):
    """
    Convert natural language command into a structured action plan.
    
    Supports multiple LLM providers with fallback to heuristic planner.
    """
    import time
    
    start_time = time.time()
    
    try:
        # Generate the action plan using the selected provider
        actions = await llm_provider.generate_plan(
            command=request.command,
            timeout_ms=request.timeout_ms
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return PlanResponse(
            actions=actions,
            provider=llm_provider.__class__.__name__,
            processing_time_ms=round(processing_time_ms, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate plan: {str(e)}"
        )


@app.post("/vision/analyze", response_model=VisionResponse)
async def vision_analyze(req: VisionRequest):
    """Phase 3 placeholder: analyze a screenshot (base64) and return heuristic element hints.
    This is a stub; replace with actual Vision AI integration later."""
    # Minimal sanity check
    if not req.image_data or not isinstance(req.image_data, str):
        raise HTTPException(status_code=400, detail="image_data is required as base64 string")

    # Return mock suggestions to drive UI/engine integration
    hints = [
        {"label": "Subscribe button", "selector": "button, #subscribe-button, [aria-label*='Subscribe']"},
        {"label": "Search box", "selector": "input[type='text'], input[name='q'], input#search"},
    ]

    return VisionResponse(ok=True, elements=hints, message="Mock analysis — integrate real Vision API in Phase 4")


# Update 1: Autonomous execution endpoint
@app.post("/autonomous/next-action", response_model=AutonomousActionResponse)
async def autonomous_next_action(request: AutonomousActionRequest):
    """Get next action for autonomous execution based on goal and observation with SEE → THINK → ACT."""
    try:
        # Initialize or update the autonomous planner with the goal
        if not autonomous_planner.current_goal_state or autonomous_planner.current_goal_state.goal != request.goal:
            autonomous_planner.start_new_goal(request.goal)
        
        # Update planner state with latest observation
        autonomous_planner.update_state(request.observation)
        
        # Update 2: Use enhanced DOM interpretation for SEE → THINK → ACT
        next_actions = autonomous_planner.decide_next_step(request.observation)
        
        if not next_actions:
            # Goal completed or no more actions
            return AutonomousActionResponse(
                completed=True,
                reasoning="Goal completed or no further actions available"
            )
        
        # Return the first action from the list
        next_action = next_actions[0].dict() if hasattr(next_actions[0], 'dict') else next_actions[0]
        
        # Add reasoning based on current state and DOM interpretation
        current_step_info = ""
        reasoning = ""
        
        if autonomous_planner.current_goal_state:
            current_subtask = autonomous_planner.current_goal_state.subtasks[
                autonomous_planner.current_goal_state.current_step
            ] if autonomous_planner.current_goal_state.current_step < len(autonomous_planner.current_goal_state.subtasks) else "Unknown"
            current_step_info = f"Current step: {current_subtask}"
            
            # Check if action came from DOM interpretation
            dom = request.observation
            if dom and not dom.get('error'):
                page_type = dom.get('pageType', 'unknown')
                reasoning = f"SEE → THINK → ACT: Analyzed {page_type} page. {current_step_info}"
                
                # Add specific reasoning based on action type
                action_type = next_action.get('action', '')
                if action_type == 'clickElement':
                    reasoning += f" | Clicking element based on page analysis"
                elif action_type == 'typeText':
                    reasoning += f" | Typing in detected input field"
                elif action_type == 'scrollPage':
                    reasoning += f" | Scrolling to find more content"
                else:
                    reasoning += f" | Executing {action_type}"
            else:
                reasoning = f"Using fallback planning. {current_step_info}"
        
        return AutonomousActionResponse(
            action=next_action,
            completed=False,
            reasoning=reasoning,
            next_step_hint="Executing action and observing results..."
        )
        
    except Exception as e:
        logger.error(f"Error in autonomous_next_action: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to determine next action: {str(e)}"
        )

