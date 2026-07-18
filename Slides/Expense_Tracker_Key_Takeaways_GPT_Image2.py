from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "Expense_Tracker_Key_Takeaways_GPT_Image2.pdf"
IMAGE_PATH = BASE_DIR / "expense_tracker_gpt_image2_mockup.png"

BLUE = colors.HexColor("#1F6FEB")
TEAL = colors.HexColor("#12A6A6")
GREEN = colors.HexColor("#25A46A")
ORANGE = colors.HexColor("#F28C28")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5F6B7A")
PANEL = colors.HexColor("#F6F8FA")
LINE = colors.HexColor("#D9E2EC")


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleLarge",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=BLUE,
            spaceBefore=6,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.2,
            textColor=INK,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CardTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.4,
            leading=11.5,
            textColor=INK,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CardBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=11.3,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=12,
            textColor=colors.white,
            alignment=TA_CENTER,
        )
    )
    return styles


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 15 * mm, A4[0] - doc.rightMargin, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(
        A4[0] / 2,
        9 * mm,
        "Expense Tracker case study | Supabase + FastAPI + dbt + Power BI + AI agent vision",
    )
    canvas.drawRightString(A4[0] - doc.rightMargin, 9 * mm, str(doc.page))
    canvas.restoreState()


def card(title, body, style):
    return [
        Paragraph(title, style["CardTitle"]),
        Paragraph(body, style["CardBody"]),
    ]


def card_table(items, col_widths):
    rows = []
    for row in items:
        rows.append([card(title, body, STYLES) for title, body in row])
    table = Table(rows, colWidths=col_widths, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def bullet_list(items):
    return "<br/>".join(f"- {item}" for item in items)


def scaled_image(path, max_width, max_height):
    with PILImage.open(path) as img:
        width, height = img.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=22 * mm,
    )

    story = []

    story.append(Paragraph("Expense Tracker", STYLES["TitleLarge"]))
    story.append(
        Paragraph(
            "AI-built personal finance tracker and product vision for an AI-assisted analytics SaaS",
            STYLES["Subtitle"],
        )
    )

    story.append(Paragraph("What Claude Code Produced Well", STYLES["Section"]))
    story.append(
        card_table(
            [
                [
                    (
                        "Clear learning narrative",
                        "The notes explain not just what was built, but why it matters: personal pain, then a path to a useful product.",
                    ),
                    (
                        "Portfolio-grade stack",
                        "Supabase, FastAPI, dbt, and Power BI are practical tools that map well to data engineering interviews and demos.",
                    ),
                    (
                        "Strong AI framing",
                        "The split between AI as builder now and AI as product feature later makes the project easy to explain.",
                    ),
                ],
                [
                    (
                        "Good production context",
                        "The notes connect this practice app to Fabric, Synapse, Databricks agents, tool calling, and AEST handling.",
                    ),
                    (
                        "Useful roadmap",
                        "Done and pending sections make it obvious what is complete and what should become the next sprint.",
                    ),
                    (
                        "Concrete debugging history",
                        "The issue log captures real implementation learning: API keys, DNS, RLS, CLI install, and Git author fixes.",
                    ),
                ],
            ],
            [53 * mm, 53 * mm, 53 * mm],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("Recommended Improvements", STYLES["Section"]))
    story.append(
        Paragraph(
            bullet_list(
                [
                    "Fix date freshness: PROJECT_NOTES says last updated 2026-05-07, but the PDF was created on 2026-06-10.",
                    "Clarify repository naming: notes mention finflow-ai and the DS monorepo; make the public demo repo story explicit.",
                    "Avoid saying zero manual coding required unless presenting it as a learning reflection; it can sound less credible than AI-paired implementation.",
                    "Move secrets detail out of showcase material. It is fine to say legacy anon key compatibility was handled, but do not dwell on key format in a public PDF.",
                    "Use one polished generated image instead of many tiny hand-drawn PDF shapes; it communicates the product faster.",
                ]
            ),
            STYLES["Body"],
        )
    )

    story.append(Paragraph("Core Takeaways", STYLES["Section"]))
    takeaway_rows = [
        [
            Paragraph("<b>1. AI as co-builder</b><br/>Claude helped design, code, debug, and explain the stack.", STYLES["CardBody"]),
            Paragraph("<b>2. Real data stack</b><br/>The project uses tools that transfer to enterprise data work.", STYLES["CardBody"]),
        ],
        [
            Paragraph("<b>3. Personal pain to product</b><br/>A household tracker becomes a SaaS idea for small businesses.", STYLES["CardBody"]),
            Paragraph("<b>4. Agent-ready architecture</b><br/>FastAPI functions can become tools for natural-language analytics.", STYLES["CardBody"]),
        ],
    ]
    takeaway_table = Table(takeaway_rows, colWidths=[79 * mm, 79 * mm], hAlign="CENTER")
    takeaway_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF7FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B7D8F5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B7D8F5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(takeaway_table)

    story.append(Spacer(1, 10))
    story.append(
        Table(
            [[Paragraph("Best presentation angle: 'I used AI to build a real data product, then designed the next step where AI becomes the product interface.'", STYLES["Callout"])]],
            colWidths=[160 * mm],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ],
        )
    )

    story.append(PageBreak())

    story.append(Paragraph("AI-Powered Product Vision", STYLES["TitleLarge"]))
    story.append(
        Paragraph(
            "A cleaner showcase visual generated with GPT Image-2 and embedded into this revised PDF",
            STYLES["Subtitle"],
        )
    )
    story.append(scaled_image(IMAGE_PATH, 165 * mm, 93 * mm))
    story.append(Spacer(1, 9))

    story.append(Paragraph("How to Explain the Architecture", STYLES["Section"]))
    story.append(
        card_table(
            [
                [
                    (
                        "1. Upload",
                        "Customer drops a CSV or Excel file. AI detects columns, normalises data, maps categories, and flags messy rows.",
                    ),
                    (
                        "2. Transform",
                        "FastAPI writes clean data to Supabase. dbt models produce monthly summaries, savings rate, and budget variance.",
                    ),
                    (
                        "3. Ask",
                        "The chat agent calls Python tools such as get_monthly_summary, compare_months, and get_budget_status.",
                    ),
                ],
                [
                    (
                        "4. Visualise",
                        "Power BI embedded shows the dashboard and can be filtered from natural-language questions.",
                    ),
                    (
                        "5. Scale",
                        "The same pattern can support restaurant or retail owners who have spreadsheets but no data team.",
                    ),
                    (
                        "6. Differentiate",
                        "This is not only a budget app; it is an AI data-cleaning and analytics workflow for non-technical users.",
                    ),
                ],
            ],
            [53 * mm, 53 * mm, 53 * mm],
        )
    )

    story.append(Spacer(1, 10))
    flow = Table(
        [
            [
                Paragraph("<b>CSV / Excel</b>", STYLES["CardBody"]),
                Paragraph("<b>AI Cleaner</b>", STYLES["CardBody"]),
                Paragraph("<b>Supabase</b>", STYLES["CardBody"]),
                Paragraph("<b>dbt</b>", STYLES["CardBody"]),
                Paragraph("<b>Power BI + Chat</b>", STYLES["CardBody"]),
            ],
            [
                Paragraph("Raw uploads", STYLES["Small"]),
                Paragraph("Column mapping and categories", STYLES["Small"]),
                Paragraph("Clean relational data", STYLES["Small"]),
                Paragraph("Analytics marts", STYLES["Small"]),
                Paragraph("Insights for users", STYLES["Small"]),
            ],
        ],
        colWidths=[32 * mm, 32 * mm, 32 * mm, 28 * mm, 36 * mm],
        hAlign="CENTER",
    )
    flow.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF6F6")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(KeepTogether([Paragraph("Customer Data Flow", STYLES["Section"]), flow]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF saved to: {OUTPUT_PATH}")


STYLES = build_styles()


if __name__ == "__main__":
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Missing image: {IMAGE_PATH}")
    build_pdf()
