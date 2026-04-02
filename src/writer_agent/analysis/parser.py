from pathlib import Path


def parse_document(path: Path) -> str:
    """Parse document and return plain text."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".text"):
        return path.read_text(encoding="utf-8")
    elif suffix == ".md":
        return path.read_text(encoding="utf-8")
    elif suffix == ".docx":
        return _parse_docx(path)
    elif suffix == ".pdf":
        return _parse_pdf(path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def _parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_pdf(path: Path) -> str:
    import pdfplumber
    with pdfplumber.open(str(path)) as pdf:
        pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
    return "\n\n".join(pages)


def parse_directory(dir_path: Path) -> dict[str, str]:
    """Parse all supported documents in directory. Returns {filename: text}."""
    results = {}
    for path in Path(dir_path).iterdir():
        if path.suffix.lower() in (".txt", ".md", ".docx", ".pdf"):
            try:
                results[path.name] = parse_document(path)
            except Exception as e:
                print(f"Warning: failed to parse {path.name}: {e}")
    return results
