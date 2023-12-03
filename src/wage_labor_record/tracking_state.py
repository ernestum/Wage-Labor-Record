import datetime
import json
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GObject, GLib


class TrackingState(GObject.GObject):
    start_time = GObject.Property(type=GLib.DateTime, default=None)
    task = GObject.Property(type=str, default="")
    client = GObject.Property(type=str, default="")

    def __init__(self, filename: str):
        GObject.GObject.__init__(self)
        self._filename = filename
        self._load()
        self.connect("notify", self._save)

    def _load(self):
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                d = json.load(f)
                self.start_time = GLib.DateTime.new_from_iso8601(d["start_time"]) if d["start_time"] else None
                self.task = d["task"]
                self.client = d["client"]

    def _save(self, *_args):
        with open(self._filename, "w") as f:
            json.dump({
            "start_time": self.start_time.format_iso8601() if self.start_time else None,
            "task": self.task,
            "client": self.client,
        }, f, indent=2)

    def is_tracking(self) -> bool:
        return self.start_time is not None

    def is_client_and_task_set(self) -> bool:
        return self.client != "" and self.task != ""

    def elapsed_time(self) -> datetime.timedelta:
        if self.start_time is None:
            return datetime.timedelta()
        return datetime.timedelta(microseconds=GLib.DateTime.new_now_local().difference(self.start_time))
