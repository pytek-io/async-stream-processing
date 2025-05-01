import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import reduce
from itertools import repeat
from typing import Dict, List

import async_stream_processing as asp

from common import log


@dataclass
class Item:
    name: str
    cost: float
    qty: int


@dataclass
class Cart:
    user_id: int
    items: List[Item]
    discount = 0.9


@dataclass
class CartUpdate:
    item: Item
    add: bool


class CartManager:
    def __init__(self) -> None:
        self.carts: Dict[int, Cart] = {}

    def remove_discount(self, event_time: datetime, user_id: int):
        log(event_time, f"Discount expired for user {user_id}")
        self.carts[user_id].discount = 1.0

    def update_cart(self, event_time: datetime, event: CartUpdate, user_id: int):
        if user_id not in self.carts:
            self.carts[user_id] = Cart(user_id, [])
            # It would make more sense to schedule the discount expiration from here, but it would not be consistent
            # with the original example where the discount is removed after 1 minute from the beginning of the
            # simulation. asp.call_later(60, self.remove_discount, user_id)
        cart = self.carts[user_id]
        if event.add:
            cart.items.append(
                dataclasses.replace(event.item, cost=event.item.cost * cart.discount)
            )
        else:
            new_items = []
            remaining_qty = event.item.qty
            for item in cart.items:
                if item.name == event.item.name:
                    if item.qty > remaining_qty:
                        item.qty -= remaining_qty
                        new_items.append(item)
                    else:
                        remaining_qty -= item.qty
                else:
                    new_items.append(item)
            cart.items = new_items
        total = reduce(lambda acc, item: acc + item.cost * item.qty, cart.items, 0.0)
        num_items = reduce(lambda acc, item: acc + item.qty, cart.items, 0)
        log(event_time, f"Cart total:{total:.2f}, number of items:{num_items}")


def main():
    st = datetime(2020, 1, 1)
    user_id = 42
    events = [
        # Add 1 unit of X at $10 plus a 10% discount
        (
            st + timedelta(seconds=15),
            CartUpdate(item=Item(name="X", cost=10, qty=1), add=True),
        ),
        # Add 2 units of Y at $15 each, plus a 10% discount
        (
            st + timedelta(seconds=30),
            CartUpdate(item=Item(name="Y", cost=15, qty=2), add=True),
        ),
        # Remove 1 unit of Y
        (
            st + timedelta(seconds=45),
            CartUpdate(item=Item(name="Y", cost=0.0, qty=1), add=False),
        ),
        # Add 1 unit of Z at $20 but no discount, since our minute expired
        (
            st + timedelta(seconds=75),
            CartUpdate(item=Item(name="Z", cost=20, qty=1), add=True),
        ),
    ]
    timestamps, updates = zip(*events)
    events = zip(timestamps, zip(updates, repeat(user_id)))
    cart_manager = CartManager()
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=cart_manager.update_cart,
                    past=events,
                    unpack_args=True,
                    on_start=lambda: asp.call_later(
                        60, cart_manager.remove_discount, user_id
                    ),
                ),
            ],
            start_time=st,
        ),
    )


if __name__ == "__main__":
    main()
