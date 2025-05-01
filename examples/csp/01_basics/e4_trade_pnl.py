import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import starmap
from typing import Tuple

import async_stream_processing as asp

from common import log


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
        return self.total_quantity * (
            mid - self.total_quantity_price / self.total_quantity
        )


class Book:
    def __init__(self):
        self.quotes = {}
        self.last_bid = None
        self.last_ask = None
        self.buy_positions = Positions()
        self.sell_positions = Positions()

    def on_new_trade(self, event_time: datetime, trade: Trade):
        if trade.buy:
            self.buy_positions.on_new_trade(trade)
        else:
            self.sell_positions.on_new_trade(trade)
        self.compute_pnl(event_time)

    def on_new_quote(self, event_time: datetime, quote: Tuple[bool, float]):
        bid_or_ask, value = quote
        if bid_or_ask:
            self.last_bid = value
        else:
            self.last_ask = value
        if mid := self.mid():
            log(event_time, f"Mid: {mid:.2f}")

    def mid(self):
        if self.last_bid and self.last_ask:
            return (self.last_ask + self.last_bid) / 2

    def compute_pnl(self, event_time):
        if mid := self.mid():
            log(
                event_time,
                f"PNL: {self.buy_positions.pnl(mid) - self.sell_positions.pnl(mid):.2f} "
                f"{self.buy_positions.pnl(mid):.2f} {self.sell_positions.pnl(mid):.2f}",
            )


def main():
    st = datetime(2020, 1, 1)
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
    quotes = sorted(
        [
            *starmap(lambda t, v: (t, (True, v)), bid),
            *starmap(lambda t, v: (t, (False, v)), ask),
        ]
    )
    trades = [
        (st + timedelta(seconds=1), Trade(price=100.0, qty=50, buy=True)),
        (st + timedelta(seconds=2), Trade(price=101.5, qty=500, buy=False)),
        (st + timedelta(seconds=3), Trade(price=100.50, qty=100, buy=True)),
        (st + timedelta(seconds=4), Trade(price=101.2, qty=500, buy=False)),
        (st + timedelta(seconds=5), Trade(price=101.3, qty=500, buy=False)),
        (st + timedelta(seconds=6), Trade(price=101.4, qty=500, buy=True)),
    ]
    book = Book()
    asyncio.run(
        asp.run(
            [
                asp.process_stream(callback=book.on_new_quote, past=quotes),
                asp.process_stream(callback=book.on_new_trade, past=trades),
            ]
        )
    )


if __name__ == "__main__":
    main()
