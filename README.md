[![Coverage](https://codecov.io/gh/pytek-io/async-stream-processing/branch/main/graph/badge.svg)](https://codecov.io/gh/pytek-io/async-stream-processing)
[![CI](https://github.com/pytek-io/async-stream-processing/actions/workflows/ci.yml/badge.svg)](https://github.com/pytek-io/async-stream-processing/actions)

Async Stream Processing (ASP) is a nested event loop providing ad hoc functionalities for event streams processing. Event streams can be either timestamped data or real time data arriving asynchronously. ASP allows past data to be processed in an accelerated yet consistent manner, moving clocks consistently. This is particularly useful to simulate a given strategy against past events, test temporal aspects of a system, hot reload a past dependent system, etc.

## Processing past events

Past event streams are passed as regular iterators over timestamped values, ie: (datetime, value) tuples. They are mapped to callbacks as shown in the below example.

```python
import asyncio
from datetime import datetime, timedelta

import async_stream_processing as asp

NAMES = ["Jane", "John", "Sarah", "Paul", "Jane"]


def format(event_time: datetime):
    return f"{event_time:%H:%M:%S.%f}"


def log(event_time: datetime, msg: str):
    print(f"{format(datetime.now())} {format(asp.now())} {format(event_time)} {msg}")


def timestamps(start: datetime, delay: timedelta):
    current_time = start
    while True:
        yield current_time
        current_time += delay


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, event_time: datetime, name: str):
        if name not in self.greeted:
            log(event_time, f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(event_time, f"Hello again {name}!")


def main():
    greeter = Greeter()
    start_time = datetime(2025, 1, 1)
    past_queue = zip(timestamps(start_time, timedelta(seconds=1)), NAMES)
    asyncio.run(asp.run([asp.process_stream(callback=greeter.greet, past=past_queue)], start_time))


if __name__ == "__main__":
    main()
```
```
11:29:10.551628 00:00:00.000029 00:00:00.000000 Hello Jane.
11:29:10.551717 00:00:01.000012 00:00:01.000000 Hello John.
11:29:10.551756 00:00:02.000010 00:00:02.000000 Hello Sarah.
11:29:10.551792 00:00:03.000009 00:00:03.000000 Hello Paul.
11:29:10.551825 00:00:04.000009 00:00:04.000000 Hello again Jane!
```
We used the following two elements of the ASP API.

- *asp.run* creates a nested event loop that will execute the coroutines passed as arguments.

- *process_stream* associate a callback to a stream of events.

One will notice that past events are processed immediately one after the other even though ASP time goes by consistently with *past_queue* timestamps. It is also worth noticing that callbacks always receive the event time as first argument. It should be used instead of *asp.now*  when the state of the system depends on the event time to the maximum precision. It can also be used to detect any significant lag when processing events.

In this example we pass only one event stream for simplicity sake, but one can pass as many as needed.

## Processing real time events

Real time events are passed as asynchronous iterators as follows.

We use *create_async_generator* auxiliary method to create a simple asynchronous generator.

```python
async def create_async_generator(values, delay=1):
    for value in values:
        yield datetime.now(), value
        await asyncio.sleep(delay)


def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run([asp.process_stream(callback=greeter.greet, future=live_queue)])
    )

```

```
21:45:58.681452 21:45:58.681449 21:45:58.681439 Hello Jane.
21:45:59.682751 21:45:59.682726 21:45:59.682746 Hello John.
21:46:00.683986 21:46:00.683925 21:46:00.683981 Hello Sarah.
21:46:01.685234 21:46:01.685148 21:46:01.685225 Hello Paul.
21:46:02.685783 21:46:02.685665 21:46:02.685777 Hello again Jane!
```

One can now see that we are now processing events in real time, that is, actual and virtual times are identical.

## Traveling through time

One can also combine the two previous examples to initialize a past dependant system.

```python
    greeter = Greeter()
    start_time = datetime.now() - timedelta(seconds=60)
    past_queue = zip(timestamps(start_time, delay=timedelta(seconds=1)), NAMES[:2])
    live_queue = create_async_generator(NAMES[:2], delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.greet,
                    past=past_queue,
                    future=live_queue,
                    on_live_start=lambda: print("** Running live **"),
                )
            ],
        )
    )
```
```
21:50:14.256495 21:50:14.256488 21:49:14.256207 Hello Jane.
21:50:14.256566 21:50:14.256538 21:49:15.256207 Hello John.
** Running live **
21:50:14.256597 21:50:14.256567 21:50:14.256594 Hello again Jane!
21:50:15.258243 21:50:15.258194 21:50:15.258234 Hello again John!
```

Note also that after virtual time catches up with actual time they become consistent with each other.

## Scheduling callbacks

 ASP allows to schedule callbacks at a later time as shown in the below example.

```python
class Greeter:
    ...
    def greet_later(self, event_time: datetime, name):
        log(event_time, f"{name} arrived.")
        asp.call_later(event_time + timedelta(seconds=1), self.greet, name)


def main():
    greeter = Greeter()
    past_queue = zip(timestamps(datetime.now() - timedelta(seconds=60), delay=timedelta(seconds=1)), NAMES[:2])
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.greet_later,
                    past=past_queue,
                    future=live_queue,
                    on_live_start=lambda: print("** Running live **"),
                )
            ],
        )
    )
```
This will produce the following output.

```
11:32:57.851073 11:32:57.851034 11:31:57.850495 Jane arrived.
11:32:57.851282 11:32:57.851229 11:31:58.850495 Hello Jane.
11:32:57.851454 11:32:57.851352 11:31:58.850495 John arrived.
** Running live **
11:32:57.851553 11:32:57.851446 11:32:57.851547 Sarah arrived.
11:32:57.851698 11:32:57.851554 11:31:59.850495 Hello John.
11:32:58.852932 11:32:58.852944 11:32:58.852923 Paul arrived.
11:32:58.853187 11:32:58.853147 11:32:58.851547 Hello Sarah.
11:32:59.854094 11:32:59.854092 11:32:59.854089 Jane arrived.
11:32:59.854210 11:32:59.854182 11:32:59.852923 Hello Paul.
11:33:00.856018 11:33:00.856005 11:33:00.854089 Hello again Jane!
```

One can see that we fast forwarded events while maintaining the expected chronology. Callbacks can be either regular methods or coroutines.

## Pausing execution

ASP provides a *sleep* method that can also be fast forwarded as shown below.

```python
class Greeter:
    ...
    async def sleep_and_greet(self, event_time: datetime, name):
        log(event_time, f"{name} arrived.")
        delay = timedelta(seconds=5)
        await asp.sleep(delay)
        self.greet(event_time + delay, name)


def main():
    greeter = Greeter()
    past_queue = zip(
        timestamps(datetime.now() - timedelta(seconds=60), delay=timedelta(seconds=1)),
        NAMES[:2],
    )
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                asp.process_stream(
                    callback=greeter.sleep_and_greet,
                    on_live_start=lambda: print("** Running live **"),
                    past=past_queue,
                    future=live_queue,
                )
            ],
        )
    )
```

```
11:38:33.836334 11:38:33.836326 11:37:33.836047 Jane arrived.
11:38:38.837079 11:38:38.837051 11:37:38.836047 Hello Jane.
11:38:38.837302 11:38:38.837213 11:37:34.836047 John arrived.
11:38:43.838395 11:38:43.838429 11:37:39.836047 Hello John.
** Running live **
11:38:43.838540 11:38:43.838513 11:38:43.838536 Sarah arrived.
11:38:48.840379 11:38:48.840366 11:38:48.838536 Hello Sarah.
11:38:49.841773 11:38:49.841686 11:38:49.841769 Paul arrived.
11:38:54.842878 11:38:54.842890 11:38:54.841769 Hello Paul.
11:38:55.844117 11:38:55.844082 11:38:55.844114 Jane arrived.
11:39:00.846036 11:39:00.845992 11:39:00.844114 Hello again Jane!
```
One can see once again the correct chronology of events being displayed.

## Executing arbitrary coroutines

While ASP is primarily designed to process event streams, it can execute any arbitrary coroutines just like *asyncio* *run* method. In the example below we use the *timer* method which invokes a method on a regular basis.

```python
async def say_hello():
    log(asp.now(), "sleeping for 1 second")
    await asp.sleep(1)
    log(asp.now(), "hello")


def main():
    asyncio.run(
        asp.run(
            [
                asp.timer(
                    timedelta(seconds=1),
                    say_hello,
                    start_time=datetime.now() - timedelta(seconds=60),
                    end_time=timedelta(seconds=5),
                )
            ],
        )
    )
```

This will produce the output below.
```
11:41:57.997942 11:41:57.997946 11:41:57.997909 sleeping for 1 second
11:41:58.999123 11:41:58.999116 11:41:58.999091 hello
```
