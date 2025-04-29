import asyncio

import async_stream_processing as asp

from common import NAMES, Greeter, create_async_generator


def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run([asp.process_stream(callback=greeter.greet, future=live_queue)])
    )


if __name__ == "__main__":
    main()
