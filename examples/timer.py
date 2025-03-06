import asyncio
from datetime import datetime, timedelta

import asp

from common import log


async def say_hello():
    log("sleeping for 1 second")
    await asp.sleep(1)
    log("hello")


def main():
    asyncio.run(
        asp.run(
            [
                asp.timer(
                    timedelta(seconds=1),
                    say_hello,
                    start_time=datetime.now() - timedelta(seconds=60),
                    end_time=timedelta(seconds=5),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
