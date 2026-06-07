from __future__ import annotations

import json

from .audit import AuditResult


def render_json(result: AuditResult) -> str:
    return json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_markdown(result: AuditResult) -> str:
    data = result.as_dict()
    lines = [
        "# Embedding Cache Inspector Report",
        "",
        "## Summary",
        "",
        f"- Records: {data['summary']['records']}",
        f"- Errors: {data['summary']['errors']}",
        f"- Warnings: {data['summary']['warnings']}",
        "",
        "## Dimension Stats",
        "",
        f"- Min: {result.dimension_stats.get('min')}",
        f"- Max: {result.dimension_stats.get('max')}",
        f"- Mean: {result.dimension_stats.get('mean')}",
        f"- Distribution: {json.dumps(result.dimension_stats.get('distribution', {}), ensure_ascii=False)}",
        "",
        "## Model Distribution",
        "",
    ]
    if result.model_distribution:
        for model, count in sorted(result.model_distribution.items()):
            lines.append(f"- {model}: {count}")
    else:
        lines.append("- No records")
    lines.extend(["", "## Duplicate Summary", ""])
    for key, value in sorted(result.duplicate_summary.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Findings", ""])
    if not result.findings:
        lines.append("No findings.")
    else:
        for index, finding in enumerate(result.findings, start=1):
            location = ""
            if finding.source or finding.position:
                location = f" ({finding.source or ''}:{finding.position or ''})"
            lines.append(f"{index}. **{finding.severity.upper()} {finding.code}**{location}")
            lines.append(f"   - {finding.message}")
            if finding.suggestion:
                lines.append(f"   - Suggestion: {finding.suggestion}")
            if finding.details:
                details = json.dumps(finding.details, ensure_ascii=False, sort_keys=True)
                lines.append(f"   - Details: `{details}`")
    return "\n".join(lines) + "\n"
