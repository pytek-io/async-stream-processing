from datetime import datetime, timedelta

import pytest

import asp
from asp import EventStreamDefinition
from asp.testing import timestamp as timestamp_values


class Client:
    def __init__(self):
        self.greeted = []

    def greet(self, value):
        self.greeted.append((asp.now(), value))

    async def greet_slow(self, value):
        await asp.sleep(1)
        self.greet(value)


@pytest.mark.asyncio
async def test_fast_forward():
    """
    - past events are all passed at roughly the right virtual time.
    - past events are correctly filtered out using start_time and end_time.
    """
    start_time = datetime.now() - timedelta(seconds=60)
    client = Client()
    values = list(range(10))
    past_values = list(timestamp_values(values, start_time, delay=1))
    await asp.run(
        [EventStreamDefinition(callback=client.greet, past_events_iter=iter(past_values))],
        on_live_start=lambda: print("** Running live **"),
        start_time=start_time + timedelta(seconds=1),
        end_time=start_time + timedelta(seconds=8),
    )
    assert len(client.greeted) == 7
    for (timestamp, value), (expected_timestamp, expected_value) in zip(client.greeted, past_values[2:]):
        assert abs((timestamp - expected_timestamp).total_seconds()) < 0.001
        assert value == expected_value

