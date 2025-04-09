from typing import Dict, Iterator, Tuple, Any
from datetime import datetime
from itertools import chain


def merge_timeseries(timeseries: Dict[str, Iterator[Tuple[datetime, Any]]]):
    # TODO: ask chatgpt to generate a version using iterators only
    timeseries = {k: dict(v) for k, v in timeseries.items()}
    for date in sorted(set(chain.from_iterable(timeseries.values()))):
        yield date, {k: v[date] for k, v in timeseries.items() if date in v}
