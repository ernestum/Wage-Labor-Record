import datetime
import time

import gi

from wage_labor_record.tracking_state import TrackingState
from wage_labor_record.utils import make_completer
from wage_labor_record.worked_time_store import WorkedTimeStore

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, GObject, Gtk


class TimeTrackerWindow(Gtk.Dialog):
    def __init__(self, tracking_state: TrackingState, worked_time_store: WorkedTimeStore, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Layout
        box = self.get_content_area()

        self.task_entry = Gtk.Entry(
            placeholder_text="Task",
            completion=make_completer(worked_time_store.all_tasks()),
        )
        self.task_entry.connect("activate", lambda *_args: self.start_tracking_button.clicked())
        self.task_entry.show()
        box.add(self.task_entry)

        self.client_entry = Gtk.Entry(
            placeholder_text="Client",
            completion=make_completer(worked_time_store.all_clients()),
        )
        self.client_entry.connect("activate", lambda *_args: self.start_tracking_button.clicked())
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

        # A Monospaced bold label with large font size
        self.elapsed_time_label = Gtk.Label(label="")
        self.elapsed_time_label.show()
        box.pack_start(self.elapsed_time_label, True, True, 0)

        # Ensure the entry fields edit the action properties
        tracking_state.bind_property("task", self.task_entry, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        tracking_state.bind_property("client", self.client_entry, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        # When the tracking is active, repeatedly update the elapsed time label
        def _update_elapsed_time_label():
            if tracking_state.is_tracking():
                label_txt = str(datetime.timedelta(seconds=int(time.time() - tracking_state.start_time)))
                self.elapsed_time_label.set_markup(f"<span font='monospace bold 24'>{label_txt}</span>")
            return tracking_state.is_tracking()

        def _setup_elapsed_time_label_updates(*_):
            if tracking_state.is_tracking():
                _update_elapsed_time_label()
                GLib.timeout_add(1000, _update_elapsed_time_label)
            else:
                label_txt = str(datetime.timedelta(seconds=0))
                self.elapsed_time_label.set_markup(f"<span font='monospace bold 24'>{label_txt}</span>")

        _setup_elapsed_time_label_updates()
        tracking_state.connect("notify::start-time", _setup_elapsed_time_label_updates)
