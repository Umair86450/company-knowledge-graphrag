"""Run the Claude Code CLI as a subprocess and return its parsed reply."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from app.models.db import get_session, update_claude_session
from app.services.graph_service import retrieve_context

load_dotenv()

logger = logging.getLogger(__name__)

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "120"))

SYSTEM_PROMPT = Path("prompts/chatbot_prompt.txt").read_text(encoding="utf-8")


class ClaudeError(RuntimeError):
    """Raised when the Claude CLI fails, times out, or returns unparseable output."""


def ask_claude(
    prompt: str,
    claude_session_id: str | None = None,
    system_prompt: str | None = None,
) -> tuple[str, str]:
    """Send a prompt to the Claude Code CLI and return (response_text, session_id)."""
    command = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--permission-mode",
        "dontAsk",
        "--tools",
        "",
        "--model",
        CLAUDE_MODEL,
    ]
    if claude_session_id:
        command += ["--resume", claude_session_id]
    if system_prompt:
        command += ["--system-prompt", system_prompt]

    logger.info("Calling Claude CLI (model=%s, session=%s)", CLAUDE_MODEL, claude_session_id or "new")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out after %ss", CLAUDE_TIMEOUT)
        raise ClaudeError(f"Claude timed out after {CLAUDE_TIMEOUT}s")

    if result.returncode != 0:
        logger.error("Claude CLI exited with %s: %s", result.returncode, result.stderr.strip())
        raise ClaudeError(f"Claude CLI failed (exit {result.returncode}): {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
        return data["result"], data["session_id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Could not parse Claude CLI output: %s", exc)
        raise ClaudeError(f"Invalid Claude CLI output: {exc}")


def chat(db_session_id: int, user_message: str) -> str:
    """Send a user message within a DB session, resuming the Claude conversation."""
    session = get_session(db_session_id)
    claude_session_id = session["claude_session_id"] if session else None

    context = retrieve_context(user_message)
    prompt = (
        f"{context}\n\nUse the above facts if relevant. Question: {user_message}"
        if context
        else user_message
    )

    reply, new_sid = ask_claude(prompt, claude_session_id, SYSTEM_PROMPT)

    if claude_session_id is None:
        update_claude_session(db_session_id, new_sid)

    return reply
