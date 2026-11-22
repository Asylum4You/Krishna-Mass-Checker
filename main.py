"""Telegram bot for BIN/IIN issuer metadata, including safe prefix-only batch files.

Only 6–8 digit issuer prefixes are accepted. Full payment-card numbers, CVVs,
expiry dates, payment credentials, and authentication checks are not supported.
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
import time
from typing import Any

import httpx
from telegram import Update
from sandbox.file_processor import parse_simulation_csv\nfrom sandbox.reporting_engine import build_simulation_report\nfrom sandbox.three_ds_simulator import simulate_3ds\nfrom telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BINLIST_URL = "https://lookup.binlist.net/"
REQUEST_TIMEOUT = 8.0
LOOKUP_COOLDOWN_SECONDS = 3.0
FILE_COOLDOWN_SECONDS = 15.0
MAX_UPLOAD_BYTES = 32 * 1024
MAX_BATCH_PREFIXES = 10
BIN_PATTERN = re.compile(r"^[0-9]{6,8}$")
HEADER_VALUES = {"bin", "iin", "bin/iin", "prefix", "bin_prefix", "iin_prefix"}

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)


def validate_bin_prefix(value: str) -> str:
    """Return a normalized 6–8 digit BIN/IIN prefix or raise ValueError."""
    candidate = value.strip()
    if not BIN_PATTERN.fullmatch(candidate):
        raise ValueError("Each entry must be only a 6–8 digit BIN/IIN prefix.")
    return candidate


def parse_prefix_file(content: str) -> tuple[list[str], int]:
    """Parse a one-prefix-per-row CSV/TXT file; reject card data and extra columns."""
    prefixes: list[str] = []
    seen: set[str] = set()
    duplicates = 0

    try:
        rows = csv.reader(io.StringIO(content))
        for row_number, row in enumerate(rows, start=1):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != 1:
                raise ValueError(f"Row {row_number}: provide exactly one BIN/IIN prefix per row.")
            value = row[0].strip()
            if row_number == 1 and value.lower() in HEADER_VALUES:
                continue
            prefix = validate_bin_prefix(value)
            if prefix in seen:
                duplicates += 1
                continue
            seen.add(prefix)
            prefixes.append(prefix)
            if len(prefixes) > MAX_BATCH_PREFIXES:
                raise ValueError(f"Files are limited to {MAX_BATCH_PREFIXES} unique prefixes per upload.")
    except csv.Error as exc:
        raise ValueError("The file is not valid CSV/TXT data.") from exc

    if not prefixes:
        raise ValueError("The file contains no valid BIN/IIN prefixes.")
    return prefixes, duplicates


def format_bin_info(prefix: str, data: dict[str, Any]) -> str:
    """Format only public issuer metadata returned by the BIN lookup service."""
    number = data.get("number") or {}
    country = data.get("country") or {}
    bank = data.get("bank") or {}

    fields = [
        f"BIN/IIN prefix: {prefix}",
        f"Scheme: {data.get('scheme') or 'Not available'}",
        f"Brand: {data.get('brand') or 'Not available'}",
        f"Card type: {data.get('type') or 'Not available'}",
        f"Card length (metadata): {number.get('length') or 'Not available'}",
        f"Country: {country.get('name') or 'Not available'}",
        f"Bank / issuer: {bank.get('name') or 'Not available'}",
        f"Issuer website: {bank.get('url') or 'Not available'}",
        "3-D Secure / VBV status: Not tested",
    ]
    return "\n".join(fields)


async def lookup_bin(prefix: str) -> dict[str, Any] | None:
    """Fetch public BIN metadata. No payment or authentication checks are made."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{BINLIST_URL}{prefix}",
            headers={"Accept": "application/json", "User-Agent": "SafeBINLookup/1.0"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("The metadata service returned an unexpected response.")
        return payload


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Welcome to BIN/IIN Metadata Lookup.\n\n"
            "Send one 6–8 digit BIN/IIN prefix, or upload a CSV/TXT file with "
            "one prefix per row (up to 10 unique prefixes).\n"
            "Do not send full card numbers, CVVs, expiry dates, or payment data.\n\n"
            "This bot reports public issuer metadata only. It does not check card "
            "validity, 3-D Secure/VBV enrollment, authentication, or transaction status."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    try:
        prefix = validate_bin_prefix(update.message.text or "")
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    now = time.monotonic()
    last_lookup = float(context.user_data.get("last_lookup", 0.0))
    if now - last_lookup < LOOKUP_COOLDOWN_SECONDS:
        await update.message.reply_text("Please wait a few seconds before another lookup.")
        return
    context.user_data["last_lookup"] = now

    await update.message.reply_text("Looking up public issuer metadata…")
    try:
        data = await lookup_bin(prefix)
        if data is None:
            await update.message.reply_text("No public BIN/IIN metadata was found for that prefix.")
            return
        await update.message.reply_text(format_bin_info(prefix, data))
    except (httpx.HTTPError, ValueError):
        logger.warning("BIN metadata lookup failed for prefix ending %s", prefix[-2:])
        await update.message.reply_text(
            "The metadata service is temporarily unavailable or returned invalid data. Try again later."
        )


def build_batch_report(results: list[dict[str, str]]) -> bytes:
    """Build a CSV report containing only prefix-level public metadata."""
    output = io.StringIO(newline="")
    fields = [
        "BIN/IIN prefix", "Scheme", "Brand", "Card type", "Country",
        "Bank / issuer", "Lookup result", "3-D Secure / VBV status",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue().encode("utf-8")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.message.document:
        return

    document = update.message.document
    filename = (document.file_name or "").lower()
    if not filename.endswith((".csv", ".txt")):
        await update.message.reply_text("Upload a .csv or .txt file containing BIN/IIN prefixes only.")
        return
    if document.file_size is not None and document.file_size > MAX_UPLOAD_BYTES:
        await update.message.reply_text(f"File too large. Maximum size is {MAX_UPLOAD_BYTES // 1024} KB.")
        return

    now = time.monotonic()
    last_upload = float(context.user_data.get("last_file_upload", 0.0))
    if now - last_upload < FILE_COOLDOWN_SECONDS:
        await update.message.reply_text("Please wait before uploading another batch.")
        return
    context.user_data["last_file_upload"] = now

    try:
        telegram_file = await document.get_file()
        raw = await telegram_file.download_as_bytearray()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(f"File too large. Maximum size is {MAX_UPLOAD_BYTES // 1024} KB.")
        decoded = bytes(raw).decode("utf-8-sig")
        if filename in {"simulation.csv", "mock-simulation.csv"}:
            cases = parse_simulation_csv(decoded)
            results = [
                {"test_id": case["test_id"], **simulate_3ds(case["scenario"])}
                for case in cases
            ]
            report_file = io.BytesIO(build_simulation_report(results))
            report_file.name = "synthetic_3ds_simulation_report.csv"
            await update.message.reply_text(
                f"Simulated {len(results)} synthetic test cases. No payment systems or card data were used."
            )
            await update.message.reply_document(
                document=report_file,
                caption="SYNTHETIC SIMULATION ONLY — not real card/authentication results."
            )
            return
        prefixes, duplicate_count = parse_prefix_file(decoded)
    except (UnicodeDecodeError, ValueError) as exc:
        await update.message.reply_text(f"File rejected: {exc}")
        return
    except Exception:
        logger.exception("Could not retrieve uploaded prefix file")
        await update.message.reply_text("The upload could not be read. Please try again.")
        return

    await update.message.reply_text(
        f"Processing {len(prefixes)} unique BIN/IIN prefixes; "
        f"removed {duplicate_count} duplicate entries. This is metadata lookup only."
    )

    results: list[dict[str, str]] = []
    for index, prefix in enumerate(prefixes):
        row = {
            "BIN/IIN prefix": prefix,
            "Scheme": "",
            "Brand": "",
            "Card type": "",
            "Country": "",
            "Bank / issuer": "",
            "Lookup result": "",
            "3-D Secure / VBV status": "Not tested",
        }
        try:
            data = await lookup_bin(prefix)
            if data is None:
                row["Lookup result"] = "No public metadata found"
            else:
                country = data.get("country") or {}
                bank = data.get("bank") or {}
                row.update({
                    "Scheme": str(data.get("scheme") or ""),
                    "Brand": str(data.get("brand") or ""),
                    "Card type": str(data.get("type") or ""),
                    "Country": str(country.get("name") or ""),
                    "Bank / issuer": str(bank.get("name") or ""),
                    "Lookup result": "Found",
                })
        except httpx.HTTPStatusError as exc:
            row["Lookup result"] = f"HTTP {exc.response.status_code}"
        except (httpx.HTTPError, ValueError):
            row["Lookup result"] = "Lookup failed"
        results.append(row)
        if index < len(prefixes) - 1:
            await asyncio.sleep(1.0)

    report = build_batch_report(results)
    report_file = io.BytesIO(report)
    report_file.name = "bin_iin_metadata_report.csv"
    found = sum(item["Lookup result"] == "Found" for item in results)
    await update.message.reply_text(
        f"Batch complete: {len(results)} prefixes processed; {found} metadata records found. "
        f"Duplicate rows removed: {duplicate_count}. Authentication status was not tested."
    )
    await update.message.reply_document(
        document=report_file,
        caption="BIN/IIN issuer metadata report — 3-D Secure/VBV status not tested.",
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your environment before starting the bot.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))\n    application.add_handler(CommandHandler("simulate", simulate_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Starting BIN/IIN Metadata Lookup bot")
    application.run_polling()


if __name__ == "__main__":
    main()
