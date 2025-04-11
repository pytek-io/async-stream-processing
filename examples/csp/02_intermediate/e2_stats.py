import asyncio

import asp
from typing import Callable
from datetime import datetime, timedelta
from asp.testing import log, merge_timeseries

st = datetime(2020, 1, 1)
prices_data = [
    (st + timedelta(minutes=1.3), 12.653),
    (st + timedelta(minutes=2.3), 14.210),
    (st + timedelta(minutes=3.8), 13.099),
    (st + timedelta(minutes=4.1), 12.892),
    (st + timedelta(minutes=4.4), 17.328),
    (st + timedelta(minutes=5.1), 18.543),
    (st + timedelta(minutes=5.3), 17.564),
    (st + timedelta(minutes=6.3), 19.023),
    (st + timedelta(minutes=8.7), 19.763),
]

volume_data = [
    (st + timedelta(minutes=1.3), 100),
    (st + timedelta(minutes=2.3), 115),
    (st + timedelta(minutes=3.8), 85),
    (st + timedelta(minutes=4.1), 90),
    (st + timedelta(minutes=4.4), 95),
    (st + timedelta(minutes=5.1), 185),
    (st + timedelta(minutes=5.3), 205),
    (st + timedelta(minutes=6.3), 70),
    (st + timedelta(minutes=8.7), 65),
]


class MVA:
    def __init__(self):
        self.prices = []
        self.volumes = []
        self.mva = 0
        self.mva_volume = 0
        self.mva_price = 0

    def on_price_update(self, price: float, volume: float):
        self.prices.append(price)
        if len(self.prices) > self.period:
            self.prices.pop(0)

    def reset(self):
        self.prices = []
        self.volumes = []
        self.mva = 0
        self.mva_volume = 0
        self.mva_price = 0


class ExponentialMovingAverage:
    def __init__(self, period: int):
        self.period = period
        self.mva = 0

    def on_price_update(self, price: float):
        if not self.mva:
            self.mva = price
        else:
            self.mva = (price - self.mva) * (2 / (self.period + 1)) + self.mva
        log(f"Exponential Moving Average: {self.mva:.2f}")


async def timer(step: timedelta, callback: Callable):
    while True:
        callback()
        await asp.sleep(step.total_seconds())


def main():
    data = merge_timeseries({"prices": prices_data, "volumes": volume_data})
    mva = MVA()
    ema = ExponentialMovingAverage(period=5)

    def reset():
        mva.reset()
        ema.reset()

    def trigger(price: float, volume: float):
        log(f"Moving Average: {mva.mva:.2f} Volume: {mva.mva_volume:.2f}")
        log(f"Exponential Moving Average: {ema.mva:.2f}")

    def print_hello():
        log("Hello")

    def on_price_update(price: float):
        mva.on_price_update(price, 0)
        ema.on_price_update(price)

    asyncio.run(
        asp.run(
            background_tasks=[timer(timedelta(minutes=1), print_hello)],
            start_time=st,
        )
    )


if __name__ == "__main__":
    main()
