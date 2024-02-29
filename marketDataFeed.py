import asyncio
import json
import websockets
# Test

# Connect to Deribit’s market data API via websocket and subscribe to both the 
#   L2 orderbook & trade channels in separate threads/tasks 
# (not a single subscription for both channels) for a single symbol
#   provided to the program as a command line argument. 

# Both channels should be subscribed to at the 100ms granularity.


# Size should be rounded to 2 decimal places and price 1 decimal place
# When an orderbook event is received, the program should output:
# the best 5 levels on each side of the book, indicating the price & liquidity of those levels.

# For example:
# 5.01 @ 36705.4 
# 32.33 @ 36700.1 
# 1.14 @ 36698.8 
# 1.44 @ 36677.4 
# 2.34 @ 36500.2 
# ---------------
# 3.32 @ 36433.1 
# 2.55 @ 36432.3 
# 0.67 @ 36421.5 
# 0.44 @ 36400.3 
# 1.17 @ 36244.2

# ____________________________________________________________________________________________________________________
# REQUEST MESSAGES

# "jsonrpc": string - version of JSON-remote procedure call - "2.0"
# "id": integer/string - request identifier (if included, response will contain same identifier)
# "method": string - method to be invoked
# "params" object - parameter values for the specific method - CHECK API FOR CONTENTS RELATING TO SPECIFIC METHODS

# "instrument" FORMATS:
#   future: BTC - [date]
#   perpetual: BTC-PERPETUAL
#   option: BTC - [date] - [option strike price USD] - [P->put or C->call]
basicRequest = {
    "jsonrpc": "2.0",
    "id": 8066,
    "method": "public/ticker",
    "params": {
        "instrument": "BTC-24AUG18-6500-P"
    }
}

# ------------------------------------
# RESPONSE MESSAGE (error)

# "jsonrpc": string - version of JSON-remote procedure call - "2.0"
# "id": integer - same as id sent in request
# "error": object - 
#   "code": integer - number indicating kind of error
#   "message": string - descrption indicating kind of error
#   [optional] "data": any - additional data about the error
# "testnet": boolean - TRUE(test server), FALSE(production server)
# "usIn": integer - timestamp when request was received
# "usOut": integer - timestamp when response was sent
# "usDiff": integer - number of microseconds spent handling request
badResponse = {
    "jsonrpc": "2.0",
    "id": 8163,
    "error": {
        "code": 11050,
        "message": "bad_request"
    },
    "testnet": False,
    "usIn": 1535037392434763,
    "usOut": 1535037392448119,
    "usDiff": 13356
}

# ------------------------------------
# RESPONSE MESSAGE (successful)

# "jsonrpc": string - version of JSON-remote procedure call - "2.0"
# "id": integer - same as id sent in request
# "testnet": boolean - TRUE(test server), FALSE(production server)
# "result": object - 
#   specific to method - CHECK API FOR CONTENTS RELATING TO SPECIFIC METHODS
# "usIn": integer - timestamp when request was received
# "usOut": integer - timestamp when response was sent
# "usDiff": integer - number of microseconds spent handling request
goodResponse = {
    "jsonrpc": "2.0",
    "id": 5239,
    "testnet": False,
    "result": [
        {
            "coin_type": "BITCOIN",
            "currency": "BTC",
            "currency_long": "Bitcoin",
            "fee_precision": 4,
            "min_confirmations": 1,
            "min_withdrawal_fee": 0.0001,
            "withdrawal_fee": 0.0001,
            "withdrawal_priorities": [
                {
                    "value": 0.15,
                    "name": "very_low"
                },
                {
                    "value": 1.5,
                    "name": "very_high"
                }
            ]
        }
    ],
    "usIn": 1535043730126248,
    "usOut": 1535043730126250,
    "usDiff": 2
}

# ------------------------------------
# ERROR CONDITIONS

# 1) If either the book stream OR the trade stream receives an event out of sequence, 
# an error message should print and the corresponding websocket connection should be restarted.

# 2) If a websocket connection is disconnected or otherwise interrupted, it should be restarted.
# ____________________________________________________________________________________________________________________

# group values:
#   BTC - none, 1, 2, 5, 10
#   ETH - none, 5, 10, 25, 100, 250 (dividied by 100) : 5 -> 0.05
# depth values:
#   1, 10, 20 - number of price levels to be included
# interval values:
#   100ms, agg2 - frequency of notifications ****(USE 100ms)****
async def subscribeToOrderbook(websocket, instrumentName:str, group:str, depth:int, interval:str):
    subscribeMsg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/public/subsribe",
        "params": {
            # notifies about changes to the order book for a certain instrument
            #   sent once per specified interval
            #   prices grouped by specified group
            #   number of price levels by specified depth
            "channels": [f"book.{instrumentName}.{group}.{depth}.{interval}"]
        }
    }

    await websocket.send(json.dumps(subscribeMsg))

    while (1):
        response = await websocket.recv()
        print(f"Order Book Update For InstrumentName {instrumentName}: {response}")



async def main():
    url = "wss.//www.deribit.com/ws/api/v2"

    # socket = websockets.connect(url)
    # orderbookTask = asyncio.create_task(subscribeToOrderbook(socket, ))