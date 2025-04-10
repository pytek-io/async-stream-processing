from __future__ import annotations
import asyncio
from dataclasses import dataclass

import asp
from asp import BackgroundTaskDefinition
from typing import Callable


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

    def on_exec_report(self, exec_report: ExecReport = None):
        if self.last_id > 10:
            return
        order = Order(order_id=self.last_id, price=self.last_price, qty=200, side="BUY")
        self.last_id += 1
        self.last_price += 0.01
        print(f"Sending new order id:{order.order_id} price {order.price}")
        asp.call_later(1, self.exchange.on_new_order, self.on_exec_report, order)
        if exec_report:
            print(
                f"Received exec report for order id:{exec_report.order_id} status {exec_report.status}"
            )


class Exchange:
    def __init__(self):
        self.quotes = {}
        self.last_price = 100.0
        self.last_id = 1

    async def on_new_order(self, exec_callback: Callable, order: Order):
        await asp.sleep(0.7)
        exec_report = ExecReport(order_id=order.order_id, status="ACK")
        asp.call_later(0.7, exec_callback, exec_report)


def main():
    exchange = Exchange()
    algo = MyAlgo(exchange)
    asyncio.run(asp.run([BackgroundTaskDefinition(callback=algo.on_exec_report)]))


if __name__ == "__main__":
    main()
