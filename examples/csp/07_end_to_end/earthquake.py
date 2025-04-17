from dataclasses import dataclass
from datetime import datetime
from obspy import read_events
import asp
from asp import EventStreamDefinition
import asyncio

url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.quakeml"


@dataclass
class EventData:
    time: datetime
    longitude: float
    latitude: float
    magnitude: float


@dataclass
class Monitor:
    last_event_time_pushed: datetime = None

    def fetch_eartquake_data(self):
        catalog = read_events(url, format="QUAKEML")
        events = sorted(catalog.events, key=lambda event: event.origins[0].time)
        if self.last_event_time_pushed:
            events = (
                event
                for event in events
                if event.origins[0].time.datetime >= self.last_event_time_pushed
            )
        for event in events:
            yield (
                event.origins[0].time.datetime,
                EventData(
                    time=event.origins[0].time.datetime,
                    longitude=event.origins[0].longitude,
                    latitude=event.origins[0].latitude,
                    magnitude=event.magnitudes[0].mag,
                ),
            )
        self.last_event_time_pushed = asp.now()

    async def update_earth_quake_data(self):
        while True:
            await asyncio.sleep(5)
            print("Updating data...")
            for _, event in self.fetch_eartquake_data():
                yield event


def main():
    monitor = Monitor()
    asyncio.run(
        asp.run(
            [
                EventStreamDefinition(
                    # past_events_iter=monitor.fetch_eartquake_data(),
                    callback=print,
                    future_events_iter=monitor.update_earth_quake_data(),
                )
            ],
        )
    )


if __name__ == "__main__":
    main()
