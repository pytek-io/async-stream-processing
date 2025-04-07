import asyncio
from datetime import timedelta


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
