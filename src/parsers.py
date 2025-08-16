from io import BytesIO
from typing import Union
import pathlib

def _read_text_from_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore")

def _read_text_from_pdf(file_bytes: bytes) -> str:
    import fitz  # PyMuPDF
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts)

def _read_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_file(uploaded_file) -> str:
    """uploaded_file is a Streamlit UploadedFile or a file-like with .name and .read()."""
    name = getattr(uploaded_file, "name", "file")
    suffix = pathlib.Path(name).suffix.lower()
    data = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()
    if suffix == ".pdf":
        return _read_text_from_pdf(data)
    elif suffix == ".docx":
        return _read_text_from_docx(data)
    elif suffix == ".txt":
        return _read_text_from_txt(data)
    else:
        # try best-effort text
        return _read_text_from_txt(data)
