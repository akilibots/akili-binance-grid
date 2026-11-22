# akili-binance-grid

A moving two-order grid for Binance Spot using the current `binance-sdk-spot`
connector and Python 3.15.2. The market is configurable; the example uses BTCUSDT
on Binance Spot Testnet. The old hard-coded BTCBUSD pair and zero-fee assumption
are removed.

## Configuration

Copy `.env.example` to `.env` and set:

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

## Behaviour

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

## Run and recovery

```sh
cp .env.example .env
# Configure .env before starting.
docker compose build
docker compose up -d
docker compose logs -f
```

Compose uses the runtime Docker target and persists `./data`. `data/state.json`
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

## Tests

```sh
docker build --target test -t binance-grid-test .
docker run --rm --network none binance-grid-test
```

The offline suite tests inventory initialization, restart recovery, cancellation,
FIFO fees and the actual SDK's signing and response-model code against mocked HTTP
responses. Live credentials are not needed. Passing the suite does not establish
live exchange execution or profitability.

Software is supplied as is under the repository licence.
