# Binance Futures Testnet Trading Bot

## Overview

A command-line trading bot for the **Binance Futures Testnet (USDT-M)**. It lets you place
market, limit, and stop-market orders, check account balances, and query order status — all
without the `python-binance` library. Every request is a direct, HMAC-SHA256–signed call to
the Binance Futures REST API via the `requests` library. All activity is written to a rotating
log file alongside a real-time console feed.

---

## Prerequisites

- **Python 3.10+**
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account
- Testnet **API Key** and **API Secret** (generated in the testnet dashboard)

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd trading_bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
# Open .env and replace the placeholder values with your real testnet API key and secret
```

Your `.env` file should look like:

```
BINANCE_API_KEY=<your_testnet_api_key>
BINANCE_API_SECRET=<your_testnet_api_secret>
```

---

## Usage Examples

### Place a MARKET BUY order

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Place a LIMIT SELL order

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 95000
```

### Place a STOP_MARKET order

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 90000
```

### Check account balance

```bash
python cli.py account-balance
```

### Check order status

```bash
python cli.py order-status --symbol BTCUSDT --order-id 123456789
```

### Show help

```bash
python cli.py --help
python cli.py place-order --help
```

---

## Sample Console Output

```
============================================================
           ORDER REQUEST SUMMARY
============================================================
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
  Price      : N/A
============================================================

============================================================
           ORDER RESULT
============================================================
  Order ID     : 3951823910
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Quantity     : 0.01
  Executed Qty : 0.01
  Avg Price    : 96512.30
  Price        : 0.00
  Time         : 2025-02-23 14:32:10 UTC
============================================================

✅ Order placed successfully!
```

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package init, exposes __version__
│   ├── client.py            # BinanceFuturesClient — REST API wrapper
│   ├── orders.py            # OrderManager — order lifecycle operations
│   ├── validators.py        # Input validation functions for CLI
│   └── logging_config.py   # Rotating file + console logging setup
├── logs/
│   └── .gitkeep             # Keeps the directory in version control
├── cli.py                   # Click CLI entry point
├── .env.example             # Template for API credentials
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Logging

| Destination | Level | Location |
|---|---|---|
| Console (stdout) | INFO | Real-time terminal output |
| File (rotating) | DEBUG | `logs/trading_bot.log` |

The log file rotates at **5 MB** and keeps **3 backup files** (`trading_bot.log.1`,
`trading_bot.log.2`, `trading_bot.log.3`). The `logs/` directory is created automatically
on first run.

Every API call logs the **endpoint and parameters before sending** (with the HMAC signature
masked as `***`) and logs the **response status code and body after receiving**.

---

## Error Handling

| Error Type | How It Is Handled |
|---|---|
| Missing `.env` credentials | `EnvironmentError` caught; friendly message printed; exit code 1 |
| Invalid CLI input | `click.BadParameter` raised by validators; `❌ Validation error: …` printed |
| Binance API error (4xx/5xx) | `requests.HTTPError` with code + message; `❌ Order failed: …` printed |
| Network / timeout error | `requests.RequestException` caught at CLI layer; user-friendly message |
| Unexpected exceptions | Caught with bare `except Exception`; `❌ Unexpected error: …` printed |

Raw tracebacks are **never** shown to the user; all errors exit with code 1.

---

## Assumptions

- All trading is done on **Binance Futures Testnet USDT-M perpetuals**.
- Quantity and price precision must comply with Binance symbol filters (user is responsible
  for inputting valid precision for the chosen symbol).
- LIMIT orders default to **GTC (Good Till Cancelled)** unless `--tif` is specified.
- Environment variables **must** be defined in a `.env` file in the project root, or exported
  in the shell environment before running the CLI.
- The testnet base URL `https://testnet.binancefuture.com` is hard-coded in the client.
