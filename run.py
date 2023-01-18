import datetime
import requests
import threading
import urllib
import os

from decimal import Decimal as decimal

from binance.spot import Spot
from binance.websocket.spot.websocket_client import SpotWebsocketClient as WebsocketClient


WIDTH = int(os.environ['WIDTH'])
STEP = int(os.environ['STEP'])
SIZE = float(os.environ['SIZE'])

# WIDTH = 25
# STEP = 2
# SIZE = 0.001

buy_order = None
sell_order = None
trades = []

def log(msg):
    def _log(_msg):
        CHATID = os.environ['CHATID']
        BOTID = os.environ['BOTID']
        
        _msg = '♨️:' + _msg
        print(datetime.datetime.now().isoformat(), _msg)

        params = {
            'chat_id': CHATID,
            'text': _msg
        }
        payload_str = urllib.parse.urlencode(params, safe='@')
        requests.get(
            'https://api.telegram.org/bot'+ BOTID +
            '/sendMessage',
            params=payload_str
        )
    threading.Thread(target=_log, args=[msg]).start()
    
def profit():
    global trades

    total = decimal('0')
    fee = decimal('0')
    calc = trades.copy()

    while len(calc)>0:
        open_trade = calc[0]
        calc.remove(open_trade)
        open_trade['price'] = decimal(str(open_trade['price']))
        open_trade['size'] = decimal(str(open_trade['size']))
        for close_trade in calc:
            close_trade['price'] = decimal(str(close_trade['price']))
            close_trade['size'] = decimal(str(close_trade['size']))
            if open_trade['size'] < 0: # this is a buy order, find corresponding sell order
                if close_trade == {'price':open_trade['price'] + STEP, 'size':-open_trade['size']}:
                    total += STEP * close_trade['size']
                    calc.remove(close_trade)
                    break
            if open_trade['size'] > 0: # this is a sell order, find corresponding buy order
                if close_trade == {'price':open_trade['price'] - STEP, 'size':-open_trade['size']}:
                    total += STEP * -close_trade['size']
                    calc.remove(close_trade)
                    break

    return total

KEY = os.environ['KEY']
SECRET = os.environ['SECRET']
client = Spot(key=KEY, secret=SECRET)


price = round(decimal(client.ticker_price('BTCBUSD')['price']))
start_order = client.new_order('BTCBUSD','BUY','MARKET', quantity=SIZE * WIDTH, recvWindow=60000)

for i in range(WIDTH):
    trades.append({'price':decimal(price + i), 'size':-SIZE})

buy_order = client.new_order('BTCBUSD','BUY','LIMIT', timeInForce='GTC', quantity=SIZE, price=price - STEP, recvWindow=60000)
sell_order = client.new_order('BTCBUSD','SELL','LIMIT', timeInForce='GTC', quantity=SIZE, price=price + STEP, recvWindow=60000)


def message_handler(data):
    global buy_order
    global sell_order
    global client
    global SIZE
    global STEP

    # data = json.loads(message)

    if buy_order is None or sell_order is None:
        return
    
    if 'e' not in data:
        return
    
    if data['e'] != 'executionReport':
        return
    
    if data['X'] != 'FILLED':
        return
    
    if data['i'] == buy_order['orderId']:
        trades.append({'price':decimal(data['p']), 'size':-SIZE})

        client.cancel_order('BTCBUSD', orderId=sell_order['orderId'])
        buy_order = client.new_order('BTCBUSD','BUY','LIMIT', timeInForce='GTC', quantity=SIZE, price=round(decimal(data['p'])) - STEP, recvWindow=60000)
        sell_order = client.new_order('BTCBUSD','SELL','LIMIT', timeInForce='GTC', quantity=SIZE, price=round(decimal(data['p'])) + STEP, recvWindow=60000)


    if data['i'] == sell_order['orderId']:
        trades.append({'price':decimal(data['p']), 'size':SIZE})

        client.cancel_order('BTCBUSD', orderId=buy_order['orderId'])
        buy_order = client.new_order('BTCBUSD','BUY','LIMIT', timeInForce='GTC', quantity=SIZE, price=round(decimal(data['p'])) - STEP, recvWindow=60000)
        sell_order = client.new_order('BTCBUSD','SELL','LIMIT', timeInForce='GTC', quantity=SIZE, price=round(decimal(data['p'])) + STEP, recvWindow=60000)
        
    log(f"{data['S']} @ {data['p']} filled 💰 {profit()}")

listen_key = client.new_listen_key()['listenKey']
ws_client = WebsocketClient()
ws_client.start()
ws_client.user_data(
    id=1,
    listen_key=listen_key,
    callback=message_handler,
)
