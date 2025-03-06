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



def merge_timeseries(
    timeseries: Dict[str, Iterable[Tuple[datetime, Any]]],
) -> Iterator[Tuple[datetime, Dict[str, Any]]]:
        for values in zip(*(iter(ts) for ts in timeseries.values())):
            yield values[0][0], dict(zip(timeseries, [v for _, v in values]))


def log(*args: Any):
    """Log a message with the current time."""
    print(asp.now().isoformat(sep=" ", timespec="milliseconds"), *args)
