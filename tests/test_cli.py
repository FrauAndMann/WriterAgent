import pytest
from typer.testing import CliRunner
from writer_agent.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_new_project_creates_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "Test Novel"])
    assert result.exit_code == 0
    assert (tmp_path / "data" / "writer_agent.db").exists()


def test_list_projects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["new", "Test"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Test" in result.output


def test_analyze_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "sample.txt").write_text("Тёмный текст для анализа стиля. Это тест.", encoding="utf-8")
    result = runner.invoke(app, ["analyze-style", str(examples)])
    assert result.exit_code == 0
