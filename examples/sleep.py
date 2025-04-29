import asyncio
from datetime import datetime, timedelta

import async_stream_processing as asp

from common import NAMES, Greeter, create_async_generator, timestamps


def main():
    greeter = Greeter()
    past_queue = zip(
        timestamps(datetime.now() - timedelta(seconds=60), delay=timedelta(seconds=1)),
        NAMES[:2],
    )
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.sleep_and_greet,
                    on_live_start=lambda: print("** Running live **"),
                    past=past_queue,
                    future=live_queue,
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
