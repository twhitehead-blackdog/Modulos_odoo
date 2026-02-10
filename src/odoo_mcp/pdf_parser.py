"""PDF parsing utilities for extracting invoice/purchase order data."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class PDFContent:
    """Parsed content from a PDF file."""

    text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    pages: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


def extract_pdf_content(file_path: str, max_pages: int = 50) -> PDFContent:
    """Extract text and tables from a PDF file.

    Args:
        file_path: Path to the PDF file.
        max_pages: Maximum number of pages to process.

    Returns:
        PDFContent with extracted text, tables, and metadata.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {file_path}")

    content = PDFContent()

    with pdfplumber.open(file_path) as pdf:
        content.pages = len(pdf.pages)
        content.metadata = pdf.metadata or {}

        pages_to_process = min(len(pdf.pages), max_pages)
        all_text = []
        all_tables = []

        for i in range(pages_to_process):
            page = pdf.pages[i]

            # Extract text
            page_text = page.extract_text()
            if page_text:
                all_text.append(f"--- Page {i + 1} ---\n{page_text}")

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                cleaned = []
                for row in table:
                    cleaned_row = [
                        (cell.strip() if cell else "") for cell in row
                    ]
                    cleaned.append(cleaned_row)
                if cleaned:
                    all_tables.append(cleaned)

        content.text = "\n\n".join(all_text)
        content.tables = all_tables

    return content


def format_tables_as_text(tables: list[list[list[str]]]) -> str:
    """Format extracted tables as readable text."""
    if not tables:
        return "No tables found in the document."

    output = []
    for idx, table in enumerate(tables):
        output.append(f"\n=== Table {idx + 1} ===")
        for row in table:
            output.append(" | ".join(row))
    return "\n".join(output)


def extract_amounts_from_text(text: str) -> dict[str, list[str]]:
    """Extract potential monetary amounts from text.

    Returns a dict with categorized amounts found in the text.
    """
    results: dict[str, list[str]] = {
        "amounts": [],
        "totals": [],
        "taxes": [],
    }

    # Common patterns for amounts (supports $, €, or plain numbers with decimals)
    amount_pattern = r'[\$€]?\s*[\d,]+\.\d{2}'

    # Look for total-related lines
    for line in text.split("\n"):
        line_lower = line.lower().strip()
        amounts_in_line = re.findall(amount_pattern, line)

        if not amounts_in_line:
            continue

        if any(word in line_lower for word in ["total", "amount due", "monto", "importe"]):
            results["totals"].extend(amounts_in_line)
        elif any(word in line_lower for word in ["tax", "iva", "igv", "vat", "impuesto"]):
            results["taxes"].extend(amounts_in_line)
        else:
            results["amounts"].extend(amounts_in_line)

    return results
