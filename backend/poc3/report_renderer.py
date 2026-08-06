"""Deterministic and escaping HTML renderer for ReportIR blocks."""

from __future__ import annotations

from html import escape

from .report import (
    CalloutBlock,
    HeadingBlock,
    KpiGridBlock,
    ParagraphBlock,
    ReportIR,
    TableBlock,
    TableScalar,
)


def _text(value: TableScalar) -> str:
    if value is None:
        return "—"
    return escape(str(value), quote=True)


def render_report_html(report: ReportIR) -> str:
    """Render only validated fields; arbitrary model-produced HTML is never used."""

    parts = ['<article class="energy-report">']
    for block in report.blocks:
        if isinstance(block, HeadingBlock):
            level = block.data.level
            parts.append(
                f'<h{level} class="report-heading">'
                f"{escape(block.data.text)}"
                f"</h{level}>"
            )
        elif isinstance(block, ParagraphBlock):
            evidence = " ".join(
                f'<sup class="evidence-ref">[{escape(item)}]</sup>'
                for item in block.data.evidence_ids
            )
            parts.append(
                f'<p class="report-paragraph">{escape(block.data.text)}{evidence}</p>'
            )
        elif isinstance(block, KpiGridBlock):
            parts.append('<section class="report-kpi-grid">')
            if block.data.title:
                parts.append(f"<h3>{escape(block.data.title)}</h3>")
            for item in block.data.items:
                unit = f" {escape(item.unit)}" if item.unit else ""
                change = ""
                if item.change is not None:
                    period = f" / {escape(item.change_period)}" if item.change_period else ""
                    change = (
                        f'<span class="kpi-change">{item.change:+.2f}%{period}</span>'
                    )
                parts.append(
                    f'<div class="kpi {item.status} {item.trend}">'
                    f'<span class="kpi-label">{escape(item.label)}</span>'
                    f'<strong class="kpi-value">{_text(item.value)}{unit}</strong>'
                    f"{change}</div>"
                )
            parts.append("</section>")
        elif isinstance(block, CalloutBlock):
            evidence = " ".join(
                f'<sup class="evidence-ref">[{escape(item)}]</sup>'
                for item in block.data.evidence_ids
            )
            parts.append(
                f'<aside class="report-callout {block.data.severity}">'
                f"<strong>{escape(block.data.title)}</strong>"
                f"<p>{escape(block.data.text)}{evidence}</p>"
                "</aside>"
            )
        elif isinstance(block, TableBlock):
            parts.append('<section class="report-table-wrap">')
            if block.data.title:
                parts.append(f"<h3>{escape(block.data.title)}</h3>")
            parts.append("<table><thead><tr>")
            for column in block.data.columns:
                unit = f" ({escape(column.unit)})" if column.unit else ""
                parts.append(f"<th>{escape(column.label)}{unit}</th>")
            parts.append("</tr></thead><tbody>")
            for row in block.data.rows:
                parts.append("<tr>")
                for column in block.data.columns:
                    parts.append(f"<td>{_text(row.get(column.key))}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table></section>")
    parts.append("</article>")
    return "".join(parts)
