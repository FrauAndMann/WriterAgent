import re
from collections import Counter

# Minimal Russian stop words
STOP_WORDS = {
    "и", "в", "на", "с", "что", "это", "как", "не", "он", "она", "они",
    "но", "а", "к", "у", "по", "из", "за", "от", "о", "для", "это",
    "был", "была", "было", "быть", "есть", "будет", "я", "ты", "мы", "вы",
    "его", "её", "их", "мой", "твой", "свой", "наш", "ваш", "тот", "этот",
    "же", "ли", "уже", "ещё", "даже", "тоже", "так", "вот", "тут", "где",
    "когда", "только", "ни", "бы", "до", "если", "при", "чем", "или",
}


class StyleAnalyzer:
    def analyze(self, text: str) -> dict:
        sentences = self._split_sentences(text)
        words = self._tokenize(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return {
            "avg_sentence_length": self._avg_sentence_len(sentences, words),
            "total_words": len(words),
            "frequent_words": self._frequent_words(words, top=30),
            "sentence_patterns": self._sentence_patterns(sentences),
            "paragraph_lengths": [self._count_words(p) for p in paragraphs],
            "dialogue_ratio": self._dialogue_ratio(text),
            "sample_passages": self._extract_passages(paragraphs, count=5),
            "pov_style": self._detect_pov(text),
        }

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'[а-яА-ЯёЁa-zA-Z]+', text)

    def _count_words(self, text: str) -> int:
        return len(self._tokenize(text))

    def _avg_sentence_len(self, sentences: list[str], words: list[str]) -> float:
        if not sentences:
            return 0.0
        return len(words) / len(sentences)

    def _frequent_words(self, words: list[str], top: int = 30) -> list[str]:
        filtered = [w.lower() for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
        counter = Counter(filtered)
        return [w for w, _ in counter.most_common(top)]

    def _sentence_patterns(self, sentences: list[str]) -> dict:
        total = len(sentences)
        if total == 0:
            return {}
        # Check against original text for punctuation since split removes it
        questions = sum(1 for s in sentences if s.endswith("?"))
        exclamations = sum(1 for s in sentences if s.endswith("!"))
        return {
            "questions_ratio": questions / total,
            "exclamations_ratio": exclamations / total,
            "statements_ratio": 1 - (questions + exclamations) / total,
        }

    def _dialogue_ratio(self, text: str) -> float:
        dialogue_chars = sum(len(m) for m in re.findall(r'—[^—]+—|«[^»]+»|"[^"]+"', text))
        total = len(text)
        return dialogue_chars / total if total > 0 else 0.0

    def _extract_passages(self, paragraphs: list[str], count: int = 5) -> list[str]:
        scored = sorted(paragraphs, key=lambda p: len(p), reverse=True)
        return scored[:count]

    def _detect_pov(self, text: str) -> str:
        first_person = len(re.findall(r'\bя\b', text, re.IGNORECASE))
        third_person = len(re.findall(r'\bон\b|\bона\b|\bони\b', text, re.IGNORECASE))
        if first_person > third_person * 2:
            return "first_person"
        return "third_person"
