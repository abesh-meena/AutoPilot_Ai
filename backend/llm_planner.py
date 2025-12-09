"""
AutoPilot AI Task Planner - Phase 4

Enhanced Features:
- Multi-step task decomposition with compound command support
- Advanced NLP understanding with Hinglish/English support
- Smart URL handling and website-specific actions
- 3-level selector fallback system (CSS → XPath → Text)
- Auto-wait and retry logic
- Support for YouTube-specific actions (play, pause, quality settings, playlists)
- Error recovery and fallback mechanisms
"""

import re
import logging
import random
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Literal, Union, Callable, Awaitable
from urllib.parse import quote_plus
from enum import Enum

from action_schema import Action, ActionType, SelectorStrategy, create_action
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Literal, Union, Callable, Awaitable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safety and common patterns
UNSAFE_KEYWORDS = ["shutdown", "format", "delete system32", "restart laptop"]

# Compound command indicators
COMPOUND_INDICATORS = [
    "and", "then", "after that", "also", "aur", "phir", "and then", "after"
]

# Video quality options
VIDEO_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "4k", "auto"]

class TaskComplexity(str, Enum):
    SIMPLE = "simple"  # Single action
    COMPOUND = "compound"  # Multiple actions with "and" or "then"
    COMPLEX = "complex"  # Requires multi-step planning

# Common website domains and their search URLs
WEBSITES = {
    "youtube": {
        "url": "https://www.youtube.com",
        "search_url": "https://www.youtube.com/results?search_query={query}",
        "search_selector": "input#search",
        "search_button_selector": "button#search-icon-legacy"
    },
    "google": {
        "url": "https://www.google.com",
        "search_url": "https://www.google.com/search?q={query}",
        "search_selector": "input[name='q']"
    },
    "github": {
        "url": "https://github.com",
        "search_url": "https://github.com/search?q={query}",
        "search_selector": "input[name='q']"
    },
    "amazon": {
        "url": "https://www.amazon.com",
        "search_url": "https://www.amazon.com/s?k={query}",
        "search_selector": "#twotabsearchtextbox"
    },
    "flipkart": {
        "url": "https://www.flipkart.com",
        "search_url": "https://www.flipkart.com/search?q={query}",
        "search_selector": "input[title*='Search for products']"
    }
}

def create_wait_action(selector: str, timeout_ms: int = 5000) -> Action:
    """Create a waitForElement action with fallback selectors."""
    return create_action(
        action_type=ActionType.WAIT_FOR_ELEMENT,
        selector=selector,
        timeout_ms=timeout_ms,
        fallback_selectors={
            SelectorStrategy.XPATH: f"//*[contains(text(), '{selector}')]"
        }
    )

def is_unsafe(command: str) -> bool:
    """Check if command contains potentially harmful operations."""
    cmd = command.lower()
    return any(word in cmd for word in UNSAFE_KEYWORDS)

def normalize_text(text: str) -> str:
    """Normalize text for better matching."""
    # Convert to lowercase and remove extra whitespace
    text = ' '.join(text.lower().split())
    # Remove common punctuation except @ and /
    text = re.sub(r'[.,!?;:]', '', text)
    return text

def extract_website(command: str) -> Tuple[Optional[str], str]:
    """Extract website name from command if specified."""
    command = normalize_text(command)
    for site in WEBSITES:
        if site in command:
            # Remove the site name from the command
            clean_cmd = command.replace(site, '').strip()
            return site, clean_cmd
    return None, command

def extract_search_query(command: str) -> str:
    """Extract search query from command."""
    patterns = [
        r"search\s+(?:for\s+)?(?:a\s+)?(?:the\s+)?(.+?)(?:\s+on\s+.+)?$",
        r"find\s+(?:me\s+)?(?:a\s+)?(?:the\s+)?(.+?)(?:\s+on\s+.+)?$",
        r"look up\s+(?:a\s+)?(?:the\s+)?(.+?)(?:\s+on\s+.+)?$",
        r"khojo\s+(.+)$",
        r"dhundho\s+(.+)$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no pattern matched, return the command as is
    return command

def create_youtube_actions(query: str) -> List[Action]:
    """Create actions for YouTube search: open site, type, press Enter."""
    return [
        create_action(ActionType.OPEN_URL, url="https://www.youtube.com"),
        create_action(ActionType.TYPE_TEXT, selector="input#search", text=query),
        create_action(ActionType.KEY_PRESS, key="Enter"),
    ]

def create_web_search_actions(query: str, site: Optional[str] = None, open_first: bool = False) -> List[Action]:
    """Create actions for web search. If site provided, prefer typing into its search box.
    open_first controls whether to navigate to the site before typing (use True for simple commands)."""
    if site and site in WEBSITES:
        selector = WEBSITES[site].get("search_selector")
        if selector:
            actions: List[Action] = []
            if open_first:
                actions.append(create_action(ActionType.OPEN_URL, url=WEBSITES[site]["url"]))
            actions.append(create_action(ActionType.TYPE_TEXT, selector=selector, text=query))
            actions.append(create_action(ActionType.KEY_PRESS, key="Enter"))
            return actions
        # Fallback to search URL if no selector known
        url = WEBSITES[site]["search_url"].format(query=quote_plus(query))
        return [create_action(ActionType.OPEN_URL, url=url)]

    # Default to Google search as a single navigation
    return [create_action(ActionType.OPEN_URL, url=f"https://www.google.com/search?q={quote_plus(query)}")]

def create_open_actions(target: str) -> List[Action]:
    """Create actions for opening a URL or searching for a term."""
    # Check if it's a URL
    if re.match(r'^https?://', target, re.IGNORECASE):
        return [create_action(ActionType.OPEN_URL, url=target)]
    
    # Check if it's a known website
    for site, data in WEBSITES.items():
        if site in target.lower():
            return [create_action(ActionType.OPEN_URL, url=data["url"])]
    
    # If it's a single word, assume it's a website
    if ' ' not in target and '.' not in target:
        return [create_action(ActionType.OPEN_URL, url=f"https://www.{target}.com")]
    
    # Otherwise, treat it as a search query
    return create_web_search_actions(target)

def handle_compound_command(command: str, default_site: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Handle compound commands with 'and', 'then', etc., preserving site context.
    Enhanced for Phase 4 with better support for YouTube actions and playlists.
    """
    actions: List[Dict[str, Any]] = []
    
    # Split the command into sub-commands using compound indicators
    pattern = r'\s+(?:' + '|'.join(re.escape(sep) for sep in COMPOUND_INDICATORS) + r')\s+'
    sub_commands = re.split(pattern, command, flags=re.IGNORECASE)
    
    current_site = default_site
    
    for cmd in sub_commands:
        try:
            if not cmd.strip():
                continue
                
            cmd = cmd.strip()
            logger.info(f"Processing sub-command: {cmd}")
            
            # Check for site context
            site_in_cmd, clean_cmd = extract_website(cmd)
            site_to_use = site_in_cmd or current_site
            cmd_lower = clean_cmd.lower()
            
            # Handle video controls
            video_action = handle_video_controls(cmd_lower)
            if video_action:
                actions.append(video_action)
                continue
            
            # Handle playlist operations
            playlist_actions = create_playlist_actions(cmd_lower)
            if playlist_actions:
                actions.extend(playlist_actions)
                continue
            
            # Handle search commands
            if any(word in cmd_lower for word in ["search", "find", "khojo", "dhundho"]):
                query = extract_search_query(clean_cmd)
                
                if site_to_use == "youtube":
                    if current_site == "youtube":
                        actions.extend([
                            create_action(
                                ActionType.TYPE_TEXT, 
                                selector="input#search", 
                                text=query
                            ).dict(),
                            create_action(
                                ActionType.KEY_PRESS, 
                                key="Enter"
                            ).dict(),
                        ])
                    else:
                        actions.extend([a.dict() for a in create_youtube_actions(query)])
                        current_site = "youtube"
                elif site_to_use and site_to_use in WEBSITES:
                    open_first = current_site != site_to_use
                    actions.extend([a.dict() for a in create_web_search_actions(query, site_to_use, open_first=open_first)])
                    if open_first:
                        current_site = site_to_use
                else:
                    actions.extend([a.dict() for a in create_web_search_actions(query)])
            
            # Handle open commands
            elif cmd_lower.startswith(('open ', 'kholo ', 'chalo ', 'go to ')):
                target = re.sub(r'^(open|kholo|chalo|go to)\s+', '', cmd, flags=re.IGNORECASE)
                actions.extend([a.dict() for a in create_open_actions(target)])
                
                # Update current site if a known site is mentioned
                for site in WEBSITES:
                    if site in target.lower():
                        current_site = site
                        break
            
            # Handle click commands
            elif cmd_lower.startswith(('click ', 'press ')):
                target = re.sub(r'^(click|press)\s+', '', cmd, flags=re.IGNORECASE)
                actions.append(create_action(
                    ActionType.CLICK_ELEMENT,
                    selector=target,
                    fallback_selectors={
                        SelectorStrategy.XPATH: f"//*[contains(text(), '{target}')]"
                    }
                ).dict())
            
            # Handle scroll commands
            elif cmd_lower.startswith(('scroll down', 'scroll up', 'scroll to')):
                direction = "down"
                if "up" in cmd_lower:
                    direction = "up"
                actions.append(create_action(
                    ActionType.SCROLL_PAGE, 
                    direction=direction
                ).dict())
            
            # Handle wait commands
            elif cmd_lower.startswith(('wait for', 'wait until')):
                # Extract timeout if specified
                timeout_match = re.search(r'wait (?:for|until) (\d+) (seconds|second|sec|s)', cmd_lower)
                timeout_ms = 5000  # default 5 seconds
                if timeout_match:
                    timeout_ms = int(timeout_match.group(1)) * 1000
                
                actions.append(create_action(
                    ActionType.WAIT_FOR_NAVIGATION,
                    timeout_ms=timeout_ms
                ).dict())
            
            # Handle quality settings
            elif "quality" in cmd_lower or "resolution" in cmd_lower:
                quality_match = re.search(r'(\d+p|hd|full hd|4k|auto)', cmd_lower)
                if quality_match:
                    quality = quality_match.group(1)
                    actions.append(create_quality_action(quality))
            
            # If no specific command matched, treat as a search
            else:
                query = extract_search_query(clean_cmd)
                if site_to_use == "youtube":
                    actions.extend([a.dict() for a in create_youtube_actions(query)])
                    current_site = "youtube"
                else:
                    actions.extend([a.dict() for a in create_web_search_actions(query, site_to_use)])
        
        except Exception as e:
            logger.error(f"Error processing sub-command '{cmd}': {e}")
            # Add a retry action for the failed command
            actions.append(create_action(
                ActionType.RETRY_ACTION,
                error_message=str(e),
                command=cmd,
                max_retries=3
            ).dict())
    
    return actions

def analyze_task_complexity(command: str) -> TaskComplexity:
    """Analyze the complexity of the task."""
    command_lower = command.lower()
    
    # Check for compound commands
    if any(sep in command_lower for sep in COMPOUND_INDICATORS):
        return TaskComplexity.COMPOUND
    
    # Check for complex tasks that might need multi-step planning
    complex_keywords = [
        "playlist", "quality", "settings", "next video", 
        "previous video", "fullscreen", "theater mode"
    ]
    
    if any(keyword in command_lower for keyword in complex_keywords):
        return TaskComplexity.COMPLEX
    
    return TaskComplexity.SIMPLE

def create_quality_action(quality: str) -> Dict[str, Any]:
    """Create an action to set video quality."""
    # Normalize quality string
    quality = quality.lower().replace(' ', '').replace('p', 'p').replace('k', 'k')
    if quality not in VIDEO_QUALITIES:
        quality = 'auto'
    
    return create_action(
        action_type=ActionType.SET_QUALITY,
        quality=quality
    ).dict()

def create_playlist_actions(command: str) -> List[Dict[str, Any]]:
    """Handle playlist-related commands."""
    command_lower = command.lower()
    actions = []
    
    if "create playlist" in command_lower:
        # Extract playlist name if provided
        playlist_name = "My Playlist"
        name_match = re.search(r'create playlist (?:named|called)?[\s"\']*(.+?)["\']?(?:\s|$)', command_lower)
        if name_match:
            playlist_name = name_match.group(1).strip()
        
        actions.append(create_action(
            action_type=ActionType.CREATE_PLAYLIST,
            playlist_name=playlist_name
        ).dict())
        
        # If the command mentions adding current video to the new playlist
        if any(word in command_lower for word in ["add", "this video", "current video"]):
            actions.append(create_action(
                action_type=ActionType.ADD_TO_PLAYLIST,
                playlist_name=playlist_name,
                playlist_item="current_video"
            ).dict())
    
    elif "add to playlist" in command_lower:
        # Extract playlist name if provided
        playlist_name = "default"
        name_match = re.search(r'add (?:to )?playlist (?:named|called)?[\s"\']*(.+?)["\']?(?:\s|$)', command_lower)
        if name_match:
            playlist_name = name_match.group(1).strip()
        
        actions.append(create_action(
            action_type=ActionType.ADD_TO_PLAYLIST,
            playlist_name=playlist_name,
            playlist_item="current_video"
        ).dict())
    
    elif "play playlist" in command_lower or "open playlist" in command_lower:
        # Extract playlist name if provided
        playlist_name = "default"
        name_match = re.search(r'(?:play|open) playlist (?:named|called)?[\s"\']*(.+?)["\']?(?:\s|$)', command_lower)
        if name_match:
            playlist_name = name_match.group(1).strip()
        
        actions.append(create_action(
            action_type=ActionType.PLAY_PLAYLIST if "play" in command_lower else ActionType.OPEN_PLAYLIST,
            playlist_name=playlist_name
        ).dict())
    
    return actions

def handle_video_controls(command: str) -> Optional[Dict[str, Any]]:
    """Handle video control commands like play, pause, etc."""
    command_lower = command.lower()
    
    if any(word in command_lower for word in ["play video", "resume video", "play the video"]):
        return create_action(action_type=ActionType.PLAY_VIDEO).dict()
    
    if any(word in command_lower for word in ["pause video", "pause the video"]):
        return create_action(action_type=ActionType.PAUSE_VIDEO).dict()
    
    # Handle video quality settings
    quality_match = re.search(r'set (?:quality|resolution) (?:to )?(\d+p|hd|full hd|4k|auto)', command_lower)
    if quality_match:
        quality = quality_match.group(1)
        return create_quality_action(quality)
    
    # Handle settings menu
    if any(word in command_lower for word in ["open settings", "settings menu", "video settings"]):
        return create_action(action_type=ActionType.OPEN_SETTINGS_MENU).dict()
    
    return None

@dataclass
class GoalState:
    goal: str
    subtasks: List[str]
    current_step: int = 0
    completed_steps: List[str] = None
    observations: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.completed_steps is None:
            self.completed_steps = []
        if self.observations is None:
            self.observations = []

class AutonomousPlanner:
    def __init__(self):
        self.current_goal_state: Optional[GoalState] = None
        self.action_history: List[Dict[str, Any]] = []
    
    def extract_goal(self, user_input: str) -> str:
        """Extract high-level goal from user input."""
        # Remove conversational fluff and extract core goal
        patterns = [
            r"(?:please |can you |i want to |help me )?(.+)$",
            r"(?:karo |kholo |search |find |dhundho |khojo )?(.+)$",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.strip(), re.IGNORECASE)
            if match:
                goal = match.group(1).strip()
                # Clean up the goal
                goal = re.sub(r'^(?:please |can you |i want to |help me )', '', goal, flags=re.IGNORECASE)
                return goal
        
        return user_input.strip()
    
    def generate_subtasks(self, goal: str) -> List[str]:
        """Generate high-level subtasks from goal."""
        subtasks = []
        goal_lower = goal.lower()
        
        # YouTube-specific patterns
        if "youtube" in goal_lower:
            if "search" in goal_lower or "find" in goal_lower:
                subtasks = ["Open YouTube", "Search for content", "View results"]
            elif "playlist" in goal_lower:
                subtasks = ["Open YouTube", "Find playlist", "Play playlist"]
            else:
                subtasks = ["Open YouTube", "Navigate to content"]
        
        # Web search patterns
        elif any(word in goal_lower for word in ["search", "find", "khojo", "dhundho"]):
            subtasks = ["Open search engine", "Enter search query", "View results"]
        
        # Website navigation patterns
        elif any(word in goal_lower for word in ["open", "kholo", "go to", "chalo"]):
            subtasks = ["Navigate to website", "Wait for page load"]
        
        # Generic pattern
        else:
            subtasks = ["Analyze goal", "Execute primary action", "Verify completion"]
        
        return subtasks
    
    def convert_subtask_to_actions(self, subtask: str, context: Dict[str, Any] = None) -> List[Action]:
        """Convert a subtask into browser actions."""
        context = context or {}
        subtask_lower = subtask.lower()
        
        if "open youtube" in subtask_lower:
            return [create_action(ActionType.OPEN_URL, url="https://www.youtube.com")]
        
        elif "search" in subtask_lower and "youtube" in context.get("goal", "").lower():
            query = self._extract_query_from_goal(context.get("goal", ""))
            return [
                create_action(ActionType.TYPE_TEXT, selector="input#search", text=query),
                create_action(ActionType.KEY_PRESS, key="Enter")
            ]
        
        elif "search" in subtask_lower:
            query = self._extract_query_from_goal(context.get("goal", ""))
            return [create_action(ActionType.OPEN_URL, url=f"https://www.google.com/search?q={quote_plus(query)}")]
        
        elif "navigate" in subtask_lower or "open" in subtask_lower:
            url = self._extract_url_from_goal(context.get("goal", ""))
            if url:
                return [create_action(ActionType.OPEN_URL, url=url)]
        
        # Default fallback
        return [create_action(ActionType.WAIT_FOR_NAVIGATION, timeout_ms=3000)]
    
    def _extract_query_from_goal(self, goal: str) -> str:
        """Extract search query from goal."""
        # Look for content after search-related keywords
        patterns = [
            r"search for (.+)$",
            r"find (.+)$", 
            r"khojo (.+)$",
            r"dhundho (.+)$",
            r"(?:youtube|google) (.+)$"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal.lower())
            if match:
                return match.group(1).strip()
        
        return goal
    
    def _extract_url_from_goal(self, goal: str) -> Optional[str]:
        """Extract URL from goal if present."""
        url_match = re.search(r'https?://[^\s]+', goal)
        if url_match:
            return url_match.group(0)
        
        # Check for known websites
        for site, data in WEBSITES.items():
            if site in goal.lower():
                return data["url"]
        
        return None
    
    def decide_next_step(self, observation: Dict[str, Any] = None) -> Optional[List[Action]]:
        """Decide next action based on current state and observation with DOM interpretation."""
        if not self.current_goal_state:
            return None
        
        # Add observation to history
        if observation:
            self.current_goal_state.observations.append(observation)
        
        # Check if goal is completed
        if self.current_goal_state.current_step >= len(self.current_goal_state.subtasks):
            return None  # Goal completed
        
        # Update 2: Use DOM interpretation first (SEE → THINK → ACT)
        if observation and not observation.get('error'):
            dom_action = self.interpret_dom(observation)
            if dom_action:
                # Convert dict back to Action object if needed
                if isinstance(dom_action, dict):
                    # Create Action from dict (simplified conversion)
                    action_type = dom_action.get('action')
                    if action_type:
                        return [create_action(
                            action_type=ActionType(action_type),
                            selector=dom_action.get('selector'),
                            text=dom_action.get('text'),
                            url=dom_action.get('url'),
                            direction=dom_action.get('direction'),
                            timeout_ms=dom_action.get('timeout_ms')
                        )]
                else:
                    return [dom_action]
        
        # Fallback to original subtask-based planning
        current_subtask = self.current_goal_state.subtasks[self.current_goal_state.current_step]
        
        # Convert to actions
        context = {"goal": self.current_goal_state.goal}
        actions = self.convert_subtask_to_actions(current_subtask, context)
        
        return actions if actions else None
    
    def update_state(self, observation: Dict[str, Any]):
        """Update planner state based on observation."""
        if not self.current_goal_state:
            return
        
        self.current_goal_state.observations.append(observation)
        
        # Simple completion detection - can be enhanced with LLM
        if self._is_current_step_complete(observation):
            current_subtask = self.current_goal_state.subtasks[self.current_goal_state.current_step]
            self.current_goal_state.completed_steps.append(current_subtask)
            self.current_goal_state.current_step += 1
    
    def _is_current_step_complete(self, observation: Dict[str, Any]) -> bool:
        """Check if current step is complete based on observation."""
        if not self.current_goal_state:
            return False
        
        current_subtask = self.current_goal_state.subtasks[self.current_goal_state.current_step].lower()
        obs_text = (observation.get("text", "") + " " + observation.get("title", "")).lower()
        
        # Simple completion heuristics
        if "open" in current_subtask and "youtube" in current_subtask:
            return "youtube" in obs_text
        
        if "search" in current_subtask:
            return "results" in obs_text or "search" in obs_text
        
        if "view" in current_subtask or "play" in current_subtask:
            return len(observation.get("links", [])) > 0 or "video" in obs_text
        
        # Default: assume complete after some action
        return len(self.current_goal_state.observations) > 2
    
    def start_new_goal(self, user_input: str) -> GoalState:
        """Start planning for a new goal."""
        goal = self.extract_goal(user_input)
        subtasks = self.generate_subtasks(goal)
        
        self.current_goal_state = GoalState(
            goal=goal,
            subtasks=subtasks
        )
        
        return self.current_goal_state

    def interpret_dom(self, dom_snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Interpret DOM snapshot and decide next action based on page content."""
        if not dom_snapshot or 'error' in dom_snapshot:
            return None
        
        text = dom_snapshot.get('text', '').lower()
        page_type = dom_snapshot.get('pageType', 'unknown')
        buttons = dom_snapshot.get('buttons', [])
        inputs = dom_snapshot.get('inputs', [])
        links = dom_snapshot.get('links', [])
        
        # Content-aware decision rules
        
        # Rule 1: Handle cookie consent
        if 'accept' in text and 'cookies' in text:
            for btn in buttons:
                if 'accept' in btn['text'].lower():
                    return create_action(
                        ActionType.CLICK_ELEMENT,
                        selector=btn['selector'],
                        fallback_selectors={
                            SelectorStrategy.XPATH: f"//*[contains(text(), 'Accept')]"
                        }
                    ).dict()
        
        # Rule 2: Handle login/sign in
        if 'sign in' in text or 'login' in text:
            for btn in buttons:
                if 'sign in' in btn['text'].lower() or 'login' in btn['text'].lower():
                    return create_action(
                        ActionType.CLICK_ELEMENT,
                        selector=btn['selector']
                    ).dict()
            
            # Look for login links
            for link in links:
                if 'login' in link['text'].lower() or 'sign in' in link['text'].lower():
                    return create_action(
                        ActionType.CLICK_ELEMENT,
                        selector=link['selector']
                    ).dict()
        
        # Rule 3: Handle search functionality
        if 'search' in text:
            # Look for search inputs
            search_input = self._find_search_input(inputs)
            if search_input:
                if self.current_goal_state:
                    query = self._extract_query_from_goal(self.current_goal_state.goal)
                    return create_action(
                        ActionType.TYPE_TEXT,
                        selector=search_input['selector'],
                        text=query
                    ).dict()
            
            # Look for search buttons
            for btn in buttons:
                if 'search' in btn['text'].lower():
                    return create_action(
                        ActionType.CLICK_ELEMENT,
                        selector=btn['selector']
                    ).dict()
        
        # Rule 4: Page-specific handling
        if page_type == 'youtube_search':
            if 'results' in text and len(links) > 0:
                # Click first video result
                for link in links:
                    if 'watch' in link.get('href', ''):
                        return create_action(
                            ActionType.CLICK_ELEMENT,
                            selector=link['selector']
                        ).dict()
        
        elif page_type == 'google_search':
            if 'results' in text and len(links) > 0:
                # Click first search result
                for link in links[:3]:  # Try first 3 results
                    if link.get('href', '').startswith('http'):
                        return create_action(
                            ActionType.CLICK_ELEMENT,
                            selector=link['selector']
                        ).dict()
        
        # Rule 5: If page content is too short, scroll
        if len(text) < 200:
            return create_action(
                ActionType.SCROLL_PAGE,
                direction="down"
            ).dict()
        
        # Rule 6: Look for primary actions
        for btn in buttons:
            btn_text = btn['text'].lower()
            if any(keyword in btn_text for keyword in ['continue', 'next', 'submit', 'get started']):
                return create_action(
                    ActionType.CLICK_ELEMENT,
                    selector=btn['selector']
                ).dict()
        
        # Default: wait and observe
        return create_action(
            ActionType.WAIT_FOR_NAVIGATION,
            timeout_ms=2000
        ).dict()
    
    def _find_search_input(self, inputs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the most likely search input with fallback logic."""
        # Priority order for search inputs
        search_selectors = [
            "input#search",
            "input[name='q']",
            "input[type='search']",
            "input[placeholder*='search']",
            "input[aria-label*='search']"
        ]
        
        # First try exact matches
        for input_elem in inputs:
            if not input_elem.get('visible', False):
                continue
                
            selector = input_elem.get('selector', '')
            for search_selector in search_selectors:
                if selector == search_selector:
                    return input_elem
        
        # Then try partial matches
        for input_elem in inputs:
            if not input_elem.get('visible', False):
                continue
                
            placeholder = input_elem.get('placeholder', '').lower()
            input_id = input_elem.get('id', '').lower()
            input_type = input_elem.get('type', '').lower()
            
            if ('search' in placeholder or 'search' in input_id or 
                input_type == 'search' or 'q' == input_id):
                return input_elem
        
        return None

# Global planner instance
autonomous_planner = AutonomousPlanner()

def plan_actions(command: str) -> List[Dict[str, Any]]:
    """
    Enhanced planner that can handle complex, multi-step commands with Phase 4 features.
    
    Examples:
    - "open youtube and search for lofi songs"
    - "search for python tutorials and then open github"
    - "find me a recipe for pasta"
    - "youtube kholo aur lofi songs search karo"
    - "play video and set quality to 1080p"
    - "create a playlist named 'Workout' and add this video"
    - "open settings and change quality to 4k"
    """
    # Check for unsafe commands
    if is_unsafe(command):
        raise ValueError("This command contains potentially harmful operations and cannot be executed.")
    
    # Analyze task complexity
    complexity = analyze_task_complexity(command)
    command_lower = command.lower()
    
    # Handle complex tasks first (video controls, playlists, etc.)
    if complexity == TaskComplexity.COMPLEX:
        # Check for video controls
        video_action = handle_video_controls(command_lower)
        if video_action:
            return [video_action]
        
        # Check for playlist operations
        playlist_actions = create_playlist_actions(command_lower)
        if playlist_actions:
            return playlist_actions
    
    # Handle compound commands (with 'and', 'then', etc.)
    if complexity == TaskComplexity.COMPOUND:
        return handle_compound_command(command)
    
    # Handle search commands
    if any(word in command_lower for word in ["search", "find", "khojo", "dhundho"]):
        site, clean_cmd = extract_website(command)
        query = extract_search_query(clean_cmd)
        
        if site == "youtube":
            return [a.dict() for a in create_youtube_actions(query)]
        elif site:
            return [a.dict() for a in create_web_search_actions(query, site)]
        else:
            return [a.dict() for a in create_web_search_actions(query)]
    
    # Handle open commands
    if command_lower.startswith(('open ', 'kholo ', 'chalo ', 'go to ')):
        target = re.sub(r'^(open|kholo|chalo|go to)\s+', '', command, flags=re.IGNORECASE)
        return [a.dict() for a in create_open_actions(target)]
    
    # Default: treat as a search query
    try:
        return [a.dict() for a in create_web_search_actions(command)]
    except Exception as e:
        logger.error(f"Error in plan_actions: {str(e)}")
        # Fallback to a simple search
        return [
            create_action(
                ActionType.OPEN_URL,
                url=f"https://www.google.com/search?q={quote_plus(command)}"
            ).dict()
        ]
