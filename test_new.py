import asyncio
from datetime import datetime, timedelta
import asp
import humanize


last_time = datetime.now()


def log(msg):
    global last_time
    now = datetime.now()
    print(f"{humanize.precisedelta(now - last_time)}, {asp.now().strftime('%H:%M:%S.%f')[:-3]} {msg}")
    last_time = now


async def live_queue(names):
    for name in names:
        await asyncio.sleep(1)
        yield name


class Greeter:
    def say_hi_again(self, name):
        log(f"Hi {name}! Nice to see you again.")

    async def greet(self, name):
        log(f"Hello {name}.")
        asp.call_later(1.5, self.say_hi_again, name)
        await asp.sleep(1)
        log(f"Goodbye {name}.")


def main():
    start_time = datetime.now() - timedelta(seconds=60)
    past_queue = [(start_time + timedelta(seconds=i), name) for i, name in enumerate(["John", "Paul"])]
    test = Greeter()
    callbacks = [(test.greet, iter(past_queue), live_queue(["Jessica", "John!"]))]
    asyncio.run(asp.run(callbacks, on_live_start=lambda: print("** Running live **")))


if __name__ == "__main__":
    main()
