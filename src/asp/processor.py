from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, List, Optional, Tuple, Iterator
from contextlib import contextmanager

current_processor: Processor

EMPTY_ITERATOR = iter(())


def evaluate_coroutine(coroutine: Coroutine):
    try:
        future = coroutine.send(None)
    except StopIteration:
        return False
    if isinstance(future, Future):
        current_processor.call_later(future.delay, evaluate_coroutine, coroutine)
    else:
        current_processor.awaiting_event_streams[future] = evaluate_coroutine, coroutine
    return True


@dataclass
class ScheduledCallback:
    timestamp: datetime
    callback: Callable
    args: Tuple

    def __call__(self):
        result = self.callback(*self.args)
        if asyncio.iscoroutine(result):
            evaluate_coroutine(result)


@dataclass
class EventStreamDefinition:
    callback: Callable
    past_events_iter: Iterator[Any] = EMPTY_ITERATOR
    future_events_iter: Optional[AsyncIterator[Any]] = None
    unpack_args: bool = False
    unpack_kwargs: bool = False


@dataclass
class BackgroundTaskDefinition:
    callback: Callable


@dataclass
class Future:
    delay: float

    def __await__(self):
        yield self


class EventStream:
    def __init__(
        self,
        processor: Processor,
        index: int,
        callback,
        past_events_iter: Optional[AsyncIterator[Any]] = None,
        future_events_iter: Optional[AsyncIterator[Any]] = None,
        unpack_args: bool = False,
        unpack_kwargs: bool = False,
    ):
        self.processor: Processor = processor
        self._priority: int = index
        self.callback: Callable[[Any], None] = callback
        self.past_events_iter = past_events_iter
        self.future_event_stream = future_events_iter
        self._next_event_value: Any = None
        self.sleeping = False
        self.pending_events: List[Tuple[datetime, Any]] = []
        self.exhausted_live_values = False
        self.iterating_past_values = True
        self.pending_events_buffer: List[Tuple[datetime, Any]] = []
        self.unpack_args = unpack_args
        self.unpack_kwargs = unpack_kwargs

    def priority(self):
        return self._priority

    def is_done(self):
        return (
            not self.iterating_past_values
            and self.exhausted_live_values
            and not self.pending_events
            and not self.sleeping
            and not self.pending_events_buffer
        )

    def execute_coroutine(self, coroutine: Coroutine):
        try:
            future = coroutine.send(None)
            self.sleeping = True
            if isinstance(future, Future):
                self.processor.call_later(future.delay, self.execute_coroutine, coroutine)
            else:
                self.processor.awaiting_event_streams[future] = self.execute_coroutine, coroutine
        except StopIteration:
            self.sleeping = False

    def evaluate_callback(self, value):
        if self.unpack_args:
            result = self.callback(*value)
        elif self.unpack_kwargs:
            result = self.callback(**value)
        else:
            result = self.callback(value)
        if asyncio.iscoroutine(result):
            self.execute_coroutine(result)

    def process_next_scheduled_event(self):
        _, value = self.pending_events.pop(0)
        self.evaluate_callback(value)

    def start(self):
        if not (self.past_events_iter or self.future_event_stream):
            self.iterating_past_values = False
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

    def fast_forwarding(self):
        return any([self.iterating_past_values, self.pending_events, self.sleeping])

    def iterate_through_past_events(self, start_time: Optional[datetime], end_time: Optional[datetime]):
        if self.past_events_iter and not self.pending_events:
            try:
                while True:
                    timestamp, value = next(self.past_events_iter)
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp >= end_time:
                        raise StopIteration
                    self.pending_events.append((timestamp, value))
            except StopIteration:
                self.iterating_past_values = False

    async def handle_live_events(self):
        if self.future_event_stream:
            async for value in self.future_event_stream:
                if self.processor.live:
                    self.pending_events.append((datetime.now(), value))
                    self.processor.new_data_arrived.set()
                else:
                    self.pending_events_buffer.append((datetime.now(), value))
        self.processor.new_data_arrived.set()
        self.exhausted_live_values = True


class Processor:
    def __init__(self):
        self.live_callback: Optional[Callable] = None
        self.actual_time = datetime.now()
        self.virtual_time = datetime.min
        self.awaiting_event_streams: Dict[asyncio.Future, Tuple[EventStream, Coroutine]] = {}
        self.live = False
        self.scheduled_callbacks: List[ScheduledCallback] = []
        self.new_data_arrived: asyncio.Event

    async def run(
        self,
        callbacks_map: List[tuple[Callable, Any, Any]],
        background_tasks: Optional[List[BackgroundTaskDefinition]] = None,
        on_live_start: Optional[Callable] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        on_start: Optional[Callable] = None,
    ):
        self.live_callback = on_live_start
        self.new_data_arrived = asyncio.Event()
        wating_for_new_data_task = asyncio.create_task(self.new_data_arrived.wait())
        event_streams = [
            EventStream(self, index, **definition.__dict__)
            for index, definition in enumerate(chain(callbacks_map, background_tasks or []))
        ]
        _tasks = [asyncio.create_task(event_stream.handle_live_events()) for event_stream in event_streams]
        active_event_streams: List[EventStream] = event_streams
        if on_start:
            if start_time:
                self.virtual_time = start_time
            with self.update_virtual_time():
                on_start()
        for event_stream in event_streams:
            event_stream.start()
        while True:
            active_event_streams: List[EventStream] = [
                event_stream for event_stream in active_event_streams if not event_stream.is_done()
            ]
            if not (active_event_streams or self.scheduled_callbacks):
                break
            if not self.live:
                for event_stream in active_event_streams:
                    event_stream.iterate_through_past_events(start_time, end_time)
                if not (any(map(EventStream.fast_forwarding, active_event_streams)) or self.scheduled_callbacks):
                    self.live = True
                    for event_stream in active_event_streams:
                        event_stream.pending_events.extend(event_stream.pending_events_buffer)
                        event_stream.pending_events_buffer.clear()
                    if self.live_callback:
                        self.live_callback()
                    self.actual_time = self.virtual_time = datetime.now()
            next_scheduled_events = list(filter(None, map(EventStream.next_scheduled_event, active_event_streams)))
            if self.scheduled_callbacks:
                next_scheduled_events.append((self.scheduled_callbacks[0].timestamp, self.call_next_scheduled_callback))
            next_event_time = min(next_scheduled_events, key=lambda x: x[0], default=(None, None))[0]
            if self.awaiting_event_streams or not next_event_time or next_event_time > datetime.now():
                timeout = None
                if next_event_time and self.virtual_time:
                    timeout = max(
                        0, (next_event_time - (datetime.now() if self.live else self.virtual_time)).total_seconds()
                    )
                with self.update_virtual_time():
                    done, _ = await asyncio.wait(
                        chain((wating_for_new_data_task,), self.awaiting_event_streams),
                        timeout=timeout,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                if wating_for_new_data_task in done:
                    done.remove(wating_for_new_data_task)
                    self.new_data_arrived.clear()
                    wating_for_new_data_task = asyncio.create_task(self.new_data_arrived.wait())
                for event_stream, coroutine in sorted(
                    map(self.awaiting_event_streams.pop, done), key=lambda x: x[0].priority()
                ):
                    with self.update_virtual_time():
                        event_stream(coroutine)
            if next_event_time and next_event_time < datetime.now():
                for event_time, callback in next_scheduled_events:
                    if event_time == next_event_time:
                        if not self.live and self.virtual_time < event_time:
                            self.actual_time = datetime.now()
                            self.virtual_time = event_time
                        with self.update_virtual_time():
                            callback()
        wating_for_new_data_task.cancel()

    @contextmanager
    def update_virtual_time(self):
        if self.live:
            yield
            return
        start = datetime.now()
        yield
        now = datetime.now()
        self.virtual_time += now - start
        self.actual_time = now

    def call_next_scheduled_callback(self):
        self.scheduled_callbacks.pop(0)()

    def now(self) -> datetime:
        return datetime.now() if self.live else self.virtual_time + (datetime.now() - self.actual_time)

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
    Get the current time. This is the virtual time if the processor is not live.
    :return: Current time.
    """
    return current_processor.now()


def increase_virtual_time(delta: timedelta):
    """
    Increase the virtual time by a given delta, to be used for testing puposes.
    :param
    delta: Time delta to increase the virtual time."
    :return: None
    """
    current_processor.increase_virtual_time(delta)


def run(
    callbacks_map: List[tuple[Callable, Any, Any]],
    background_tasks: Optional[List[BackgroundTaskDefinition]] = None,
    on_live_start: Optional[Callable] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    on_start: Optional[Callable] = None,
):
    """
    Run the processor with the given callbacks map.
    :param callbacks_map: List of EventStreamDefinition objects.
    :param on_live_start: Callback function to be called when the processor starts running live.
    :param start_time: Start time for the past events.
    :param end_time: End time for the past events.
    :return: Awaitable object.
    """
    global current_processor
    current_processor = Processor()
    return current_processor.run(callbacks_map, background_tasks, on_live_start, start_time, end_time, on_start)
