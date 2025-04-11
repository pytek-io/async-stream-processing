"""
    This requires websocket_server.py to be running.
"""

import asp
from asp import EventStreamDefinition
import asyncio
import websockets


async def data(uri: str, number: int):
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(str(number))
            while True:
                yield await websocket.recv()
    except websockets.exceptions.ConnectionClosedOK:
        pass


def main():
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=print,
                    future_events_iter=data("ws://localhost:8765", 5),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
