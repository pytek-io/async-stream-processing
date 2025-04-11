import asyncio
from datetime import datetime, timedelta
from itertools import chain
from typing import Any, Dict, Iterator, Tuple

import asp


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


def merge_timeseries(timeseries: Dict[str, Iterator[Tuple[datetime, Any]]]):
    # TODO: ask chatgpt to generate a version using iterators only
    timeseries = {k: dict(v) for k, v in timeseries.items()}
    for date in sorted(set(chain.from_iterable(timeseries.values()))):
        yield date, {k: v[date] for k, v in timeseries.items() if date in v}


def log(*args: Any):
    """Log a message with the current time."""
    print(asp.now().isoformat(sep=" ", timespec="milliseconds"), *args)
