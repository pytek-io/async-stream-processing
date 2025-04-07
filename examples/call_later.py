import asyncio
from datetime import datetime, timedelta

from common import NAMES, create_async_generator, log, timestamp
from asp import EventStreamDefinition
import asp


def greet(name):
    log(f"Hello {name}.")
    asp.call_later(1, log, f"Bye {name}!")


def main():
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greet,
                    past_events_iter=past_queue,
                    future_events_iter=live_queue,
                )
            ],
            on_live_start=lambda: print("** Running live **"),
        )
    )


if __name__ == "__main__":
    main()
