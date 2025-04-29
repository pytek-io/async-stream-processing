import asyncio
from typing import Optional
from datetime import datetime, timedelta
from itertools import count
import asp

from asp.testing import merge_timeseries, log


class Calculator:
    def __init__(self) -> None:
        self.bid: Optional[float] = None
        self.ask: Optional[float] = None

    def spread(
        self,
        _timestamp: datetime,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ):
        if bid is not None:
            self.bid = bid
            log(f"bid: {self.bid}")
        if ask is not None:
            self.ask = ask
            log(f"ask: {self.ask}")
        if self.bid is not None and self.ask is not None:
            log(f"spread: {self.ask - self.bid:.2f}")


def create_timeseries(start: datetime, end: datetime, step: timedelta, factor: int = 1):
    value = count(1)
    while start < end:
        start += step
        yield start, next(value) * factor


def main():
    st = datetime(2020, 1, 1)
    bid = create_timeseries(st, st + timedelta(seconds=10), timedelta(seconds=2.5), 2)
    ask = create_timeseries(st, st + timedelta(seconds=10), timedelta(seconds=1), 2)
    # We aggregate the events in a single event stream as this is how ASP handles simultanous events.
    quotes = merge_timeseries({"bid": bid, "ask": ask})
    calculator = Calculator()
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=calculator.spread, past=quotes, unpack_kwargs=True
                )
            ],
            start_time=st,
        )
    )


if __name__ == "__main__":
    main()
