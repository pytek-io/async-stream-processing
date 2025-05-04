from datetime import datetime, timedelta
from typing import Any
from itertools import product
import pytest

import async_stream_processing as asp
from async_stream_processing.testing import timestamps, create_async_generator

TIMESTAMP_TOLERANCE = 0.001


class Client:
    def __init__(self, start_time):
        self.start_time = start_time
        self.greeted = []

    def greet(self, _event_time: datetime, value):
        self.greeted.append(((asp.now() - self.start_time).total_seconds(), value))

    async def sleep_and_greet(self, _event_time: datetime, value):
        delay = timedelta(seconds=1)
        await asp.sleep(delay)
        self.greet(_event_time + delay, value)

    def greet_later(self, _event_time: datetime, value: Any):
        asp.call_later(1, self.greet, value)


@pytest.mark.parametrize("method,lags", [("greet", [0] * 10), ("sleep_and_greet", [1] * 10), ("greet_later", [1] * 10)])
async def test_fast_forward(method, lags):
    """
    past events are all passed at roughly the right virtual time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    client = Client(start_time)
    values = list(range(10))
    past_values = list(zip(timestamps(start_time, delay=timedelta(seconds=1)), values))
    await asp.run([asp.process_stream(callback=getattr(client, method), past=past_values)], start_time=start_time)
    assert len(client.greeted) == len(values)
    for (event_time, value), (expected_timestamp, expected_value), lag in zip(client.greeted, past_values, lags):
        assert abs(event_time - lag - (expected_timestamp - start_time).total_seconds()) < TIMESTAMP_TOLERANCE
        assert value == expected_value


@pytest.mark.parametrize("unpack_kwargs", [True, False])
async def test_unpack(unpack_kwargs: bool):
    """
    using unpack and unpack_kwargs.
    """
    start_time = datetime.now() - timedelta(seconds=60)

    result = 0

    def test(event_time: datetime, x: int, y: int):
        nonlocal result
        result += x + y

    values = [{"x": i, "y": i} if unpack_kwargs else (i, i) for i in range(10)]
    past_values = list(zip(timestamps(start_time, delay=timedelta(seconds=1)), values))
    await asp.run(
        [
            asp.process_stream(
                callback=test, past=past_values, unpack_args=not unpack_kwargs, unpack_kwargs=unpack_kwargs
            )
        ],
        start_time=start_time,
    )
    assert result == sum(range(10)) * 2


@pytest.mark.parametrize(
    "coroutine,delay", product([True, False], [None, 1, timedelta(seconds=1), datetime.now() + timedelta(seconds=1)])
)
async def test_call_later(coroutine, delay):
    start_time = datetime.now() - timedelta(seconds=60)
    called = False

    async def switch_flag_async(event_time: datetime):
        nonlocal called
        called = True

    def switch_flag(event_time: datetime):
        nonlocal called
        called = True

    async def callback():
        asp.call_later(delay, switch_flag_async if coroutine else switch_flag)

    await asp.run([callback()], start_time=start_time)
    assert called


async def test_future():
    """
    - past events are all passed at roughly the right virtual time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    client = Client(start_time)
    values = list(range(10))
    future_values = create_async_generator(values, delay=0.1)
    await asp.run([asp.process_stream(callback=client.greet, future=future_values)], start_time=start_time)


async def test_timer():
    """
    - past events are all passed at roughly the right virtual time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    count = 0

    def update_count(event_time: datetime):
        nonlocal count
        count += 1

    await asp.run(
        [asp.timer(timedelta(seconds=1), update_count, start_time=start_time, end_time=timedelta(seconds=10))],
        start_time=start_time,
    )
    assert count == 10


async def test_callbacks():
    """
    - past events are all passed at roughly the right virtual time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    started = False
    live = False

    def start():
        nonlocal started
        started = True

    def live_start():
        nonlocal live
        live = True

    values = list(range(10))
    future_values = create_async_generator(values, delay=0.1)
    await asp.run(
        [asp.process_stream(callback=print, future=future_values, on_start=start, on_live_start=live_start)],
        start_time=start_time,
    )

    assert started and live
