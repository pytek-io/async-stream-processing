import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterable, Awaitable, Callable, Coroutine, Dict, Iterable, List, Tuple, Union, Optional


@dataclass
class Future:
    due_time: datetime

    def __await__(self):
        yield self


def wrap_as_coroutine(func: Callable, event_time: datetime, *args: Any) -> Coroutine:
    async def result():
        func(event_time, *args)

    return result()


@dataclass
class Processor:
    def __init__(self, coroutines: List[Coroutine], start_time: datetime):
        self.start_time = start_time
        self.virtual_time = start_time
        self.actual_time = datetime.now()
        self.scheduled_coroutines: List[Tuple[datetime, Coroutine]] = []
        self.ready_coroutines = coroutines.copy()

    @contextmanager
    def update_virtual_time(self):
        self.actual_time = datetime.now()
        yield
        self.virtual_time += datetime.now() - self.actual_time

    def now(self) -> datetime:
        return self.virtual_time + (datetime.now() - self.actual_time)

    def call_later(
        self, delay: Union[float, timedelta, datetime, None], coroutine_or_func: Union[Coroutine, Callable], *args: Any
    ) -> None:
        """
        Call a function after a delay.
        :param delay: Delay in seconds.
        :param func: Function to call.
        :param args: Arguments to pass to the function.
        :return: None
        """
        if isinstance(delay, timedelta):
            delay = self.now() + delay
        elif isinstance(delay, (float, int)):
            delay = self.now() + timedelta(seconds=delay)
        elif delay is None:
            delay = self.now()
        if asyncio.iscoroutinefunction(coroutine_or_func):
            coroutine_or_func = coroutine_or_func(delay, *args)
        elif not asyncio.iscoroutine(coroutine_or_func):
            coroutine_or_func = wrap_as_coroutine(coroutine_or_func, delay, *args)  # type: ignore
        self.scheduled_coroutines.append((delay, coroutine_or_func))
        self.scheduled_coroutines.sort(key=lambda x: x[0])

    async def run(self) -> None:
        awaiting_coroutines: Dict[asyncio.Task, Coroutine] = {}
        self.virtual_time = self.start_time
        while awaiting_coroutines or self.scheduled_coroutines or self.ready_coroutines:
            next_due_time = self.scheduled_coroutines[0][0] if self.scheduled_coroutines else None
            if next_due_time:
                # move virtual time forward if in the past
                if next_due_time and next_due_time < datetime.now():
                    self.virtual_time = max(self.virtual_time, next_due_time)
                else:
                    self.virtual_time = datetime.now()
            while self.scheduled_coroutines and self.scheduled_coroutines[0][0] <= self.virtual_time:
                self.ready_coroutines.append(self.scheduled_coroutines.pop(0)[1])
            if not self.ready_coroutines:
                with self.update_virtual_time():
                    if awaiting_coroutines:
                        timeout = (next_due_time - datetime.now()).total_seconds() if next_due_time else None
                        done, _pending = await asyncio.wait(
                            list(awaiting_coroutines), timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                        )
                        for future in done:
                            self.ready_coroutines.append(awaiting_coroutines.pop(future))
                    elif next_due_time:
                        await asyncio.sleep((next_due_time - datetime.now()).total_seconds())
            for coroutine in self.ready_coroutines:
                with self.update_virtual_time():
                    try:
                        result = coroutine.send(None)
                    except StopIteration:
                        continue
                    else:
                        if isinstance(result, Future):
                            self.scheduled_coroutines.append((result.due_time, coroutine))
                            self.scheduled_coroutines.sort(key=lambda x: x[0])
                        else:
                            awaiting_coroutines[result] = coroutine
            self.ready_coroutines.clear()


processor: Processor = None  # type: ignore


async def sleep(delay) -> None:
    """
    Sleep for a given delay.
    :param delay: Delay in seconds.
    :return: None
    """
    if isinstance(delay, timedelta):
        delay = processor.now() + delay
    elif isinstance(delay, (float, int)):
        delay = processor.now() + timedelta(seconds=delay)
    await Future(delay)


def now() -> datetime:
    """
    Get the current virtual time.
    :return: Current virtual time.
    """
    return processor.now()


def call_later(
    delay: Union[float, timedelta, datetime, None], coroutine_or_func: Union[Coroutine, Callable], *args: Any
) -> None:
    """
    Call a function after a delay.
    :param delay: Delay in seconds.
    :param func: Function to call.
    :param args: Arguments to pass to the function.
    :return: None
    """
    processor.call_later(delay, coroutine_or_func, *args)


async def timer(
    step: timedelta, callback: Callable, start_time: datetime, end_time: Union[datetime, timedelta, None] = None
) -> None:
    if isinstance(end_time, timedelta):
        end_time = start_time + end_time
    await sleep(start_time)
    while True:
        await sleep(step.total_seconds())
        call_later(None, callback)
        if end_time and processor.now() >= end_time:
            break


def call_method(
    callback: Callable,
    unpack_args,
    unpack_kwargs,
) -> Callable:
    def result(event_time, value):
        if unpack_args:
            return callback(event_time, *value)
        elif unpack_kwargs:
            return callback(event_time, **value)
        else:
            return callback(event_time, value)

    return result


async def process_stream(
    callback: Union[Callable[..., None], Callable[..., Awaitable]],
    past: Iterable[Tuple[datetime, Any]] = [],
    future: Optional[AsyncIterable] = None,
    on_start: Optional[Callable[[], None]] = None,
    on_live_start: Optional[Callable[[], None]] = None,
    unpack_args: bool = False,
    unpack_kwargs: bool = False,
):
    wrapped_callback = call_method(callback, unpack_args, unpack_kwargs)
    if not asyncio.iscoroutinefunction(callback):
        original_callback = wrapped_callback

        async def wrapped_callback(event_time, value):
            original_callback(event_time, value)

    if on_start:
        on_start()
    for event_time, value in past:
        await sleep(event_time)
        await wrapped_callback(event_time, value)
    if on_live_start:
        on_live_start()
    if future:
        async for event_time, value in future:
            await wrapped_callback(event_time, value)


async def run(coroutines: List[Coroutine[Any, Any, Any]], start_time: Optional[datetime] = None) -> None:
    """
    Run the processor with the given coroutines.
    :param coroutines: List of coroutines to run.
    :param start_time: Start time for the processor.
    :return: None
    """
    global processor
    processor = Processor(coroutines, start_time or datetime.now())
    return await processor.run()
