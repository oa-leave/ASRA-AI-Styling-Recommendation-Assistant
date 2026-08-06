from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    city: str
    occasion: str
    style: Optional[str]
    user_id: int
    weather: Optional[Dict[str, Any]]
    scene: Optional[Dict[str, Any]]
    profile: Optional[Dict[str, Any]]
    wardrobe: List[Dict[str, Any]]
    memory: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
