"""Interactive Agent Engine — orchestrates tools via LLM conversation loop."""

from __future__ import annotations

import json
import re

from writer_agent.db.database import Database
from writer_agent.db.repositories import AgentSessionRepo
from writer_agent.engine.agent_tools import ToolDef, build_tool_registry
from writer_agent.engine.session_state import SessionState
from writer_agent.llm.prompts import build_system_agent


class AgentEngine:
    """Interactive agent that uses LLM + tools to help write novels."""

    MAX_HISTORY = 20

    def __init__(self, db: Database, llm_client, project_id: int, session_id: int | None = None):
        self.db = db
        self.llm = llm_client
        self.project_id = project_id
        self.tools = build_tool_registry()
        self.session_repo = AgentSessionRepo(db)
        self.session_id: int | None = None
        self.history: list[dict] = []
        self._state = SessionState.SPAWNING

        if session_id:
            # Restore existing session
            self.session_id = session_id
            self.history = self.session_repo.get_messages(session_id)
            # Resume: paused → ready
            self._state = SessionState.READY
            self._save_state(SessionState.READY)
        else:
            # Create new session
            self.session_id = self.session_repo.create(project_id)
            # spawning → ready
            self._state = SessionState.READY
            self._save_state(SessionState.READY)

    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state

    def chat(self, user_message: str) -> str:
        """Process a user message through the agent loop.

        Returns the final text response (with tool results already executed).
        """
        # ready/waiting → running
        self._transition(SessionState.RUNNING)

        # Add user message to history
        self._append_message("user", user_message)

        # Trim history
        self._trim_history()

        # Agent loop: send to LLM, parse tools, execute, repeat
        max_iterations = 5  # prevent infinite loops
        final_text = ""

        for _ in range(max_iterations):
            # Build messages for LLM
            messages = self._build_messages()

            # Call LLM
            response = self.llm.chat(messages=messages, max_tokens=4000)
            self._append_message("assistant", response)

            # Track tokens (rough estimate: 1 token ≈ 4 chars)
            self._update_token_counts(
                input_tokens=len(user_message) // 4,
                output_tokens=len(response) // 4,
            )

            # Parse tool calls
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # No tools — just text response
                final_text = self._clean_response(response)
                break

            # Execute tool calls
            results_text = ""
            for tc in tool_calls:
                result = self._execute_tool(tc["name"], tc.get("args", {}))
                result_str = json.dumps(result, ensure_ascii=False)
                results_text += f"\n```result\n{result_str}\n```\n"

            # Feed results back as user message
            self._append_message("user", results_text)

            # Trim history if too long
            self._trim_history()

            # Build display text from the response
            clean = self._clean_response(response)
            if clean.strip():
                final_text = clean + "\n"

        else:
            final_text = final_text or "Достигнут лимит итераций. Попробуй продолжить."

        # running → waiting
        self._transition(SessionState.WAITING)

        return final_text.strip()

    def pause_session(self):
        """Mark current session as paused."""
        if self.session_id:
            self._transition(SessionState.PAUSED)

    def complete_session(self):
        """Mark current session as completed."""
        if self.session_id:
            self._transition(SessionState.COMPLETED)

    def get_session_stats(self) -> dict:
        """Return session metadata."""
        if not self.session_id:
            return {"messages": 0, "input_tokens": 0, "output_tokens": 0, "state": "spawning"}
        session = self.session_repo.get(self.session_id)
        if not session:
            return {"messages": 0, "input_tokens": 0, "output_tokens": 0, "state": "spawning"}
        messages = json.loads(session["messages"])
        return {
            "messages": len(messages),
            "input_tokens": session["input_tokens"],
            "output_tokens": session["output_tokens"],
            "status": session["status"],
            "state": self._state.value,
            "created_at": session["created_at"],
        }

    def get_tools_prompt(self) -> str:
        """Build the tools description for the system prompt."""
        return "\n\n".join(t.to_prompt_text() for t in self.tools.values())

    def _transition(self, new_state: SessionState):
        """Transition to a new state with validation."""
        if not self._state.can_transition(new_state):
            raise ValueError(
                f"Invalid state transition: {self._state.value} → {new_state.value}"
            )
        self._state = new_state
        self._save_state(new_state)

    def _save_state(self, state: SessionState):
        """Persist state to DB."""
        if self.session_id:
            self.session_repo.set_state(self.session_id, state.value)

    def _append_message(self, role: str, content: str):
        """Add message to in-memory history and persist to DB."""
        self.history.append({"role": role, "content": content})
        if self.session_id:
            self.session_repo.add_message(self.session_id, role, content)

    def _update_token_counts(self, input_tokens: int = 0, output_tokens: int = 0):
        """Accumulate token usage for the session."""
        if self.session_id:
            self.session_repo.update_tokens(self.session_id, input_tokens, output_tokens)

    def _build_messages(self) -> list[dict]:
        """Build the full message list for the LLM."""
        system = build_system_agent(self.get_tools_prompt())
        messages = [{"role": "system", "content": system}]
        messages.extend(self.history)
        return messages

    def _parse_tool_calls(self, response: str) -> list[dict]:
        """Extract tool call JSON blocks from LLM response."""
        calls = []
        pattern = r"```tool\s*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match.strip())
                if "name" in data:
                    calls.append(data)
            except json.JSONDecodeError:
                try:
                    start = match.strip().find("{")
                    end = match.strip().rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(match.strip()[start:end])
                        if "name" in data:
                            calls.append(data)
                except json.JSONDecodeError:
                    pass
        return calls

    def _execute_tool(self, name: str, args: dict) -> dict:
        """Execute a single tool by name."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}. Available: {list(self.tools.keys())}"}

        try:
            result = tool.fn(
                db=self.db,
                project_id=self.project_id,
                llm_client=self.llm,
                context_builder=None,
                **args,
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    def _clean_response(self, response: str) -> str:
        """Remove tool-call and result blocks from response for display."""
        cleaned = re.sub(r"```tool\s*\n.*?```", "", response, flags=re.DOTALL)
        cleaned = re.sub(r"```result\s*\n.*?```", "", cleaned, flags=re.DOTALL)
        return cleaned.strip()

    def _trim_history(self):
        """Keep history within limits."""
        if len(self.history) > self.MAX_HISTORY * 2:
            self.history = self.history[:1] + self.history[-(self.MAX_HISTORY * 2):]
