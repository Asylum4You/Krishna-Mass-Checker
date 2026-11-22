# BIN/IIN Metadata Lookup Bot

A Telegram bot for single and batch lookup of **public BIN/IIN issuer metadata** using the [binlist.net](https://binlist.net/) lookup service.

## Supported features

- Single-prefix lookup and CSV/TXT batch uploads.
- One 6–8 digit BIN/IIN prefix per row.
- Up to 10 unique prefixes per uploaded file.
- Duplicate detection and removal.
- Public scheme, brand, card type, issuer country, and bank metadata.
- Downloadable CSV batch report.
- Per-user cooldowns, upload-size limits, and HTTP timeouts.

## Data and authentication boundaries

- Do not upload or send full payment-card numbers, CVVs, expiry dates, magnetic-stripe data, or payment credentials.
- Files containing full card-like values, multiple columns, or malformed entries are rejected.
- The bot does **not** validate payment cards, test transactions, check 3-D Secure/VBV enrollment, perform authentication challenges, or classify cards by authentication passability.
- The report explicitly marks 3-D Secure/VBV status as **Not tested**.

BIN/IIN metadata can be incomplete or outdated and is not proof that a payment instrument is valid or usable. Uploaded file contents are processed in memory for the request and are not written to local storage by this application.

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

On Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-token"
python main.py
```

Never commit a real bot token. The application reads it from the process environment and exits if it is missing.

## Use

1. Open the bot in Telegram and send `/start`.
2. For a single lookup, send a 6–8 digit prefix such as the synthetic example `411111`.
3. For a batch, upload a `.csv` or `.txt` file with one prefix per row. An optional first-row header such as `BIN/IIN` is supported.
4. Receive a CSV report containing issuer metadata, lookup results, and an explicit “Not tested” authentication status.

Example batch file:

```text
BIN/IIN
411111
555555
```

Maximum upload size is 32 KB and each file may contain at most 10 unique prefixes. Duplicate prefixes are looked up once.

## Tests

Tests use synthetic prefixes and local formatting/parsing only; they do not contact Telegram, binlist.net, payment processors, or authentication systems.

Recommended local verification (creates `.venv`, installs dependencies, compiles the source, and runs the unit suite):

```bash
bash scripts/verify.sh
```

To run the checks manually in an already configured environment:

```bash
python -m compileall -q main.py sandbox tests
python -m unittest discover -s tests -v
```

## Configuration

- `TELEGRAM_BOT_TOKEN` (required): Telegram bot token supplied at runtime.
- `LOG_LEVEL` (optional): Python logging level; defaults to `INFO`.

## License

No license was present in the original repository. Add an appropriate license before redistributing this project.


## Modular synthetic testing sandbox

The project also includes separate sandbox components:

- File processor: accepts a bounded CSV of synthetic test cases.
- BIN classifier: formats public issuer/network metadata only; authentication status remains Not tested.
- Validation engine: accepts only an opaque test_id and an allowlisted scenario.
- 3-D Secure simulator: returns deterministic mock outcomes without contacting card networks, issuers, payment processors, or authentication services.
- Reporting engine: produces a CSV labeled as simulation-only.
- Telegram interface: supports the /simulate command and the dedicated simulation.csv or mock-simulation.csv upload names.

### Synthetic simulation scenarios

- frictionless_success
- challenge_required
- challenge_failed
- not_enrolled
- unavailable

Run one scenario in Telegram with /simulate followed by a scenario name. For a batch, upload a file named simulation.csv with exactly these columns:

    test_id,scenario
    case_001,frictionless_success
    case_002,challenge_required
    case_003,unavailable

Simulation test IDs are opaque labels, not payment credentials. The validator rejects extra columns and unknown scenarios. Batch files are limited to 16 KB and 50 rows. Every generated result is explicitly marked SIMULATION ONLY and must not be interpreted as a real card, issuer, enrollment, or authentication result.
