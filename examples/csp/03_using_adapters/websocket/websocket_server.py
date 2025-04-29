import asyncio
import websockets  # pyright: ignore[reportMissingImports]


async def echo(websocket):
    for i in range(int(await websocket.recv())):
        await asyncio.sleep(1)
        await websocket.send(f"{i}")
    await websocket.close()


async def main():
    async with websockets.serve(echo, "localhost", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
