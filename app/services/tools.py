"""LangChain/LangGraph tools for the agent."""

from __future__ import annotations

import ast
import operator

from langchain_core.tools import tool

from app.services.graph_service import retrieve_context

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("unsupported expression")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression and return the result.

    Use this for math like addition, subtraction, multiplication, division,
    and exponents, e.g. "2 + 3 * 4" or "(10 - 2) ** 2". Only numbers and the
    operators + - * / ** with parentheses are supported.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_evaluate(tree.body))
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
        return f"Error: '{expression}' is not a valid arithmetic expression."


@tool
def graph_lookup(entity_name: str) -> str:
    """Look up how a company entity connects to others in the knowledge graph.

    Use this to find relationships for a person, project, skill, or technology,
    e.g. who works on a project, what skills someone has, or which technologies
    a project uses. Pass the entity name, e.g. "Ali Khan" or "Internal AI Assistant".
    """
    context = retrieve_context(entity_name)
    return context or f"No graph data found for {entity_name}"


@tool
def knowledge_search(query: str) -> str:
    """Search the company knowledge base for employees, projects, skills, and technologies.

    Use this to answer questions about company data, e.g. "Which projects use Python?"
    or "What does Sara Malik work on?".
    """
    context = retrieve_context(query)
    return context or "No relevant company knowledge found"


TOOLS = [calculator, graph_lookup, knowledge_search]
