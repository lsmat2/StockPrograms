import asyncio
import websockets
import json
import nest_asyncio
nest_asyncio.apply()
import sys

# GLOBAL VARS
deribitTestUrl = "wss://test.deribit.com/ws/api/v2"
deribitMainUrl = "wss://www.deribit.com/ws/api/v2"

# ORDERBOOK HELPER FUNCTIONS
async def updateBids(allBids:list, bidUpdates:list) -> list:
    for bid in bidUpdates:
        # Type: bid[0], Price: bid[1], Quantity: bid[2]
        # print(f"Type: {bid[0]}, Price: {bid[1]}, Quantity: {bid[2]}")

        if bid[0] == "new": # Add to list if 'new' bid
            allBids.append(bid)

        elif bid[0] == "delete": # Delete by finding bid with same price (quantity always 0)
            for otherBid in allBids:
                if otherBid[1] == bid[1]: 
                    allBids.remove(otherBid) # removes bid with that price
                    break

        elif bid[0] == "change": # 'change' affects amount -> find bid with same price -> adjust amount
            for otherBid in allBids:
                if otherBid[1] == bid[1]:
                    otherBid[2] = bid[2] # adjusts amount of the bid at that price
                    break
    
    return allBids

async def updateAsks(allAsks:list, askUpdates:list) -> list:
    for ask in askUpdates:
        # Type: ask[0], Price: ask[1], Quantity: ask[2]
        # print(f"Type: {ask[0]}, Price: {ask[1]}, Quantity: {ask[2]}")

        if ask[0] == "new": # Add to list if 'new' ask
          allAsks.append(ask)

        elif ask[0] == "delete": # Delete by finding ask with same price (quantity always 0)
            for otherAsk in allAsks:
                if otherAsk[1] == ask[1]:
                    allAsks.remove(otherAsk) # removes ask with that price
                    break

        elif ask[0] == "change": # 'change' affects amount -> find ask with same price -> adjust amount
            for otherAsk in allAsks:
                if otherAsk[1] == ask[1]: 
                    otherAsk[2] = ask[2] # adjusts amount of the ask at that price
                    break
    
    return allAsks

async def getrequestFromSymbol(symbol:str) -> str:
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "public/subscribe",
        "params": {
            "channels": [f"book.{symbol}.100ms"]
        },
    }
    return subscribeRequest

async def printBestBidsAndAsks(allBids:list[str], allAsks:list[str]):
    # Sort Bids/Asks & Filter Top/Bottom 5
    topBids = sorted(allBids, key=lambda x: x[1], reverse=True)[:5]
    bottomAsks = sorted(allAsks, key=lambda x: x[1], reverse=True)[-5:]

    # Print Best Bids/Asks
    for bid in topBids: print(f"{bid[2]} @ {bid[1]}")
    print("----------------")
    for ask in bottomAsks: print(f"{ask[2]} @ {ask[1]}")
    print()

async def checkFirstResponseForError(jsonResponse:str) -> int:
    if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"First Response Error: {errorMessage}")
        return 1
    elif "result" not in jsonResponse:
        print("Missing 'result' field in first response")
        return 2
    elif len(jsonResponse["result"]) == 0:
        print ("Empty 'result' field in first response")
        return 3
    else: return 0

async def checkResponseForError(jsonResponse:str) -> int:
    if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        return 1 # ********* HANDLE ERRORS DIFFERENTLY -> RESTART WEBSOCKET CONNECTION
    
    elif "params" not in jsonResponse:
        print("Missing 'params' field in response")
        return 2
    
    elif "data" not in jsonResponse["params"]:
        print("Missing 'data' field in response['params']")
        return 3
    
    # EXTRA ERROR CONDITION
        # Each notification will contain a change_id field, 
        # and each message except for the first one will contain a field prev_change_id. 
        # If prev_change_id is equal to the change_id of the previous message, 
        # this means that no messages have been missed.
    
    else: return 0

async def subscribeToOrderbook(symbol):

  # Create websocket connection
  async with websockets.connect(deribitTestUrl) as websocket:

    # Subscribe to orderbook
    print(f"Subscribing to orderbook for {symbol}")
    subscribeRequest = await getrequestFromSymbol(symbol)
    await websocket.send(json.dumps(subscribeRequest))

    # Check subscription response for errors
    initialResponse = await websocket.recv()
    initialJsonResponse = json.loads(initialResponse)
    initialErrorResponse = await checkFirstResponseForError(initialJsonResponse)
    if (initialErrorResponse != 0): exit()
    
    # Print subscription confirmation & initialize bid/ask lists
    print(f"Subscribed to {symbol} L2 order book updates.")
    print(f"Response: {initialJsonResponse}\n")
    allBids = []
    allAsks = []

    # Listen for updates
    while True:
        response = await websocket.recv()
        jsonResponse = json.loads(response)

        # Check response for errors
        errorResponse = await checkResponseForError(jsonResponse)
        if (errorResponse != 0) : exit()

        # Extract bids/asks updates and adjust respective overall lists
        bidUpdates = jsonResponse["params"]["data"]["bids"]
        askUpdates = jsonResponse["params"]["data"]["asks"]
        allBids = await updateBids(allBids, bidUpdates)
        allAsks = await updateAsks(allAsks, askUpdates)
        
        # Print top 5 sorted bids / bottom 5 sorted asks
        await printBestBidsAndAsks(allBids, allAsks)


# MAIN PROGRAM
# 1) Verify Command Line Arguments
if len(sys.argv) == 1: 
  print("Provide a symbol as an argument:    test.py <symbol>")
  exit()
elif len(sys.argv) > 2:
  print("Too many arguments provided, only need [1] symbol")
  exit()
symbol = sys.argv[1]
print("Program invoked with symbol: ", symbol)

# 2) Subscribe to Orderbook and [something else]
asyncio.get_event_loop().run_until_complete(subscribeToOrderbook(symbol))