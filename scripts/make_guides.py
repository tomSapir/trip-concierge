"""Render each destination guide in guide_content.py to data/destinations/<name>.pdf.

The PDFs are build artifacts you can regenerate any time; guide_content.py is the
source of truth, and the registry decides which guides must exist.
"""
import sys
import pathlib

# Make the repo root importable so `app...` resolves wherever this is run from.
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.destination_registry import all_destinations
from guide_content import GUIDES  # sibling module (scripts/ is on sys.path[0])
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

OUT_DIR = ROOT / "data" / "destinations"


def main():
    styles = getSampleStyleSheet()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for dest in all_destinations():
        # Same-set invariant: a registry destination with no guide content is a
        # bug, not a file to skip silently. Fail loudly so the corpus stays in
        # lockstep with the registry.
        if dest.name not in GUIDES:
            raise SystemExit(f"No guide content for registry destination: {dest.name}")

        guide = GUIDES[dest.name]

        # Title line, then a bold heading + paragraph for each facet of the guide.
        flowables = [
            Paragraph(f"{dest.name}, {guide['country']}", styles["Title"]),
            Spacer(1, 12),
        ]
        for heading, body in guide["sections"]:
            flowables.append(Paragraph(heading, styles["Heading2"]))
            flowables.append(Paragraph(body, styles["BodyText"]))
            flowables.append(Spacer(1, 8))

        SimpleDocTemplate(str(OUT_DIR / f"{dest.name}.pdf"), pagesize=A4).build(flowables)
        print(f"wrote {dest.name}.pdf")


if __name__ == "__main__":
    main()
