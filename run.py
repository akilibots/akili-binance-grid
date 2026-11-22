"""Durable moving two-order Binance Spot grid."""
import hashlib
import os
import time
from decimal import ROUND_DOWN

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_spot.spot import Spot

from runtime import State, log, number, single_instance

TERMINAL = {'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'}


class Exchange:
    def __init__(self, symbol, base_url):
        self.symbol = symbol
        self.api = Spot(config_rest_api=ConfigurationRestAPI(api_key=os.environ['KEY'], api_secret=os.environ['SECRET'], base_path=base_url, retries=0, timeout=20000)).rest_api
        self.market = self.api.exchange_info(symbol=symbol).data().to_dict()['symbols'][0]
        if self.market['status'] != 'TRADING':
            raise ValueError('Symbol is not available for trading')
        self.base, self.quote = self.market['baseAsset'], self.market['quoteAsset']
        account = [base_url, symbol, hashlib.sha256(os.environ['KEY'].encode()).hexdigest()]
        self.journal = State('data/exchange.json', {'account': account, 'orders': {}})
        if self.journal.data['account'] != account:
            raise ValueError('Exchange journal belongs to a different account, symbol or network')

    def price(self):
        return number(self.api.ticker_price(symbol=self.symbol).data().to_dict()['price'])

    def place(self, key, side, size, price=None):
        orders = self.journal.data['orders']
        if key in orders:
            ref = orders[key]
            self.status(ref)
            return ref
        filters = {f['filterType']: f for f in self.market['filters']}
        step = number(filters['LOT_SIZE']['stepSize'])
        size = number(size)
        if size <= 0 or size % step or not number(filters['LOT_SIZE']['minQty']) <= size <= number(filters['LOT_SIZE']['maxQty']):
            raise ValueError('Size violates the symbol LOT_SIZE filter')
        if price is not None:
            tick = number(filters['PRICE_FILTER']['tickSize'])
            price = (number(price) / tick).to_integral_value(rounding=ROUND_DOWN) * tick
            if not number(filters['PRICE_FILTER']['minPrice']) <= price <= number(filters['PRICE_FILTER']['maxPrice']):
                raise ValueError('Price violates the symbol PRICE_FILTER')
        ref = {'client_id': 'akili-' + hashlib.sha256(key.encode()).hexdigest()[:28], 'side': side, 'size': str(size), 'price': None if price is None else str(price)}
        # Persist before sending: a timeout must not create a second order.
        orders[key] = ref
        self.journal.save()
        params = dict(symbol=self.symbol, side=side, type='MARKET' if price is None else 'LIMIT', quantity=float(size), new_client_order_id=ref['client_id'], new_order_resp_type='FULL')
        if price is not None:
            params.update(price=float(price), time_in_force='GTC')
        result = self.api.new_order(**params).data().to_dict()
        ref['order_id'] = result['orderId']
        self.journal.save()
        return ref

    def status(self, ref):
        result = self.api.get_order(symbol=self.symbol, orig_client_order_id=ref['client_id']).data().to_dict()
        if 'order_id' not in ref:
            ref['order_id'] = result['orderId']
            self.journal.save()
        return result

    def cancel(self, ref):
        result = self.status(ref)
        if result['status'] in TERMINAL:
            return result
        # A failed cancellation stops the bot. It never submits a replacement blindly.
        self.api.delete_order(symbol=self.symbol, orig_client_order_id=ref['client_id'])
        result = self.status(ref)
        if result['status'] not in TERMINAL:
            raise RuntimeError('Cancellation is not confirmed')
        return result

    def execution(self, ref):
        result = self.status(ref)
        expected = number(result['executedQty'])
        fills, cursor = {}, None
        while True:
            params = dict(symbol=self.symbol, order_id=result['orderId'], limit=1000)
            if cursor is not None:
                del params['order_id']
                params['from_id'] = cursor
            batch = [fill.to_dict() for fill in self.api.my_trades(**params).data()]
            for fill in batch:
                if fill['orderId'] == result['orderId']:
                    fills[fill['id']] = fill
            size = sum((number(f['qty']) for f in fills.values()), number(0))
            if size == expected:
                break
            if not batch or batch[-1]['id'] == cursor:
                raise RuntimeError('Trade history does not reconcile with executed quantity')
            cursor = batch[-1]['id'] + 1
        fees = {}
        for fill in fills.values():
            asset = fill['commissionAsset']
            fees[asset] = str(number(fees.get(asset, 0)) + number(fill['commission']))
        quote = sum((number(f['quoteQty']) for f in fills.values()), number(0))
        return {'side': ref['side'], 'size': str(expected), 'quote': str(quote), 'fees': fees}


def profit(trades, base, quote):
    """FIFO realised quote profit; retain fees in other assets separately."""
    lots, total, other_fees = [], number(0), {}
    for trade in trades:
        size, value = number(trade['size']), number(trade['quote'])
        base_fee, quote_fee = (number(trade['fees'].get(asset, 0)) for asset in (base, quote))
        for asset, amount in trade['fees'].items():
            if asset not in {base, quote}:
                other_fees[asset] = str(number(other_fees.get(asset, 0)) + number(amount))
        if trade['side'] == 'BUY':
            if size > base_fee:
                lots.append([size - base_fee, value + quote_fee])
        else:
            remaining = size + base_fee
            cost = number(0)
            for lot in lots:
                quantity = min(remaining, lot[0])
                if not quantity:
                    continue
                allocated = lot[1] if quantity == lot[0] else lot[1] * quantity / lot[0]
                cost += allocated
                lot[0] -= quantity
                lot[1] -= allocated
                remaining -= quantity
            if remaining:
                raise RuntimeError('Sold more inventory than this bot has recorded')
            total += value - quote_fee - cost
    return total, other_fees


class Grid:
    def __init__(self, exchange, size, step, width, state=None):
        self.exchange, self.size, self.step, self.width = exchange, number(size), number(step), width
        if self.size <= 0 or self.step <= 0 or type(width) is not int or width < 1:
            raise ValueError('SIZE and STEP must be positive; WIDTH must be a positive integer')
        self.state = state or State(initial={'settings': [str(self.size), str(self.step), width], 'centre': None, 'initial': None, 'active': {}, 'generation': 0, 'trades': [], 'processed': [], 'rebuild': False})
        if self.state.data['settings'] != [str(self.size), str(self.step), width]:
            raise ValueError('Settings differ from saved state')

    def tick(self):
        d = self.state.data
        if d['initial'] is None:
            d['initial'] = self.exchange.place('initial', 'BUY', self.size * self.width)
            self.state.save()
        if d['centre'] is None:
            result = self.exchange.status(d['initial'])
            if result['status'] not in TERMINAL:
                return
            if result['status'] != 'FILLED':
                raise RuntimeError('Initial inventory purchase did not fill completely')
            execution = self.exchange.execution(d['initial'])
            d['trades'].append(execution)
            d['centre'] = str(number(execution['quote']) / number(execution['size']))
            self.state.save()
        results = [(side, ref, self.exchange.status(ref)) for side, ref in d['active'].items()]
        filled = [row for row in results if row[2]['status'] == 'FILLED']
        if filled or d['rebuild']:
            d['rebuild'] = True
            self.state.save()
            # Reconcile every sibling, including fills that raced a cancellation.
            for side, ref in list(d['active'].items()):
                result = self.exchange.cancel(ref)
                if number(result['executedQty']) and ref['client_id'] not in d['processed']:
                    execution = self.exchange.execution(ref)
                    d['trades'].append(execution)
                    d['processed'].append(ref['client_id'])
                    d['centre'] = str(number(execution['quote']) / number(execution['size']))
                    self.state.save()
            d['active'] = {}
            d['generation'] += 1
            d['rebuild'] = False
            self.state.save()
            realised, fees = profit(d['trades'], self.exchange.base, self.exchange.quote)
            log(f'Realised {self.exchange.quote} profit: {realised}; other fees: {fees}')
        else:
            for side, ref, result in results:
                if result['status'] in TERMINAL:
                    if number(result['executedQty']):
                        d['rebuild'] = True
                        self.state.save()
                        return
                    raise RuntimeError('Grid order was cancelled or expired; reconcile before restarting')
        for side, direction in [('BUY', -1), ('SELL', 1)]:
            if side not in d['active']:
                price = number(d['centre']) + direction * self.step
                d['active'][side] = self.exchange.place(f'grid:{d["generation"]}:{side}', side, self.size, price)
                self.state.save()


def main():
    with single_instance():
        exchange = Exchange(os.environ['SYMBOL'], os.environ['BINANCE_BASE_URL'])
        bot = Grid(exchange, os.environ['SIZE'], os.environ['STEP'], int(os.environ['WIDTH']))
        interval = float(os.environ.get('POLL_SECONDS', '1'))
        if interval <= 0:
            raise ValueError('POLL_SECONDS must be positive')
        while True:
            bot.tick()
            time.sleep(interval)


if __name__ == '__main__':
    main()
