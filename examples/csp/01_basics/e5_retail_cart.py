from dataclasses import dataclass
import dataclasses
from datetime import datetime, timedelta
from functools import reduce
from typing import List, Dict
import asyncio
import asp
from asp import EventStreamDefinition
from itertools import repeat

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
    def __init__(self):
        self.carts: Dict[int, Cart] = {}

    def remove_discount(self, user_id: int):
        self.carts[user_id].discount = 1.0
        print(asp.now(), f"Discount expired for user {user_id}")

    def update_cart(self, event: CartUpdate, user_id: int):
        if user_id not in self.carts:
            self.carts[user_id] = Cart(user_id, [])
            asp.call_later(45, self.remove_discount, user_id)
        cart = self.carts[user_id]
        if event.add:
            cart.items.append(dataclasses.replace(event.item, cost=event.item.cost * cart.discount))
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
        total = reduce(lambda acc, item: acc + item.cost * item.qty, cart.items, 0)
        num_items = reduce(lambda acc, item: acc + item.qty, cart.items, 0)
        print(asp.now().strftime('%Y-%m-%d %H:%M:%S.000'), f"Cart total:{total:.2f}, number of items:{num_items}")


def main():
    st = datetime(2020, 1, 1)
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
    events = zip(timestamps, zip(updates, repeat(42)))
    cart_manager = CartManager()
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=cart_manager.update_cart, past_events_iter=iter(events), unpack=True
                )
            ]
        )
    )


if __name__ == "__main__":
    main()

# 2020-01-01 00:00:15 Events:CartUpdate( item=Item( name=X, cost=10.0, qty=1 ), add=True )
# 2020-01-01 00:00:15 Cart total:9.0
# 2020-01-01 00:00:15 Cart number of items:1
# 2020-01-01 00:00:30 Events:CartUpdate( item=Item( name=Y, cost=15.0, qty=2 ), add=True )
# 2020-01-01 00:00:30 Cart total:36.0
# 2020-01-01 00:00:30 Cart number of items:3
# 2020-01-01 00:00:45 Events:CartUpdate( item=Item( name=Y, cost=<unset>, qty=1 ), add=False )
# 2020-01-01 00:00:45 Cart total:22.5
# 2020-01-01 00:00:45 Cart number of items:2
# 2020-01-01 00:01:15 Events:CartUpdate( item=Item( name=Z, cost=20.0, qty=1 ), add=True )
# 2020-01-01 00:01:15 Cart total:42.5
# 2020-01-01 00:01:15 Cart number of items:3
