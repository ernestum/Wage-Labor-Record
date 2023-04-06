import json
import os
from datetime import timedelta
from typing import Generator, Optional, Set, Tuple

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GObject


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

        # notify of derived duration property change
        self.connect("notify::start-time", self._notify_duration)
        self.connect("notify::end-time", self._notify_duration)

    def _notify_duration(self, *args):
        self.notify("duration")

    @GObject.Property(type=object)
    def duration(self) -> timedelta:
        return timedelta(microseconds=self.end_time.difference(self.start_time))

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
                    self.add_worked_time(WorkedTime.fromdict(d), save=False)
        self._sort_by_start_time()  # just to be sure

    def _sort_by_start_time(self):
        def compare_start_times(a: WorkedTime, b: WorkedTime):
            # Note: GLib.DateTime.compare() is not available in Python apparently
            return a.start_time.to_unix() - b.start_time.to_unix()

        self.sort(compare_start_times)

    def get_subset(
            self,
            tasks: Optional[Set[str]] = None,
            clients: Optional[Set[str]] = None,
            start_time: Optional[GLib.DateTime] = None,
            end_time: Optional[GLib.DateTime] = None) -> Gio.ListStore:
        list_store = Gio.ListStore(item_type=WorkedTime)

        def populate_list_store():
            list_store.remove_all()
            for wt in self:
                if start_time is not None and wt.start_time.to_unix() < start_time.to_unix():
                    continue
                if end_time is not None and wt.start_time.to_unix() > end_time.to_unix():
                    continue
                if tasks is not None and wt.task not in tasks:
                    continue
                if clients is not None and wt.client not in clients:
                    continue
                list_store.append(wt)

        self.connect("items-changed", lambda *_args: populate_list_store())

        populate_list_store()
        return list_store


    def save(self, *_args):
        print("Saving to", self._filename)
        with open(self._filename, "w") as f:
            json.dump([wt.asdict() for wt in self], f, indent=2)

    def add_worked_time(self, worked_time: WorkedTime, save: bool = True):
        worked_time.connect("notify", self.save)
        self.append(worked_time)
        if save:
            self.save()

    def all_clients(self) -> Gtk.ListStore:
        clients = Gtk.ListStore(str)

        def fill_clients(*_args):
            clients.clear()
            for client in self._all_clients():
                clients.append([client])

        fill_clients()
        self.connect("items-changed", fill_clients)
        return clients

    def _all_clients(self) -> set:
        return {wt.client for wt in self}

    def all_tasks(self) -> Gtk.ListStore:
        tasks = Gtk.ListStore(str)

        def fill_tasks(*_args):
            tasks.clear()
            for task in self._all_tasks():
                tasks.append([task])

        fill_tasks()
        self.connect("items-changed", fill_tasks)
        return tasks

    def _all_tasks(self) -> set:
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