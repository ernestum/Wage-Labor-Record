import gi

from wage_labor_record.history_view.summary_view import SummaryView

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from wage_labor_record.worked_time_store import WorkedTimeStore
from wage_labor_record.history_view.selector_widget import SelectorWidget
from wage_labor_record.history_view.worked_times_list_view import WorkedTimesListView


class HistoryBrowserWindow(Gtk.Window):
    def __init__(self, work_time_store: WorkedTimeStore):
        super().__init__(title="Worked Time")
        self.set_default_size(200, 100)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.show()
        self.add(box)

        selector_box = SelectorWidget(work_time_store)
        selector_box.show()
        box.add(selector_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.show()
        box.pack_start(scrolled_window, True, True, 0)  # Expand=True

        self.worked_time_widget = WorkedTimesListView()
        self.worked_time_widget.show()
        scrolled_window.add(self.worked_time_widget)


        self.summary_view = SummaryView()
        box.add(self.summary_view)

        def on_selection_changed(selector: SelectorWidget):

            subset = work_time_store.get_subset(tasks=selector.selected_tasks, clients=selector.selected_clients, start_time=selector.selected_start_time, end_time=selector.selected_end_time, )
            self.worked_time_widget.set_worked_times_list(subset)
            self.summary_view.set_worked_times_list(subset)
        selector_box.connect("selection-changed", on_selection_changed)
