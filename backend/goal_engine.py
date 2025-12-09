"""
High-Level Goals Engine for AutoPilot AI

Transforms user commands into autonomous goal-driven execution.
This is the core of Update 4 - making AutoPilot AI a true autonomous agent.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)

class GoalType(str, Enum):
    SEARCH = "search"
    EXTRACTION = "extraction"
    NAVIGATION = "navigation"
    COMPARISON = "comparison"
    ANALYSIS = "analysis"
    INTERACTION = "interaction"
    MONITORING = "monitoring"

@dataclass
class Goal:
    """Represents a high-level user goal."""
    original_command: str
    goal_statement: str
    success_condition: str
    goal_type: GoalType
    priority: str = "medium"  # high, medium, low
    estimated_steps: int = 5
    domain: str = "general"

@dataclass
class Subgoal:
    """Represents a subgoal in the execution plan."""
    id: str
    description: str
    dependencies: List[str]  # IDs of subgoals that must be completed first
    success_criteria: str
    estimated_actions: int = 3
    status: str = "pending"  # pending, in_progress, completed, failed

class TaskGraph:
    """Manages the execution graph of subgoals."""
    
    def __init__(self, subgoals: List[Subgoal]):
        self.subgoals = {sg.id: sg for sg in subgoals}
        self.completed = []
        self.current = None
        self.execution_order = self._calculate_execution_order()
        
    def _calculate_execution_order(self) -> List[str]:
        """Calculate the optimal execution order based on dependencies."""
        order = []
        visited = set()
        
        def visit(subgoal_id: str):
            if subgoal_id in visited:
                return
            visited.add(subgoal_id)
            
            # Visit dependencies first
            for dep_id in self.subgoals[subgoal_id].dependencies:
                if dep_id in self.subgoals:
                    visit(dep_id)
            
            order.append(subgoal_id)
        
        for subgoal_id in self.subgoals:
            visit(subgoal_id)
        
        return order
    
    def get_next_subgoal(self) -> Optional[Subgoal]:
        """Get the next subgoal to execute."""
        for subgoal_id in self.execution_order:
            if subgoal_id not in self.completed:
                subgoal = self.subgoals[subgoal_id]
                
                # Check if all dependencies are completed
                deps_completed = all(
                    dep_id in self.completed 
                    for dep_id in subgoal.dependencies
                )
                
                if deps_completed:
                    self.current = subgoal_id
                    return subgoal
        
        return None
    
    def mark_completed(self, subgoal_id: str):
        """Mark a subgoal as completed."""
        if subgoal_id in self.subgoals:
            self.subgoals[subgoal_id].status = "completed"
            self.completed.append(subgoal_id)
    
    def mark_failed(self, subgoal_id: str):
        """Mark a subgoal as failed."""
        if subgoal_id in self.subgoals:
            self.subgoals[subgoal_id].status = "failed"
    
    def is_complete(self) -> bool:
        """Check if all subgoals are completed."""
        return len(self.completed) == len(self.subgoals)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress status."""
        total = len(self.subgoals)
        completed = len(self.completed)
        failed = len([sg for sg in self.subgoals.values() if sg.status == "failed"])
        
        return {
            "total_subgoals": total,
            "completed": completed,
            "failed": failed,
            "remaining": total - completed - failed,
            "progress_percentage": (completed / total) * 100 if total > 0 else 0,
            "current_subgoal": self.current
        }

class GoalInterpreter:
    """Interprets user commands and extracts high-level goals."""
    
    def __init__(self):
        self.goal_patterns = {
            GoalType.SEARCH: [
                r"search\s+(?:for\s+)?(.+)",
                r"find\s+(.+)",
                r"look\s+for\s+(.+)",
                r"khojo\s+(.+)",
                r"dhundho\s+(.+)"
            ],
            GoalType.EXTRACTION: [
                r"extract\s+(.+)",
                r"get\s+(.+)",
                r"collect\s+(.+)",
                r"gather\s+(.+)",
                r"list\s+(.+)"
            ],
            GoalType.COMPARISON: [
                r"compare\s+(.+)",
                r"which\s+is\s+(.+)",
                r"best\s+(.+)",
                r"cheapest\s+(.+)"
            ],
            GoalType.ANALYSIS: [
                r"analyze\s+(.+)",
                r"summarize\s+(.+)",
                r"review\s+(.+)"
            ]
        }
    
    def extract_goal(self, user_command: str) -> Goal:
        """Extract a structured goal from user command."""
        command_lower = user_command.lower()
        
        # Detect goal type
        goal_type = self._detect_goal_type(command_lower)
        
        # Extract goal statement
        goal_statement = self._extract_goal_statement(user_command, goal_type)
        
        # Generate success condition
        success_condition = self._generate_success_condition(goal_statement, goal_type)
        
        # Determine domain
        domain = self._detect_domain(user_command)
        
        # Estimate complexity
        estimated_steps = self._estimate_complexity(goal_statement, goal_type)
        
        return Goal(
            original_command=user_command,
            goal_statement=goal_statement,
            success_condition=success_condition,
            goal_type=goal_type,
            domain=domain,
            estimated_steps=estimated_steps
        )
    
    def _detect_goal_type(self, command: str) -> GoalType:
        """Detect the type of goal from the command."""
        for goal_type, patterns in self.goal_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return goal_type
        
        return GoalType.NAVIGATION  # Default
    
    def _extract_goal_statement(self, command: str, goal_type: GoalType) -> str:
        """Extract a clean goal statement."""
        # Remove conversational words and extract core intent
        cleaned = re.sub(r'\b(?:please|can you|could you|i want to|help me)\b', '', command, flags=re.IGNORECASE)
        cleaned = cleaned.strip().capitalize()
        
        # Add context based on goal type
        if goal_type == GoalType.SEARCH:
            if not cleaned.startswith("Search"):
                cleaned = f"Search for {cleaned}"
        elif goal_type == GoalType.EXTRACTION:
            if not cleaned.startswith("Extract"):
                cleaned = f"Extract {cleaned}"
        
        return cleaned
    
    def _generate_success_condition(self, goal_statement: str, goal_type: GoalType) -> str:
        """Generate a measurable success condition."""
        success_templates = {
            GoalType.SEARCH: "Search results found and relevant information extracted",
            GoalType.EXTRACTION: "Required data extracted and structured",
            GoalType.COMPARISON: "Comparison completed and best option identified",
            GoalType.ANALYSIS: "Analysis performed and summary generated",
            GoalType.NAVIGATION: "Target page reached and key information accessed",
            GoalType.INTERACTION: "Interaction completed successfully",
            GoalType.MONITORING: "Monitoring data collected and trends identified"
        }
        
        base_condition = success_templates.get(goal_type, "Goal completed successfully")
        
        # Add specific metrics if possible
        if "top" in goal_statement.lower():
            number = re.search(r'top\s+(\d+)', goal_statement.lower())
            if number:
                base_condition += f" (top {number.group(1)} results obtained)"
        
        return base_condition
    
    def _detect_domain(self, command: str) -> str:
        """Detect the website/domain context."""
        domains = {
            "youtube": ["youtube", "yt"],
            "linkedin": ["linkedin"],
            "amazon": ["amazon"],
            "google": ["google"],
            "github": ["github"],
            "twitter": ["twitter", "x.com"],
            "facebook": ["facebook", "fb"],
            "instagram": ["instagram", "ig"]
        }
        
        command_lower = command.lower()
        for domain, keywords in domains.items():
            if any(keyword in command_lower for keyword in keywords):
                return domain
        
        return "general"
    
    def _estimate_complexity(self, goal_statement: str, goal_type: GoalType) -> int:
        """Estimate the number of steps needed to complete the goal."""
        base_complexity = {
            GoalType.SEARCH: 3,
            GoalType.EXTRACTION: 4,
            GoalType.COMPARISON: 6,
            GoalType.ANALYSIS: 5,
            GoalType.NAVIGATION: 2,
            GoalType.INTERACTION: 3,
            GoalType.MONITORING: 4
        }
        
        base = base_complexity.get(goal_type, 3)
        
        # Increase complexity for specific indicators
        complexity_indicators = {
            "compare": +2,
            "analyze": +2,
            "summarize": +1,
            "list": +1,
            "multiple": +2,
            "all": +1,
            "detailed": +1
        }
        
        for indicator, increase in complexity_indicators.items():
            if indicator in goal_statement.lower():
                base += increase
        
        return min(base, 10)  # Cap at 10 steps

class SubgoalDecomposer:
    """Breaks down high-level goals into executable subgoals."""
    
    def __init__(self):
        self.decomposition_templates = {
            GoalType.SEARCH: [
                "Navigate to target website",
                "Locate search functionality",
                "Execute search query",
                "Extract search results",
                "Format and present results"
            ],
            GoalType.EXTRACTION: [
                "Navigate to target page",
                "Locate target elements",
                "Extract required data",
                "Structure extracted data",
                "Validate data completeness"
            ],
            GoalType.COMPARISON: [
                "Identify items to compare",
                "Extract data for first item",
                "Extract data for second item",
                "Perform comparison analysis",
                "Identify best option",
                "Present comparison results"
            ],
            GoalType.ANALYSIS: [
                "Gather relevant data",
                "Extract key information",
                "Perform analysis",
                "Generate insights",
                "Create summary"
            ]
        }
    
    def decompose_goal(self, goal: Goal) -> List[Subgoal]:
        """Decompose a goal into subgoals."""
        base_template = self.decomposition_templates.get(goal.goal_type, [
            "Navigate to target location",
            "Perform primary action",
            "Extract results",
            "Format output"
        ])
        
        # Customize subgoals based on the specific goal
        subgoals = []
        for i, template in enumerate(base_template):
            subgoal_id = f"subgoal_{i+1}"
            description = self._customize_subgoal(template, goal)
            
            # Determine dependencies (usually sequential)
            dependencies = [f"subgoal_{i}" for j in range(1, i+1)] if i > 0 else []
            
            # Generate success criteria
            success_criteria = self._generate_subgoal_success_criteria(description, goal)
            
            subgoals.append(Subgoal(
                id=subgoal_id,
                description=description,
                dependencies=dependencies,
                success_criteria=success_criteria,
                estimated_actions=3
            ))
        
        return subgoals
    
    def _customize_subgoal(self, template: str, goal: Goal) -> str:
        """Customize a subgoal template based on the specific goal."""
        domain_specific = {
            "youtube": {
                "Navigate to target website": "Open YouTube and navigate to relevant section",
                "Locate search functionality": "Find YouTube search bar",
                "Execute search query": f"Search for: {self._extract_search_term(goal.goal_statement)}",
                "Extract search results": "Extract video results from search page"
            },
            "amazon": {
                "Navigate to target website": "Open Amazon homepage",
                "Locate search functionality": "Find Amazon search bar",
                "Execute search query": f"Search for: {self._extract_search_term(goal.goal_statement)}",
                "Extract search results": "Extract product listings with prices"
            },
            "linkedin": {
                "Navigate to target website": "Open LinkedIn and navigate to jobs section",
                "Locate search functionality": "Find LinkedIn job search bar",
                "Execute search query": f"Search for jobs: {self._extract_search_term(goal.goal_statement)}",
                "Extract search results": "Extract job listings with details"
            }
        }
        
        domain_templates = domain_specific.get(goal.domain, {})
        return domain_templates.get(template, template)
    
    def _extract_search_term(self, goal_statement: str) -> str:
        """Extract the search term from a goal statement."""
        # Look for patterns like "Search for X" or "Find X"
        patterns = [
            r"search\s+(?:for\s+)?(.+?)(?:\s+on|\s+in|$)",
            r"find\s+(.+?)(?:\s+on|\s+in|$)",
            r"look\s+for\s+(.+?)(?:\s+on|\s+in|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal_statement.lower())
            if match:
                return match.group(1).strip()
        
        return goal_statement
    
    def _generate_subgoal_success_criteria(self, description: str, goal: Goal) -> str:
        """Generate success criteria for a subgoal."""
        if "navigate" in description.lower():
            return "Target page loaded successfully"
        elif "search" in description.lower():
            return "Search executed and results displayed"
        elif "extract" in description.lower():
            return "Required data extracted successfully"
        elif "format" in description.lower():
            return "Data properly formatted and structured"
        else:
            return "Subgoal completed successfully"

# Global instances
goal_interpreter = GoalInterpreter()
subgoal_decomposer = SubgoalDecomposer()
