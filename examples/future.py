import asyncio

from common import NAMES, Greeter, create_async_generator

import asp
from asp import EventStreamDefinition


def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet, future_events_iter=live_queue
                )
            ]
        )
    )


if __name__ == "__main__":
    main()
