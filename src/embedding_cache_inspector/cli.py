from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import AuditOptions, audit_records
from .loaders import SchemaOptions, load_jsonl, load_sqlite
from .reporter import render_json, render_junit, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    return args.handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embedding-cache-inspector",
        description="Inspect local JSONL and SQLite embedding caches.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a cache file.")
    inspect_subparsers = inspect_parser.add_subparsers(dest="source_type", required=True)

    jsonl_parser = inspect_subparsers.add_parser("jsonl", help="Inspect a JSONL cache.")
    jsonl_parser.add_argument("path", help="Path to a JSONL cache file.")
    _add_json_schema_args(jsonl_parser)
    _add_audit_args(jsonl_parser)
    jsonl_parser.set_defaults(handler=_handle_jsonl)

    sqlite_parser = inspect_subparsers.add_parser("sqlite", help="Inspect a SQLite cache.")
    sqlite_parser.add_argument("path", help="Path to a SQLite database.")
    _add_sqlite_schema_args(sqlite_parser)
    _add_audit_args(sqlite_parser)
    sqlite_parser.set_defaults(handler=_handle_sqlite)

    schema_parser = subparsers.add_parser("schema", help="Show schema configuration help.")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command", required=True)
    options_parser = schema_subparsers.add_parser("options", help="List JSONL and SQLite options.")
    options_parser.set_defaults(handler=_handle_schema_options)
    return parser


def _add_json_schema_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id-field", default="id", help="JSON field for document id.")
    parser.add_argument("--chunk-field", default="chunk", help="JSON field for chunk text.")
    parser.add_argument("--embedding-field", default="embedding", help="JSON field for vectors.")
    parser.add_argument("--model-field", default="model", help="JSON field for model name.")
    parser.add_argument("--metadata-field", default="metadata", help="JSON field for metadata object.")


def _add_sqlite_schema_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--table", default="embeddings", help="SQLite table name.")
    parser.add_argument("--id-column", default="id", help="SQLite column for document id.")
    parser.add_argument("--chunk-column", default="chunk", help="SQLite column for chunk text.")
    parser.add_argument("--embedding-column", default="embedding", help="SQLite column for vectors.")
    parser.add_argument("--model-column", default="model", help="SQLite column for model name.")
    parser.add_argument("--metadata-column", default="metadata", help="SQLite column for metadata JSON.")


def _add_audit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-dimension", type=int, help="Expected embedding dimension.")
    parser.add_argument(
        "--required-metadata",
        default="",
        help="Comma-separated required metadata fields, for example source,language.",
    )
    parser.add_argument(
        "--allow-mixed-models",
        action="store_true",
        help="Do not warn when multiple model names are present.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown", "junit"),
        default="markdown",
        help="Report format.",
    )
    parser.add_argument("--report", help="Write report to this path instead of stdout.")
    parser.add_argument(
        "--fail-on",
        choices=("never", "error", "warning"),
        default="error",
        help="Exit non-zero when findings at this level exist.",
    )


def _handle_jsonl(args: argparse.Namespace) -> int:
    schema = SchemaOptions(
        id_field=args.id_field,
        chunk_field=args.chunk_field,
        embedding_field=args.embedding_field,
        model_field=args.model_field,
        metadata_field=args.metadata_field,
    )
    load_result = load_jsonl(args.path, schema)
    return _audit_and_emit(load_result.records, load_result.findings, args)


def _handle_sqlite(args: argparse.Namespace) -> int:
    schema = SchemaOptions(
        sqlite_table=args.table,
        id_column=args.id_column,
        chunk_column=args.chunk_column,
        embedding_column=args.embedding_column,
        model_column=args.model_column,
        metadata_column=args.metadata_column,
    )
    load_result = load_sqlite(args.path, schema)
    return _audit_and_emit(load_result.records, load_result.findings, args)


def _audit_and_emit(records, findings, args: argparse.Namespace) -> int:
    options = AuditOptions(
        expected_dimension=args.expected_dimension,
        required_metadata=_parse_required_metadata(args.required_metadata),
        allow_mixed_models=args.allow_mixed_models,
    )
    result = audit_records(records, options, findings)
    output = _render_report(result, args.format)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    if args.fail_on == "warning" and (result.errors_count or result.warnings_count):
        return 1
    if args.fail_on == "error" and result.errors_count:
        return 1
    return 0


def _handle_schema_options(args: argparse.Namespace) -> int:
    del args
    sys.stdout.write(
        "\n".join(
            [
                "JSONL options:",
                "  --id-field, --chunk-field, --embedding-field, --model-field, --metadata-field",
                "SQLite options:",
                "  --table, --id-column, --chunk-column, --embedding-column, --model-column, --metadata-column",
                "Audit options:",
                "  --expected-dimension, --required-metadata, --allow-mixed-models, --format, --report, --fail-on",
                "",
            ]
        )
    )
    return 0


def _parse_required_metadata(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _render_report(result, format_name: str) -> str:
    if format_name == "json":
        return render_json(result)
    if format_name == "junit":
        return render_junit(result)
    return render_markdown(result)


if __name__ == "__main__":
    raise SystemExit(main())
