"""Convert style analysis metrics into detailed writing instructions."""

from __future__ import annotations


def build_style_injection(analysis: dict, sample_passages: list[str] | None = None) -> str:
    """Convert style analysis into a detailed style-injection prompt.

    Args:
        analysis: Dict from StyleAnalyzer.analyze() or stored in DB.
        sample_passages: Optional list of text passages for few-shot examples.

    Returns:
        A multi-line string to inject into the system prompt.
    """
    lines = ["[Стиль автора — точная имитация]"]

    # Rhythm
    avg_sent = analysis.get("avg_sentence_length", 12)
    if avg_sent > 20:
        lines.append(
            "- Ритм: длинные, плавные предложения с придаточными и перечислениями. "
            "Пушкинский период."
        )
    elif avg_sent > 12:
        lines.append(
            "- Ритм: средние предложения, баланс длинных и коротких. Чередуй."
        )
    else:
        lines.append(
            "- Ритм: короткие, рубленые фразы. Хемингуэевская лаконичность. "
            "Каждое слово — удар."
        )

    # POV
    pov = analysis.get("pov_style", "third_person")
    if pov == "first_person":
        lines.append(
            "- POV: первое лицо. Интимность, субъективность. Мир через призму «я»."
        )
    else:
        lines.append(
            "- POV: третье лицо. Ограниченный фокус — мир через восприятие "
            "одного персонажа в сцене."
        )

    # Dialogue ratio
    dial = analysis.get("dialogue_ratio", 0)
    if dial > 0.3:
        lines.append(
            f"- Доля диалогов: {dial:.0%}. "
            "Диалоги — основной инструмент. Минимум narration между репликами."
        )
    elif dial > 0.1:
        lines.append(
            f"- Доля диалогов: {dial:.0%}. "
            "Диалоги для ключевых моментов. Баланс с описаниями."
        )
    else:
        lines.append(
            "- Мало диалогов. Основной инструмент — описание, рефлексия, атмосфера."
        )

    # Vocabulary signature
    words = analysis.get("frequent_words", [])[:12]
    if words:
        lines.append(
            f"- Лексическая сигнатура: {', '.join(words)}. "
            "Используй эти слова как якоря стиля."
        )

    # Sentence patterns
    patterns = analysis.get("sentence_patterns", {})
    if patterns.get("questions_ratio", 0) > 0.1:
        lines.append("- Часто использует риторические вопросы как приём.")
    if patterns.get("exclamations_ratio", 0) > 0.05:
        lines.append("- Восклицания для эмоциональных пиков.")

    # Sample passages as few-shot examples
    if sample_passages:
        lines.append("\n[Образцы стиля — пиши так же]")
        for i, p in enumerate(sample_passages[:3], 1):
            snippet = p[:300].strip()
            if len(snippet) > 50:
                lines.append(f"  {i}. «{snippet}…»")

    return "\n".join(lines)
