import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import starmap
from typing import Tuple

# import numpy as np
# import uvloop

import asp

random.seed(0)


async def live_quotes(nb_values=10, initial_value=100.0, volatility: float = 0.1, delay: float = 1.0):
    # values = np.random.normal(loc=0, scale=volatility, size=nb_values) + initial_value
    values = range(nb_values)
    for value in values:
        await asyncio.sleep(delay)
        yield value > initial_value, value


@dataclass
class Trade:
    price: float
    qty: int
    buy: bool


class Positions:
    def __init__(self):
        self.total_quantity = 0
        self.total_quantity_price = 0

    def on_new_trade(self, trade: Trade):
        self.total_quantity += trade.qty
        self.total_quantity_price += trade.qty * trade.price

    def pnl(self, mid: float):
        if not self.total_quantity:
            return 0
        return self.total_quantity * (mid - self.total_quantity_price / self.total_quantity)


log = asp.log


class Test:
    def __init__(self):
        self.quotes = {}
        self.last_bid = None
        self.last_ask = None
        self.buy_positions = Positions()
        self.sell_positions = Positions()

    def hello(self, value):
        log(f"Hello: {value}")

    async def whatever(self, value):
        # log(f"Whatever {value}")
        # processor.call_later(1, self.hello, value)
        await asp.sleep(1)
        # log("Whatever 1")
        # await asyncio.sleep(1)
        log(f"Whatever {value}")

    async def new_whatever(self, value):
        await asp.sleep(1)
        log(f"New Whatever: {value}")

    def on_new_trade(self, trade: Trade):
        if trade.buy:
            self.buy_positions.on_new_trade(trade)
        else:
            self.sell_positions.on_new_trade(trade)
        self.compute_pnl()

    def on_new_quote(self, quote: Tuple[bool, float]):
        bid, quote = quote
        if bid:
            self.last_bid = quote
        else:
            self.last_ask = quote
        if mid := self.mid():
            asp.log(f"Mid: {mid:.2f}")

    def mid(self):
        if self.last_bid and self.last_ask:
            return (self.last_ask + self.last_bid) / 2

    def compute_pnl(self):
        if mid := self.mid():
            asp.log(
                f"PNL: {self.buy_positions.pnl(mid) - self.sell_positions.pnl(mid):.2f} {self.buy_positions.pnl(mid):.2f} {self.sell_positions.pnl(mid):.2f}"
            )


async def check_tasks():
    while True:
        await asyncio.sleep(1)
        tasks = asyncio.all_tasks()
        for task in tasks:
            if task != asyncio.current_task():  # Avoid checking itself
                stack = task.get_stack()
                if stack:
                    frame = stack[0]
                    # if task.get_name() == "EventStream.process_current_event":
                    print(f"Task '{task.get_name()}' is waiting at: {frame.f_code.co_name}, line {frame.f_lineno}")


def main():
    st = datetime(2020, 1, 1)
    ts = [(st + timedelta(seconds=i), i) for i in range(10)]

    bid = [
        (st + timedelta(seconds=0.5), 99.0),
        (st + timedelta(seconds=1.5), 99.1),
        (st + timedelta(seconds=5), 99.2),
    ]
    ask = [
        (st + timedelta(seconds=0.6), 99.1),
        (st + timedelta(seconds=1.3), 99.2),
        (st + timedelta(seconds=4.2), 99.25),
    ]
    quotes = sorted([*starmap(lambda t, v: (t, (True, v)), bid), *starmap(lambda t, v: (t, (False, v)), ask)])
    trades = [
        (st + timedelta(seconds=1), Trade(price=100.0, qty=50, buy=True)),
        (st + timedelta(seconds=2), Trade(price=101.5, qty=500, buy=False)),
        (st + timedelta(seconds=3), Trade(price=100.50, qty=100, buy=True)),
        (st + timedelta(seconds=4), Trade(price=101.2, qty=500, buy=False)),
        (st + timedelta(seconds=5), Trade(price=101.3, qty=500, buy=False)),
        (st + timedelta(seconds=6), Trade(price=101.4, qty=500, buy=True)),
    ]
    test = Test()
    quotes = ts
    # quotes = quotes[:10]
    callbacks = []
    for i in range(1):
        # callbacks.append((test.on_new_quote, quotes, None))
        # callbacks.append((test.on_new_trade, trades, None))
        # callbacks.append((test.new_whatever, ts, None))
        callbacks.append((test.whatever, iter(quotes), live_quotes(10, 100.0, 1, 0.001)))
        # callbacks.append((test.whatever, iter(quotes), None))

    asyncio.run(asp.run(callbacks))


if __name__ == "__main__":
    main()
