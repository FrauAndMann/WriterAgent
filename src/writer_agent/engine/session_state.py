"""Session state machine — explicit lifecycle for agent sessions."""

from __future__ import annotations

from enum import Enum


class SessionState(str, Enum):
    """Agent session lifecycle states.

    Transitions:
        spawning → ready → running ⇄ waiting → paused → completed
                         ↑               │
                         └─── (resume) ───┘
    """
    SPAWNING = "spawning"      # Session created, loading context
    READY = "ready"            # Initialized, waiting for first message
    RUNNING = "running"        # Processing LLM request
    WAITING = "waiting"        # Response sent, waiting for next input
    PAUSED = "paused"          # User quit, session preserved
    COMPLETED = "completed"    # Session finished (novel done or explicit end)

    def can_transition(self, to_state: SessionState) -> bool:
        """Check if transition to another state is valid."""
        return to_state in TRANSITIONS.get(self, set())

    def is_terminal(self) -> bool:
        """Check if this state is terminal (no further transitions)."""
        return self == SessionState.COMPLETED


# Valid transitions: from_state → set of allowed to_states
TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.SPAWNING: {SessionState.READY},
    SessionState.READY: {SessionState.RUNNING, SessionState.PAUSED, SessionState.COMPLETED},
    SessionState.RUNNING: {SessionState.WAITING, SessionState.PAUSED, SessionState.COMPLETED},
    SessionState.WAITING: {SessionState.RUNNING, SessionState.PAUSED, SessionState.COMPLETED},
    SessionState.PAUSED: {SessionState.READY, SessionState.COMPLETED},
    SessionState.COMPLETED: set(),  # Terminal state
}

# Map legacy status values to new states
LEGACY_STATUS_MAP: dict[str, SessionState] = {
    "active": SessionState.WAITING,  # Pre-state-machine "active" → waiting
    "paused": SessionState.PAUSED,
    "completed": SessionState.COMPLETED,
}


class InvalidTransition(Exception):
    """Raised when attempting an invalid state transition."""

    def __init__(self, from_state: SessionState, to_state: SessionState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Allowed: {[s.value for s in TRANSITIONS.get(from_state, set())]}"
        )


def can_transition(from_state: SessionState, to_state: SessionState) -> bool:
    """Check if a transition is valid."""
    return to_state in TRANSITIONS.get(from_state, set())


def transition(from_state: SessionState, to_state: SessionState) -> SessionState:
    """Validate and perform a state transition.

    Returns the new state.
    Raises InvalidTransition if the transition is not allowed.
    """
    if not can_transition(from_state, to_state):
        raise InvalidTransition(from_state, to_state)
    return to_state


def resolve_state(status_value: str) -> SessionState:
    """Resolve a status string (possibly from DB) to a SessionState.

    Handles both new state names and legacy 'active' status.
    """
    # Try direct match first
    try:
        return SessionState(status_value)
    except ValueError:
        pass
    # Try legacy mapping
    if status_value in LEGACY_STATUS_MAP:
        return LEGACY_STATUS_MAP[status_value]
    # Default to spawning for unknown values
    return SessionState.SPAWNING


def is_terminal(state: SessionState) -> bool:
    """Check if a state is terminal (no further transitions)."""
    return state == SessionState.COMPLETED
