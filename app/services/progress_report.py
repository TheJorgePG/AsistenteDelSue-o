from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.progress import DailySleepLogModel, UserProfileModel
from app.services.progress import build_gamification


GREEN = colors.HexColor("#316c58")
MUTED = colors.HexColor("#74817c")
GRID = colors.HexColor("#e6ebe7")


def _sleep_chart(
    logs: list[DailySleepLogModel],
    target_hours: float,
) -> Drawing:
    width, height = 170 * mm, 96 * mm
    drawing = Drawing(width, height)
    left, right = 14 * mm, 8 * mm
    chart_width = width - left - right
    hours_bottom, hours_top = 54 * mm, height - 12 * mm
    quality_bottom, quality_top = 12 * mm, 40 * mm
    chart_height = hours_top - hours_bottom
    maximum = max(10.0, target_hours + 2.0)

    drawing.add(
        String(left, height - 7 * mm, "Horas dormidas", fontSize=8, fillColor=MUTED)
    )
    for tick in range(0, int(maximum) + 1, 2):
        y = hours_bottom + chart_height * tick / maximum
        drawing.add(
            Line(left, y, width - right, y, strokeColor=GRID, strokeWidth=0.5)
        )
        drawing.add(
            String(
                left - 3 * mm,
                y - 1 * mm,
                str(tick),
                textAnchor="end",
                fontSize=7,
                fillColor=MUTED,
            )
        )

    target_y = hours_bottom + chart_height * min(target_hours, maximum) / maximum
    drawing.add(
        Line(
            left,
            target_y,
            width - right,
            target_y,
            strokeColor=GREEN,
            strokeWidth=1,
            strokeDashArray=[4, 2],
        )
    )
    drawing.add(
        String(width - right, target_y + 2 * mm, f"Objetivo {target_hours:g} h",
               textAnchor="end", fontSize=7, fillColor=GREEN)
    )

    drawing.add(
        String(left, 45 * mm, "Calidad percibida (1–10)", fontSize=8, fillColor=MUTED)
    )
    visible_logs = logs[-14:]
    if not visible_logs:
        drawing.add(
            String(
                width / 2,
                hours_bottom - 10 * mm,
                "Aún no hay registros para mostrar.",
                textAnchor="middle",
                fontSize=9,
                fillColor=MUTED,
            )
        )
        return drawing

    slot = chart_width / len(visible_logs)
    bar_width = min(9 * mm, slot * 0.55)
    quality_points = []
    for index, log in enumerate(visible_logs):
        x = left + index * slot + (slot - bar_width) / 2
        bar_height = chart_height * min(log.hours_slept, maximum) / maximum
        drawing.add(
            Rect(x, hours_bottom, bar_width, bar_height, fillColor=GREEN, strokeColor=None)
        )
        center_x = x + bar_width / 2
        quality_y = quality_bottom + (
            (log.quality_score - 1) / 9
        ) * (quality_top - quality_bottom)
        quality_points.append((center_x, quality_y))
        drawing.add(
            String(
                center_x,
                quality_bottom - 4 * mm,
                log.sleep_date.strftime("%d/%m"),
                textAnchor="middle",
                fontSize=6,
                fillColor=MUTED,
            )
        )

    for tick in (1, 5, 10):
        y = quality_bottom + ((tick - 1) / 9) * (quality_top - quality_bottom)
        drawing.add(
            Line(left, y, width - right, y, strokeColor=GRID, strokeWidth=0.5)
        )
        drawing.add(
            String(
                left - 3 * mm,
                y - 1 * mm,
                str(tick),
                textAnchor="end",
                fontSize=7,
                fillColor=MUTED,
            )
        )
    for previous, current in zip(quality_points, quality_points[1:]):
        drawing.add(
            Line(
                previous[0],
                previous[1],
                current[0],
                current[1],
                strokeColor=colors.HexColor("#d49859"),
                strokeWidth=1.5,
            )
        )
    for x, y in quality_points:
        drawing.add(
            Circle(
                x,
                y,
                1.3 * mm,
                fillColor=colors.white,
                strokeColor=colors.HexColor("#d49859"),
                strokeWidth=1.2,
            )
        )
    return drawing


def create_progress_pdf(
    profile: UserProfileModel | None,
    logs: list[DailySleepLogModel],
) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Mi progreso de sueño",
        author="Asistente del Sueño",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            textColor=MUTED,
            alignment=TA_CENTER,
            fontSize=9,
            spaceAfter=12,
        )
    )
    styles["Title"].textColor = GREEN
    story = [
        Paragraph("Mi progreso de sueño", styles["Title"]),
        Paragraph(
            "Resumen de hábitos, evolución y logros registrados en la aplicación.",
            styles["ReportSubtitle"],
        ),
    ]

    profile_rows = [["Perfil", ""]]
    if profile:
        profile_rows.extend(
            [
                ["Nombre", profile.display_name],
                ["Rango de edad", profile.age_range],
                ["Objetivo por noche", f"{profile.sleep_goal_hours:g} horas"],
                ["Zona horaria", profile.timezone],
            ]
        )
        target = profile.sleep_goal_hours
    else:
        profile_rows.append(["Perfil", "Aún no configurado"])
        target = 8.0
    profile_table = Table(profile_rows, colWidths=[48 * mm, 112 * mm], hAlign="LEFT")
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f8f6")),
                ("TEXTCOLOR", (0, 1), (0, -1), MUTED),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            Paragraph("Tu perfil", styles["Heading2"]),
            profile_table,
            Spacer(1, 8 * mm),
            Paragraph("Actividad y recompensas", styles["Heading2"]),
        ]
    )

    gamification = build_gamification(logs, profile)
    unlocked = [badge["title"] for badge in gamification["badges"] if badge["unlocked"]]
    activity_table = Table(
        [
            ["Puntos", "Racha actual", "Noches registradas"],
            [
                str(gamification["points"]),
                (
                    f'{gamification["current_streak"]} día'
                    if gamification["current_streak"] == 1
                    else f'{gamification["current_streak"]} días'
                ),
                str(gamification["nights_logged"]),
            ],
        ],
        colWidths=[53 * mm] * 3,
        hAlign="LEFT",
    )
    activity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ed")),
                ("TEXTCOLOR", (0, 0), (-1, 0), GREEN),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            activity_table,
            Spacer(1, 3 * mm),
            Paragraph(
                "Insignias obtenidas: " + (", ".join(unlocked) if unlocked else "ninguna todavía"),
                styles["Normal"],
            ),
            Spacer(1, 8 * mm),
            Paragraph("Evolución de horas de sueño (últimas 14 noches)", styles["Heading2"]),
            _sleep_chart(logs, target),
            Spacer(1, 5 * mm),
            Paragraph("Historial de sueño", styles["Heading2"]),
        ]
    )

    table_rows = [["Fecha", "Horas", "Calidad (1–10)", "Despertares"]]
    for log in reversed(logs):
        table_rows.append(
            [
                log.sleep_date.strftime("%d/%m/%Y"),
                f"{log.hours_slept:g}",
                str(log.quality_score),
                str(log.awakenings),
            ]
        )
    if not logs:
        table_rows.append(["Todavía no hay noches registradas.", "", "", ""])

    history_table = Table(
        table_rows,
        colWidths=[40 * mm, 32 * mm, 45 * mm, 40 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    history_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8f6")]),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            history_table,
            Spacer(1, 5 * mm),
            Paragraph(
                "Este informe es orientativo y no sustituye la valoración de un profesional sanitario.",
                styles["ReportSubtitle"],
            ),
        ]
    )
    document.build(story)
    return output.getvalue()
