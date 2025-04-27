import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Iterator, Tuple

import asp


async def create_async_generator(values, delay=1):
    """ "
    Yield values in the future with a delay.
    """
    for value in values:
        yield datetime.now(), value
        await asyncio.sleep(delay)


def timestamps(start: datetime, delay: timedelta):
    current_time = start
    while True:
        yield current_time
        current_time += delay


def merge_timeseries(
    timeseries: Dict[str, Iterable[Tuple[datetime, Any]]],
) -> Iterator[Tuple[datetime, Dict[str, Any]]]:
    for values in zip(*(iter(ts) for ts in timeseries.values())):
        yield values[0][0], dict(zip(timeseries, [v for _, v in values]))


def log(*args: Any):
    """Log a message with the current time."""
    print(asp.now().isoformat(sep=" ", timespec="milliseconds"), *args)
