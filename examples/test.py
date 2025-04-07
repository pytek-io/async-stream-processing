import asyncio
from datetime import datetime, timedelta

from common import NAMES, create_async_generator, Greeter
from asp import EventStreamDefinition
import asp


def main():
    greeter = Greeter()
    start_time = datetime.now() - timedelta(seconds=60)
    past_queue = iter(
        [(start_time + timedelta(seconds=i), name) for i, name in enumerate(NAMES[:2])]
    )
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet_later,
                    past_events_iter=past_queue,
                    future_events_iter=live_queue,
                )
            ],
            on_live_start=lambda: print("** Running live **"),
        )
    )


if __name__ == "__main__":
    main()
