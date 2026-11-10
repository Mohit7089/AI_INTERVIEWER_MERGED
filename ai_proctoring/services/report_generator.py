"""
ReportGenerator

Renders a `SessionReport` into a polished, multi-section PDF using ReportLab
for layout/typography and matplotlib for charts (score bar chart + timeline
line chart), embedded as images. Output goes to `settings.reports_dir`.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import List

import matplotlib
matplotlib.use("Agg")  # headless rendering, no display server required
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.settings import get_settings
from models.schemas import SessionReport
from utils.logger import logger

_settings = get_settings()


class ReportGenerator:
    def __init__(self) -> None:
        os.makedirs(_settings.reports_dir, exist_ok=True)
        self._styles = getSampleStyleSheet()
        self._styles.add(ParagraphStyle(name="SectionHeading", fontSize=14, spaceAfter=10,
                                         textColor=colors.HexColor("#0f766e"), spaceBefore=16))
        self._styles.add(ParagraphStyle(name="ReportTitle", fontSize=22, spaceAfter=6,
                                         textColor=colors.HexColor("#0f172a")))
        self._styles.add(ParagraphStyle(name="SubTitle", fontSize=11, textColor=colors.grey))

    def generate(self, report: SessionReport) -> str:
        filename = f"interview_report_{report.session_id}.pdf"
        path = os.path.join(_settings.reports_dir, filename)

        doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
        story = []

        story.extend(self._build_header(report))
        story.extend(self._build_score_summary_table(report))
        story.append(self._build_score_chart(report))
        if report.timeline:
            story.append(self._build_timeline_chart(report))
        story.extend(self._build_blink_and_reading_section(report))
        story.extend(self._build_violation_log(report))
        story.extend(self._build_recommendations(report))
        story.extend(self._build_summaries(report))

        doc.build(story)
        logger.info(f"Generated PDF report at {path}")
        return path

    # -- Sections -------------------------------------------------------

    def _build_header(self, report: SessionReport) -> list:
        title = Paragraph("AI Interview Proctoring &amp; Behavioral Report", self._styles["ReportTitle"])
        candidate = report.candidate_name or "Candidate"
        subtitle = Paragraph(
            f"{candidate} &nbsp;|&nbsp; Interview ID: {report.interview_id} &nbsp;|&nbsp; "
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            self._styles["SubTitle"],
        )
        meta = Paragraph(
            f"Session duration: {round(report.duration_seconds / 60, 1)} minutes &nbsp;|&nbsp; "
            f"Frames analyzed: {report.frames_analyzed} &nbsp;|&nbsp; Status: {report.status.value}",
            self._styles["SubTitle"],
        )
        return [title, subtitle, meta, Spacer(1, 0.6 * cm)]

    def _build_score_summary_table(self, report: SessionReport) -> list:
        heading = Paragraph("Overall Score Summary", self._styles["SectionHeading"])
        data = [
            ["Metric", "Score"],
            ["Overall Score", f"{report.overall_score}/100"],
            ["Eye Contact", f"{report.eye_contact_percentage}%"],
            ["Confidence", f"{report.confidence}/100"],
            ["Calmness", f"{report.calmness}/100"],
            ["Stress", f"{report.stress}/100"],
            ["Professionalism", f"{report.professionalism}/100"],
            ["Attention", f"{report.attention}/100"],
            ["Communication (engagement proxy)", f"{report.communication_proxy}/100"],
            ["Posture", f"{report.posture_score}/100"],
            ["Head Stability", f"{report.avg_head_stability}/100"],
        ]
        table = Table(data, colWidths=[9 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [heading, table, Spacer(1, 0.4 * cm)]

    def _build_score_chart(self, report: SessionReport) -> Image:
        labels = ["Eye Contact", "Confidence", "Calmness", "Professionalism", "Attention", "Posture"]
        values = [
            report.eye_contact_percentage, report.confidence, report.calmness,
            report.professionalism, report.attention, report.posture_score,
        ]
        fig, ax = plt.subplots(figsize=(6.2, 3.2))
        bars = ax.bar(labels, values, color="#0f766e")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Score")
        ax.set_title("Behavioral Score Breakdown")
        plt.xticks(rotation=20, ha="right", fontsize=8)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.0f}", ha="center", fontsize=8)
        fig.tight_layout()

        img_path = os.path.join(_settings.reports_dir, f"_chart_scores_{report.session_id}.png")
        fig.savefig(img_path, dpi=150)
        plt.close(fig)
        return Image(img_path, width=15 * cm, height=7.5 * cm)

    def _build_timeline_chart(self, report: SessionReport) -> Image:
        idx = list(range(len(report.timeline)))
        eye_contact = [p.eye_contact_score for p in report.timeline]
        attention = [p.attention for p in report.timeline]
        stress = [p.stress for p in report.timeline]

        fig, ax = plt.subplots(figsize=(6.2, 3.0))
        ax.plot(idx, eye_contact, label="Eye Contact", color="#0f766e")
        ax.plot(idx, attention, label="Attention", color="#2563eb")
        ax.plot(idx, stress, label="Stress", color="#dc2626")
        ax.set_ylim(0, 100)
        ax.set_xlabel("Timeline (sampled points)")
        ax.set_ylabel("Score")
        ax.set_title("Behavior Over Time")
        ax.legend(fontsize=8, loc="lower left")
        fig.tight_layout()

        img_path = os.path.join(_settings.reports_dir, f"_chart_timeline_{report.session_id}.png")
        fig.savefig(img_path, dpi=150)
        plt.close(fig)
        return Image(img_path, width=15 * cm, height=7.2 * cm)

    def _build_blink_and_reading_section(self, report: SessionReport) -> list:
        heading = Paragraph("Blink Analysis &amp; Reading Detection", self._styles["SectionHeading"])
        data = [
            ["Metric", "Value"],
            ["Total Blinks", str(report.blink_count)],
            ["Average Blink Rate", f"{report.avg_blink_rate} blinks/min"],
            ["Fatigue Score", f"{report.fatigue_score}/100"],
            ["Average Reading Probability", f"{report.avg_reading_probability}%"],
        ]
        table = Table(data, colWidths=[9 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [heading, table, Spacer(1, 0.4 * cm)]

    def _build_violation_log(self, report: SessionReport) -> list:
        heading = Paragraph(
            f"Suspicious Activity &amp; Violation Log ({report.suspicious_events_count} events)",
            self._styles["SectionHeading"],
        )
        elements: List = [heading]
        if not report.violation_log:
            elements.append(Paragraph("No suspicious activity was detected during this session.",
                                       self._styles["Normal"]))
            elements.append(Spacer(1, 0.4 * cm))
            return elements

        rows = [["Time", "Severity", "Event"]]
        for w in report.violation_log[:60]:  # cap table length; full log stored in DB
            rows.append([w.timestamp.strftime("%H:%M:%S"), w.severity.value.upper(), w.message])

        table = Table(rows, colWidths=[3 * cm, 3 * cm, 9 * cm])
        severity_colors = {
            "INFO": colors.HexColor("#dbeafe"),
            "WARNING": colors.HexColor("#fef3c7"),
            "CRITICAL": colors.HexColor("#fee2e2"),
        }
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]
        for i, row in enumerate(rows[1:], start=1):
            bg = severity_colors.get(row[1], colors.white)
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        table.setStyle(TableStyle(style_cmds))
        elements.append(table)
        elements.append(Spacer(1, 0.4 * cm))
        return elements

    def _build_recommendations(self, report: SessionReport) -> list:
        heading = Paragraph("Recommendations", self._styles["SectionHeading"])
        items = [Paragraph(f"&bull; {r}", self._styles["Normal"]) for r in report.recommendations]
        return [heading, *items, Spacer(1, 0.4 * cm)]

    def _build_summaries(self, report: SessionReport) -> list:
        recruiter_heading = Paragraph("Recruiter Summary", self._styles["SectionHeading"])
        recruiter_text = Paragraph(report.recruiter_summary, self._styles["Normal"])
        candidate_heading = Paragraph("Candidate Feedback", self._styles["SectionHeading"])
        candidate_text = Paragraph(report.candidate_feedback, self._styles["Normal"])
        return [recruiter_heading, recruiter_text, Spacer(1, 0.3 * cm),
                candidate_heading, candidate_text]
