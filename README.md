<p align="center"><img src="https://raw.githubusercontent.com/akilibots/.github/main/assets/akilibots-icon.svg" width="144" alt="Akilibots"></p>

# Welcome to akili-binance-grid!

[![Python 3.15.2](https://img.shields.io/badge/Python-3.15.2-6966FF?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Binance Spot](https://img.shields.io/badge/Binance_Spot-0B0B18)](https://github.com/akilibots/akili-binance-grid)
[![Docker tests](https://github.com/akilibots/akili-binance-grid/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/akilibots/akili-binance-grid/actions/workflows/tests.yaml)
[![Telegram](https://img.shields.io/badge/Telegram-community-6966FF?logo=telegram&logoColor=white)](https://t.me/+9F0CZj8emLc2YTY0)

> **Updated 22 November 2026:** Python 3.15.2, the current Binance Spot SDK, configurable markets, persistent recovery and actual fill-and-fee accounting.

Jambo! and welcome! **akili-binance-grid** keeps a buy and a sell around the latest
filled price. It started as a tight-grid bot for zero-fee pairs; now you choose a
listed Spot market and the bot records the fees you actually pay. ♨️

The word **akili** means brain or mind in Swahili. These bots are non-opinionated: you set the strategy and stay in control. They grew out of wanting that little extra tweak that commercial bots always seemed to miss.

## Configuration

Clone the repository and create your environment file:

```sh
git clone https://github.com/akilibots/akili-binance-grid.git
cd akili-binance-grid
cp .env.example .env
```

Edit `.env` and set:

| Variable | Meaning |
| --- | --- |
| `KEY`, `SECRET` | API credentials for the selected environment |
| `SYMBOL` | A listed Spot market, for example BTCUSDT |
| `BINANCE_BASE_URL` | REST URL; the example selects `https://testnet.binance.vision` |
| `WIDTH` | Initial inventory multiplier, a positive integer |
| `SIZE` | Base-asset quantity for each grid order |
| `STEP` | Quote-asset price spacing on either side of the centre |
| `POLL_SECONDS` | Order-status polling interval, default 1 second |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Optional status notifications |

Verify the current market's filters and fees. Sizes must satisfy LOT_SIZE;
limit prices are rounded down to PRICE_FILTER tick size. Binance applies its
remaining notional, balance and other order filters. A rejected order stops the
bot; it is not silently retried with changed quantities.

## How it works

The bot buys `SIZE * WIDTH` at market once to establish inventory, using actual
executed quantity and price in its records. It then places one buy at `centre -
STEP` and one sell at `centre + STEP`, both of `SIZE`.

When an order fills, the bot cancels and reconciles its sibling before rebuilding
both orders around the observed execution price. Partial fills during cancellation
are recorded before rebuilding. All recorded purchases are real fills, including
the initial inventory. No synthetic entry prices are inserted.

The implementation polls REST order status. It has no expiring listen key to
renew and does not promise a particular high-frequency throughput. Polling must
respect the exchange's request-weight and order-rate limits.

Realised FIFO profit is reported in the quote asset and includes commissions
paid in the base or quote asset. Commissions in other assets, such as BNB, are
reported separately rather than converted at an invented rate. The figure excludes
unrealised inventory value. Inventory and available balances still limit how far
the grid can follow a sustained move.

## Get it running and keep it running

```sh
docker compose up --build -d
docker compose logs -f
```

Stop it with `docker compose down`. This stops the process, not its exchange
orders. Compose uses the runtime Docker target and persists `./data`. `data/state.json`
records strategy progress and `data/exchange.json` records client order IDs before
submission. Keep these files together. Restarting reconciles the original IDs
instead of buying the starting inventory again. An uncertain submission or failed
cancellation stops execution rather than creating an untracked replacement.

Do not delete state to recover from an error. Check exchange orders, fills and
balances first. Existing settings, account, symbol and API environment are bound
to the saved state. Use a separate data directory for each bot. A process lock
prevents two instances from using the same directory. Stopping the process leaves
its orders on the exchange; cancel them explicitly when required.

Legacy versions did not persist their trades. Reconcile their existing inventory
and orders before starting this version with a fresh data directory.

## Test it yourself

```sh
docker build --target test -t binance-grid-test .
docker run --rm --network none binance-grid-test
```

The offline suite tests inventory initialization, restart recovery, cancellation,
FIFO fees and the actual SDK's signing and response-model code against mocked HTTP
responses. Live credentials are not needed. Passing the suite does not establish
live exchange execution or profitability.

## The usual bit

This software is for educational purposes only. Do not risk money you are afraid
to lose. **USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME
NO RESPONSIBILITY FOR YOUR TRADING RESULTS.**

See [LICENSE](LICENSE) for the full terms.

Part of [Akilibots](https://github.com/akilibots). Come say jambo in [Telegram](https://t.me/+9F0CZj8emLc2YTY0).
