import asyncio

from datetime import datetime, timedelta
from typing import Optional
import asp
from asp.testing import merge_timeseries, log


class Calculator:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.accum = 0

    def new_value(
        self, _timestamp: datetime, x: Optional[int] = None, y: Optional[int] = None
    ):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        self.accum += self.x + self.y
        log(f"x: {self.x}, y: {self.y}, sum: {self.x + self.y}, accum: {self.accum}")


def main():
    st = datetime(2020, 1, 1)
    x = [(st + timedelta(1), 1), (st + timedelta(2), 2), (st + timedelta(3), 3)]
    y = [(st + timedelta(1), -1), (st + timedelta(3), -1), (st + timedelta(4), -1)]
    # We aggregate the events in a single event stream as this is how ASP handles simultaneous events.
    values = merge_timeseries({"x": x, "y": y})

    calculator = Calculator()
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=calculator.new_value,
                    past=values,
                    unpack_kwargs=True,
                )
            ],
            start_time=st,
        )
    )


if __name__ == "__main__":
    main()
