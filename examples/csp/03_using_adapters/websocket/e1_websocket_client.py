"""
This requires websocket_server.py to be running.
"""

import async_stream_processing as asp
import asyncio
import websockets  # pyright: ignore[reportMissingImports]


async def data(uri: str, number: int):
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(str(number))
            while True:
                value = await websocket.recv()
                yield asp.now(), value
    except websockets.exceptions.ConnectionClosedOK:
        pass


def main():
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=print,
                    future=data("ws://localhost:8765", 5),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
