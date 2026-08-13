"""LangGraph 状态图：决策后按 tool_plan 顺序动态执行注册工具。"""
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from backend.agent.decision import decide_agent_plan
from backend.agent.registry import DEFAULT_TOOL_PLAN, TOOL_REGISTRY
from backend.agent.state import AgentState


def _execute_tool_plan(
    state: AgentState,
    db: Session,
) -> Dict[str, Any]:
    """按 tool_plan 顺序执行工具，保持 LLM/规则给出的顺序。"""
    plan = state.get("tool_plan") or DEFAULT_TOOL_PLAN
    current = dict(state)

    for tool_name in plan:
        tool = TOOL_REGISTRY.get(tool_name)
        if tool:
            current.update(tool(current, db))

    return current


def build_agent_graph(db: Session):
    def decide_plan_node(state: AgentState) -> Dict[str, Any]:
        """LLM 或规则决定本次请求的城市、场景、风格和工具计划。"""
        plan = decide_agent_plan(
            query=state.get("query"),
            city=state.get("city"),
            occasion=state.get("occasion"),
            style=state.get("style"),
        )
        return {
            "city": plan["city"],
            "occasion": plan["occasion"],
            "style": plan["style"],
            "scene_type": plan.get("scene_type"),
            "formality": plan.get("formality"),
            "activity_level": plan.get("activity_level"),
            "forecast_day": plan.get("forecast_day", 0),
            "tool_plan": plan["tool_plan"],
        }

    workflow = StateGraph(AgentState)
    workflow.add_node("decide_plan", decide_plan_node)
    workflow.add_node(
        "execute_plan",
        lambda state: _execute_tool_plan(state, db),
    )

    workflow.add_edge(START, "decide_plan")
    workflow.add_edge("decide_plan", "execute_plan")
    workflow.add_edge("execute_plan", END)

    return workflow.compile()
