import dataclasses
import datetime
import logging
import os.path
import sys
import time
import warnings
from typing import Generator, Iterable, List, Optional, Set, Tuple

import jsonpickle as jsonpickle
import gi

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gio, GLib, GObject, XApp

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(THIS_DIR, "resources")

logging.basicConfig(level=logging.DEBUG)


def get_idle_time():
    # TODO: maybe this is a better way to do idle time detection:
    #  https://stackoverflow.com/questions/217157/how-can-i-determine-the-display-idle-time-from-python-in-windows-linux-and-mac
    if sys.platform=="win32":
        import ctypes
        return ctypes.windll.user32.GetLastInputInfo() / 1000
    elif sys.platform=="linux":
        import subprocess
        return int(subprocess.check_output(["xprintidle"])) / 1000
    else:
        warnings.warn(f"No idle time detection for platform {sys.platform}")
        return 0


def link_gtk_menu_item_to_gio_action(menu_item: Gtk.MenuItem, action: Gio.SimpleAction, parameter: Optional[GLib.Variant] = None):
    """
    Links a Gtk.MenuItem to a Gio.SimpleAction.
    This is an ugly hack needed because Gtk.MenuItem does not support Gio.SimpleAction.
    However, we can't use Gio.Menu because it does not support Xapp.StatusIcon.
    And we need Xapp.StatusIcon because it is supported by awesome-wm as opposed to Gtk.StatusIcon.
    """
    menu_item.connect("activate", lambda _0: action.activate(parameter))
    menu_item.set_sensitive(action.get_enabled())
    action.connect("notify::enabled", lambda _0, _1: menu_item.set_sensitive(action.get_enabled()))


@dataclasses.dataclass
class WorkedTime:
    start_time: float
    end_time: float
    task: str
    client: str

    def duration(self) -> float:
        return self.end_time - self.start_time


class WorkedTimeStore:
    def __init__(self, filename: str):
        self._filename = filename
        self._worked_times: List[WorkedTime] = []
        self.load()

    def load(self):
        if os.path.exists(self._filename):
            with open(self._filename, "r") as f:
                self._worked_times = jsonpickle.decode(f.read())

    def save(self):
        with open(self._filename, "w") as f:
            f.write(jsonpickle.encode(self._worked_times, indent=2))

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


class TrackingState(GObject.GObject):
    start_time = GObject.Property(type=float, default=-1)
    task = GObject.Property(type=str, default="")
    client = GObject.Property(type=str, default="")

    def __init__(self):
        GObject.GObject.__init__(self)

    def is_tracking(self) -> bool:
        return self.start_time >= 0

    def is_client_and_task_set(self) -> bool:
        return self.client != "" and self.task != ""


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
            self._tracking_state.start_time,
            time.time(),
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


def make_completer(items: Iterable[str]):
    model = Gtk.ListStore(str)
    for item in items:
        model.append([item])
    completer = Gtk.EntryCompletion(
        model=model,
        inline_completion=True,
        inline_selection=True,
        popup_completion=False,
        minimum_key_length=0,
    )
    # we cant set it in the constructor, otherwise the
    # completions are not properly rendered
    completer.set_text_column(0)
    return completer


class TimeTrackerWindow(Gtk.Dialog):
    def __init__(self, tracking_state: TrackingState, worked_time_store: WorkedTimeStore, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Layout
        box = self.get_content_area()

        self.task_entry = Gtk.Entry(
            placeholder_text="Task",
            completion=make_completer(worked_time_store.all_tasks()),
        )
        self.task_entry.show()
        box.add(self.task_entry)

        self.client_entry = Gtk.Entry(
            placeholder_text="Client",
            completion=make_completer(worked_time_store.all_clients()),
        )
        self.client_entry.show()
        box.add(self.client_entry)

        self.action_bar = Gtk.ActionBar()
        self.action_bar.show()
        box.add(self.action_bar)

        # Green Start Button
        self.start_tracking_button = Gtk.Button(label="Start")
        self.start_tracking_button.show()
        self.start_tracking_button.set_action_name("app.start_tracking")
        self.action_bar.pack_start(self.start_tracking_button)
        self.start_tracking_button.get_style_context().add_class("suggested-action")

        # Red Stop Button
        self.stop_tracking_button = Gtk.Button(label="Stop")
        self.stop_tracking_button.show()
        self.stop_tracking_button.set_action_name("app.stop_tracking")
        self.action_bar.pack_start(self.stop_tracking_button)
        self.stop_tracking_button.get_style_context().add_class("destructive-action")

        # Abort Button
        self.abort_tracking_button = Gtk.Button(label="Abort")
        self.abort_tracking_button.show()
        self.abort_tracking_button.set_action_name("app.abort_tracking")
        self.action_bar.pack_start(self.abort_tracking_button)

        self.elapsed_time_label = Gtk.Label(label="")
        self.elapsed_time_label.show()
        box.add(self.elapsed_time_label)

        # Ensure the entry fields edit the action properties
        self.task_entry.bind_property("text", tracking_state, "task", GObject.BindingFlags.BIDIRECTIONAL)
        self.client_entry.bind_property("text", tracking_state, "client", GObject.BindingFlags.BIDIRECTIONAL)

        # When the tracking is active, repeatedly update the elapsed time label
        def _update_elapsed_time_label():
            if tracking_state.is_tracking():
                self.elapsed_time_label.set_text(
                    str(datetime.timedelta(seconds=int(time.time() - tracking_state.start_time)))
                )
            return tracking_state.is_tracking()

        def _setup_elapsed_time_label_updates(*_):
            self.elapsed_time_label.set_text(str(datetime.timedelta(seconds=0)))
            if tracking_state.is_tracking():
                GLib.timeout_add(1000, _update_elapsed_time_label)

        tracking_state.connect("notify::start-time", _setup_elapsed_time_label_updates)


class TimeTrackerTrayIcon(XApp.StatusIcon):
    def __init__(self, tracking_state: TrackingState, worked_time_store: WorkedTimeStore, application: Gtk.Application):
        super().__init__()
        self.set_name("Time Tracker")

        def _update_tooltip(*_):
            task = tracking_state.task
            client = tracking_state.client
            is_tracking = tracking_state.is_tracking()

            tooltip_text = (
                    ("Working\n" if is_tracking else "Not working\n") +
                    (f"On: {task}\n" if task != "" else "") +
                    (f"For: {client}\n" if client != "" else "")
            ).strip()
            self.set_tooltip_text(tooltip_text)

        _update_tooltip()
        tracking_state.connect("notify::start-time", _update_tooltip)
        tracking_state.connect("notify::task", _update_tooltip)
        tracking_state.connect("notify::client", _update_tooltip)

        start_tracking_action = application.lookup_action("start_tracking")
        start_tracking_task_action = application.lookup_action("start_tracking_task")
        stop_tracking_action = application.lookup_action("stop_tracking")
        abort_tracking_action = application.lookup_action("abort_tracking")

        def on_left_click(*_):
            logging.debug("Left click")
            if start_tracking_action.get_enabled():
                start_tracking_action.activate()
            elif stop_tracking_action.get_enabled():
                stop_tracking_action.activate()
            else:
                application.activate()

        self.connect("activate", on_left_click)

        def _update_icon(*_):
            logging.debug("Update icon")
            if start_tracking_action.get_enabled():
                self.set_icon_name(os.path.join(RESOURCES_DIR, "start-tracking.svg"))
            elif stop_tracking_action.get_enabled():
                self.set_icon_name(os.path.join(RESOURCES_DIR, "stop-tracking.svg"))
            else:
                self.set_icon_name(os.path.join(RESOURCES_DIR, "stop-tracking-disabled.svg"))

        _update_icon()
        start_tracking_action.connect("notify::enabled", _update_icon)
        stop_tracking_action.connect("notify::enabled", _update_icon)

        # Add menu to the tray icon
        def _update_menu(*_):
            # NOTE: This is not the most efficient way to do this, but it works for now
            menu = Gtk.Menu()

            # CLIENT ----------------------------
            client_item = Gtk.MenuItem(label="")

            def _update_client_menu_item(*_):
                client = tracking_state.client
                client_item.set_label("Set Client" if client == "" else f"Client: {client}")

            _update_client_menu_item()
            tracking_state.connect("notify::client", _update_client_menu_item)
            client_item.connect("activate", lambda _0: application.activate())
            menu.append(client_item)

            # TASK ----------------------------
            task_item = Gtk.MenuItem(label="")

            def _update_task_menu_item(*_):
                task = tracking_state.task
                task_item.set_label("Set Task" if task=="" else f"Task: {task}")

            _update_task_menu_item()
            tracking_state.connect("notify::task", _update_task_menu_item)
            task_item.connect("activate", lambda _0: application.activate())
            menu.append(task_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # WORKED ITEMS -------------------------
            for task, client in worked_time_store.most_recent_worked_tasks_and_clients(5):

                worked_time_item = Gtk.MenuItem(label=f"\u25B6 {client} - {task}")
                worked_time_item.client = client
                worked_time_item.task = task

                link_gtk_menu_item_to_gio_action(worked_time_item, start_tracking_task_action, GLib.Variant("(ss)", (client, task)))
                menu.append(worked_time_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # ABORT ----------------------------
            abort_item = Gtk.MenuItem(label="Abort")
            link_gtk_menu_item_to_gio_action(abort_item, abort_tracking_action)
            menu.append(abort_item)

            # QUIT ----------------------------
            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", lambda _0: application.quit())
            menu.append(quit_item)

            menu.show_all()
            self.set_secondary_menu(menu)

        _update_menu()

        stop_tracking_action.connect("worked-time", _update_menu)


class TimerTrackerApplication(Gtk.Application):

    def __init__(self):
        super().__init__(
            register_session=True,
            application_id="net.ernestum.simple_time_tracker",
        )

        self.tracking_state = tracking_state = TrackingState()
        self.start_tracking_action = start_tracking_action = StartTrackingAction(tracking_state)
        self.start_tracking_task_action = start_tracking_task_action = SetCurrentTaskAction(tracking_state)
        self.stop_tracking_action = stop_tracking_action = StopTrackingAction(tracking_state)
        self.abort_tracking_action = abort_tracking_action = AbortTrackingAction(tracking_state)
        self.add_action(start_tracking_action)
        self.add_action(start_tracking_task_action)
        self.add_action(stop_tracking_action)
        self.add_action(abort_tracking_action)

        self.worked_time_store = worked_time_store = WorkedTimeStore("my_times.json")

        stop_tracking_action.connect("worked-time", lambda _, worked_time: worked_time_store.add_worked_time(worked_time))
        self.tray_icon = TimeTrackerTrayIcon(tracking_state, worked_time_store, self)

    def do_activate(self):
        self.hold()  # Keep the application running until we explicitly quit
        self.show_window()

    def show_window(self):
        if len(self.get_windows())==0:
            TimeTrackerWindow(
                tracking_state=self.tracking_state,
                worked_time_store=self.worked_time_store,
                application=self, title="Time Tracker").present()

    def on_quit(self, action, param):
        self.worked_time_store.save()
        self.quit()


if __name__=="__main__":
    app = TimerTrackerApplication()
    app.run(sys.argv)
