"""
Context Manager for AutoPilot AI

Handles state management and context preservation between commands.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

@dataclass
class BrowserTabState:
    """Represents the state of a browser tab."""
    url: str
    title: str
    dom_snapshot: Optional[Dict[str, Any]] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CommandContext:
    """Context for the current command execution."""
    current_tab: Optional[BrowserTabState] = None
    previous_actions: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

class ContextManager:
    """Manages context and state for command execution."""
    
    def __init__(self, storage_path: str = "./context"):
        self.storage_path = storage_path
        self.contexts: Dict[str, CommandContext] = {}
        self.current_session_id: Optional[str] = None
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
    
    def create_session(self, session_id: str) -> CommandContext:
        """Create a new session context."""
        self.contexts[session_id] = CommandContext()
        self.current_session_id = session_id
        return self.contexts[session_id]
    
    def get_current_context(self) -> CommandContext:
        """Get the current command context."""
        if not self.current_session_id:
            raise ValueError("No active session")
        return self.contexts[self.current_session_id]
    
    def update_tab_state(self, url: str, title: str, dom_snapshot: Optional[Dict] = None):
        """Update the current tab state."""
        context = self.get_current_context()
        context.current_tab = BrowserTabState(
            url=url,
            title=title,
            dom_snapshot=dom_snapshot
        )
        context.last_updated = datetime.utcnow()
    
    def add_action(self, action: Dict[str, Any], result: Optional[Dict[str, Any]] = None):
        """Add a completed action to the context."""
        context = self.get_current_context()
        action_record = {
            "action": action,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        context.previous_actions.append(action_record)
        context.last_updated = datetime.utcnow()
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.get_current_context().variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """Set a variable in the context."""
        self.get_current_context().variables[name] = value
        self.get_current_context().last_updated = datetime.utcnow()
    
    def save_context(self, session_id: Optional[str] = None):
        """Save the current context to disk."""
        session_id = session_id or self.current_session_id
        if not session_id:
            raise ValueError("No session ID provided")
            
        context = self.contexts.get(session_id)
        if not context:
            return
            
        file_path = os.path.join(self.storage_path, f"{session_id}.json")
        with open(file_path, 'w') as f:
            # Convert dataclass to dict for JSON serialization
            context_dict = {
                "current_tab": {
                    "url": context.current_tab.url if context.current_tab else None,
                    "title": context.current_tab.title if context.current_tab else None,
                    "last_updated": context.current_tab.last_updated.isoformat() if context.current_tab else None
                },
                "previous_actions": context.previous_actions,
                "variables": context.variables,
                "last_updated": context.last_updated.isoformat()
            }
            json.dump(context_dict, f, indent=2)
    
    def load_context(self, session_id: str) -> CommandContext:
        """Load a context from disk."""
        file_path = os.path.join(self.storage_path, f"{session_id}.json")
        if not os.path.exists(file_path):
            return self.create_session(session_id)
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        context = CommandContext()
        if data["current_tab"] and data["current_tab"]["url"]:
            context.current_tab = BrowserTabState(
                url=data["current_tab"]["url"],
                title=data["current_tab"]["title"],
                last_updated=datetime.fromisoformat(data["current_tab"]["last_updated"])
            )
        
        context.previous_actions = data.get("previous_actions", [])
        context.variables = data.get("variables", {})
        context.last_updated = datetime.fromisoformat(data["last_updated"])
        
        self.contexts[session_id] = context
        self.current_session_id = session_id
        return context
    
    def clear_session(self, session_id: str):
        """Clear a session's context."""
        if session_id in self.contexts:
            del self.contexts[session_id]
        
        file_path = os.path.join(self.storage_path, f"{session_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if self.current_session_id == session_id:
            self.current_session_id = None

# Global context manager instance
context_manager = ContextManager()
