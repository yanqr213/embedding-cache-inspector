from __future__ import annotations

import json
from xml.sax.saxutils import escape

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


def render_junit(result: AuditResult, suite_name: str = "embedding-cache-inspector") -> str:
    findings = result.findings
    tests = len(findings) if findings else 1
    failures = result.errors_count
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        (
            f'<testsuite name="{_xml(suite_name)}" tests="{tests}" '
            f'failures="{failures}" errors="0" skipped="0">'
        ),
        (
            f'  <properties><property name="records" value="{result.records_count}" />'
            f'<property name="warnings" value="{result.warnings_count}" /></properties>'
        ),
    ]

    if not findings:
        lines.append('  <testcase classname="embedding_cache" name="cache.clean" />')
    else:
        for index, finding in enumerate(findings, start=1):
            name = f"{finding.code}.{index}"
            lines.append(f'  <testcase classname="embedding_cache" name="{_xml(name)}">')
            detail = _finding_text(finding)
            if finding.severity == "error":
                lines.append(f'    <failure type="{_xml(finding.code)}" message="{_xml(finding.message)}">')
                lines.append(_xml(detail))
                lines.append("    </failure>")
            else:
                lines.append(f"    <system-out>{_xml(detail)}</system-out>")
            lines.append("  </testcase>")

    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"


def _finding_text(finding) -> str:
    parts = [
        f"severity: {finding.severity}",
        f"code: {finding.code}",
        f"message: {finding.message}",
    ]
    if finding.source or finding.position:
        parts.append(f"location: {finding.source or ''}:{finding.position or ''}")
    if finding.suggestion:
        parts.append(f"suggestion: {finding.suggestion}")
    if finding.details:
        parts.append("details: " + json.dumps(finding.details, ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def _xml(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})
