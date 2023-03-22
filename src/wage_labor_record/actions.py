import datetime
import logging
import time

import gi

from wage_labor_record.tracked_time_store import WorkedTime

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gio, GLib, GObject

from wage_labor_record.tracking_state import TrackingState


class AbortTrackingAction(Gio.SimpleAction):
    def __init__(self, tracking_state: TrackingState):
        super().__init__(name="abort_tracking", parameter_type=None, state=None)
        self._tracking_state = tracking_state
        self.connect("activate", self._abort_tracking)
        tracking_state.connect("notify::start-time", self._update_enabled_state)
        self._update_enabled_state()

    def _abort_tracking(self, *_args):
        self._tracking_state.start_time = -1

        logging.debug("Abort tracking")

    def _update_enabled_state(self, *_args):
        self.set_enabled(self._tracking_state.is_tracking())
        if self.get_enabled():
            logging.debug("Abort tracking enabled")
        else:
            logging.debug("Abort tracking disabled")


class StopTrackingAction(Gio.SimpleAction):
    worked_time = GObject.Signal("worked-time", arg_types=[GObject.TYPE_PYOBJECT])

    def __init__(self, tracking_state: TrackingState):
        super().__init__(name="stop_tracking", parameter_type=None, state=None)
        self._tracking_state = tracking_state
        self.connect("activate", self._stop_tracking)
        tracking_state.connect("notify", self._update_enabled_state)
        self._update_enabled_state()

    def _stop_tracking(self, *_args):
        assert self.get_enabled()
        assert self._tracking_state.start_time >= 0
        assert self._tracking_state.task != ""
        assert self._tracking_state.client != ""

        self.emit("worked-time", WorkedTime(
            datetime.datetime.fromtimestamp(self._tracking_state.start_time),
            datetime.datetime.now(),
            self._tracking_state.task,
            self._tracking_state.client
        ))

        self._tracking_state.start_time = -1

        logging.debug("Stop tracking")

    def _update_enabled_state(self, *_args):
        self.set_enabled(self._tracking_state.is_client_and_task_set() and self._tracking_state.is_tracking())
        if self.get_enabled():
            logging.debug("Stop tracking enabled")
        else:
            logging.debug("Stop tracking disabled")


class SetCurrentTaskAction(Gio.SimpleAction):
    """
    Action to set the current task and start tracking it.
    Can only be used if the current task is not set, or we are currently not tracking any task.
    """
    def __init__(self, tracking_state: TrackingState):
        super().__init__(name="start_tracking_task", parameter_type=GLib.VariantType("(ss)"), state=None)
        self._tracking_state = tracking_state
        self.connect("activate", self._start_tracking_task)
        tracking_state.connect("notify", self._update_enabled_state)
        self._update_enabled_state()

    def _start_tracking_task(self, _action, parameter):
        client, task = parameter
        self._tracking_state.task = task
        self._tracking_state.client = client
        if not self._tracking_state.is_tracking():
            self._tracking_state.start_time = time.time()
        logging.debug(f"Start tracking task {self._tracking_state.task}")

    def _update_enabled_state(self, *_args):
        self.set_enabled(not self._tracking_state.is_tracking() or not self._tracking_state.is_client_and_task_set())

        if self.get_enabled():
            logging.debug("Start tracking task enabled")
        else:
            logging.debug("Start tracking task disabled")


class StartTrackingAction(Gio.SimpleAction):
    def __init__(self, tracking_state: TrackingState):
        super().__init__(name="start_tracking", parameter_type=None, state=None)
        self._tracking_state = tracking_state
        self.connect("activate", self._start_tracking)
        tracking_state.connect("notify::start-time", self._update_enabled_state)
        self._update_enabled_state()

    def _start_tracking(self, *_args):
        self._tracking_state.start_time = time.time()
        logging.debug("Start tracking")

    def _update_enabled_state(self, *_args):
        self.set_enabled(not self._tracking_state.is_tracking())
        if self.get_enabled():
            logging.debug("Start tracking enabled")
        else:
            logging.debug("Start tracking disabled")