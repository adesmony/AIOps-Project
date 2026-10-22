import argparse
import asyncio
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database.providers import create_database_provider

REQUIRED_COLUMNS = {
    "row_id",
    "issue_id",
    "category",
    "azure_service",
    "log_source",
    "error_code",
    "severity",
    "timestamp_utc",
    "host",
    "os_version",
    "vm_size",
    "region",
    "occurrence_context",
    "log_message",
    "root_cause",
    "solution",
    "prevention",
    "tags",
    "rag_text",
}

UPSERT = text("""
    INSERT INTO knowledge_records
        (id, source_file, row_id, issue_id, service, rag_text, metadata, fingerprint)
    VALUES (:id, :source_file, :row_id, :issue_id, :service, :rag_text,
            CAST(:metadata AS jsonb), :fingerprint)
    ON CONFLICT (source_file, row_id) DO UPDATE SET
        issue_id = EXCLUDED.issue_id, service = EXCLUDED.service,
        rag_text = EXCLUDED.rag_text, metadata = EXCLUDED.metadata,
        fingerprint = EXCLUDED.fingerprint
    WHERE knowledge_records.fingerprint <> EXCLUDED.fingerprint
    RETURNING id
""")


@dataclass
class ImportCounts:
    imported: int = 0
    skipped: int = 0
    failed: int = 0


async def import_csv(path: Path, sessions) -> ImportCounts:
    counts = ImportCounts()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")
        async with sessions.begin() as session:
            for row in reader:
                if (
                    None in row
                    or any(value is None for value in row.values())
                    or any(not row[column].strip() for column in REQUIRED_COLUMNS)
                    or len(row["rag_text"]) > 30000
                ):
                    counts.failed += 1
                    continue
                payload = json.dumps(row, sort_keys=True, ensure_ascii=True)
                identity = f"{path.name}:{row['row_id']}"
                parameters = {
                    "id": "csv-" + hashlib.sha256(identity.encode()).hexdigest()[:32],
                    "source_file": path.name,
                    "row_id": row["row_id"],
                    "issue_id": row["issue_id"],
                    "service": row["azure_service"],
                    "rag_text": row["rag_text"],
                    "metadata": payload,
                    "fingerprint": hashlib.sha256(payload.encode()).hexdigest(),
                }
                try:
                    async with session.begin_nested():
                        result = await session.execute(UPSERT, parameters)
                        changed = result.scalar_one_or_none() is not None
                    if changed:
                        counts.imported += 1
                    else:
                        counts.skipped += 1
                except SQLAlchemyError:
                    counts.failed += 1
    return counts


async def run(path: Path) -> int:
    database = create_database_provider(get_settings())
    try:
        counts = await import_csv(path, database.session_factory)
        print(json.dumps(asdict(counts)))
        return 1 if counts.failed else 0
    except (OSError, ValueError, csv.Error, SQLAlchemyError):
        print(
            json.dumps({"error": "Import failed; verify CSV headers, database and migration state"})
        )
        return 1
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorized local CSV knowledge import")
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(run(arguments.path)))


if __name__ == "__main__":
    main()
