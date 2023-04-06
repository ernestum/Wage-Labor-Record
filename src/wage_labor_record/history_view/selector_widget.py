from typing import Optional, Set

from gi.repository import GLib, GObject, Gtk, Gdk

from wage_labor_record.worked_time_store import WorkedTimeStore


class SelectorWidget(Gtk.Box):
    """Widget to select a subset of the history of tracked worked times."""
    selection_changed = GObject.Signal("selection-changed")

    def __init__(self, worked_time_store: WorkedTimeStore):
        Gtk.Box.__init__(self,
            orientation=Gtk.Orientation.VERTICAL,
            spacing=40,
            border_width=20,
        )

        self.selected_start_time: Optional[GLib.DateTime] = None
        self.selected_end_time: Optional[GLib.DateTime] = None
        self.selected_clients: Optional[Set[str]] = None
        self.selected_tasks: Optional[Set[str]] = None



        # Time Selector
        time_selections_model = Gtk.ListStore(str)
        time_selections_model.append(["Today"])
        time_selections_model.append(["This Week"])
        time_selections_model.append(["This Month"])
        time_selections_model.append(["Last Month"])
        time_selector = Gtk.TreeView()
        time_selector.set_model(time_selections_model)

        time_selector.append_column(
            Gtk.TreeViewColumn("Time Selection", Gtk.CellRendererText(), text=0))
        time_selector.show()

        def on_time_selector_changed(_):
            model, treeiter = time_selector.get_selection().get_selected()
            if treeiter is not None:
                time_selection = model[treeiter][0]
                if time_selection == "Today":
                    now = GLib.DateTime.new_now_local()
                    start_of_day = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), now.get_day_of_month(), 0, 0, 0)
                    self.selected_start_time = start_of_day
                    self.selected_end_time = None

                elif time_selection == "This Week":
                    now = GLib.DateTime.new_now_local()
                    start_of_week = now.add_days(-now.get_day_of_week() + 1)  # Monday
                    self.selected_start_time = start_of_week
                    self.selected_end_time = None

                elif time_selection == "This Month":
                    now = GLib.DateTime.new_now_local()
                    start_of_month = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), 1, 0, 0, 0)
                    self.selected_start_time = start_of_month
                    self.selected_end_time = None

                elif time_selection == "Last Month":
                    now = GLib.DateTime.new_now_local()
                    start_of_month = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), 1, 0, 0, 0)
                    start_of_prev_month = start_of_month.add_months(-1)
                    self.selected_start_time = start_of_prev_month
                    self.selected_end_time = start_of_month
                else:
                    assert False, f"Unknown time selection: {time_selection}"
                self.selection_changed.emit()

        time_selector.connect("cursor-changed", on_time_selector_changed)
        self.add(time_selector)

        # Task and Client Selectors (multiple selection)

        def on_esc_deselect_all(widget, event):
            if event.keyval == Gdk.KEY_Escape:
                widget.get_selection().unselect_all()

        task_selector = Gtk.TreeView(rubber_banding=True)
        task_selector.connect("key-press-event", on_esc_deselect_all)
        task_selector.set_model(worked_time_store.all_tasks())
        task_selector.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        task_selector.append_column(Gtk.TreeViewColumn("Task", Gtk.CellRendererText(), text=0))

        def on_task_selector_changed(_):
            if task_selector.get_selection().count_selected_rows() == 0:
                self.selected_tasks = None
            else:
                model, rows = task_selector.get_selection().get_selected_rows()
                self.selected_tasks = {model[row][0] for row in rows}
            self.selection_changed.emit()

        task_selector.get_selection().connect("changed", on_task_selector_changed)
        task_selector.show()

        self.add(task_selector)

        client_selector = Gtk.TreeView(rubber_banding=True)
        client_selector.connect("key-press-event", on_esc_deselect_all)
        client_selector.set_model(worked_time_store.all_clients())
        client_selector.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        client_selector.append_column(Gtk.TreeViewColumn("Client", Gtk.CellRendererText(), text=0))

        def on_client_selector_changed(_):
            if client_selector.get_selection().count_selected_rows() == 0:
                self.selected_clients = None
            else:
                model, rows = client_selector.get_selection().get_selected_rows()
                self.selected_clients = {model[row][0] for row in rows}
            self.selection_changed.emit()

        client_selector.get_selection().connect("changed", on_client_selector_changed)
        client_selector.show()

        self.add(client_selector)

        self.show()
