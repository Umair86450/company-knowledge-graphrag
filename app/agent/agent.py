from __future__ import annotations

import json
import logging
import os
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.claude_service import ask_claude
from app.services.tools import calculator, graph_lookup, knowledge_search

logger = logging.getLogger(__name__)

ROUTING_MODEL = os.getenv("ROUTING_MODEL", "claude-sonnet-4-6")

_TOOLS = {
    "calculator": calculator,
    "graph_lookup": graph_lookup,
    "knowledge_search": knowledge_search,
}


class AgentState(TypedDict):
    question: str
    db_session_id: int
    tool_name: str
    tool_input: str
    tool_result: str
    answer: str


def route(state: AgentState) -> AgentState:
    prompt = (
        "Pick one tool for the question. Tools: "
        "calculator (math), graph_lookup (one entity's connections), "
        "knowledge_search (company knowledge base), none (answer directly). "
        'Reply ONLY a JSON object: {"tool": "<name|none>", "input": "<tool input>"}.\n'
        f"Question: {state['question']}"
    )
    text, _ = ask_claude(prompt, model=ROUTING_MODEL)
    try:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        state["tool_name"] = data["tool"]
        state["tool_input"] = data["input"]
    except (ValueError, KeyError):
        state["tool_name"] = "none"
        state["tool_input"] = state["question"]
    logger.info("route -> tool=%s input=%r", state["tool_name"], state["tool_input"])
    return state


def run_tool(state: AgentState) -> AgentState:
    tool = _TOOLS.get(state["tool_name"])
    state["tool_result"] = tool.invoke(state["tool_input"]) if tool else ""
    logger.info("run_tool -> tool=%s result_len=%d", state["tool_name"], len(state["tool_result"]))
    return state


def respond(state: AgentState) -> AgentState:
    if state["tool_result"]:
        prompt = f"Tool result: {state['tool_result']}\n\nQuestion: {state['question']}"
    else:
        prompt = state["question"]
    text, _ = ask_claude(prompt)
    state["answer"] = text
    logger.info("respond -> answer ready answer_len=%d", len(state["answer"]))
    return state


def should_use_tool(state: AgentState) -> str:
    return "respond" if state["tool_name"] in ("none", "") else "run_tool"


def _build_app():
    graph = StateGraph(AgentState)
    graph.add_node("route", route)
    graph.add_node("run_tool", run_tool)
    graph.add_node("respond", respond)
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route", should_use_tool, {"run_tool": "run_tool", "respond": "respond"}
    )
    graph.add_edge("run_tool", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


agent_app = _build_app()


def run_agent(question: str, db_session_id: int) -> tuple[str, dict]:
    initial: AgentState = {
        "question": question,
        "db_session_id": db_session_id,
        "tool_name": "",
        "tool_input": "",
        "tool_result": "",
        "answer": "",
    }
    result = agent_app.invoke(initial)
    trace = {
        "tool": result["tool_name"] or "none",
        "tool_input": result["tool_input"],
        "tool_result": result["tool_result"],
        "answer": result["answer"],
    }
    return result["answer"], trace
