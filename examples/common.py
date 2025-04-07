from humanize import precisedelta
from datetime import datetime
import asp
from asp.testing import create_async_generator, timestamp  # noqa: F401

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
        log(f"{name} arrived.")
        asp.call_later(1, self.greet, name)

    async def slow_greet(self, name):
        log(f"{name} arrived.")
        await asp.sleep(1)
        self.greet(name)
