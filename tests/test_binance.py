from run import Grid, profit
from runtime import State, number


def execution(fake, ref):
    result = fake.status(ref)
    size = number(result['executedQty'])
    price = number(result.get('execution_price', result['price']))
    return {'side': result['side'], 'size': str(size), 'quote': str(size * price), 'fees': {}}


def test_initial_inventory_uses_real_fills_and_recovers(fake, state_dir):
    fake.execution = lambda ref: execution(fake, ref)
    bot = Grid(fake, 1, 2, 2)
    bot.tick()
    fake.fill('initial', price=100)
    bot.tick()
    assert len(bot.state.data['trades']) == 1
    assert bot.state.data['trades'][0]['size'] == '2'
    before = len(fake.calls)
    bot = Grid(fake, 1, 2, 2, State())
    bot.tick()
    assert len(fake.calls) == before
    fake.fill('grid:0:SELL', price=102)
    bot.tick()
    assert bot.state.data['centre'] == '102'
    assert fake.orders['grid:0:BUY']['status'] == 'CANCELED'
    assert len(bot.state.data['active']) == 2


def test_actual_fifo_profit_and_nonquote_fees():
    trades = [{'side': 'BUY', 'size': '2', 'quote': '200', 'fees': {'USDT': '0.2'}}, {'side': 'SELL', 'size': '1', 'quote': '110', 'fees': {'USDT': '0.11', 'BNB': '0.001'}}]
    assert profit(trades, 'BTC', 'USDT') == (number('9.79'), {'BNB': '0.001'})


def test_base_asset_fees_reduce_inventory():
    trades = [{'side': 'BUY', 'size': '2', 'quote': '200', 'fees': {'BTC': '0.01'}}, {'side': 'SELL', 'size': '1.99', 'quote': '219', 'fees': {}}]
    assert profit(trades, 'BTC', 'USDT')[0] == number(19)


def test_restart_mid_rebuild_does_not_record_fill_twice(fake, state_dir):
    fake.execution = lambda ref: execution(fake, ref)
    bot = Grid(fake, 1, 2, 2)
    bot.tick()
    fake.fill('initial')
    bot.tick()
    fake.fill('grid:0:SELL')
    bot.state.data['rebuild'] = True
    filled = fake.orders['grid:0:SELL']
    bot.state.data['trades'].append(execution(fake, filled))
    bot.state.data['processed'].append(filled['client_id'])
    bot.state.save()
    bot = Grid(fake, 1, 2, 2, State())
    bot.tick()
    assert len(bot.state.data['trades']) == 2
