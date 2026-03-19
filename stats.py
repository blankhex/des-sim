from __future__ import annotations
from dataclasses import dataclass
import des
import matplotlib.pyplot as plt
import numpy as np


class StatCollector:
    @dataclass
    class Event(des.Event):
        collector: StatCollector

        def process(self, queue: des.EventQueue):
            self.collector.collect()
            new_event = StatCollector.Event(queue.timestamp +
                                            self.collector.time,
                                            self.collector)
            queue.add_event(new_event)

    def __init__(self, target: any, time: int):
        self.target = target
        self.time = time
        self.last_stats: dict = {}
        self.diff_stats: list[dict] = []
        self.timings: list[list[int]] = []

    def start(self, event_queue: des.EventQueue, delay: int = 0):
        next_timestamp = event_queue.timestamp + delay
        event_queue.add_event(StatCollector.Event(next_timestamp, self))

    def _collect_stats(self):
        if not hasattr(self.target, 'stat'):
            return

        new_diff: dict = {}
        for key, value in self.target.stat.items():
            if key in self.last_stats:
                value = self.target.stat[key] - self.last_stats[key]
                self.last_stats[key] = self.target.stat[key]
                new_diff[key] = value
            else:
                self.last_stats[key] = self.target.stat[key]
                continue
        if len(new_diff):
            self.diff_stats.append(new_diff)

    def _collect_timings(self):
        if not hasattr(self.target, 'timing'):
            return

        self.timings.append(self.target.timing.copy())
        self.target.timings = []

    def collect(self):
        self._collect_stats()
        self._collect_timings()

    def plot_stats(self,
                   keys: str | list[str],
                   ax: any = None,
                   title: str | None = None,
                   xlabel: str = "Time Interval",
                   ylabel: str = "Count per Interval",
                   figsize: tuple[int, int] = (10, 6)):
        if isinstance(keys, str):
            keys = [keys]

        valid_keys = [k for k in keys if any(k in s for s in self.diff_stats)]
        if not valid_keys:
            raise ValueError(f"Keys not found in stats: {set(keys) - set(valid_keys)}")

        # Use provided axis or create new one
        created_ax = False
        if ax is None:
            plt.figure(figsize=figsize)
            ax = plt.gca()
            created_ax = True

        x = np.arange(len(self.diff_stats))
        colors = plt.cm.tab10(np.linspace(0, 1, len(valid_keys)))

        for idx, key in enumerate(valid_keys):
            values = [s.get(key, 0) for s in self.diff_stats]
            ax.plot(x, values, label=key, color=colors[idx])

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title or f"Stat: {', '.join(valid_keys)} per Interval")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.grid(True, alpha=0.3)

        if created_ax:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_timings(self,
                     percentiles: tuple[float, ...] = (50.0, 90.0, 99.0),
                     ax: any = None,
                     title: str | None = None,
                     xlabel: str = "Time Interval",
                     ylabel: str = "Latency (seconds)",
                     figsize: tuple[int, int] = (10, 6)):
        if not self.timings:
            print("No timing data collected.")
            return ax if ax is not None else None

        created_ax = False
        if ax is None:
            plt.figure(figsize=figsize)
            ax = plt.gca()
            created_ax = True

        x = np.arange(len(self.timings))
        colors = plt.cm.plasma(np.linspace(0, 1, len(percentiles)))

        for pct_idx, pct in enumerate(percentiles):
            y_data = []
            for interval in self.timings:
                if len(interval) == 0:
                    y_data.append(0)
                else:
                    val = float(np.percentile(interval, pct)) / 1_000_000.0  # µs → s
                    y_data.append(val)
            ax.plot(x, y_data, label=f"P{pct}", color=colors[pct_idx], linewidth=2)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title or "Latency Percentiles Over Time")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                  title="Percentiles")
        ax.grid(True, alpha=0.3)

        if created_ax:
            plt.tight_layout()
            plt.show()

        return ax
