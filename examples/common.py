from humanize import precisedelta
from datetime import datetime, timedelta
import asyncio
import asp

NAMES = ["Jane", "John", "Sarah", "Paul", "Jane"]


def elapsed_time(clock):
    previous_actual_time = clock()
    while True:
        now = clock()
        elapsed = precisedelta(now - previous_actual_time)
        previous_actual_time = now
        yield elapsed


actual_time = iter(elapsed_time(datetime.now))
virtual_time = iter(elapsed_time(asp.now))


def log(msg):
    print(f"{next(actual_time)}, {next(virtual_time)}: {msg}", flush=True)


async def create_async_generator(values, delay=1):
    """ "
    Yield values in the future with a delay.
    """
    for name in values:
        yield name
        await asyncio.sleep(delay)


def timestamp(values, start, delay=1):
    """
    Yield values in the future with a delay.
    """

    def timestamp_generator():
        nonlocal start
        while True:
            yield start
            start += timedelta(seconds=delay)

    return zip(timestamp_generator(), values)


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, name):
        if name not in self.greeted:
            log(f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(f"Hello again {name}!")

    def greet_later(self, name):
        asp.call_later(1, self.greet, name)
