import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    genre TEXT DEFAULT '',
    tropes TEXT DEFAULT '[]',
    status TEXT DEFAULT 'brainstorming',
    target_words INTEGER DEFAULT 600000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    background TEXT DEFAULT '',
    arc TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    char_a TEXT NOT NULL,
    char_b TEXT NOT NULL,
    type TEXT DEFAULT '',
    description TEXT DEFAULT '',
    evolution TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS plot_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    importance INTEGER DEFAULT 5,
    introduced_chapter INTEGER,
    resolved_chapter INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS world_elements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    category TEXT DEFAULT '',
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    full_text TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS style_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_files TEXT DEFAULT '[]',
    analysis TEXT DEFAULT '{}',
    sample_passages TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brainstorm_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    messages TEXT DEFAULT '[]',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER,
    event_order INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    characters_involved TEXT DEFAULT '[]',
    plot_threads TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);

CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id);
CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);
CREATE INDEX IF NOT EXISTS idx_chapters_number ON chapters(project_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_plots_project ON plot_threads(project_id);
CREATE INDEX IF NOT EXISTS idx_relationships_project ON relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_world_project ON world_elements(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON brainstorm_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_timeline_project ON timeline_events(project_id);
CREATE INDEX IF NOT EXISTS idx_timeline_chapter ON timeline_events(chapter_id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row

    def initialize(self):
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def execute(self, sql: str, params=()):
        return self._conn.execute(sql, params)

    @property
    def connection(self):
        return self._conn
