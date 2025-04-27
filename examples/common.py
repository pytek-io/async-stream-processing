from datetime import datetime, timedelta
import asp
from asp.testing import create_async_generator, timestamps  # noqa: F401

NAMES = ["Jane", "John", "Sarah", "Paul", "Jane"]


def format(timestamp: datetime):
    return f"{timestamp:%H:%M:%S.%f}"


def log(timestamp: datetime, msg: str):
    print(f"{format(datetime.now())} {format(asp.now())} {format(timestamp)} {msg}")


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, timestamp: datetime, name: str):
        if name not in self.greeted:
            log(timestamp, f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(timestamp, f"Hello again {name}!")

    def greet_later(self, timestamp: datetime, name):
        log(timestamp, f"{name} arrived.")
        asp.call_later(timestamp + timedelta(seconds=1), self.greet, name)

    async def sleep_and_greet(self, timestamp: datetime, name):
        log(timestamp, f"{name} arrived.")
        delay = timedelta(seconds=5)
        await asp.sleep(delay)
        self.greet(timestamp + delay, name)
