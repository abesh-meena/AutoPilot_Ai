"""
Command Analyzer for AutoPilot AI

Analyzes and breaks down complex commands into simpler sub-tasks.
"""
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum, auto
import re
import logging

logger = logging.getLogger(__name__)

class CommandComplexity(Enum):
    SIMPLE = auto()
    MEDIUM = auto()
    COMPLEX = auto()

class CommandAnalyzer:
    """Analyzes commands and breaks them down into sub-tasks."""
    
    # Keywords that indicate command separation
    SEPARATORS = ["and", "then", "after that", "next", "phir", "aur"]
    
    # Keywords that indicate complex operations
    COMPLEX_KEYWORDS = [
        "create", "make", "build", "generate", "set up", "configure",
        "search", "find", "look up", "khojo", "dhundho"
    ]
    
    def __init__(self, min_words_for_complex: int = 8):
        self.min_words_for_complex = min_words_for_complex
    
    def analyze_complexity(self, command: str) -> CommandComplexity:
        """Analyze the complexity of a command."""
        words = command.lower().split()
        word_count = len(words)
        
        # Check for explicit complexity indicators
        if any(sep in command.lower() for sep in self.SEPARATORS):
            return CommandComplexity.COMPLEX
            
        # Check for complex keywords
        if any(keyword in command.lower() for keyword in self.COMPLEX_KEYWORDS):
            return CommandComplexity.MEDIUM
            
        # Use word count as a fallback
        if word_count >= self.min_words_for_complex:
            return CommandComplexity.COMPLEX
        elif word_count > 4:
            return CommandComplexity.MEDIUM
        else:
            return CommandComplexity.SIMPLE
    
    def split_into_subtasks(self, command: str) -> List[Dict[str, Any]]:
        """Split a complex command into simpler sub-tasks."""
        # First, try to split by common separators
        subtasks = self._split_by_separators(command)
        
        # If no separators found, try to break down based on complexity
        if len(subtasks) <= 1:
            subtasks = self._break_down_complex_command(command)
        
        return subtasks
    
    def _split_by_separators(self, command: str) -> List[Dict[str, Any]]:
        """Split command by common separators."""
        # Create a regex pattern that matches any of the separators
        pattern = r'\s+(' + '|'.join(re.escape(sep) for sep in self.SEPARATORS) + r')\s+'
        
        # Split and clean up the results
        parts = re.split(pattern, command, flags=re.IGNORECASE)
        
        # Recombine the separators with their following commands
        subtasks = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue
                
            # If this part is a separator, combine it with the next part
            if part.lower() in self.SEPARATORS and i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                if next_part:
                    subtasks.append({"command": next_part, "connector": part})
                    i += 2
                    continue
            
            # Otherwise, add as a standalone command
            if part.lower() not in self.SEPARATORS:
                subtasks.append({"command": part})
            i += 1
        
        return subtasks
    
    def _break_down_complex_command(self, command: str) -> List[Dict[str, Any]]:
        """Break down a complex command into simpler sub-tasks."""
        # This is a simplified version - in a real implementation, you might use an LLM
        # to break down the command more intelligently
        
        # For now, we'll just split long commands into logical chunks
        words = command.split()
        if len(words) <= 6:
            return [{"command": command}]
        
        # Try to find natural breakpoints (commas, conjunctions, etc.)
        breakpoints = []
        for i, word in enumerate(words):
            if word.lower() in ["and", "or", "then", "after"] and i > 0 and i < len(words) - 1:
                breakpoints.append(i)
        
        # If no natural breakpoints, split in half
        if not breakpoints:
            mid = len(words) // 2
            return [
                {"command": " ".join(words[:mid])},
                {"command": " ".join(words[mid:]), "connector": "and"}
            ]
        
        # Otherwise, split at the most central breakpoint
        mid_point = len(words) // 2
        best_break = min(breakpoints, key=lambda x: abs(x - mid_point))
        
        return [
            {"command": " ".join(words[:best_break])},
            {"command": " ".join(words[best_break:]), "connector": words[best_break].lower()}
        ]
    
    def generate_subtask_prompt(self, command: str, context: Dict[str, Any]) -> str:
        """Generate a prompt for an LLM to break down a complex command."""
        return f"""You are a command analysis assistant. Break down the following command into atomic, executable sub-tasks.

Current Context:
- Current URL: {context.get('current_url', 'N/A')}
- Previous Actions: {len(context.get('previous_actions', []))} actions performed

Command to analyze: "{command}"

Please provide the sub-tasks in the following JSON format:
[
  {{
    "command": "The first sub-command to execute",
    "description": "What this sub-command aims to accomplish",
    "depends_on": []  // Any previous sub-task indices this depends on
  }}
]

Return only the JSON array, nothing else."""

# Global analyzer instance
command_analyzer = CommandAnalyzer()
