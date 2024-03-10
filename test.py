import asyncio
import websockets
import json
import nest_asyncio
nest_asyncio.apply()
from pprint import pprint

import sys 
  
if len(sys.argv) == 1: 
  print("Provide a symbol as an argument:    test.py <symbol>")
  exit()

elif len(sys.argv) > 2:
  print("Too many arguments provided, only need [1] symbol")
  exit()

symbol = sys.argv[1]
print("Program invoked with symbol: ", symbol)


# DO NOT RUN USING HOMEBREW / 'RUN' BOTTOM IN TOP RIGHT CORNER

# websockets & nest_asyncio are installed in python version 3.11 packages
# make sure to set local python version to 3.11:
#     >> pyenv local 3.11

# running file:
#     >> python3 [file.py]

# __________________________________________________________________________________________

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

deribitTestUrl = "wss://test.deribit.com/ws/api/v2"
deribitMainUrl = "wss://www.deribit.com/ws/api/v2"



async def subscribeToOrderbook(symbol):

  # Create websocket connection
  async with websockets.connect(deribitTestUrl) as websocket:

    # Send subscribe request to orderbook
    print(f"Subscribing to orderbook for {symbol}")
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "public/subscribe",
        "params": {
            "channels": [f"book.{symbol}.100ms"]
        },
    }
    await websocket.send(json.dumps(subscribeRequest))

    # Receive initial response & check for errors
    initialResponse = await websocket.recv()
    initialJsonResponse = json.loads(initialResponse)

    if "error" in initialJsonResponse:
      errorMessage = initialJsonResponse["error"]["message"]
      print(f"Error: {errorMessage}")
      exit() # ********* HANDLE ERRORS DIFFERENTLY -> RESTART WEBSOCKET CONNECTION
    elif "result" not in initialJsonResponse:
      print("Deribit response did not contain result")
      exit()
    else:
      print(f"Subscribed to {symbol} L2 order book updates.")
      print(f"Response: {initialJsonResponse}\n")

    # Receive first data response & extract bids/asks
    firstResponse = await websocket.recv()
    firstJsonResponse = json.loads(firstResponse)
    initialBids = firstJsonResponse["params"]["data"]["bids"]
    initialAsks = firstJsonResponse["params"]["data"]["asks"]
    
    # Print top 5 bids/asks
    print("INITIAL BID/ASK LISTS:")
    sortedInitialBids = sorted(initialBids, key=lambda x: x[1], reverse=True)
    topInitialBids = sortedInitialBids[:5]
    sortedInitialAsks = sorted(initialAsks, key=lambda x: x[1], reverse=True)
    bottomInitialAsks = sortedInitialAsks[-5:]

    for bid in topInitialBids:
      # print(f"Type: {bid[0]}, Price: {bid[1]}, Quantity: {bid[2]}")
      print(f"{bid[2]} @ {bid[1]}")
    print("----------------")
    for ask in bottomInitialAsks:
      # print(f"Type: {ask[0]}, Price: {ask[1]}, Quantity: {ask[2]}")
      print(f"{ask[2]} @ {ask[1]}")
    print()

    
    # Listen for updates
    while True:
      response = await websocket.recv()
      jsonResponse = json.loads(response)

      # Check for error field or lack of params/data (exit if so)
      if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        exit() # ********* HANDLE ERRORS DIFFERENTLY -> RESTART WEBSOCKET CONNECTION
      if "params" not in jsonResponse or "data" not in jsonResponse["params"]:
        print("Deribit response did not contain error, params, or data")
        exit()
      # EXTRA ERROR CONDITION
      # Each notification will contain a change_id field, 
      # and each message except for the first one will contain a field prev_change_id. 
      # If prev_change_id is equal to the change_id of the previous message, 
      # this means that no messages have been missed.

      # Extract bids/asks updates and adjust respective overall lists
      # print("UPDATE:")
      bidUpdates = jsonResponse["params"]["data"]["bids"]
      for bid in bidUpdates:
        # print(f"Type: {bid[0]}, Price: {bid[1]}, Quantity: {bid[2]}")
        type = bid[0]

        if type == "new":
          initialBids.append(bid)
        elif type == "delete": # Delete by finding other bid with same price
          priceToDelete = bid[1]
          for otherBid in initialBids:
            if otherBid[1] == priceToDelete: initialBids.remove(otherBid)
        elif type == "change": # Update amount by finding other bid with same price
          updatedAmount = bid[2]
          for otherBid in initialBids:
            if otherBid[1] == bid[1]: otherBid[2] = updatedAmount
      # print("----------------")
      askUpdates = jsonResponse["params"]["data"]["asks"]
      for ask in askUpdates:
        # print(f"Type: {ask[0]}, Price: {ask[1]}, Quantity: {ask[2]}")
        type = ask[0]

        if type == "new":
          initialAsks.append(ask)
        elif type == "delete": # Delete by finding other ask with same price
          priceToDelete = ask[1]
          for otherAsk in initialAsks:
            if otherAsk[1] == priceToDelete: initialAsks.remove(otherAsk)
        elif type == "change": # Update amount by finding other ask with same price
          updatedAmount = ask[2]
          for otherAsk in initialAsks:
            if otherAsk[1] == ask[1]: 
              otherAsk[2] = updatedAmount
      # print()
      
      # Print best 5 levels on each side (highest bids, lowest asks)
      sortedBids = sorted(initialBids, key=lambda x: x[1], reverse=True)
      topBids = sortedBids[:5]
      sortedAsks = sorted(initialAsks, key=lambda x: x[1], reverse=True)
      bottomAsks = sortedAsks[-5:]

      for bid in topBids:
        # print(f"Type: {bid[0]}, Price: {bid[1]}, Quantity: {bid[2]}")
        print(f"{bid[2]} @ {bid[1]}")
      print("----------------")
      for ask in bottomAsks:
        # print(f"Type: {ask[0]}, Price: {ask[1]}, Quantity: {ask[2]}")
        print(f"{ask[2]} @ {ask[1]}")
      print()


async def subscribeToOrderbook2(symbol):

  # Create websocket connection
  async with websockets.connect(deribitTestUrl) as websocket:

    # Send subscribe request to orderbook
    print(f"Subscribing to orderbook for {symbol} at group: 10, depth: 20")
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "public/subscribe",
        "params": {
            "channels": [f"book.{symbol}.10.20.100ms"]
        },
    }
    await websocket.send(json.dumps(subscribeRequest))

    # Receive initial response & check for errors
    initialResponse = await websocket.recv()
    initialJsonResponse = json.loads(initialResponse)

    if "error" in initialJsonResponse:
      errorMessage = initialJsonResponse["error"]["message"]
      print(f"Error: {errorMessage}")
      exit() # ********* HANDLE ERRORS DIFFERENTLY -> RESTART WEBSOCKET CONNECTION
    elif "result" not in initialJsonResponse:
      print("Deribit response did not contain result")
      exit()
    else:
      print(f"Subscribed to {symbol} L2 order book updates.")
      print(f"Response: {initialJsonResponse}\n")
    
    # Listen for updates
    while True:
      response = await websocket.recv()
      jsonResponse = json.loads(response)

      # Check for error field or lack of params/data (exit if so)
      if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        exit() # ********* HANDLE ERRORS DIFFERENTLY -> RESTART WEBSOCKET CONNECTION
      if "params" not in jsonResponse or "data" not in jsonResponse["params"]:
        print("Deribit response did not contain error, params, or data")
        exit()
      # EXTRA ERROR CONDITION
      # Each notification will contain a change_id field, 
      # and each message except for the first one will contain a field prev_change_id. 
      # If prev_change_id is equal to the change_id of the previous message, 
      # this means that no messages have been missed.
        
      # Extract bids/asks from response
      newBids = jsonResponse["params"]["data"]["bids"]
      newAsks = jsonResponse["params"]["data"]["asks"]
      
      # Update highestBids and lowestAsks Lists
      highestBids = []
      for bid in newBids:
        for i in range(5):
          if (i == len(highestBids)):
          # If there's only i bids (<5), put bid in list at index i 
            highestBids.append(bid)
            break
          else: 
          # Otherwise, check if this bid is higher than current highest at index i
            if bid[0] > highestBids[i][0]:
              tmp = highestBids[i]
              highestBids[i] = bid
              bid = tmp
      
      lowestAsks = []
      for ask in newAsks:
        for i in range(5):
          if (i == len(lowestAsks)):
          # If there's only i asks (<5), put ask in list at index i 
            lowestAsks.append(ask)
            break
          else: 
          # Otherwise, check if this ask is lower than current lowest at index i
            if ask[0] < lowestAsks[i][0]:
              tmp = lowestAsks[i]
              lowestAsks[i] = ask
              ask = tmp

      # Print out highestBids/lowestAsks lists after update
      for bid in highestBids:
        print(f"{bid[1]} @ {bid[0]}")
      print("----------------")
      for ask in lowestAsks:
        print(f"{ask[1]} @ {ask[0]}")
      print()


asyncio.get_event_loop().run_until_complete(subscribeToOrderbook("BTC-PERPETUAL"))