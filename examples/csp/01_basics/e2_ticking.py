import asyncio

from datetime import datetime, timedelta

import asp
from asp import EventStreamDefinition


class Calculator:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.accum = 0

    def new_value(self, value):
        if value.get("x"):
            self.x = value["x"]
        if value.get("y"):
            self.y = value["y"]
        self.accum += self.x + self.y
        print(
            asp.now().strftime("%Y-%m-%d %H:%M:%S.00"),
            f"x: {self.x}, y: {self.y}, sum: {self.x + self.y}, accum: {self.accum}",
        )


def main():
    st = datetime(2020, 1, 1)
    # Contrary to the original example we collate the events in a single event stream.
    # This is because ASP doesn't support simultanous events.
    values = [
        (st + timedelta(1), {"x": 1, "y": -1}),
        (st + timedelta(2), {"x": 2}),
        (st + timedelta(3), {"x": 3, "y": -1}),
        (st + timedelta(4), {"y": -1}),
    ]
    calculator = Calculator()
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=calculator.new_value,
                    past_events_iter=iter(values),
                )
            ],
            start_time=st,
        )
    )


if __name__ == "__main__":
    main()
