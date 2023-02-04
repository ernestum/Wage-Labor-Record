import dataclasses
import datetime
import os.path
import sys
import time
import warnings
from typing import Generator, Iterable, List, Set, Tuple

import jsonpickle as jsonpickle
import gi

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gio, GLib, GObject, XApp

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(THIS_DIR, "resources")


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
        for worked_time in self.worked_times():
            work_item = (worked_time.task, worked_time.client)
            if work_item not in work_items:
                work_items.add(work_item)
                yield work_item
            if len(work_items) >= n:
                break



class TimeTrackingAction(Gio.SimpleAction):
    start_time = GObject.Property(type=float, default=-1)
    task = GObject.Property(type=str, default="")
    client = GObject.Property(type=str, default="")

    worked_time = GObject.Signal("worked-time", arg_types=(GObject.TYPE_PYOBJECT,))

    def __init__(self):
        super().__init__(name="time_tracking", parameter_type=None, state=GLib.Variant.new_boolean(False))

        self.connect("activate", self._toggle_tracking)
        self.connect("notify::state", lambda _0, _1: self._update_enabled_state())
        self.connect("notify::task", lambda _0, _1: self._update_enabled_state())
        self.connect("notify::client", lambda _0, _1: self._update_enabled_state())

    def _update_enabled_state(self):
        if self.get_state().get_boolean():
            self.set_enabled(self.get_property("task")!="" and self.get_property("client")!="")
        else:
            self.set_enabled(True)

    def start_timer(self):
        self.set_property("start_time", time.time())
        self.set_state(GLib.Variant.new_boolean(True))
        notification = Gio.Notification("Time Tracker")
        notification.set_body(f"Time tracking started\n:{self.get_property('client')} - {self.get_property('task')}")
        notification.send()

    def _stop_timer(self):
        assert self.get_property("start_time") >= 0
        assert self.get_property("task")!=""
        assert self.get_property("client")!=""

        self.emit("worked-time", WorkedTime(
            self.get_property("start_time"),
            time.time(),
            self.get_property("task"),
            self.get_property("client")
        ))

        self.set_property("start_time", -1)
        self.set_state(GLib.Variant.new_boolean(False))

    def _toggle_tracking(self, action, param):
        if self.get_state():
            self._stop_timer()
        else:
            self.start_timer()

    def abort_tracking(self):
        self.set_property("start_time", -1)
        self.set_state(GLib.Variant.new_boolean(False))


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
    def __init__(self, tracking_action: TimeTrackingAction, worked_time_store: WorkedTimeStore, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Layout
        box = self.get_content_area()
        # box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        # box.show()
        # self.add(box)

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

        self.tracking_button = Gtk.Button(label="Start")
        self.tracking_button.show()
        box.add(self.tracking_button)

        self.elapsed_time_label = Gtk.Label(label="")
        self.elapsed_time_label.show()
        box.add(self.elapsed_time_label)

        # Connect signals

        # Ensure the entry fields edit the action properties
        self.task_entry.bind_property("text", tracking_action, "task", GObject.BindingFlags.BIDIRECTIONAL)
        self.client_entry.bind_property("text", tracking_action, "client", GObject.BindingFlags.BIDIRECTIONAL)

        # Ensure the action is triggered by the switch
        self.tracking_button.connect("clicked", lambda _0: tracking_action.activate(None))
        tracking_action.connect("notify::state", lambda _0, _1: self.tracking_button.set_label("Stop" if tracking_action.get_state() else "Start"))

        # set background color of button according to state of action
        def _update_button_style():
            style_context = self.tracking_button.get_style_context()
            if tracking_action.get_state():
                style_context.remove_class("suggested-action")
                style_context.add_class("destructive-action")
            else:
                style_context.remove_class("destructive-action")
                style_context.add_class("suggested-action")

        _update_button_style()
        tracking_action.connect("notify::state", lambda _0, _1: _update_button_style())

        # Ensure the switch sensitivity is updated when the action state changes
        tracking_action.bind_property("enabled", self.tracking_button, "sensitive")

        # When the action is active, repeatedly update the elapsed time label
        def _update_elapsed_time_label():
            if tracking_action.get_state():
                self.elapsed_time_label.set_text(
                    str(datetime.timedelta(seconds=int(time.time() - tracking_action.get_property("start_time"))))
                )
            return tracking_action.get_state()

        def _setup_elapsed_time_label_updates():
            self.elapsed_time_label.set_text(str(datetime.timedelta(seconds=0)))
            if tracking_action.get_state():
                GLib.timeout_add(1000, _update_elapsed_time_label)

        tracking_action.connect("notify::state", lambda _0, state: _setup_elapsed_time_label_updates())


class TimeTrackerTrayIcon(XApp.StatusIcon):
    def __init__(self, tracking_action: TimeTrackingAction, worked_time_store: WorkedTimeStore, application: Gtk.Application):
        super().__init__()
        self.set_name("Time Tracker")

        def _update_tooltip(*_):
            task = tracking_action.get_property("task")
            client = tracking_action.get_property("client")
            state = tracking_action.get_state()

            tooltip_text = (
                    ("Working\n" if state else "Not working\n") +
                    (f"On: {task}\n" if task!="" else "") +
                    (f"For: {client}\n" if client!="" else "")
            ).strip()
            self.set_tooltip_text(tooltip_text)

        _update_tooltip()
        tracking_action.connect("notify::state", _update_tooltip)
        tracking_action.connect("notify::task", _update_tooltip)
        tracking_action.connect("notify::client", _update_tooltip)

        def on_left_click(*_):
            if tracking_action.get_enabled():
                tracking_action.activate()
            else:
                application.activate()

        self.connect("activate", on_left_click)

        def _update_icon(*_):
            if tracking_action.get_state():
                if tracking_action.get_enabled():
                    self.set_icon_name(os.path.join(RESOURCES_DIR, "stop-tracking.svg"))
                else:
                    self.set_icon_name(os.path.join(RESOURCES_DIR, "stop-tracking-disabled.svg"))
            else:
                self.set_icon_name(os.path.join(RESOURCES_DIR, "start-tracking.svg"))

        _update_icon(tracking_action.get_state())
        tracking_action.connect("notify::state", _update_icon)
        tracking_action.connect("notify::enabled", _update_icon)

        # Add menu to the tray icon
        def _update_menu(*_):
            # NOTE: This is not the most efficient way to do this, but it works for now
            menu = Gtk.Menu()

            # CLIENT ----------------------------
            client_item = Gtk.MenuItem(label="")

            def _update_client_menu_item(*_):
                client = tracking_action.get_property("client")
                client_item.set_label("Set Client" if client=="" else f"Client: {client}")

            _update_client_menu_item()
            tracking_action.connect("notify::client", _update_client_menu_item)
            client_item.connect("activate", lambda _0: application.activate())
            menu.append(client_item)

            # TASK ----------------------------
            task_item = Gtk.MenuItem(label="")

            def _update_task_menu_item(*_):
                task = tracking_action.get_property("task")
                task_item.set_label("Set Task" if task=="" else f"Task: {task}")

            _update_task_menu_item()
            tracking_action.connect("notify::task", _update_task_menu_item)
            task_item.connect("activate", lambda _0: application.activate())
            menu.append(task_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # WORKED ITEMS -------------------------
            for task, client in worked_time_store.most_recent_worked_tasks_and_clients(5):

                worked_time_item = Gtk.MenuItem(label=f"\u25B6 {client} - {task}")
                worked_time_item.client = client
                worked_time_item.task = task

                # TODO: I think this magic does not work. It always picks the same item
                def _activate_worked_time_item(menu_item):
                    client = menu_item.client
                    task = menu_item.task
                    tracking_action.set_property("client", client)
                    tracking_action.set_property("task", task)
                    if tracking_action.get_state():
                        tracking_action.activate()
                    tracking_action.activate()

                worked_time_item.connect("activate", _activate_worked_time_item)
                worked_time_item.set_sensitive(tracking_action.get_enabled())
                menu.append(worked_time_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # ABORT ----------------------------
            abort_item = Gtk.MenuItem(label="Abort")
            abort_item.connect("activate", lambda _0: tracking_action.abort_tracking())
            menu.append(abort_item)

            # QUIT ----------------------------
            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", lambda _0: application.quit())
            menu.append(quit_item)

            menu.show_all()
            self.set_secondary_menu(menu)

        _update_menu()

        tracking_action.connect("notify::enabled", _update_menu)
        tracking_action.connect("worked-time", _update_menu)


class TimerTrackerApplication(Gtk.Application):

    def __init__(self):
        super().__init__(
            register_session=True,
            application_id="net.ernestum.simple_time_tracker",
        )

        self.tracking_action = time_tracking_action = TimeTrackingAction()
        self.worked_time_store = worked_time_store = WorkedTimeStore("my_times.json")

        time_tracking_action.connect("worked-time", lambda _, worked_time: worked_time_store.add_worked_time(worked_time))
        self.add_action(time_tracking_action)
        self.tray_icon = TimeTrackerTrayIcon(time_tracking_action, worked_time_store, self)

    def do_activate(self):
        self.hold()  # Keep the application running until we explicitly quit

    def show_window(self):
        if len(self.get_windows())==0:
            TimeTrackerWindow(
                tracking_action=self.tracking_action,
                worked_time_store=self.worked_time_store,
                application=self, title="Time Tracker").present()

    def on_quit(self, action, param):
        self.worked_time_store.save()
        self.quit()


if __name__=="__main__":
    app = TimerTrackerApplication()
    app.run(sys.argv)
