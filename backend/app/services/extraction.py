"""Turn an uploaded artefact into plain text for the agent.

Deliberately shallow: the assignment says production-grade OCR / document parsing
is out of scope. PDFs and .eml are parsed properly because those are the two real
intake channels; images return a labelled placeholder so the flow stays honest
rather than pretending to have read them.
"""
from __future__ import annotations

import io
from email import policy
from email.parser import BytesParser

TEXT_TYPES = {".txt", ".md", ".csv", ".log"}


def detect_source_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".eml", ".msg")):
        return "email"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")):
        return "image"
    return "text"


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)


def _from_email(data: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(data)
    header = "\n".join(
        f"{label}: {message.get(key, '')}"
        for label, key in (("From", "from"), ("To", "to"), ("Date", "date"), ("Subject", "subject"))
    )
    body_part = message.get_body(preferencelist=("plain", "html"))
    body = body_part.get_content() if body_part else ""

    chunks = [header, "", body.strip()]
    for att in message.iter_attachments():
        name = att.get_filename() or "attachment"
        payload = att.get_payload(decode=True) or b""
        if name.lower().endswith(".pdf"):
            chunks += [f"\n--- attachment: {name} ---", _from_pdf(payload)]
        elif name.lower().endswith(tuple(TEXT_TYPES)):
            chunks += [f"\n--- attachment: {name} ---", payload.decode("utf-8", "ignore")]
        else:
            chunks.append(f"\n[attachment not parsed: {name}]")
    return "\n".join(chunks).strip()


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (source_type, text)."""
    source_type = detect_source_type(filename)
    if source_type == "pdf":
        return source_type, _from_pdf(data)
    if source_type == "email":
        return source_type, _from_email(data)
    if source_type == "image":
        return source_type, (
            f"[Image received: {filename}. OCR is out of scope for this build; "
            "type or paste the complaint text to have it read.]"
        )
    return "text", data.decode("utf-8", "ignore")
