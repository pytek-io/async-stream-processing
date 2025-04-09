import asyncio

from datetime import datetime, timedelta
from itertools import count
import asp
from asp import EventStreamDefinition

from common import merge_timeseries


class Calculator:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.accum = 0

    def spread(self, value):
        if value.get("x"):
            self.x = value["x"]
        if value.get("y"):
            self.y = value["y"]
        self.accum += self.x + self.y
        print(
            asp.now().strftime("%Y-%m-%d %H:%M:%S.00"),
            f"x: {self.x}, y: {self.y}, sum: {self.x + self.y}, accum: {self.accum}",
        )

def create_timeseries(start: datetime, end: datetime, step: timedelta, factor: int = 1):
    value = count(1)
    while start < end:
        yield start, next(value) * factor
        start += step

def main():
    st = datetime(2020, 1, 1)
    bid = create_timeseries(st, st + timedelta(seconds=10), timedelta(seconds=2.5), 2)
    ask = create_timeseries(st, st + timedelta(seconds=10), timedelta(seconds=1), 2)
    # Contrary to the original example we collate the events in a single event stream.
    # This is because ASP doesn't support simultanous events.
    quotes = merge_timeseries({"bid": bid, "ask": ask})
    calculator = Calculator()
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=calculator.new_value,
                    past_events_iter=quotes,
                )
            ],
            start_time=st,
        )
    )


if __name__ == "__main__":
    main()
