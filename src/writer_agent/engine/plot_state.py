"""Plot state machine — structured tracking of novel plot progression."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Conflict:
    name: str
    parties: str = ""
    status: str = "active"  # active, resolved, dormant
    intensity: int = 5  # 1-10
    since_chapter: int = 0


@dataclass
class CharacterArc:
    character: str
    current_state: str = ""
    trajectory: str = ""
    last_chapter: int = 0


@dataclass
class Mystery:
    name: str
    clues_given: int = 0
    reader_knows: bool = False
    resolution_chapter: int | None = None


@dataclass
class Relationship:
    pair: str
    type: str = ""
    intensity: int = 5  # 1-10
    direction: str = "warming"  # warming, cooling, complicated, stable
    since_chapter: int = 0


@dataclass
class Hook:
    description: str
    planted_chapter: int = 0
    expected_payoff_chapter: int | None = None


@dataclass
class PlotState:
    conflicts: list[dict] = field(default_factory=list)
    character_arcs: list[dict] = field(default_factory=list)
    mysteries: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    tone: str = "rising_tension"
    hooks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conflicts": self.conflicts,
            "character_arcs": self.character_arcs,
            "mysteries": self.mysteries,
            "relationships": self.relationships,
            "tone": self.tone,
            "hooks": self.hooks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlotState:
        return cls(
            conflicts=data.get("conflicts", []),
            character_arcs=data.get("character_arcs", []),
            mysteries=data.get("mysteries", []),
            relationships=data.get("relationships", []),
            tone=data.get("tone", "rising_tension"),
            hooks=data.get("hooks", []),
        )


def empty_plot_state() -> PlotState:
    """Return an empty initial plot state."""
    return PlotState()


TONE_VALUES = ("rising_tension", "plateau", "climax", "falling", "resolution")
