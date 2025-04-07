import asyncio
from datetime import datetime, timedelta

from common import NAMES, log, timestamp

import asp
from asp import EventStreamDefinition


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, name):
        if name not in self.greeted:
            log(f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(f"Hello again {name}!")


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    asyncio.run(
        asp.run(
            [EventStreamDefinition(callback=greeter.greet, past_events_iter=past_queue)]
        )
    )


if __name__ == "__main__":
    main()
