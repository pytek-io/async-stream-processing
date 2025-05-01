import asyncio
from datetime import datetime, timedelta
from itertools import count
from typing import Optional

import async_stream_processing as asp

from common import log, merge_timeseries


class Calculator:
    def __init__(self) -> None:
        self.bid: Optional[float] = None
        self.ask: Optional[float] = None

    def spread(
        self,
        event_time: datetime,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ):
        if bid is not None:
            self.bid = bid
            log(event_time, f"bid: {self.bid}")
        if ask is not None:
            self.ask = ask
            log(event_time, f"ask: {self.ask}")
        if self.bid is not None and self.ask is not None:
            log(event_time, f"spread: {self.ask - self.bid:.2f}")


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
