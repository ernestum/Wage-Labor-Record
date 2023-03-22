from datetime import datetime, timedelta
import dataclasses
import json
import os
from typing import Generator, Iterable, List, Set, Tuple


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


class WorkedTimeStore:
    def __init__(self, filename: str):
        self._filename = filename
        self._worked_times: List[WorkedTime] = []
        self.load()

    def load(self):
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                self._worked_times = [WorkedTime(**d) for d in json.load(f)]

    def save(self):
        with open(self._filename, "w") as f:
            json.dump([wt.asdict() for wt in self._worked_times], f, indent=2)

    def add_worked_time(self, worked_time: WorkedTime):
        self._worked_times.append(worked_time)
        self.save()

    def worked_times(self) -> Iterable[WorkedTime]:
        return self._worked_times

    def all_clients(self) -> Set[str]:
        return {wt.client for wt in self._worked_times}

    def all_tasks(self) -> Set[str]:
        return {wt.task for wt in self._worked_times}

    def most_recent_worked_tasks_and_clients(self, n: int) -> Generator[Tuple[str, str], None, None]:
        """
        Yields the most recent n task-client-tuples.
        If a task-client-tuple is worked on multiple times, it is only yielded once.

        :param n: The number of task-client-tuples to yield (at most)
        :return: A generator yielding the most recent n task-client-tuples.
        """
        work_items = set()
        for worked_time in reversed(self.worked_times()):
            work_item = (worked_time.task, worked_time.client)
            if work_item not in work_items:
                work_items.add(work_item)
                yield work_item
            if len(work_items) >= n:
                break