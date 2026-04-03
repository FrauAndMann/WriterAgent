"""Scene classification and type-specific prompt fragments."""

from __future__ import annotations

SCENE_TYPES = ("opening", "dialogue", "action", "climax", "reflection", "erotic", "transition")

SCENE_PROMPTS: dict[str, str] = {
    "opening": (
        "Сцена-вступление. Создай плотную атмосферу с первых строк. "
        "Используй synesthetic details (запах + звук + цвет). "
        "Читатель должен почувствовать мир кожей. "
        "Начинай in media res — без долгих описаний, сразу в действие/эмоцию."
    ),
    "dialogue": (
        "Диалог-сцена. Каждая реплика — это битва или танец. "
        "Подтекст важнее текста: персонажи говорят одно, значат другое. "
        "Используй action beats между репликами (взгляды, жесты, дыхание). "
        "Диалог должен обнажать отношения и power dynamics."
    ),
    "action": (
        "Экшен-сцена. Короткие, резкие предложения. Глаголы-действия. "
        "Ощущение скорости и опасности. Кинематографичные ракурсы. "
        "Перемежай экшен с моментами тишины — контраст усиливает напряжение. "
        "Тело персонажа — усталость, боль, адреналин — всё физически."
    ),
    "climax": (
        "Кульминация. Максимальное эмоциональное напряжение. "
        "Каждое слово — на вес золота. Внутренний конфликт обнажается. "
        "Используй contrast: тихий момент перед взрывом, нежность в жестокости. "
        "Читатель должен забыть дышать."
    ),
    "reflection": (
        "Сцена рефлексии. Внутренний мир персонажа. "
        "Длинные, плавные предложения. Поток сознания, обрывки воспоминаний. "
        "Метафоры и образы из подсознания. Прошлое вторгается в настоящее. "
        "Не объясняй — покажи через ощущения и ассоциации."
    ),
    "erotic": (
        "Сенсуальная сцена. Не porn — erotics. "
        "Пять чувств: кожа, запах, вкус, звук, зрение. Метафоры природы (огонь, вода, гроза). "
        "Power dynamics и vulnerability одновременно. Контроль и потеря контроля. "
        "Pace: медленное нарастание, чередование нежности и интенсивности. "
        "Тело говорит языком, который слова не знают."
    ),
    "transition": (
        "Связующая сцена. Краткая, функциональная, но не скучная. "
        "Один яркий образ, одна деталь, которая запомнится. "
        "Подразни читателя тем, что будет дальше. Тизер, крючок."
    ),
}

CLASSIFICATION_PROMPT = """\
Проанализируй план главы и определи типы сцен.
Для каждой сцены укажи: тип, краткое описание, вовлечённые персонажи.

Типы: opening, dialogue, action, climax, reflection, erotic, transition

Ответ в формате:
1. [type] — описание (персонажи)
2. [type] — описание (персонажи)
"""


def get_scene_prompt(scene_type: str) -> str:
    """Return the prompt fragment for a scene type."""
    return SCENE_PROMPTS.get(scene_type, "")


def classify_scenes(llm_client, outline: str) -> list[dict]:
    """Classify an outline into scene types via LLM.

    Returns a list of dicts: [{"type": str, "description": str, "characters": str}]
    """
    response = llm_client.generate(
        system_prompt=CLASSIFICATION_PROMPT,
        user_prompt=f"[План главы]\n{outline}",
        max_tokens=500,
        temperature=0.3,
    )
    return _parse_classification(response)


def _parse_classification(response: str) -> list[dict]:
    """Parse LLM classification response into structured list."""
    scenes = []
    for line in response.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Try to parse "1. [type] — description (characters)"
        # Remove leading numbering
        cleaned = line.lstrip("0123456789.-) ")
        # Find scene type
        found_type = None
        for stype in SCENE_TYPES:
            if stype in cleaned.lower().split("—")[0].split()[0]:
                found_type = stype
                break

        if found_type is None:
            # Fallback: check first word
            first_word = cleaned.split()[0].strip("[]").lower()
            if first_word in SCENE_TYPES:
                found_type = first_word

        if found_type is None:
            continue

        # Extract description and characters
        parts = cleaned.split("—", 1)
        desc = parts[1].strip() if len(parts) > 1 else ""
        characters = ""
        if "(" in desc:
            paren_start = desc.rfind("(")
            characters = desc[paren_start:].strip("()")
            desc = desc[:paren_start].strip()

        scenes.append({
            "type": found_type,
            "description": desc,
            "characters": characters,
        })

    return scenes
