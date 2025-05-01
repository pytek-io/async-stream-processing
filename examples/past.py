import asyncio
from datetime import datetime, timedelta

import async_stream_processing as asp

from common import NAMES, Greeter, timestamps


def main():
    greeter = Greeter()
    start_time = datetime(2025, 1, 1)
    past_queue = zip(timestamps(start_time, timedelta(seconds=1)), NAMES)
    asyncio.run(
        asp.run(
            [asp.process_stream(callback=greeter.greet, past=past_queue)], start_time
        )
    )


if __name__ == "__main__":
    main()
