import asyncio
from datetime import datetime, timedelta

import asp

from common import NAMES, log, timestamp


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, timestamp: datetime, name: str):
        if name not in self.greeted:
            log(f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(f"Hello again {name}!")


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    asyncio.run(asp.run([asp.process_stream(callback=greeter.greet, past=past_queue)]))


if __name__ == "__main__":
    main()
