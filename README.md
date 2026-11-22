# Safe BIN Lookup Bot

A Telegram bot that retrieves **public issuer metadata** for a BIN/IIN prefix using the public [binlist.net](https://binlist.net/) lookup service.

## Safety scope

- Accepts only 6–8 digit BIN/IIN prefixes.
- Displays public scheme, brand, card type, issuer country, and bank metadata.
- Does **not** accept full payment-card numbers, CVVs, expiry dates, card lists, or uploaded files.
- Does **not** determine card validity, 3-D Secure / VBV enrollment, authentication state, or transaction outcomes.
- Applies a per-user lookup cooldown and an HTTP request timeout.

BIN/IIN metadata can be incomplete or outdated and must not be treated as proof that a payment instrument is valid or usable.

## Requirements

- Python 3.10 or newer
- A Telegram bot token created through Telegram's BotFather

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN='your-token'
python main.py
```

On Windows PowerShell, set the token with:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-token"
python main.py
```

Never commit a real bot token. `.env.example` documents the expected environment variable; the application reads the token from the process environment and exits if it is missing.

## Use

1. Open the bot in Telegram and send `/start`.
2. Send a 6–8 digit BIN/IIN prefix, such as the synthetic test prefix `411111`.
3. Review the public issuer metadata returned by the lookup service.

Do not send payment-card data. The bot intentionally has no bulk-file mode.

## Tests

The unit tests use synthetic strings and local formatting only; they do not contact Telegram, binlist.net, payment processors, or authentication systems.

```bash
python -m unittest discover -s tests -v
python -m compileall -q main.py tests
```

## Configuration

- `TELEGRAM_BOT_TOKEN` (required): Telegram bot token supplied at runtime.
- `LOG_LEVEL` (optional): Python logging level; defaults to `INFO`.

## License

No license was present in the original repository. Add an appropriate license before redistributing this project.
