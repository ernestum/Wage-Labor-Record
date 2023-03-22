from datetime import datetime, timedelta
import dataclasses
import json
import os
from typing import Generator, Iterable, Tuple

import gi

from wage_labor_record.utils import filter_duplicate_items

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


@dataclasses.dataclass
class WorkedTime:
    start_time: datetime
    end_time: datetime
    task: str
    client: str

    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    def asdict(self) -> dict:
        d = dataclasses.asdict(self)
        d["start_time"] = self.start_time.isoformat()
        d["end_time"] = self.end_time.isoformat()
        return d

    def __post_init__(self):
        if isinstance(self.start_time, str):
            self.start_time = datetime.fromisoformat(self.start_time)
        if isinstance(self.end_time, str):
            self.end_time = datetime.fromisoformat(self.end_time)


class WorkedTimeStore(Gtk.ListStore):

    COLUMN_TASK = 0
    COLUMN_CLIENT = 1
    COLUMN_START_TIME = 2
    COLUMN_END_TIME = 3

    def __init__(self, filename: str):
        super().__init__(str, str, GLib.DateTime, GLib.DateTime)
        self._filename = filename

        def sort_func(model, a, b, _):
            start_a = model[a][WorkedTimeStore.COLUMN_START_TIME].to_unix()
            start_b = model[b][WorkedTimeStore.COLUMN_START_TIME].to_unix()
            return start_a - start_b

        self.set_sort_func(WorkedTimeStore.COLUMN_START_TIME, sort_func, None)
        self.set_sort_column_id(WorkedTimeStore.COLUMN_START_TIME, Gtk.SortType.DESCENDING)

        self.load()

    def load(self):
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                for d in json.load(f):
                    self.add_worked_time(WorkedTime(**d))

    def save(self):
        with open(self._filename, "w") as f:
            json.dump([wt.asdict() for wt in self.worked_times()], f, indent=2)

    def add_worked_time(self, worked_time: WorkedTime):
        start_time = GLib.DateTime.new_from_unix_local(worked_time.start_time.timestamp())
        end_time = GLib.DateTime.new_from_unix_local(worked_time.end_time.timestamp())
        self.append([worked_time.task, worked_time.client, start_time, end_time])
        self.save()

    def worked_times(self) -> Iterable[WorkedTime]:
        for row in self:
            yield WorkedTime(
                start_time=datetime.fromtimestamp(row[2].to_unix()),
                end_time=datetime.fromtimestamp(row[3].to_unix()),
                task=row[0],
                client=row[1],
            )

    def all_clients(self) -> Gtk.TreeModelFilter:
        filter = self.filter_new()
        filter.set_visible_func(filter_duplicate_items, (WorkedTimeStore.COLUMN_CLIENT, set()))
        return filter

    def all_tasks(self) -> Gtk.TreeModelFilter:
        filter = self.filter_new()
        filter.set_visible_func(filter_duplicate_items, (WorkedTimeStore.COLUMN_TASK, set()))
        return filter

    def most_recent_worked_tasks_and_clients(self, n: int) -> Generator[Tuple[str, str], None, None]:
        """
        Yields the most recent n task-client-tuples.
        If a task-client-tuple is worked on multiple times, it is only yielded once.

        :param n: The number of task-client-tuples to yield (at most)
        :return: A generator yielding the most recent n task-client-tuples.
        """
        work_items = set()
        for row in self:
            work_item = (row[WorkedTimeStore.COLUMN_TASK], row[WorkedTimeStore.COLUMN_CLIENT])
            if work_item not in work_items:
                work_items.add(work_item)
                yield work_item
            if len(work_items) >= n:
                break