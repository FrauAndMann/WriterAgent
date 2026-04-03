from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    CharacterRepo, PlotThreadRepo, RelationshipRepo,
)


class ConsistencyChecker:
    def __init__(self, db: Database):
        self.characters = CharacterRepo(db)
        self.plots = PlotThreadRepo(db)
        self.relationships = RelationshipRepo(db)

    def check(self, project_id: int, outline: str) -> list[str]:
        """Check outline for inconsistencies against stored state."""
        warnings = []
        outline_lower = outline.lower()

        # Check: dead characters shouldn't appear alive
        chars = self.characters.list_by_project(project_id)
        for char in chars:
            if char.get("status") == "dead" and char["name"].lower() in outline_lower:
                warnings.append(
                    f"Персонаж '{char['name']}' мёртв, но упомянут в плане как активный."
                )

        # Check: resolved threads referenced as active
        threads = self.plots.list_by_project(project_id)
        for thread in threads:
            if thread["status"] == "resolved" and thread["name"].lower() in outline_lower:
                warnings.append(
                    f"Сюжетная нить '{thread['name']}' уже разрешена, но упоминается как активная."
                )

        return warnings
