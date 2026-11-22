import json

import pytest
import requests

from run import Exchange
from runtime import State, number


@pytest.fixture
def sdk(monkeypatch, state_dir):
    monkeypatch.setenv('KEY', 'test-key')
    monkeypatch.setenv('SECRET', 'test-secret')
    calls = []
    state = {'status': 'NEW', 'filled': '0', 'timeout': False}
    market = {'symbol': 'BTCUSDT', 'status': 'TRADING', 'baseAsset': 'BTC', 'quoteAsset': 'USDT', 'filters': [{'filterType': 'LOT_SIZE', 'stepSize': '0.001', 'minQty': '0.001', 'maxQty': '1000'}, {'filterType': 'PRICE_FILTER', 'tickSize': '0.01', 'minPrice': '0.01', 'maxPrice': '1000000'}]}
    def request(session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        if state['timeout'] and method.upper() == 'POST':
            raise requests.Timeout('connection lost')
        if url.endswith('/exchangeInfo'):
            data = {'symbols': [market]}
        elif url.endswith('/ticker/price'):
            data = {'symbol': 'BTCUSDT', 'price': '100'}
        elif url.endswith('/myTrades'):
            data = [{'symbol': 'BTCUSDT', 'id': 1, 'orderId': 1, 'price': '100', 'qty': '0.001', 'quoteQty': '0.1', 'commission': '0.0001', 'commissionAsset': 'USDT', 'time': 1, 'isBuyer': True, 'isMaker': True, 'isBestMatch': True}]
        elif url.endswith('/order'):
            if method.upper() == 'DELETE':
                state['status'] = 'CANCELED'
            data = {'symbol': 'BTCUSDT', 'orderId': 1, 'clientOrderId': 'test', 'price': '100', 'origQty': '0.001', 'executedQty': state['filled'], 'cummulativeQuoteQty': '0.1', 'status': state['status'], 'type': 'LIMIT', 'side': 'BUY', 'timeInForce': 'GTC', 'transactTime': 1}
        else:
            raise AssertionError(url)
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response._content = json.dumps(data).encode()
        response.headers['Content-Type'] = 'application/json'
        return response
    monkeypatch.setattr(requests.Session, 'request', request)
    exchange = Exchange('BTCUSDT', 'https://testnet.binance.vision')
    return exchange, state, calls


def test_actual_sdk_order_models_and_signing(sdk):
    exchange, state, calls = sdk
    ref = exchange.place('entry', 'BUY', '0.001', '100.123')
    assert ref['price'] == '100.12'
    assert ref['order_id'] == 1
    assert exchange.price() == number(100)
    assert exchange.status(ref)['status'] == 'NEW'
    assert exchange.cancel(ref)['status'] == 'CANCELED'
    assert sum(method.upper() == 'POST' for method, _, _ in calls) == 1
    exchange.place('entry', 'BUY', '0.001', '100.123')
    assert sum(method.upper() == 'POST' for method, _, _ in calls) == 1


def test_actual_sdk_array_fill_response(sdk):
    exchange, state, calls = sdk
    ref = exchange.place('entry', 'BUY', '0.001', 100)
    state['filled'], state['status'] = '0.001', 'FILLED'
    result = exchange.execution(ref)
    assert result == {'side': 'BUY', 'size': '0.001', 'quote': '0.1', 'fees': {'USDT': '0.0001'}}


def test_timeout_journal_is_retained(sdk):
    exchange, state, calls = sdk
    state['timeout'] = True
    with pytest.raises(Exception):
        exchange.place('entry', 'BUY', '0.001', 100)
    assert 'entry' in State('data/exchange.json').data['orders']
    assert sum(method.upper() == 'POST' for method, _, _ in calls) == 1
