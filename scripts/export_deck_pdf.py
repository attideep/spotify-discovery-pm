#!/usr/bin/env python3
"""Export deck HTML to PDF via weasyprint if available, else print instructions."""

from pathlib import Path

DECK = Path(__file__).resolve().parent.parent / "deck" / "index.html"
OUT = Path(__file__).resolve().parent.parent / "deck" / "NL Spotify.pdf"


def main() -> None:
    if not DECK.exists():
        print(f"Missing {DECK}")
        return
    try:
        from weasyprint import HTML
        HTML(filename=str(DECK)).write_pdf(str(OUT))
        print(f"Exported {OUT} ({OUT.stat().st_size // 1024} KB)")
    except ImportError:
        print("Install weasyprint: pip install weasyprint")
        print(f"Or open {DECK} in Chrome → Print → Save as PDF → {OUT}")


if __name__ == "__main__":
    main()
