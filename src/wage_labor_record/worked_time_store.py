import json
import logging
import os
from datetime import timedelta
from typing import Callable, Generator, Optional, Set, Tuple

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
    clients_changed = GObject.Signal("clients-changed")
    tasks_changed = GObject.Signal("tasks-changed")
    item_added = GObject.Signal("item-added", arg_types=(WorkedTime,))
    item_removed = GObject.Signal("item-removed", arg_types=(WorkedTime,))

    def __init__(self, filename: str):
        GObject.GObject.__init__(self)
        Gio.ListStore.__init__(self, item_type=WorkedTime)
        self._filename = filename
        self._clients = set()
        self._tasks = set()
        self.clients = Gtk.ListStore(str)
        self.tasks = Gtk.ListStore(str)

        # Load from file
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                for d in json.load(f):
                    self.append(WorkedTime.fromdict(d), suppress_signals=True)
        self._sort_by_start_time()  # just to be sure
        self._refresh_tasks()
        self._refresh_clients()

        # Only start saving when new items are added after the initial load
        self.connect("item-added", self.save)

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

        def is_in_subset(wt: WorkedTime):
            if start_time is not None and wt.start_time.to_unix() < start_time.to_unix():
                return False
            if end_time is not None and wt.start_time.to_unix() > end_time.to_unix():
                return False
            if tasks is not None and wt.task not in tasks:
                return False
            if clients is not None and wt.client not in clients:
                return False
            return True

        for wt in self:
            if is_in_subset(wt):
                list_store.append(wt)

        def _on_item_added(_wt_store, added_item):
            if is_in_subset(added_item):
                list_store.append(added_item)

        def _on_item_removed(_wt_store, removed_item):
            if is_in_subset(removed_item):
                found, position = list_store.find(removed_item)
                if found:
                    list_store.remove(position)
                else:
                    logging.error(f"Could not find item {removed_item} in subset")

        # TODO: if an item in the subset is changed, it should be removed if it no longer matches the subset
        # TODO: if an item outside the subset is changed, it should be added if it now matches the subset

        self.connect("item-added", _on_item_added)
        self.connect("item-removed", _on_item_removed)

        return list_store

    def save(self, *_args):
        logging.info(f"Saving worked time store to {self._filename}")
        with open(self._filename, "w") as f:
            json.dump([wt.asdict() for wt in self], f, indent=2)

    def insert(self, position: int, item: WorkedTime):
        super().insert(position, item)
        self._connect_item_to_signals(item)
        self.emit("item-added", item)

    def append(self, item: WorkedTime, suppress_signals: bool = False):
        super().append(item)
        self._connect_item_to_signals(item)
        if not suppress_signals:
            self.emit("item-added", item)

    def insert_sorted(self, item: WorkedTime, compare_func: Callable[[WorkedTime, WorkedTime], int], *user_data):
        raise NotImplementedError("Not implemented yet")

    def remove_item(self, item: WorkedTime):
        found, position = self.find(item)
        if found:
            self.remove(position)
        else:
            raise ValueError(f"Item not found: {item}")

    def remove(self, position: int):
        item = self[position]
        super().remove(position)
        self.emit("item-removed", item)

    def remove_all(self):
        for i in range(len(self)):
            self.remove(0)

    def _connect_item_to_signals(self, item: WorkedTime):
        item.connect("notify::client", self._refresh_clients)
        item.connect("notify::task", self._refresh_tasks)
        # Save to disk when item was changed
        item.connect("notify", self.save)

    def _refresh_clients(self, *_args):
        new_clients = {wt.client for wt in self}
        if new_clients != self._clients:
            added_clients = new_clients - self._clients
            removed_clients = self._clients - new_clients
            for client in added_clients:
                self.clients.append([client])
            for client in removed_clients:
                for row in self.clients:
                    if row[0] == client:
                        self.clients.remove(row.iter)

            self._clients = new_clients
            self.emit("clients-changed")

    def _refresh_tasks(self, *_args):
        new_tasks = {wt.task for wt in self}
        if new_tasks != self._tasks:
            added_tasks = new_tasks - self._tasks
            removed_tasks = self._tasks - new_tasks
            for task in added_tasks:
                self.tasks.append([task])
            for task in removed_tasks:
                for row in self.tasks:
                    if row[0] == task:
                        self.tasks.remove(row.iter)

            self._tasks = new_tasks
            self.emit("tasks-changed")

    def most_recent_worked_tasks_and_clients(self, n: int) -> Generator[Tuple[str, str], None, None]:
        """
        Yields the most recent n task-client-tuples.
        If a task-client-tuple is worked on multiple times, it is only yielded once.

        :param n: The number of task-client-tuples to yield (at most)
        :return: A generator yielding the most recent n task-client-tuples.
        """
        work_items = set()
        for worked_time in reversed(self):
            work_item = (worked_time.task, worked_time.client)
            if work_item not in work_items:
                work_items.add(work_item)
                yield work_item
            if len(work_items) >= n:
                break