from datetime import datetime, timedelta
import asp
from asp.testing import create_async_generator, timestamps  # noqa: F401

NAMES = ["Jane", "John", "Sarah", "Paul", "Jane"]


def format(event_time: datetime):
    return f"{event_time:%H:%M:%S.%f}"


def log(event_time: datetime, msg: str):
    print(f"{format(datetime.now())} {format(asp.now())} {format(event_time)} {msg}")


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, event_time: datetime, name: str):
        if name not in self.greeted:
            log(event_time, f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(event_time, f"Hello again {name}!")

    def greet_later(self, event_time: datetime, name):
        log(event_time, f"{name} arrived.")
        asp.call_later(event_time + timedelta(seconds=1), self.greet, name)

    async def sleep_and_greet(self, event_time: datetime, name):
        log(event_time, f"{name} arrived.")
        delay = timedelta(seconds=5)
        await asp.sleep(delay)
        self.greet(event_time + delay, name)
