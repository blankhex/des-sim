from __future__ import annotations
from dataclasses import dataclass
import heapq
import random


@dataclass
class Event:
    timestamp: int

    def __lt__(self, other: Event):
        return self.timestamp < other.timestamp

    def process(self, queue: EventQueue):
        del queue


@dataclass
class EventQueue:
    def __init__(self):
        self.heap: list[Event] = []
        self.timestamp: int = 0

    def add_event(self, event: Event):
        heapq.heappush(self.heap, event)

    def process_event(self) -> Event | None:
        if len(self.heap) == 0:
            return None

        event = heapq.heappop(self.heap)
        self.timestamp = event.timestamp
        event.process(self)
        return event


def event_timestamp(now: int, rate: float, delay: int = 0) -> int:
    if rate:
        return now + int(random.expovariate(rate) * 1_000_000) + delay
    else:
        return now + delay
