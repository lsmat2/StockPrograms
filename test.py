import asyncio
import websockets
import json
import nest_asyncio
nest_asyncio.apply()
from pprint import pprint

# DO NOT RUN USING HOMEBREW / 'RUN' BOTTOM IN TOP RIGHT CORNER

# websockets & nest_asyncio are installed in python version 3.11 packages
# make sure to set local python version to 3.11:
#     >> pyenv local 3.11

# running file:
#     >> python3 [file.py]

async def call_api(msg):
    async with websockets.connect('wss://test.deribit.com/ws/api/v2') as websocket:
        await websocket.send(msg)
        while websocket.open:
            response = await websocket.recv()
            json_par = json.loads(response)
            # print(json_par)
            pprint(json_par)
            return(json_par)
        

currencyMsg = {
  "jsonrpc" : "2.0",
  "id" : 7538,
  "method" : "public/get_currencies",
  "params" : {
  }
}           

ticketMsg = {
  "jsonrpc" : "2.0",
  "id" : 8106,
  "method" : "public/ticker",
  "params" : {
    "instrument_name" : "BTC-PERPETUAL"
  }
}

indexMsg = {
  "jsonrpc": "2.0",
  "id": 42,
  "method": "public/get_index_price",
  "params": {
    "index_name": "btc_usd"
  }
}

orderbookMsg = {
  "jsonrpc" : "2.0",
  "id" : 8772,
  "method" : "public/get_order_book",
  "params" : {
    "instrument_name" : "BTC-PERPETUAL",
    "depth" : 25
  }
}

# RESPONSES:  
#   json.dumps(jsonVariable) >> puts a string into correct JSON format
#   json.loads(jsonVariable) >> puts a JSON string into string format

# response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(currencyMsg)))
# response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(ticketMsg)))
# response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(indexMsg)))

async def subscribe_to_orderbook(symbol):
    uri = "wss://www.deribit.com/ws/api/v2"

    # Create a WebSocket connection
    async with websockets.connect(uri) as websocket:
        # Create a subscription message for the L2 order book
        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "public/subscribe",
            "params": {
                "channels": [f"book.{symbol}.100ms"]
            },
        }

        # Send the subscription message
        await websocket.send(json.dumps(subscribe_msg))

        # Keep listening for updates
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if "result" in data:
                # Check if it's a subscription confirmation
                print(f"Subscribed to {symbol} L2 order book updates.")
            elif "params" in data and "data" in data["params"]:
                # Extract order book data and print the best 5 levels on each side
                bids = data["params"]["data"]["bids"][:5]
                asks = data["params"]["data"]["asks"][:5]

                print(f"\nBest 5 Bids for {symbol}:")
                for bid in bids:
                    print(f"Price: {bid[0]}, Quantity: {bid[1]}")

                print(f"\nBest 5 Asks for {symbol}:")
                for ask in asks:
                    print(f"Price: {ask[0]}, Quantity: {ask[1]}")

asyncio.get_event_loop().run_until_complete(subscribe_to_orderbook("BTC-PERPETUAL"))