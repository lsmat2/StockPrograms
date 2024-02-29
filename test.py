import asyncio
import websockets
import json
import nest_asyncio
nest_asyncio.apply()
from pprint import pprint

# DO NOT RUN USING HOMEBREW / 'RUN' BOTTOM IN TOP RIGHT CORNER

# instead use command:      python3 [file.py]

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
     "method": "public/get_index_price",
     "id": 42,
     "params": {
     "index_name": "btc_usd"
    }
}

response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(currencyMsg)))

response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(ticketMsg)))

response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(indexMsg)))