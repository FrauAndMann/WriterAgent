import pytest
from writer_agent.analysis.style import StyleAnalyzer


def test_analyze_extracts_basic_metrics():
    analyzer = StyleAnalyzer()
    sample = "Она вошла в комнату. Тёмные волосы падали на плечи. Он смотрел не отрываясь."
    result = analyzer.analyze(sample)
    assert "avg_sentence_length" in result
    assert "total_words" in result
    assert result["total_words"] > 0


def test_analyze_extracts_vocabulary_patterns():
    analyzer = StyleAnalyzer()
    sample = "Тьма обволакивала её. Тёмные глаза сверкали. Тьма снова наступала."
    result = analyzer.analyze(sample)
    assert "frequent_words" in result
    assert any("тьм" in w.lower() for w in result["frequent_words"])


def test_analyze_extracts_sample_passages():
    analyzer = StyleAnalyzer()
    text = "Параграф один. Достаточно длинный. Для анализа.\n\nПараграф второй. Тоже текст. Для проверки."
    result = analyzer.analyze(text)
    assert "sample_passages" in result
    assert len(result["sample_passages"]) > 0
