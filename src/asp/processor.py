from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, Iterable, Iterator, List, Optional, Tuple
from functools import wraps

current_processor: Processor = None  # type: ignore

EMPTY_ITERATOR = iter(())


@dataclass
class ScheduledCallback:
    timestamp: datetime
    callback: Callable
    args: Tuple

    def __call__(self):
        result = self.callback(*self.args)
        if asyncio.iscoroutine(result):
            current_processor.evaluate_coroutine(result)


@dataclass
class EventStreamDefinition:
    callback: Callable
    future_events_iter: Optional[AsyncIterator[Any]] = None
    unpack_args: bool = False
    unpack_kwargs: bool = False


@dataclass
class Future:
    delay: float

    def __await__(self):
        yield self


def wrap_async_callback(event_stream: EventStream, callback: Callable):
    @wraps(callback)
    async def wrapped_callback(*args, **kwargs):
        event_stream.sleeping = True
        await callback(*args, **kwargs)
        event_stream.sleeping = False

    return wrapped_callback


class EventStream:
    def __init__(
        self,
        processor: Processor,
        index: int,
        callback: Callable,
        future_events_iter: Optional[AsyncIterator[Any]] = None,
        unpack_args: bool = False,
        unpack_kwargs: bool = False,
    ):
        self.processor: Processor = processor
        self._priority: int = index
        self.callback = wrap_async_callback(self, callback) if asyncio.iscoroutinefunction(callback) else callback
        self.future_event_stream = future_events_iter
        self._next_event_value: Any = None
        self.sleeping = False
        self.pending_events: List[Tuple[datetime, Any]] = []
        self.exhausted_live_values = False
        self.pending_events_buffer: List[Tuple[datetime, Any]] = []
        self.unpack_args = unpack_args
        self.unpack_kwargs = unpack_kwargs
        self.ready_for_next_event = asyncio.Event()
        self.ready_for_next_event.set()

    def priority(self):
        return self._priority

    def is_done(self):
        r = self.exhausted_live_values and not self.pending_events and not self.sleeping
        if r:
            print(f"Event stream {self._priority} is done")
        return r
    
    def evaluate_callback(self, value):
        if self.unpack_args:
            result = self.callback(*value)
        elif self.unpack_kwargs:
            result = self.callback(**value)
        else:
            result = self.callback(value)
        if asyncio.iscoroutine(result):
            self.processor.evaluate_coroutine(result)

    def process_next_scheduled_event(self):
        _, value = self.pending_events.pop(0)
        self.ready_for_next_event.set()
        self.evaluate_callback(value)

    def start(self):
        if not self.future_event_stream:
            self.unpack_args = True
            self.evaluate_callback(())

    def next_scheduled_event(self):
        next_event_time, callback = None, None
        if not self.sleeping and self.pending_events:
            next_event_time, callback = self.pending_events[0][0], self.process_next_scheduled_event
        if next_event_time:
            return next_event_time, callback

    def done(self):
        return not any([self.pending_events, self.sleeping])

    async def handle_live_events(self):
        if self.future_event_stream:
            async for timestamp, value in self.future_event_stream:
                self.pending_events.append((timestamp, value))
                self.processor.new_data_arrived.set()
                await self.ready_for_next_event.wait()
                self.ready_for_next_event.clear()

        self.processor.new_data_arrived.set()
        self.exhausted_live_values = True


class Processor:
    def __init__(self):
        self.actual_time = datetime.now()
        self.virtual_time = datetime.min
        self.live = True
        self.scheduled_callbacks: List[ScheduledCallback] = []
        self.new_data_arrived: asyncio.Event
        self.event_streams: List[EventStream] = []
        self.tasks: List[asyncio.Task] = []
        self.awaiting_coroutines: Dict[asyncio.Future, Coroutine] = {}

    def evaluate_coroutine(self, coroutine: Coroutine):
        try:
            future = coroutine.send(None)
        except StopIteration:
            return False
        if isinstance(future, Future):
            current_processor.call_later(future.delay, self.evaluate_coroutine, coroutine)
        else:
            current_processor.awaiting_coroutines[future] = coroutine
        return True

    def add_event_stream(self, definition: EventStreamDefinition):
        event_stream = EventStream(self, len(self.event_streams), **definition.__dict__)
        self.event_streams.append(event_stream)
        event_stream.start()
        self.tasks.append(asyncio.create_task(event_stream.handle_live_events()))

    async def run(
        self,
        callbacks_map: List[EventStreamDefinition] = [],
        background_tasks: List[Coroutine] = [],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        on_start: Optional[Callable] = None,
    ):
        if start_time:
            self.virtual_time = start_time
        self.new_data_arrived = asyncio.Event()
        waiting_for_new_data_task = asyncio.create_task(self.new_data_arrived.wait())
        for event_stream_definition in callbacks_map:
            self.add_event_stream(event_stream_definition)
        for coroutine in background_tasks:
            self.evaluate_coroutine(coroutine)
        active_event_streams: List[EventStream] = self.event_streams
        if on_start:
            with self.update_virtual_time():
                on_start()
        for event_stream in self.event_streams:
            event_stream.start()
        while not end_time or self.now() < end_time:
            active_event_streams: List[EventStream] = [
                event_stream for event_stream in self.event_streams if not event_stream.is_done()
            ]
            if not (active_event_streams or self.scheduled_callbacks):
                break
            next_scheduled_events = list(filter(None, map(EventStream.next_scheduled_event, active_event_streams)))
            if self.scheduled_callbacks:
                next_scheduled_events.append((self.scheduled_callbacks[0].timestamp, self.call_next_scheduled_callback))
            next_event_time = min(next_scheduled_events, key=lambda x: x[0], default=(None, None))[0]
            if not next_event_time or self.awaiting_coroutines:
                timeout = None
                if next_event_time and self.virtual_time:
                    timeout = max(0, (next_event_time - datetime.now()).total_seconds())
                with self.update_virtual_time():
                    done, _ = await asyncio.wait(
                        chain((waiting_for_new_data_task,), self.awaiting_coroutines),
                        timeout=timeout,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                if waiting_for_new_data_task in done:
                    done.remove(waiting_for_new_data_task)
                    self.new_data_arrived.clear()
                    waiting_for_new_data_task = asyncio.create_task(self.new_data_arrived.wait())
                for coroutine in map(self.awaiting_coroutines.pop, done):
                    with self.update_virtual_time():
                        self.evaluate_coroutine(coroutine)
            if next_event_time:
                for event_time, callback in next_scheduled_events:
                    if event_time == next_event_time:
                        with self.update_virtual_time(event_time):
                            callback()
        waiting_for_new_data_task.cancel()

    @contextmanager
    def update_virtual_time(self, event_time: datetime | None = None):
        if event_time is not None:
            self.virtual_time = event_time
        start = datetime.now()
        yield
        now = datetime.now()
        self.virtual_time += now - start
        self.actual_time = now

    def call_next_scheduled_callback(self):
        self.scheduled_callbacks.pop(0)()

    def now(self) -> datetime:
        return self.virtual_time + (datetime.now() - self.actual_time)

    def call_later(self, delay: float, callback: Callable, *args):
        self.scheduled_callbacks.append(ScheduledCallback(self.now() + timedelta(seconds=delay), callback, args))
        self.scheduled_callbacks.sort(key=lambda x: x.timestamp)

    def increase_virtual_time(self, delta: timedelta):
        self.virtual_time += delta


async def sleep(delay: float) -> None:
    """
    Sleep for a given delay.
    :param delay: Delay in seconds.
    :return: None
    """
    await Future(delay)


def call_later(delay: float, callback: Callable, *args):
    """
    Schedule a callback to be called after a delay.
    :param delay: Delay in seconds.
    :param callback: Callback function to be called.
    :param args: Arguments to be passed to the callback function.
    :return: None
    """
    current_processor.call_later(delay, callback, *args)


def now() -> datetime:
    """
    Get the current time.
    :return: Current time.
    """
    return current_processor.now()


def increase_virtual_time(delta: timedelta):
    """
    Increase the virtual time by a given delta, to be used for testing purposes.
    :param
    delta: Time delta to increase the virtual time."
    :return: None
    """
    current_processor.increase_virtual_time(delta)


def add_event_stream(
    event_stream: EventStreamDefinition,
):
    """
    Add an event stream to the processor.
    :param event_stream: Event stream to be added.
    :return: None
    """
    current_processor.add_event_stream(event_stream)


def run(
    callbacks_map: List[EventStreamDefinition] = [],
    background_tasks: List[Coroutine] = [],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    on_start: Optional[Callable] = None,
):
    """
    Run the processor with the given callbacks map.
    :param callbacks_map: List of EventStreamDefinition objects.
    :param start_time: Start time for the past events.
    :param end_time: End time for the past events.
    :return: Awaitable object.
    """
    global current_processor
    current_processor = Processor()
    return current_processor.run(callbacks_map, background_tasks, start_time, end_time, on_start)


async def timer(step: timedelta, callback: Callable):
    while True:
        await sleep(step.total_seconds())
        callback()
