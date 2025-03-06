import asyncio
from datetime import datetime, timedelta

import asp

from common import NAMES, Greeter, timestamp, create_async_generator


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
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
