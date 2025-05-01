import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncIterable, Iterable, Tuple


def timestamps(start: datetime, delay: timedelta):
    current_time = start
    while True:
        yield current_time
        current_time += delay


async def create_async_generator(values: Iterable[Any], delay: float = 1.0) -> AsyncIterable[Tuple[datetime, Any]]:
    """ "
    Yield values in the future with a delay.
    """
    for value in values:
        yield datetime.now(), value
        await asyncio.sleep(delay)
