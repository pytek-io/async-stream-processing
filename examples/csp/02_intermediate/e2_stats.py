import asyncio
import polars as pl
import asp
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


class MovingAverage:
    def __init__(self, interval: timedelta, min_windows: timedelta):
        self.interval = interval
        self.min_windows = min_windows
        self.last_timestamp = None
        self.values: pl.DataFrame = pl.DataFrame(
            schema=[
                ("timestamp", pl.Datetime),
                ("value", pl.Float64),
                ("weight", pl.Float64),
            ]
        )

    def __call__(self, timestamp: datetime):
        filtered = self.values.filter(pl.col("timestamp") >= timestamp - self.interval)
        if filtered.is_empty():
            return None
        return (filtered["value"] * filtered["weight"]).sum() / filtered["weight"].sum()

    def reset(self):
        self.values.clear()

    def add_value(self, timestamp: datetime, value: float, weight: float):
        new_row = pl.DataFrame(
            data=[[timestamp, value, weight]], schema=self.values.schema, orient="row"
        )
        self.values = self.values.filter(
            pl.col("timestamp") >= timestamp - self.interval
        ).vstack(new_row)


def main():
    data = merge_timeseries({"value": prices_data, "weight": volume_data})
    mva = MovingAverage(interval=timedelta(minutes=2), min_windows=timedelta(minutes=1))
    cummulative_volume = 0

    def update(value: float, weight: float):
        nonlocal cummulative_volume
        timestamp = asp.now()
        mva.add_value(timestamp, value, weight)
        cummulative_volume += weight

    def print_values():
        if cummulative_volume > 0:
            mva_value = mva(asp.now())
            vwap = f"{mva(asp.now()):g}" if mva_value is not None else "none"
            log(f"VWAP: {vwap}\t Cum. Vol:{cummulative_volume:.2f}")

    asyncio.run(
        asp.run(
            [
                asp.EventStreamDefinition(
                    callback=update,
                    past_events_iter=data,
                    unpack_kwargs=True,
                )
            ],
            start_time=st,
            end_time=st + timedelta(minutes=10),
            background_tasks=[asp.timer(timedelta(minutes=1), print_values)],
        )
    )


if __name__ == "__main__":
    main()
