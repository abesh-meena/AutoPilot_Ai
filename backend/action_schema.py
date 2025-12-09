from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    # Basic actions
    OPEN_URL = "openUrl"
    TYPE_TEXT = "typeText"
    CLICK_ELEMENT = "clickElement"
    SCROLL_PAGE = "scrollPage"
    EXTRACT_CONTENT = "extractContent"
    KEY_PRESS = "keyPress"
    WAIT_FOR_ELEMENT = "waitForElement"
    HOVER_ELEMENT = "hoverElement"
    FOCUS_INPUT = "focusInput"
    SCREENSHOT = "screenshot"
    EXTRACT_LINKS = "extractLinks"
    RETRY_ACTION = "retryAction"
    
    # Phase 4: Video Actions
    PLAY_VIDEO = "playVideo"
    PAUSE_VIDEO = "pauseVideo"
    OPEN_SETTINGS_MENU = "openSettingsMenu"
    SET_QUALITY = "setQuality"
    
    # Phase 4: Playlist Actions
    CREATE_PLAYLIST = "createPlaylist"
    ADD_TO_PLAYLIST = "addToPlaylist"
    SAVE_PLAYLIST = "savePlaylist"
    OPEN_PLAYLIST = "openPlaylist"
    PLAY_PLAYLIST = "playPlaylist"
    
    # Phase 4: Utility Actions
    WAIT_FOR_NAVIGATION = "waitForNavigation"
    SCROLL_UNTIL_FOUND = "scrollUntilFound"


class SelectorStrategy(str, Enum):
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"


class Action(BaseModel):
    action: ActionType
    
    # Common fields
    selector: Optional[str] = None
    selector_strategy: SelectorStrategy = SelectorStrategy.CSS
    fallback_selectors: Optional[Dict[SelectorStrategy, str]] = None
    
    # URL actions
    url: Optional[str] = None
    
    # Text input
    text: Optional[str] = None
    
    # Key press
    key: Optional[str] = None
    
    # Scrolling
    direction: Optional[Literal["up", "down"]] = "down"
    amount: Optional[int] = 500
    
    # Wait conditions
    timeout_ms: int = 5000  # Default 5s timeout for waits
    visible: bool = True
    
    # Retry logic
    max_retries: int = 3
    retry_delay_ms: int = 1000
    
    # For screenshot and content extraction
    output_path: Optional[str] = None
    
    # Metadata for action chaining
    depends_on: Optional[str] = None  # Action ID this action depends on
    
    # Phase 4: Video quality settings
    quality: Optional[str] = None
    
    # Phase 4: Playlist settings
    playlist_name: Optional[str] = None
    playlist_item: Optional[str] = None
    
    # Phase 4: Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            SelectorStrategy: lambda v: v.value,
            ActionType: lambda v: v.value
        }


def create_action(
    action_type: ActionType,
    **kwargs
) -> Action:
    """Helper to create actions with type hints and defaults"""
    return Action(action=action_type, **kwargs)
