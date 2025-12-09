"""
API Endpoints for AutoPilot AI

Provides HTTP endpoints for interacting with the task executor.
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import logging

from .enhanced_task_executor import task_executor, TaskResult
from .context_manager import context_manager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoPilot AI API",
    description="API for executing and managing browser automation tasks",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None

class CommandResponse(BaseModel):
    task_id: str
    session_id: str
    status: str
    result: Optional[Dict] = None
    error: Optional[str] = None

@app.post("/execute", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """
    Execute a natural language command.
    
    The command will be analyzed and broken down into sub-tasks if needed.
    """
    try:
        # Generate a session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Execute the command
        result = await task_executor.execute_command(session_id, request.command)
        
        # Convert the result to a dict for the response
        response_data = {
            "task_id": result.task_id,
            "session_id": session_id,
            "status": result.status,
            "result": result.result,
            "error": result.error
        }
        
        return response_data
        
    except Exception as e:
        logger.exception("Error executing command")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get the current state of a session."""
    try:
        context = context_manager.load_context(session_id)
        return {
            "session_id": session_id,
            "current_tab": {
                "url": context.current_tab.url if context.current_tab else None,
                "title": context.current_tab.title if context.current_tab else None
            },
            "last_updated": context.last_updated.isoformat(),
            "actions_count": len(context.previous_actions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {str(e)}"
        )

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its context."""
    try:
        context_manager.clear_session(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
