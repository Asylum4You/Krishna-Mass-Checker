"""Telegram bot for safe, public BIN/IIN issuer metadata lookups.

This bot accepts only 6–8 digit issuer prefixes. It never accepts or processes
full payment-card numbers, CVVs, expiry dates, authentication status, or files.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BINLIST_URL = "https://lookup.binlist.net/"
REQUEST_TIMEOUT = 8.0
LOOKUP_COOLDOWN_SECONDS = 3.0
BIN_PATTERN = re.compile(r"^[0-9]{6,8}$")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)


def validate_bin_prefix(value: str) -> str:
    """Return a normalized 6–8 digit BIN/IIN prefix or raise ValueError."""
    candidate = value.strip()
    if not BIN_PATTERN.fullmatch(candidate):
        raise ValueError("Enter only a 6–8 digit BIN/IIN prefix (not a full card number).")
    return candidate


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
            "Welcome to Safe BIN Lookup.\n\n"
            "Send a 6–8 digit BIN/IIN prefix to retrieve public issuer metadata.\n"
            "Do not send full card numbers, CVVs, expiry dates, or payment data.\n\n"
            "This bot does not check card validity, 3-D Secure, VBV, or transaction status."
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


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your environment before starting the bot.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Starting Safe BIN Lookup bot")
    application.run_polling()


if __name__ == "__main__":
    main()
