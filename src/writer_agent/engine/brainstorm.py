from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, BrainstormSessionRepo,
    PlotThreadRepo, WorldElementRepo,
)
from writer_agent.llm.prompts import SYSTEM_BRAINSTORM


class BrainstormEngine:
    def __init__(self, db: Database, llm_client):
        self.db = db
        self.llm_client = llm_client
        self.project_repo = ProjectRepo(db)
        self.char_repo = CharacterRepo(db)
        self.session_repo = BrainstormSessionRepo(db)
        self.plot_repo = PlotThreadRepo(db)
        self.world_repo = WorldElementRepo(db)

    def start_session(self, title: str) -> int:
        project_id = self.project_repo.create(name=title, genre="dark romance")
        session_id = self.session_repo.create(project_id=project_id, notes="")
        return session_id

    def chat(self, session_id: int, user_message: str) -> str:
        self.session_repo.add_message(session_id, role="user", content=user_message)
        history = self.session_repo.get_messages(session_id)
        messages = [{"role": "system", "content": SYSTEM_BRAINSTORM}] + history
        response = self.llm_client.chat(messages=messages, max_tokens=2000)
        self.session_repo.add_message(session_id, role="assistant", content=response)
        return response

    def get_history(self, session_id: int) -> list[dict]:
        return self.session_repo.get_messages(session_id)

    def save_character(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.char_repo.create(project_id=project_id, **kwargs)

    def save_plot_thread(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.plot_repo.create(project_id=project_id, **kwargs)

    def save_world_element(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.world_repo.create(project_id=project_id, **kwargs)

    def finalize_session(self, session_id: int) -> int:
        """Mark project as ready for writing. Returns project_id."""
        session = self.session_repo.get(session_id)
        self.project_repo.update_status(session["project_id"], "outlined")
        return session["project_id"]
