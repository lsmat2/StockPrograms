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

async def typeOfResponseOB(jsonResponse:str) -> int:
    # Error indicator
    if "error" in jsonResponse:
        print("Error in response, restarting websocket")
        return 1
    # Heartbeat/Trade Channel indicators
    if "params" in jsonResponse:
        # Heartbeat
        if "type" in jsonResponse["params"]:
            if (jsonResponse["params"]["type"] == "test_request"): return 2
            if (jsonResponse["params"]["type"] == "heartbeat"): return 3
        # Trade Channel
        if "data" in jsonResponse["params"]:
            orderbookResponse = await checkOrderbookResponseForError(jsonResponse)
            if (orderbookResponse != 0): return 1
            else: return 4
    # Heartbeat Response Confirmation
    if "id" in jsonResponse and jsonResponse["id"] == 2: return 5
    # Unknown Response
    return 6

async def typeOfResponseTC(jsonResponse:str) -> int:
    # Error indicator
    if "error" in jsonResponse:
        print("Error in response, restarting websocket")
        return 1
    # Heartbeat/Trade Channel indicators
    if "params" in jsonResponse:
        # Heartbeat
        if "type" in jsonResponse["params"]:
            if (jsonResponse["params"]["type"] == "test_request"): return 2
            if (jsonResponse["params"]["type"] == "heartbeat"): return 3
        # Trade Channel
        if "data" in jsonResponse["params"]:
            tradeChannelResponse = await checkTradeChannelResponseForError(jsonResponse)
            if (tradeChannelResponse != 0): return 1
            else: return 4
    # Heartbeat Response Confirmation
    if "id" in jsonResponse and jsonResponse["id"] == 2: return 5
    # Unknown Response
    return 6


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
    print(f"Subscribing to orderbook for {symbol} @ 100ms granularity")
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 3,
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

                # Connect to hearbeat mechanism
                print("Connecting to heartbeat mechanism")
                await websocket.send(json.dumps(heartbeatInitRequest))
                heartbeatInitResponse = await websocket.recv()
                initialHeartbeatErrorResponse = await checkFirstResponseForError(json.loads(heartbeatInitResponse))
                if (initialHeartbeatErrorResponse != 0): await websocket.close()

                # Subscribe to orderbook
                subscribeRequest = await getOrderbookRequestFromSymbol(symbol)
                await websocket.send(json.dumps(subscribeRequest))

                # Check subscription response for errors
                initialResponse = await websocket.recv()
                initialErrorResponse = await checkFirstResponseForError(json.loads(initialResponse))
                if (initialErrorResponse != 0): await websocket.close()
                
                # Print subscription confirmation & initialize bid/ask lists
                print(f"Subscribed to {symbol} Orderbook.")
                allBids = []
                allAsks = []

                # Listen for updates
                while True:
                    # Determine type of response
                    response = await websocket.recv()
                    typeResponse = await typeOfResponseOB(json.loads(response))

                    # Error Response
                    if (typeResponse == 1): await websocket.close()
                    # Heartbeat Request Response
                    elif (typeResponse == 2): await websocket.send(json.dumps(heartbeatNotificationRequest))
                    # Handle Orderbook Responses
                    elif (typeResponse == 4):
                        # Extract bids/asks updates, update 'best 5' lists, & print
                        allBids = await updateBids(allBids, json.loads(response)["params"]["data"]["bids"])
                        allAsks = await updateAsks(allAsks, json.loads(response)["params"]["data"]["asks"])
                        await printBestBidsAndAsks(allBids, allAsks)
                    # Ignore Other Responses
                    elif (typeResponse == 3) or (typeResponse == 5) or (typeResponse == 6): continue

    
        except websockets.exceptions.ConnectionClosed:
            # Wait & restart connection
            print("Orderbook websocket connection closed. Reconnecting...")
            await asyncio.sleep(5)


# TRADE CHANNEL HELPER FUNCTIONS
async def getTradeChannelRequestFromSymbol(symbol:str) -> str:
    print(f"Subscribing to trade channel for {symbol} @ 100ms granularity")
    subscribeRequest = {
        "jsonrpc": "2.0",
        "id": 4,
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
                initialHeartbeatErrorResponse = await checkFirstResponseForError(json.loads(heartbeatInitResponse))
                if (initialHeartbeatErrorResponse != 0): await websocket.close()

                # Subscribe to trade channel
                subscribeRequest = await getTradeChannelRequestFromSymbol(symbol)
                await websocket.send(json.dumps(subscribeRequest))
                tradeChannelInitResponse = await websocket.recv()
                tradeChannelInitErrorResponse = await checkFirstResponseForError(json.loads(tradeChannelInitResponse))
                if (tradeChannelInitErrorResponse != 0): await websocket.close()

                print(f"Subscribed to {symbol} Trade Channel.")

                # Listen for updates
                while True:
                    # Determine type of response
                    response = await websocket.recv()
                    typeResponse = await typeOfResponseTC(json.loads(response))
                    
                    # Error Response
                    if (typeResponse == 1): await websocket.close()
                    # Heartbeat Request Response
                    elif (typeResponse == 2): await websocket.send(json.dumps(heartbeatNotificationRequest))
                    # Handle trade channel response
                    elif (typeResponse == 4): await printTradeEvents(json.loads(response)["params"]["data"])
                    # Ignore Other Responses
                    elif (typeResponse == 3) or (typeResponse == 5) or (typeResponse == 6): continue
        
        except websockets.exceptions.ConnectionClosed:
            # Wait & restart connection
            print("Trade Channel websocket connection closed. Reconnecting...")
            await asyncio.sleep(5)


# MAIN FUNCTION
async def main(symbol):
    # Create tasks
    orderbookTask = asyncio.create_task(subscribeToOrderbook(symbol))
    tradeChannelTask = asyncio.create_task(subscribeToTradeChannel(symbol))
    # 'Wait' for both to complete
    await orderbookTask
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
