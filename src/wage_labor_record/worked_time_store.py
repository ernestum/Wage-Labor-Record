from datetime import datetime, timedelta
import dataclasses
import json
import os
from typing import Generator, Tuple

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject


class WorkedTime(GObject.GObject):
    task = GObject.Property(type=str, default="")
    client = GObject.Property(type=str, default="")
    start_time = GObject.Property(type=GLib.DateTime, default=None)
    end_time = GObject.Property(type=GLib.DateTime, default=None)

    def __init__(self,  task: str, client: str, start_time: GLib.DateTime, end_time: GLib.DateTime):
        GObject.GObject.__init__(self)
        self.task = task
        self.client = client
        self.start_time = start_time
        self.end_time = end_time

    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    def asdict(self) -> dict:
        return dict(
            start_time=self.start_time.format_iso8601(),
            end_time=self.end_time.format_iso8601(),
            task=self.task,
            client=self.client,
        )

    @classmethod
    def fromdict(cls, d: dict) -> "WorkedTime":
        tz = GLib.TimeZone.new_local()
        return cls(
            start_time=GLib.DateTime.new_from_iso8601(d["start_time"], tz),
            end_time=GLib.DateTime.new_from_iso8601(d["end_time"], tz),
            task=d["task"],
            client=d["client"],
        )

    def is_done(self) -> bool:
        return self.end_time is not None

    def is_started(self) -> bool:
        return self.start_time is not None


class WorkedTimeStore(Gio.ListStore):

    def __init__(self, filename: str):
        super().__init__(item_type=WorkedTime)
        self._filename = filename
        self.load()

    def load(self):
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                for d in json.load(f):
                    self.add_worked_time(WorkedTime.fromdict(d))
        self._sort_by_start_time()  # just to be sure

    def _sort_by_start_time(self):
        def compare_start_times(a: WorkedTime, b: WorkedTime):
            # Note: GLib.DateTime.compare() is not available in Python apparently
            return a.start_time.to_unix() - b.start_time.to_unix()

        self.sort(compare_start_times)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start is not None and not isinstance(item.start, GLib.DateTime):
                raise TypeError("start must be a GLib.DateTime")
            if item.stop is not None and not isinstance(item.stop, GLib.DateTime):
                raise TypeError("stop must be a GLib.DateTime")

            list_store = Gio.ListStore(item_type=WorkedTime)

            def populate_list_store():
                list_store.remove_all()
                for wt in self:
                    if item.start is not None and wt.start_time.to_unix() < item.start.to_unix():
                        continue
                    if item.stop is not None and wt.start_time.to_unix() > item.stop.to_unix():
                        continue
                    list_store.append(wt)

            self.connect("items-changed", lambda *_args: populate_list_store())

            populate_list_store()
            return list_store

        return self.get_item(item)

    def save(self, *_args):
        with open(self._filename, "w") as f:
            json.dump([wt.asdict() for wt in self], f, indent=2)

    def add_worked_time(self, worked_time: WorkedTime):
        worked_time.connect("notify", self.save)
        self.append(worked_time)

    def all_clients(self) -> set:
        return {wt.client for wt in self}

    def all_tasks(self) -> set:
        return {wt.task for wt in self}

    def most_recent_worked_tasks_and_clients(self, n: int) -> Generator[Tuple[str, str], None, None]:
        """
        Yields the most recent n task-client-tuples.
        If a task-client-tuple is worked on multiple times, it is only yielded once.

        :param n: The number of task-client-tuples to yield (at most)
        :return: A generator yielding the most recent n task-client-tuples.
        """
        work_items = set()
        for worked_time in self:
            work_item = (worked_time.task, worked_time.client)
            if work_item not in work_items:
                work_items.add(work_item)
                yield work_item
            if len(work_items) >= n:
                break