import asyncio
from datetime import datetime, timedelta

import async_stream_processing as asp
from common import NAMES, timestamps, Greeter, create_async_generator


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
                    callback=greeter.greet_later,
                    past=past_queue,
                    future=live_queue,
                    on_live_start=lambda: print("** Running live **"),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
