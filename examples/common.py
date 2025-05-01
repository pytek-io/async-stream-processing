from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Iterator, Tuple

import async_stream_processing as asp
from async_stream_processing.testing import timestamps, create_async_generator  # noqa: F401

NAMES = ["Jane", "John", "Sarah", "Paul", "Jane"]


def format(event_time: datetime):
    return f"{event_time:%H:%M:%S.%f}"


def log(event_time: datetime, msg: str):
    print(f"{format(datetime.now())} {format(asp.now())} {format(event_time)} {msg}")


def merge_timeseries(
    timeseries: Dict[str, Iterable[Tuple[datetime, Any]]],
) -> Iterator[Tuple[datetime, Dict[str, Any]]]:
    for values in zip(*(iter(ts) for ts in timeseries.values())):
        yield values[0][0], dict(zip(timeseries, [v for _, v in values]))


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
