import asyncio
from datetime import datetime, timedelta

import async_stream_processing as asp

from common import NAMES, Greeter, timestamps, create_async_generator


def main():
    greeter = Greeter()
    start_time = datetime.now() - timedelta(seconds=60)
    past_queue = zip(timestamps(start_time, delay=timedelta(seconds=1)), NAMES[:2])
    live_queue = create_async_generator(NAMES[:2], delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.greet,
                    past=past_queue,
                    future=live_queue,
                    on_live_start=lambda: print("** Running live **"),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
