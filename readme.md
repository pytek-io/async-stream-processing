Async Stream Processing (ASP) is a nested event loop providing ad hoc functionalities for event streams processing. Event streams can be either timestamped data or real time data arriving asynchronously. ASP allows past data to be processed in an accelerated yet consistent manner, moving clocks consistently. This is particularly useful to simulate a given strategy against past events, test temporal aspects of a system, hot reload a past dependent system, etc.

## Processing past events

Past event streams are passed as regular iterators over timestamped values, ie: (datetime, value) tuples. They are mapped to callbacks in the example below example.  

We introduce a couple of auxiliary methods in order to keep examples short.

- *NAMES*: contains a few example first names.

- *timestamp*: turns a value iterator into a timestamped values iterator.

- *log*: displays two elapsed times before messages. The first one is the actual elapsed time, computed by subtracting *datetime.now*. The second one is the ASP (virtual) elapsed time, computed by subtracting *asp.now*.


```python
import asyncio
from datetime import datetime, timedelta

import asp

from common import NAMES, log, timestamp


class Greeter:
    def __init__(self):
        self.greeted = set()

    def greet(self, _timestamp: datetime, name):
        if name not in self.greeted:
            log(f"Hello {name}.")
            self.greeted.add(name)
        else:
            log(f"Hello again {name}!")


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES, datetime.now() - timedelta(seconds=60), delay=1)
    asyncio.run(
        asp.run([asp.process_stream(callback=greeter.greet, past=past_queue)])
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

- *asp.run* creates a nested event loop that will execute the coroutines passed as arguments.

- *process_stream* associate a callback to a stream of events.

One will notice that past events are processed immediately one after the other even though ASP time goes by consistently with *past_queue* timestamps.

In this example we pass only one event stream for simplicity sake, but one can pass as many as needed.


## Processing real time events

Real time events are passed as asynchronous iterators as follows.

We use *create_async_generator* auxiliary method to create a simple asynchronous generator.

```python
def main():
    greeter = Greeter()
    live_queue = create_async_generator(NAMES, delay=1)
    asyncio.run(
        asp.run([asp.process_stream(callback=greeter.greet, future=live_queue)])
    )
```

```
0.00 seconds, 0.00 seconds: Hello Jane.
1.00 seconds, 1.00 seconds: Hello John.
1.00 seconds, 1.00 seconds: Hello Sarah.
1.00 seconds, 1.00 seconds: Hello Paul.
1.00 seconds, 1.00 seconds: Hello again Jane!
```

One can now see that we are now processing events in real time, that is, actual and virtual times are identical.

## Traveling through time 

One can also combine the two previous examples to initialize a past dependant system.

```python
def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
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
    def greet_later(self, _timestamp: datetime, name):
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
                    events=past_queue,
                    events=live_queue,
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

One can can see that we fast forwarded events while maintaining the expected chronology. Callbacks can be either regular methods or coroutines.

## Pausing execution

ASP provides a *sleep* method that can also be fast forwarded as shown below. 

```python
class Greeter:
    ...
    async def sleep_and_greet(self, name):
        log(f"{name} arrived.")
        await asp.sleep(5)
        self.greet(name)


def main():
    greeter = Greeter()
    past_queue = timestamp(NAMES[:2], datetime.now() - timedelta(seconds=60), delay=1)
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

## Executing arbitrary coroutines

While ASP is primarily designed to process event streams, it can execute any arbitrary coroutines just like *asyncio* *run* method. In the example below we use the *timer* method which invokes a method on a regular basis.

```python
async def say_hello():
    log("sleeping for 1 second")
    await asp.sleep(1)
    log("hello")


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
0.00 seconds, 0.00 seconds: sleeping for 1 second
0.00 seconds, 1.00 seconds: sleeping for 1 second
0.00 seconds, 0.00 seconds: hello
0.00 seconds, 1.00 seconds: sleeping for 1 second
0.00 seconds, 0.00 seconds: hello
0.00 seconds, 1.00 seconds: sleeping for 1 second
0.00 seconds, 0.00 seconds: hello
0.00 seconds, 1.00 seconds: sleeping for 1 second
0.00 seconds, 0.00 seconds: hello
0.00 seconds, 1.00 seconds: hello
```
