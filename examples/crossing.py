import asyncio
from datetime import datetime, timedelta

import asp
from asp import EventStreamDefinition

from common import NAMES, Greeter


async def create_async_generator(values, delay=1):
    """ "
    Yield values in the future with a delay.
    """
    current = datetime.now() - timedelta(seconds=60)
    for name in NAMES:
        yield current, name
        current += timedelta(seconds=delay)
    print("** Running live **")
    for name in values:
        yield datetime.now(), name
        await asyncio.sleep(delay)


def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet, future_events_iter=live_queue
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
