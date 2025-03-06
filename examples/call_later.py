import asyncio
from datetime import datetime, timedelta

import asp

from common import NAMES, Greeter, create_async_generator, timestamp


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.greet_later,
                    past=past_queue,
                    future=live_queue,
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
