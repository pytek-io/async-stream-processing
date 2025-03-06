from datetime import datetime, timedelta

import pytest

import asp
from asp.testing import timestamp as timestamp_values

TIMESTAMP_TOLERANCE = 0.001


class Client:
    def __init__(self, start_time):
        self.start_time = start_time
        self.greeted = []

    def greet(self, value):
        self.greeted.append(((asp.now() - self.start_time).total_seconds(), value))

    async def sleep_and_greet(self, value):
        await asp.sleep(1)
        self.greet(value)

    def greet_later(self, value):
        asp.call_later(1, self.greet, value)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,lags", [("greet", [0] * 10), ("sleep_and_greet", [1] * 10), ("greet_later", [1] * 10)])
async def test_fast_forward(method, lags):
    """
    - past events are all passed at roughly the right virtual time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    client = Client(start_time)
    values = list(range(10))
    past_values = list(timestamp_values(values, start_time, delay=1))
    await asp.run(
        [asp.process_stream(callback=getattr(client, method), past=past_values)],
    )
    assert len(client.greeted) == len(values)
    for (timestamp, value), (expected_timestamp, expected_value), lag in zip(client.greeted, past_values, lags):
        assert abs(timestamp - lag - (expected_timestamp - start_time).total_seconds()) < TIMESTAMP_TOLERANCE
        assert value == expected_value
