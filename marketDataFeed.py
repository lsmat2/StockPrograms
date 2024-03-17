import asyncio
import websockets
import json
import sys
from pprint import pprint

# GLOBAL VARS
deribitTestUrl = "wss://test.deribit.com/ws/api/v2"
deribitMainUrl = "wss://www.deribit.com/ws/api/v2"
lastChangeID = ""

heartbeatInitRequest = {
    "method": "public/set_heartbeat",
    "params": { "interval":15 },
    "jsonrpc": "2.0",
    "id": 1
}

heartbeatNotificationRequest = {
    "method": "public/test",
    "params": {},
    "jsonrpc": "2.0",
    "id": 2
}

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

async def getOrderbookRequestFromSymbol(symbol:str) -> str:
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
    print()
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

async def checkOrderbookResponseForError(jsonResponse:str) -> int:
    if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        return 1
    
    if "params" not in jsonResponse:
        print("Missing 'params' field in response")
        return 2
    
    if "data" not in jsonResponse["params"]:
        print("Missing 'data' field in response['params']")
        return 3
    
    # Compare changeID's
    global lastChangeID
    if "prev_change_id" in jsonResponse["params"]["data"]:
        if jsonResponse["params"]["data"]["prev_change_id"] != lastChangeID:
            print("Event received out of sequence")
            return 4
    lastChangeID = jsonResponse["params"]["data"]["change_id"]

    return 0

async def subscribeToOrderbook(symbol:str):
  
    while True:
        try:
            # Create websocket connection
            async with websockets.connect(deribitMainUrl) as websocket:

                # Subscribe to orderbook
                print(f"Subscribing to orderbook for {symbol} @ 100ms granularity")
                subscribeRequest = await getOrderbookRequestFromSymbol(symbol)
                await websocket.send(json.dumps(subscribeRequest))

                # Check subscription response for errors
                initialResponse = await websocket.recv()
                initialJsonResponse = json.loads(initialResponse)
                initialErrorResponse = await checkFirstResponseForError(initialJsonResponse)
                if (initialErrorResponse != 0): await websocket.close()
                
                # Print subscription confirmation & initialize bid/ask lists
                print(f"Subscribed to {symbol} Orderbook.")
                allBids = []
                allAsks = []

                # Listen for updates
                while True:
                    response = await websocket.recv()
                    jsonResponse = json.loads(response)

                    # Check response for errors
                    errorResponse = await checkOrderbookResponseForError(jsonResponse)
                    if (errorResponse != 0): await websocket.close()

                    # Extract bids/asks updates, update 'best 5' lists, & print
                    bidUpdates = jsonResponse["params"]["data"]["bids"]
                    askUpdates = jsonResponse["params"]["data"]["asks"]
                    allBids = await updateBids(allBids, bidUpdates)
                    allAsks = await updateAsks(allAsks, askUpdates)
                    await printBestBidsAndAsks(allBids, allAsks)
    
        except websockets.exceptions.ConnectionClosed:
            # Wait & restart connection
            print("Orderbook websocket connection closed. Reconnecting...")
            await asyncio.sleep(5)

# HEARTBEAT HELPER FUNCTIONS
async def checkHeartbeatResponseForError(jsonResponse:str) -> int:
    if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        return 1
    
    if "params" not in jsonResponse:
        print("Missing 'params' field in response")
        return 2
    
    if "type" not in jsonResponse["params"]:
        print("Missing 'type' field in response['params']")
        return 3
    
    return 0

async def typeOfResponse(jsonResponse:str) -> int:
    # Error indicator
    if "error" in jsonResponse:
        return 1
    # Heartbeat/Trade Channel indicators
    if "params" in jsonResponse:
        # Heartbeat
        if "type" in jsonResponse["params"]:
            responseType = jsonResponse["params"]["type"]
            if (responseType == "test_request"):
                return 2
            if (responseType == "heartbeat"):
                return 3
        # Trade Channel
        if "data" in jsonResponse["params"]:
            return 4
    # Neither error, trade channel, or heartbeat indicator (/public/test response?)
    if "id" in jsonResponse:
        if jsonResponse["id"] == 2: return 5
    return 6

# TRADE CHANNEL HELPER FUNCTIONS
async def getTradeChannelRequestFromSymbol(symbol:str) -> str:
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "public/subscribe",
        "params": {
            "channels": [f"trades.{symbol}.100ms"]
        },
    }
    return subscribeRequest        

async def printTradeEvents(tradeEvents:list[dict]):
    totalAmount = 0
    price = 0
    direction = ""

    for tradeEvent in tradeEvents:
        totalAmount += tradeEvent["amount"]
        # Price & Direction is the same for each 'event'
        price = tradeEvent["price"]
        direction = tradeEvent["direction"]

    if direction == "buy": print(f"\nBOUGHT {totalAmount} @ {price}\n")
    else: print(f"\nSOLD {totalAmount} @ {price}\n")

async def checkTradeChannelResponseForError(jsonResponse:str) -> int:
    if "error" in jsonResponse:
        errorMessage = jsonResponse["error"]["message"]
        print(f"Error: {errorMessage}")
        return 1
    
    elif "params" not in jsonResponse:
        print("Missing 'params' field in response")
        return 2
    
    elif "data" not in jsonResponse["params"]:
        print("Missing 'data' field in response['params']")
        return 3
    
    tradeEvents = jsonResponse["params"]["data"]
    
    for tradeEvent in tradeEvents:
        if "amount" not in tradeEvent:
            print ("Missing 'amount' field in tradeEvent")
            return 4
        elif "price" not in tradeEvent:
            print ("Missing 'price' field in tradeEvent")
            return 5
        elif "direction" not in tradeEvent:
            print ("Missing 'direction' field in tradeEvent")
            return 6

    return 0

async def subscribeToTradeChannel(symbol:str):

    while True:
        try:
            # Create websocket connection
            async with websockets.connect(deribitMainUrl) as websocket:

                # Connect to hearbeat mechanism
                print("Connecting to heartbeat mechanism")
                await websocket.send(json.dumps(heartbeatInitRequest))
                heartbeatInitResponse = await websocket.recv()
                heartbeatInitResponse = json.loads(heartbeatInitResponse)
                initialHeartbeatErrorResponse = await checkFirstResponseForError(heartbeatInitResponse)
                if (initialHeartbeatErrorResponse != 0): 
                    print("*error1*, response:")
                    pprint(heartbeatInitResponse)
                    await websocket.close()

                # Subscribe to trade channel
                print(f"Subscribing to trade channel for {symbol} @ 100ms granularity")
                subscribeRequest = await getTradeChannelRequestFromSymbol(symbol)
                await websocket.send(json.dumps(subscribeRequest))
                tradeChannelInitResponse = await websocket.recv()
                tradeChannelInitResponse = json.loads(tradeChannelInitResponse)
                tradeChannelInitErrorResponse = await checkFirstResponseForError(tradeChannelInitResponse)
                if (tradeChannelInitErrorResponse != 0): 
                    print("*error2*, response:")
                    pprint(tradeChannelInitResponse)
                    await websocket.close()

                # Print subscription confirmation
                print(f"Subscribed to {symbol} Trade Channel.")

                # Listen for updates
                while True:
                    response = await websocket.recv()
                    jsonResponse = json.loads(response)

                    # Determine if heartbeat request or trade channel notification
                    typeResponse = await typeOfResponse(jsonResponse)
                    print("type of response:", typeResponse)
                    if len(jsonResponse) < 200: pprint(jsonResponse)
                    else: print("too long of response")
                    
                    # Handle Response Based On Type
                    if (typeResponse == 1): 
                        print("Error, restarting websocket")
                        await websocket.close()

                    # Handle heartbeat request
                    elif (typeResponse == 2):
                        print("Sending back heartbeat")
                        await websocket.send(json.dumps(heartbeatNotificationRequest))

                    elif (typeResponse == 4):
                        # Check response for errors
                        errorResponse = await checkTradeChannelResponseForError(jsonResponse)
                        if (errorResponse != 0): 
                            print("*tradeChannelError*, restarting websocket:")
                            await websocket.close()

                        # Extract prices/amounts/directions from response & print
                        # tradeEvents = jsonResponse["params"]["data"]
                        # await printTradeEvents(tradeEvents)

                    elif (typeResponse == 3) or (typeResponse == 6):
                        print("null heartbeat response OR nothing...")
                        print("*null*, response:")
                        pprint(jsonResponse)
        
        except websockets.exceptions.ConnectionClosed:
            # Wait & restart connection
            print("Trade Channel websocket connection closed. Reconnecting...")
            await asyncio.sleep(5)

# SUBSCRIBE TO HEARTBEAT MECHANISMS

# MAIN FUNCTION
async def main(symbol):
    # Create tasks
    # orderbookTask = asyncio.create_task(subscribeToOrderbook(symbol))
    tradeChannelTask = asyncio.create_task(subscribeToTradeChannel(symbol))
    # 'Wait' for both to complete
    # await orderbookTask
    await tradeChannelTask

# -------------------------------------MAIN PROGRAM-------------------------------------

if __name__ == "__main__":
# 1) Verify Command Line Arguments
    if len(sys.argv) == 1: 
        print("Provide a symbol as an argument:       marketDataFeed.py <symbol>")
        exit()
    elif len(sys.argv) > 2:
        print("Too many arguments provided, provide only [1] symbol")
        exit()
    symbol = sys.argv[1]
    print("Program invoked with symbol: ", symbol)

# 2) Subscribe to Orderbook and Trade Events
    asyncio.run(main(symbol))
