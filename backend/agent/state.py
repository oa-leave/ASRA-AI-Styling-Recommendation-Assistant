from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    query: Optional[str]
    city: str
    occasion: str
    style: Optional[str]
    tool_plan: List[str]
    user_id: int
    weather: Optional[Dict[str, Any]]
    scene: Optional[Dict[str, Any]]
    profile: Optional[Dict[str, Any]]
    context_profile: Optional[Dict[str, Any]]
    wardrobe: List[Dict[str, Any]]
    memory: Optional[Dict[str, Any]]
    conversation_context: Optional[Dict[str, Any]]
    knowledge_rules: List[Dict[str, Any]]
    knowledge_text: Optional[str]
    recommendation: Optional[Dict[str, Any]]
    history_id: Optional[int]
