import asyncio
from marketDataFeed import checkFirstResponseForError, checkOrderbookResponseForError, checkTradeChannelResponseForError


async def testCheckFirstReponseForError():

    # Error: Includes 'error' field
    jsonResponse1 = {
        "error": {
            "message": "Error message"
        }
    }
    response1 = await checkFirstResponseForError(jsonResponse1)
    assert response1 == 1

    # Error: Missing 'result' field
    jsonResponse2 = {
        "empty": []
    }
    response2 = await checkFirstResponseForError(jsonResponse2)
    assert response2 == 2

    # Error: Empty 'result' field
    jsonResponse3 = {
        "result": []
    }
    response3 = await checkFirstResponseForError(jsonResponse3)
    assert response3 == 3

    # No Error
    jsonResponse4 = {
        "result": ["data1", "data2"]
    }
    response4 = await checkFirstResponseForError(jsonResponse4)
    assert response4 == 0


async def testCheckOrderbookResponseForError():

    # Error: Includes 'error' field
    jsonResponse1 = {
        "error": {
            "message": "Error message"
        },
        "params": {
            "data": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response1 = await checkOrderbookResponseForError(jsonResponse1)
    assert response1 == 1

    # Error: Missing 'params' field
    jsonResponse2 = {
        "notParams": {
            "data": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response2 = await checkOrderbookResponseForError(jsonResponse2)
    assert response2 == 2

    # Error: Missing 'data' field
    jsonResponse3 = {
        "params": {
            "notData": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response3 = await checkOrderbookResponseForError(jsonResponse3)
    assert response3 == 3

    # Error: out or order events received
    lastChangeID = "123456789"
    jsonResponse4 = {
        "params": {
            "data": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response4 = await checkOrderbookResponseForError(jsonResponse4)
    assert response4 == 4

    # No Error
    jsonResponse5 = {
        "params": {
            "data": {
                "change_id": "987654321",
            }
        }
    }
    response5 = await checkOrderbookResponseForError(jsonResponse5)
    assert response5 == 0


async def testCheckTradeChannelResponseForError():

    # Error: Includes 'error' field
    jsonResponse1 = {
        "error": {
            "message": "Error message"
        },
        "params": {
            "data": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response1 = await checkTradeChannelResponseForError(jsonResponse1)
    assert response1 == 1

    # Error: Missing 'params' field
    jsonResponse2 = {
        "notParams": {
            "data": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response2 = await checkTradeChannelResponseForError(jsonResponse2)
    assert response2 == 2

    # Error: Missing 'data' field
    jsonResponse3 = {
        "params": {
            "notData": {
                "change_id": "987654321",
                "prev_change_id": "123456789"
            }
        }
    }
    response3 = await checkTradeChannelResponseForError(jsonResponse3)
    assert response3 == 3

    # Error: Trade Event missing 'amount' field
    jsonResponse4 = {
        "params": {
            "data": [
                {
                    "price": "387.3",
                    "amount": "193.0",
                    "direction": "buy"
                },
                {
                    "price": "387.3",
                    "amount": "12003.0",
                    "direction": "buy"
                },
                {
                    "price": "387.3",
                    "notAmount": "1999",
                    "direction": "buy"
                }
            ]
        }
    }
    response4 = await checkTradeChannelResponseForError(jsonResponse4)
    assert response4 == 4
    
    # Error: Trade Event missing 'price' field
    jsonResponse5 = {
        "params": {
            "data": [
                {
                    "price": "93285.2",
                    "amount": "4982.0",
                    "direction": "sell"
                },
                {
                    "notPrice": "93285.2",
                    "amount": "19248.0",
                    "direction": "sell"
                },
                {
                    "price": "93285.2",
                    "amount": "958.0",
                    "direction": "sell"
                }
            ]
        }
    }
    response5 = await checkTradeChannelResponseForError(jsonResponse5)
    assert response5 == 5

    # Error: Trade Event missing 'direction' field
    jsonResponse6 = {
        "params": {
            "data": [
                {
                    "price": "93285.2",
                    "amount": "4982.0",
                    "notDirection": "sell"
                },
                {
                    "notPrice": "93285.2",
                    "amount": "19248.0",
                    "direction": "sell"
                },
                {
                    "price": "93285.2",
                    "amount": "958.0",
                    "direction": "sell"
                }
            ]
        }
    }
    response6 = await checkTradeChannelResponseForError(jsonResponse6)
    assert response6 == 6

    # No Error
    jsonResponse7 = {
        "params": {
            "data": [
                {
                    "price": "93285.2",
                    "amount": "4982.0",
                    "direction": "buy"
                },
                {
                    "price": "93285.2",
                    "amount": "19248.0",
                    "direction": "buy"
                },
                {
                    "price": "93285.2",
                    "amount": "958.0",
                    "direction": "buy"
                }
            ]
        }
    }
    response7 = await checkTradeChannelResponseForError(jsonResponse7)
    assert response7 == 0


asyncio.run(testCheckFirstReponseForError())
asyncio.run(testCheckOrderbookResponseForError())
asyncio.run(testCheckTradeChannelResponseForError())
