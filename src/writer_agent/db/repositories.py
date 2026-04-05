"""CRUD repositories for all database tables."""

import json
from writer_agent.db.database import Database


def _row_to_dict(row) -> dict:
    """Convert sqlite3.Row to dict."""
    if row is None:
        return None
    return dict(row)


def _json_default(val):
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return val


class ProjectRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, name: str, genre: str = "", description: str = "",
               tropes: list = None, target_words: int = 600000) -> int:
        cur = self.db.execute(
            "INSERT INTO projects (name, genre, description, tropes, target_words) VALUES (?, ?, ?, ?, ?)",
            (name, genre, description, _json_default(tropes or []), target_words),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, project_id: int) -> dict:
        row = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _row_to_dict(row)

    def get_by_name(self, name: str) -> dict:
        row = self.db.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
        return _row_to_dict(row)

    def list(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]

    def update_status(self, project_id: int, status: str):
        self.db.execute(
            "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, project_id),
        )
        self.db.connection.commit()


class CharacterRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, name: str, description: str = "",
               personality: str = "", full_name: str = "", background: str = "",
               arc: str = "", metadata: dict = None) -> int:
        cur = self.db.execute(
            "INSERT INTO characters (project_id, name, full_name, description, personality, background, arc, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, name, full_name, description, personality, background, arc,
             _json_default(metadata or {})),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, char_id: int) -> dict:
        row = self.db.execute("SELECT * FROM characters WHERE id = ?", (char_id,)).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM characters WHERE project_id = ? ORDER BY created_at", (project_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def update(self, char_id: int, **kwargs):
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [char_id]
        self.db.execute(f"UPDATE characters SET {sets} WHERE id = ?", vals)
        self.db.connection.commit()

    def get_relationships(self, char_id: int) -> list[dict]:
        char = self.get(char_id)
        if not char:
            return []
        name = char["name"]
        rows = self.db.execute(
            "SELECT * FROM relationships WHERE char_a = ? OR char_b = ?", (name, name)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


class ChapterRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, chapter_number: int, title: str = "",
               summary: str = "", full_text: str = "",
               compact_summary: str = "", arc_summary: str = "") -> int:
        word_count = len(full_text.split()) if full_text else 0
        cur = self.db.execute(
            "INSERT INTO chapters "
            "(project_id, chapter_number, title, summary, compact_summary, arc_summary, full_text, word_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, chapter_number, title, summary, compact_summary, arc_summary, full_text, word_count),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, chapter_id: int) -> dict:
        row = self.db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        return _row_to_dict(row)

    def get_by_number(self, project_id: int, chapter_number: int) -> dict:
        row = self.db.execute(
            "SELECT * FROM chapters WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter_number),
        ).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number", (project_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_latest(self, project_id: int) -> dict:
        row = self.db.execute(
            "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return _row_to_dict(row)

    def update_text(self, chapter_id: int, full_text: str):
        word_count = len(full_text.split()) if full_text else 0
        self.db.execute(
            "UPDATE chapters SET full_text = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (full_text, word_count, chapter_id),
        )
        self.db.connection.commit()

    def update_summaries(self, chapter_id: int, summary: str = "",
                         compact_summary: str = "", arc_summary: str = ""):
        self.db.execute(
            "UPDATE chapters SET summary = ?, compact_summary = ?, arc_summary = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (summary, compact_summary, arc_summary, chapter_id),
        )
        self.db.connection.commit()


class PlotThreadRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, name: str, description: str = "",
               status: str = "active", importance: int = 5) -> int:
        cur = self.db.execute(
            "INSERT INTO plot_threads (project_id, name, description, status, importance) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, name, description, status, importance),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, thread_id: int) -> dict:
        row = self.db.execute("SELECT * FROM plot_threads WHERE id = ?", (thread_id,)).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int, status: str = None) -> list[dict]:
        if status:
            rows = self.db.execute(
                "SELECT * FROM plot_threads WHERE project_id = ? AND status = ? ORDER BY importance DESC",
                (project_id, status),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM plot_threads WHERE project_id = ? ORDER BY importance DESC",
                (project_id,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def resolve(self, thread_id: int, resolved_chapter: int = None):
        self.db.execute(
            "UPDATE plot_threads SET status = 'resolved', resolved_chapter = ? WHERE id = ?",
            (resolved_chapter, thread_id),
        )
        self.db.connection.commit()


class RelationshipRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, char_a: str, char_b: str,
               type: str = "", description: str = "", evolution: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO relationships (project_id, char_a, char_b, type, description, evolution) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, char_a, char_b, type, description, evolution),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, rel_id: int) -> dict:
        row = self.db.execute("SELECT * FROM relationships WHERE id = ?", (rel_id,)).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM relationships WHERE project_id = ?", (project_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


class WorldElementRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, name: str, category: str = "",
               description: str = "", metadata: dict = None) -> int:
        cur = self.db.execute(
            "INSERT INTO world_elements (project_id, category, name, description, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, category, name, description, _json_default(metadata or {})),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, elem_id: int) -> dict:
        row = self.db.execute("SELECT * FROM world_elements WHERE id = ?", (elem_id,)).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM world_elements WHERE project_id = ? ORDER BY category, name",
            (project_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


class StyleProfileRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, name: str, source_files: list = None,
               analysis: dict = None, sample_passages: list = None) -> int:
        cur = self.db.execute(
            "INSERT INTO style_profiles (name, source_files, analysis, sample_passages) "
            "VALUES (?, ?, ?, ?)",
            (name, _json_default(source_files or []),
             _json_default(analysis or {}),
             _json_default(sample_passages or [])),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, profile_id: int) -> dict:
        row = self.db.execute("SELECT * FROM style_profiles WHERE id = ?", (profile_id,)).fetchone()
        return _row_to_dict(row)

    def list(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM style_profiles ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]


class BrainstormSessionRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, notes: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO brainstorm_sessions (project_id, messages, notes) VALUES (?, '[]', ?)",
            (project_id, notes),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, session_id: int) -> dict:
        row = self.db.execute(
            "SELECT * FROM brainstorm_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_dict(row)

    def add_message(self, session_id: int, role: str, content: str):
        session = self.get(session_id)
        messages = json.loads(session["messages"])
        messages.append({"role": role, "content": content})
        self.db.execute(
            "UPDATE brainstorm_sessions SET messages = ? WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), session_id),
        )
        self.db.connection.commit()

    def get_messages(self, session_id: int) -> list[dict]:
        session = self.get(session_id)
        return json.loads(session["messages"])


class TimelineEventRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, description: str = "",
               chapter_id: int = None, event_order: int = 0,
               characters_involved: list = None, plot_threads: list = None) -> int:
        cur = self.db.execute(
            "INSERT INTO timeline_events (project_id, chapter_id, event_order, description, "
            "characters_involved, plot_threads) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, chapter_id, event_order, description,
             _json_default(characters_involved or []),
             _json_default(plot_threads or [])),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get_by_chapter(self, chapter_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM timeline_events WHERE chapter_id = ? ORDER BY event_order",
            (chapter_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM timeline_events WHERE project_id = ? ORDER BY event_order",
            (project_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


class PlotStateRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int, chapter_number: int, state: dict) -> int:
        cur = self.db.execute(
            "INSERT INTO plot_states (project_id, chapter_number, state) VALUES (?, ?, ?)",
            (project_id, chapter_number, json.dumps(state, ensure_ascii=False)),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get_latest(self, project_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM plot_states WHERE project_id = ? ORDER BY chapter_number DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return _row_to_dict(row)

    def get_by_chapter(self, project_id: int, chapter_number: int) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM plot_states WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter_number),
        ).fetchone()
        return _row_to_dict(row)

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM plot_states WHERE project_id = ? ORDER BY chapter_number",
            (project_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


class AgentSessionRepo:
    """CRUD for agent_sessions — persistent conversation history with state machine."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, project_id: int) -> int:
        cur = self.db.execute(
            "INSERT INTO agent_sessions (project_id, status) VALUES (?, 'spawning')",
            (project_id,),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def get(self, session_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM agent_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_dict(row)

    def get_active(self, project_id: int) -> dict | None:
        """Find the most recent resumable session (ready, waiting, or paused)."""
        row = self.db.execute(
            "SELECT * FROM agent_sessions WHERE project_id = ? "
            "AND status IN ('ready', 'waiting', 'paused') "
            "ORDER BY updated_at DESC, id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return _row_to_dict(row)

    def set_state(self, session_id: int, state: str):
        """Update session status to a new state machine state."""
        self.db.execute(
            "UPDATE agent_sessions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (state, session_id),
        )
        self.db.connection.commit()

    def add_message(self, session_id: int, role: str, content: str):
        session = self.get(session_id)
        messages = json.loads(session["messages"])
        messages.append({"role": role, "content": content})
        self.db.execute(
            "UPDATE agent_sessions SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), session_id),
        )
        self.db.connection.commit()

    def update_tokens(self, session_id: int, input_tokens: int = 0, output_tokens: int = 0):
        session = self.get(session_id)
        self.db.execute(
            "UPDATE agent_sessions SET input_tokens = ?, output_tokens = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session["input_tokens"] + input_tokens, session["output_tokens"] + output_tokens, session_id),
        )
        self.db.connection.commit()

    def pause(self, session_id: int):
        self.set_state(session_id, "paused")

    def complete(self, session_id: int):
        self.set_state(session_id, "completed")

    def get_messages(self, session_id: int) -> list[dict]:
        session = self.get(session_id)
        return json.loads(session["messages"])

    def list_by_project(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM agent_sessions WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
