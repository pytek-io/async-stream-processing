import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Tuple

import asp
from asp import EventStreamDefinition

# This example demonstrates the advanced concept of dynamic graphs. Dynamic graphs provide the ability to extend the shape of the graph during runtime,
# which is useful when you may not necessarily know what you will be processing at start


@dataclass
class Order:
    symbol: str
    size: int
    price: float


def process_symbol(order: Order):
    print(
        f"Processing order for symbol {order.symbol} with size {order.size} at price {order.price}"
    )


def iterate_orders_for_symbol(orders: Iterable[Tuple[timedelta, Order]], symbol: str):
    for timestamp, order in orders:
        if order.symbol == symbol:
            yield timestamp, order


def classify_orders(
    orders: Iterable[Tuple[timedelta, Order]],
) -> Iterable[Tuple[timedelta, Iterable[Tuple[timedelta, Order]]]]:
    symbols = set()
    for timestamp, order in orders:
        if order.symbol not in symbols:
            symbols.add(order.symbol)
            print(f"New symbol detected: {order.symbol}")
            yield timestamp, iterate_orders_for_symbol(orders, order.symbol)


def main():
    # We have a stream of incoming orders to deal with, we dont know the symbols up front
    start_time = datetime.now() - timedelta(seconds=60)
    orders = [
        (start_time + timedelta(seconds=0), Order(symbol="AAPL", price=135, size=100)),
        (start_time + timedelta(seconds=1), Order(symbol="FB", price=350, size=-200)),
        (start_time + timedelta(seconds=2), Order(symbol="GME", price=210, size=1000)),
        (start_time + timedelta(seconds=3), Order(symbol="AAPL", price=138, size=-100)),
        (start_time + timedelta(seconds=4), Order(symbol="FB", price=330, size=100)),
        (start_time + timedelta(seconds=5), Order(symbol="AMC", price=57, size=400)),
        (start_time + timedelta(seconds=6), Order(symbol="GME", price=200, size=800)),
    ]

    def on_new_symbol_orders(orders: Iterable[Tuple[timedelta, Order]]):
        asp.add_event_stream(
            EventStreamDefinition(past_events_iter=orders, callback=process_symbol)
        )

    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    past_events_iter=classify_orders(orders),
                    callback=on_new_symbol_orders,
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
