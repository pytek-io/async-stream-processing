import asyncio
from dataclasses import dataclass

import asp
from asp import BackgroundTaskDefinition


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


class Exchange:
    def __init__(self):
        self.quotes = {}
        self.last_price = 100.0
        self.last_id = 1

    def on_new_order(self, order: Order):
        # await asyncio.sleep(0.7)
        exec_report = ExecReport(order_id=order.order_id, status="ACK")
        asp.call_later(0.7, self.my_algo, exec_report)

    def my_algo(self, exec_report: ExecReport = None):
        order = Order(order_id=self.last_id, price=self.last_price, qty=200, side="BUY")
        self.last_id += 1
        self.last_price += 0.01
        print(f"Sending new order id:{order.order_id} price {order.price}")
        asp.call_later(1, self.on_new_order, order)
        if exec_report:
            print(
                f"Received exec report for order id:{exec_report.order_id} status {exec_report.status}"
            )


def main():
    exchange = Exchange()
    asyncio.run(asp.run([BackgroundTaskDefinition(callback=exchange.my_algo)]))


if __name__ == "__main__":
    main()
