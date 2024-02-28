import asyncio
import json
import websockets
# Test

# Connect to Deribit’s market data API via websocket and subscribe to both the L2 orderbook & trade channels in separate threads/tasks 
# (not a single subscription for both channels) for a single symbol provided to the program as a command line argument. 

# Both channels should be subscribed to at the 100ms granularity.


# Size should be rounded to 2 decimal places and price 1 decimal place
# When an orderbook event is received, the program should output:
# the best 5 levels on each side of the book, indicating the price & liquidity of those levels.

