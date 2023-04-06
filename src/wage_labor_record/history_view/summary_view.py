import datetime

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class SummaryView(Gtk.Box):
    """A widget to show summary information about a set of worked times."""
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=40,
            border_width=20,
        )

        self.total_time_label = Gtk.Label()
        self.total_time_label.set_markup(f"<span font='monospace bold 24'>00:00</span>")
        self.total_time_label.show()
        self.add(self.total_time_label)

        self.durations_by_task = Gtk.TreeView()

        self.durations_by_task.set_size_request(-1, 3 * 24)  # Ensure that the list is at least 3 lines tall
        self.durations_by_task.get_selection().set_mode(Gtk.SelectionMode.NONE)  # Disable selection
        self.durations_by_task.append_column(Gtk.TreeViewColumn("Task", Gtk.CellRendererText(), text=0))
        self.durations_by_task.append_column(Gtk.TreeViewColumn("Duration", Gtk.CellRendererText(), text=1))

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

    def set_worked_times_list(self, worked_times_list):
        total_duration = datetime.timedelta()
        durations_by_task = dict()
        for worked_time in worked_times_list:
            total_duration += worked_time.duration
            if worked_time.task not in durations_by_task:
                durations_by_task[worked_time.task] = worked_time.duration
            else:
                durations_by_task[worked_time.task] += worked_time.duration

        durations_by_task_list = Gtk.ListStore(str, str)
        for task, duration in durations_by_task.items():
            durations_by_task_list.append([task, str(duration)])

        self._durations_by_task_string = "\n".join([f'{task}, {duration}' for task, duration in durations_by_task.items()])

        self.durations_by_task.set_model(durations_by_task_list)

        hours, remainder = divmod(int(total_duration.total_seconds()), 60 * 60)
        minutes, seconds = divmod(remainder, 60)

        self.total_time_label.set_markup(f"<span font='monospace bold 24'>{hours:02}:{minutes:02}</span>")

