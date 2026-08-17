"""
PDF Report Generation using ReportLab.
Generates a structured crop health report and uploads to S3.
"""

from __future__ import annotations
import io
import logging
from datetime import datetime, timezone
from bson import ObjectId

logger = logging.getLogger(__name__)


async def generate_pdf_report(
    upload_id: str,
    field_id: str,
    health_score: float,
    disease_summary: list[dict],
    detections: list[dict],
    db,
) -> str | None:
    """Generate PDF, upload to S3, return URL."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                 topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle("Title", parent=styles["Title"],
                                      fontSize=22, textColor=colors.HexColor("#1a4a1a"),
                                      spaceAfter=6)
        subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"],
                                         fontSize=11, textColor=colors.gray)
        section_style = ParagraphStyle("Section", parent=styles["Heading2"],
                                        fontSize=13, textColor=colors.HexColor("#1a4a1a"),
                                        spaceBefore=12, spaceAfter=4)
        body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                     fontSize=9, leading=14)

        field = await db.fields.find_one({"_id": ObjectId(field_id)})
        field_name = field["name"] if field else field_id
        now = datetime.now(timezone.utc)

        story = [
            Paragraph("AgriScan 3D — Crop Health Report", title_style),
            Paragraph(
                f"Field: <b>{field_name}</b> &nbsp;|&nbsp; Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
                subtitle_style,
            ),
            Spacer(1, 0.4*cm),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a4a1a")),
            Spacer(1, 0.3*cm),
        ]

        # Health score summary
        health_color = (
            colors.HexColor("#22c55e") if health_score >= 70
            else colors.HexColor("#f59e0b") if health_score >= 40
            else colors.HexColor("#ef4444")
        )
        summary_data = [
            ["Metric", "Value"],
            ["Overall Health Score", f"{health_score:.1f}%"],
            ["Total Detections", str(len(detections))],
            ["Diseases Found", str(len([d for d in disease_summary if d["severity"] != "healthy"]))],
            ["Report ID", upload_id[:16] + "..."],
        ]
        t = Table(summary_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a4a1a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f7f0")]),
            ("TEXTCOLOR", (1, 1), (1, 1), health_color),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ]))
        story.append(Paragraph("Executive Summary", section_style))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Disease breakdown
        story.append(Paragraph("Disease Breakdown", section_style))
        if disease_summary:
            ds_data = [["Disease", "Count", "Area %", "Severity", "Avg. Confidence"]]
            for d in disease_summary:
                sev_color = {
                    "high": colors.HexColor("#fee2e2"),
                    "medium": colors.HexColor("#fff7ed"),
                    "low": colors.HexColor("#fefce8"),
                    "healthy": colors.HexColor("#f0fdf4"),
                }.get(d["severity"], colors.white)
                ds_data.append([
                    d["label"].replace("_", " "),
                    str(d["count"]),
                    f"{d['area_pct']:.1f}%",
                    d["severity"].upper(),
                    f"{d['avg_confidence']:.1f}%",
                ])
            dt = Table(ds_data, colWidths=[5.5*cm, 2*cm, 2*cm, 3*cm, 3.5*cm])
            dt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a2d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f7f0")]),
            ]))
            story.append(dt)
        else:
            story.append(Paragraph("No disease detections.", body_style))

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Recommendations", section_style))
        high_diseases = [d for d in disease_summary if d["severity"] == "high"]
        if high_diseases:
            for d in high_diseases:
                story.append(Paragraph(
                    f"• <b>{d['label'].replace('_', ' ')}</b>: Immediate intervention required. "
                    f"Inspect rows in affected area and apply appropriate fungicide/treatment.",
                    body_style,
                ))
        else:
            story.append(Paragraph(
                "No high-severity diseases found. Continue regular monitoring. "
                "Field appears healthy — maintain current irrigation and nutrition schedule.",
                body_style,
            ))

        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Paragraph(
            f"Generated by AgriScan 3D AI Platform · {now.strftime('%Y-%m-%d %H:%M UTC')} · YOLOv8 model",
            ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
                           textColor=colors.grey, alignment=1),
        ))

        doc.build(story)
        pdf_bytes = buf.getvalue()

        from app.utils.storage import upload_file_to_s3
        url = upload_file_to_s3(pdf_bytes, f"report_{upload_id}.pdf", folder="results/reports")
        logger.info("PDF report uploaded: %s", url)
        return url

    except ImportError:
        logger.warning("reportlab not installed — PDF skipped.")
        return None
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return None
