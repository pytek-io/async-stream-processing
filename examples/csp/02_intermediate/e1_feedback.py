from __future__ import annotations

import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Callable

import async_stream_processing as asp

from common import log


@dataclass
class Order:
    order_id: int
    price: float
    qty: int
    side: str


@dataclass
class ExecReport:
    order_id: int
    status: str


class MyAlgo:
    def __init__(self, exchange: Exchange):
        self.last_id = 1
        self.last_price = 100.0
        self.exchange = exchange

    async def on_exec_report(
        self, event_time: datetime, exec_report: ExecReport | None = None
    ):
        if exec_report:
            log(
                event_time,
                f"Received exec report for order id:{exec_report.order_id} status {exec_report.status}",
            )
        order = Order(order_id=self.last_id, price=self.last_price, qty=200, side="BUY")
        self.last_id += 1
        self.last_price += 0.01
        log(event_time, f"Sending new order id:{order.order_id} price {order.price}")
        if self.last_id <= 10:
            asp.call_later(0.3, self.exchange.on_new_order, self.on_exec_report, order)


class Exchange:
    def __init__(self):
        self.quotes = {}
        self.last_price = 100.0
        self.last_id = 1

    def on_new_order(
        self, _event_time: datetime, exec_callback: Callable, order: Order
    ):
        exec_report = ExecReport(order_id=order.order_id, status="ACK")
        asp.call_later(0.7, exec_callback, exec_report)


def main():
    exchange = Exchange()
    algo = MyAlgo(exchange)
    start_time = datetime.now()
    asyncio.run(asp.run([algo.on_exec_report(start_time)], start_time=start_time))


if __name__ == "__main__":
    main()
