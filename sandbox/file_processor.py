"""Parse bounded CSV files containing synthetic simulation cases only."""
import csv
import io

from .validation_engine import validate_simulation_record

MAX_SIMULATION_BYTES = 16 * 1024
MAX_SIMULATION_ROWS = 50


def parse_simulation_csv(content: str) -> list[dict[str, str]]:
    if len(content.encode("utf-8")) > MAX_SIMULATION_BYTES:
        raise ValueError("Simulation file exceeds the 16 KB limit.")
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None or set(reader.fieldnames) != {"test_id", "scenario"}:
        raise ValueError("CSV header must contain exactly: test_id,scenario")
    records = []
    seen = set()
    for row_number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {row_number}: malformed or extra CSV columns.")
        record = validate_simulation_record(row)
        if record["test_id"] in seen:
            raise ValueError(f"Row {row_number}: duplicate test_id.")
        seen.add(record["test_id"])
        records.append(record)
        if len(records) > MAX_SIMULATION_ROWS:
            raise ValueError(f"Simulation files are limited to {MAX_SIMULATION_ROWS} rows.")
    if not records:
        raise ValueError("Simulation file contains no test cases.")
    return records
