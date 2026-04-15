"""
PDF Converter - Converts Word (.docx) to PDF using LibreOffice headless.

Requires LibreOffice installed:
- Mac: brew install --cask libreoffice
- Linux/Docker: apt-get install libreoffice
- Railway: Add to Dockerfile
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Common LibreOffice paths
LIBREOFFICE_PATHS = [
    "libreoffice",
    "soffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_libreoffice() -> str | None:
    """Find LibreOffice executable on the system."""
    for path in LIBREOFFICE_PATHS:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes | None:
    """
    Convert a .docx file (as bytes) to PDF using LibreOffice headless.

    Returns PDF bytes or None if LibreOffice is not available.
    """
    lo_path = find_libreoffice()
    if not lo_path:
        logger.warning("LibreOffice not found — PDF conversion unavailable")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "report.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        try:
            result = subprocess.run(
                [
                    lo_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmpdir,
                    docx_path,
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr.decode()}")
                return None

            pdf_path = os.path.join(tmpdir, "report.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()

            logger.error("PDF file not created after conversion")
            return None

        except subprocess.TimeoutExpired:
            logger.error("LibreOffice conversion timed out (60s)")
            return None
        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            return None


def is_pdf_available() -> bool:
    """Check if PDF conversion is available."""
    return find_libreoffice() is not None
