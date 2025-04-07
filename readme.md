Async Stream Processing (ASP) is a nested event loop providing ad hoc functionalities for event streams processing. Event streams can be either timestamped data or real time data arriving asynchronously. ASP allows past data to be processed in an accelerated yet consistent manner, moving clocks and timers consistenly. This is particuarly useful to simulate a given strategy against past events, test temporal aspects of a system, hot reload a past dependent system, etc.

## Processing past events

Past event streams are passed as regular iterators over timestamped values, ie: (datetime, value) tuples. They are mapped to callbacks in the example below example.  

We introduce a couple of auxilliary methods in order to keep examples short.

- *NAMES*: contains a few example first names.

- *timestamp*: turns a value iterator into a timestamped values iterator.

- *log*: displays two elasped times before messages. The first one is the actual elapsed time, computed by substracting *datetime.now*. The second one is the ASP (virtual) elapsed time, computed by substracting *asp.now*.


```python
import asyncio
from datetime import datetime, timedelta

from common import NAMES, log, timestamp

import asp
from asp import EventStreamDefinition


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, name):
        if name not in self.greeted:
            log(f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(f"Hello again {name}!")


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    asyncio.run(
        asp.run(
            [EventStreamDefinition(callback=greeter.greet, past_events_iter=past_queue)]
        )
    )


if __name__ == "__main__":
    main()
```
```
0.00 seconds, 0.00 seconds: Hello Jane.
0.00 seconds, 1.00 seconds: Hello John.
0.00 seconds, 1.00 seconds: Hello Sarah.
0.00 seconds, 1.00 seconds: Hello Paul.
0.00 seconds, 1.00 seconds: Hello again Jane!
```
We used the following two elements of the ASP API.

- *asp.run* is the main entry point. It runs a nested event loop that will handle events and manage callback executions within asyncio.

- *EventStreamDefinition* describes event streams and their associated processing.

One will notice that past events are processed immediately one after the other even though ASP time goes by consistenly with *past_queue* timestamps.

In this example we pass only one event stream for simplicity sake, but one can pass as many as needed.


## Processing real time events

Real time events are passed as asynchronous iterators which can also be mapped to callbacks.

```python
def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet, future_events_iter=live_queue
                )
            ]
        )
    )
```

```
0.00 seconds, 0.00 seconds: Hello Jane.
1.00 seconds, 1.00 seconds: Hello John.
1.00 seconds, 1.00 seconds: Hello Sarah.
1.00 seconds, 1.00 seconds: Hello Paul.
1.00 seconds, 1.00 seconds: Hello again Jane!
```
One can now see that we are now procesing events in real time, that is, actual and virtual times are identical (pun intented).

## Travelling through time 

One can also combine the two previous examples to initialize a past dependant system.

```python
def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet,
                    past_events_iter=past_queue,
                    future_events_iter=live_queue,
                )
            ],
            on_live_start=lambda: print("** Running live **"),
        )
    )
```
```
0.00 seconds, 0.00 seconds: Hello Jane.
0.00 seconds, 1.00 seconds: Hello John.
** Running live **
0.00 seconds, 59.00 seconds: Hello Sarah.
1.00 seconds, 1.00 seconds: Hello Paul.
1.00 seconds, 1.00 seconds: Hello again Jane!
```

Note also that after virtual time catches up with actual time they become consistent with each other.

## Scheduling callbacks

 ASP allows to schedule callbacks at a later time as shown in the below example.

```python
class Greeter:
    ...
    def greet_later(self, name):
        log(f"{name} arrived.")
        asp.call_later(1, self.greet, name)


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.greet_later,
                    past_events_iter=past_queue,
                    future_events_iter=live_queue,
                )
            ],
            on_live_start=lambda: print("** Running live **"),
        )
    )
```
This will produce the following output.

```
0 seconds, 0.00 seconds: Jane arrived.
0.00 seconds, 1.00 seconds: John arrived.
0.00 seconds, 0.00 seconds: Hello Jane.
0.00 seconds, 1.00 seconds: Hello John.
** Running live **
0.00 seconds, 58.00 seconds: Sarah arrived.
1.00 seconds, 1.00 seconds: Hello Sarah.
0.00 seconds, 0.00 seconds: Paul arrived.
1.00 seconds, 1.00 seconds: Hello Paul.
0.00 seconds, 0.00 seconds: Jane arrived.
1.00 seconds, 1.00 seconds: Hello again Jane!
```

One can can see that we fast forwarded events while maintaining the expected chronology.

## Sleeping

Callbacks passed to ASP can be either regular methods or coroutine. ASP provides a *sleep* method that can also be fast forwarded as shown below. 

```python
class Greeter:
    ...
    async def slow_greet(self, name):
        log(f"{name} arrived.")
        await asp.sleep(1)
        self.greet(name)


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
    live_queue = create_async_generator(NAMES[2:], delay=1)
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    callback=greeter.slow_greet,
                    past_events_iter=past_queue,
                    future_events_iter=live_queue,
                )
            ],
            on_live_start=lambda: print("** Running live **"),
        )
    )
```

```
0 seconds, 0.00 seconds: Jane arrived.
0.00 seconds, 1.00 seconds: Hello Jane.
0.00 seconds, 0.00 seconds: John arrived.
0.00 seconds, 1.00 seconds: Hello John.
** Running live **
0.00 seconds, 58.00 seconds: Sarah arrived.
1.00 seconds, 1.00 seconds: Hello Sarah.
0.00 seconds, 0.00 seconds: Paul arrived.
1.00 seconds, 1.00 seconds: Hello Paul.
0.00 seconds, 0.00 seconds: Jane arrived.
1.00 seconds, 1.00 seconds: Hello again Jane!
```
One can see once again the correct chronology of events being displayed. 


