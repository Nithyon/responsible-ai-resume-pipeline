"""Generate the public, fully synthetic PDF fixture and its profile illustration."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as ReportLabImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "pdf_samples"
PROFILE_PATH = OUTPUT_DIR / "synthetic_profile.png"
PDF_PATH = OUTPUT_DIR / "synthetic_resume.pdf"


def create_profile_illustration() -> None:
    canvas = Image.new("RGB", (360, 360), "#eef2ff")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((112, 52, 248, 188), fill="#4338ca")
    draw.rounded_rectangle((62, 188, 298, 338), radius=65, fill="#6366f1")
    draw.ellipse((139, 88, 165, 114), fill="#eef2ff")
    draw.ellipse((195, 88, 221, 114), fill="#eef2ff")
    draw.arc((145, 108, 215, 158), start=10, end=170, fill="#eef2ff", width=8)
    canvas.save(PROFILE_PATH)


def create_resume() -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ResumeName",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=27,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#3730a3"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ResumeBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1f2937"),
        )
    )

    document = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Synthetic Resume Fixture",
        author="Resume Knowledge Pipeline",
        subject="Synthetic data for reproducible document-ingestion tests",
    )

    profile = ReportLabImage(str(PROFILE_PATH), width=30 * mm, height=30 * mm)
    identity = [
        Paragraph("MIRA SEN", styles["ResumeName"]),
        Paragraph("Data Systems Engineer", styles["ResumeBody"]),
        Paragraph(
            "mira.sen@example.test | +91 90000 00999 | Pune, India<br/>"
            '<link href="https://portfolio.example/mira-sen" color="#4338ca">portfolio.example/mira-sen</link>',
            styles["ResumeBody"],
        ),
    ]
    header = Table([[profile, identity]], colWidths=[36 * mm, 137 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [header, Spacer(1, 4 * mm)]
    content = [
        (
            "SUMMARY",
            "Data systems engineer focused on reliable pipelines, observable services, and privacy-aware analytics.",
        ),
        (
            "EXPERIENCE",
            "Data Systems Engineer | Northwind Research | Pune, India | 2022-07 to Present<br/>"
            "Built batch and streaming pipelines processing twelve million synthetic events per day. "
            "Introduced data-quality checks that reduced failed jobs by 32 percent.",
        ),
        (
            "EDUCATION",
            "B.Tech Computer Science | Example Institute of Technology | 2022",
        ),
        (
            "PROJECTS",
            "Traceable Document Index | Python, Neo4j, Chroma<br/>"
            "Linked extracted claims to their source page and document block.",
        ),
    ]
    for heading, body in content:
        story.extend(
            [
                Paragraph(heading, styles["SectionHeading"]),
                Paragraph(body, styles["ResumeBody"]),
            ]
        )

    story.append(Paragraph("SKILLS", styles["SectionHeading"]))
    skills = Table(
        [
            ["Category", "Skills"],
            ["Programming", "Python, SQL"],
            ["Data", "Apache Spark, Kafka, Airflow"],
            ["Infrastructure", "Docker, AWS"],
        ],
        colWidths=[42 * mm, 128 * mm],
        repeatRows=1,
    )
    skills.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#312e81")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d2fe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(skills)
    story.extend(
        [
            Paragraph("CERTIFICATIONS", styles["SectionHeading"]),
            Paragraph("Cloud Data Foundations | Example Learning Institute | 2025", styles["ResumeBody"]),
            Paragraph("LANGUAGES", styles["SectionHeading"]),
            Paragraph("English | Professional; Hindi | Native", styles["ResumeBody"]),
        ]
    )
    document.build(story)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_profile_illustration()
    create_resume()
    print(f"Created {PROFILE_PATH.relative_to(ROOT)}")
    print(f"Created {PDF_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
