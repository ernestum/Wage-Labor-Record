import datetime

import gi

from wage_labor_record.tracking_state import TrackingState

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


class SummaryView(Gtk.Box):
    """A widget to show summary information about a set of worked times."""
    def __init__(self, tracking_state: TrackingState):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=40,
            border_width=20,
        )
        self._tracking_state = tracking_state

        self.total_time_label = Gtk.Label()
        self.total_time_label.set_markup(f"<span font='monospace bold 24'>00:00</span>")
        self.total_time_label.show()
        self.add(self.total_time_label)

        self.durations_by_task = Gtk.TreeView()

        self.durations_by_task.set_size_request(-1, 3 * 24)  # Ensure that the list is at least 3 lines tall
        self.durations_by_task.get_selection().set_mode(Gtk.SelectionMode.NONE)  # Disable selection
        self.durations_by_task.append_column(Gtk.TreeViewColumn("Task", Gtk.CellRendererText(), text=0))
        self.durations_by_task.append_column(Gtk.TreeViewColumn("Total Duration", Gtk.CellRendererText(), text=1))

        self.durations_by_task.show()
        self.add(self.durations_by_task)

        self._durations_by_task_string = ""
        self.copy_to_clipboard_button = Gtk.Button(label="Copy to Clipboard")
        def copy_to_clipboard(*args):
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(self._durations_by_task_string, -1)
        self.copy_to_clipboard_button.connect("clicked", copy_to_clipboard)
        self.copy_to_clipboard_button.show()
        self.add(self.copy_to_clipboard_button)
        self.show()

    def set_worked_times_list(self, worked_times_list, include_tracking_state: bool = False):
        # Compute the durations aggregated by task
        durations_by_task = dict()
        for worked_time in worked_times_list:
            durations_by_task.setdefault(worked_time.task, datetime.timedelta())
            durations_by_task[worked_time.task] += worked_time.duration

        # Save the durations by task as a string for copying to the clipboard
        self._durations_by_task_string = "\n".join([f'{task}, {_duration_to_str(duration)}' for task, duration in durations_by_task.items()])

        # Put the aggregated durations into a Gtk.ListStore and display it in the list view
        durations_by_task_list = Gtk.ListStore(str, str)
        for task, duration in durations_by_task.items():
            durations_by_task_list.append([task, _duration_to_str(duration)])
        self.durations_by_task.set_model(durations_by_task_list)

        # Compute the total duration
        total_duration = sum(durations_by_task.values(), start=datetime.timedelta())

        def update_total_duration_view():
            if include_tracking_state and self._tracking_state.is_tracking():
                total_duration_with_tracking_state = total_duration + self._tracking_state.elapsed_time()
                self.total_time_label.set_markup(
                    f"<span font='monospace bold 24'>{_duration_to_str(total_duration, include_seconds=False)}</span>\n"
                    f"<span font='monospace bold 16' color='grey'>({_duration_to_str(total_duration_with_tracking_state)})</span>"
                )
            else:
                self.total_time_label.set_markup(f"<span font='monospace bold 24'>{_duration_to_str(total_duration, include_seconds=False)}</span>")

        update_total_duration_view()
        if include_tracking_state:
            self._tracking_state.connect("notify", lambda *args: update_total_duration_view())

            # regularly update the total time label
            # When the tracking is active, repeatedly update the elapsed time label
            # when tracking stopped, stop the regular updates as well
            def _update_view():
                update_total_duration_view()
                return self._tracking_state.is_tracking()

            GLib.timeout_add(1000, _update_view)
            self._tracking_state.connect("notify::start-time", lambda *args: GLib.timeout_add(1000, _update_view))


def _duration_to_str(d: datetime.timedelta, include_seconds: bool = True) -> str:
    """Format the duration to HH:mm:ss format"""
    hours, remainder = divmod(int(d.total_seconds()), 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    if include_seconds:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{hours:02}:{minutes:02}"