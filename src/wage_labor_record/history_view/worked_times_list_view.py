import gi

from wage_labor_record.history_view.datetime_picker import DatetimePicker
from wage_labor_record.utils import make_completer

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gio, Gtk

from wage_labor_record.worked_time_store import WorkedTime, WorkedTimeStore


class WorkedTimesListView(Gtk.ListBox):
    """A view to show and edit a set of worked times."""

    def __init__(self, worked_time_store: WorkedTimeStore):
        super().__init__()
        self.show()
        self._worked_times: Gio.ListStore = None
        self._all_items_in_same_year = False
        self._all_items_in_same_month = False
        self._all_items_in_same_day = False
        self._worked_time_store = worked_time_store

    def set_worked_times_list(self, model: Gio.ListStore):
        self._all_items_in_same_year = len({item.start_time.get_year() for item in model}) == 1
        self._all_items_in_same_month = self._all_items_in_same_year and len({item.start_time.get_month() for item in model}) == 1
        self._all_items_in_same_day = self._all_items_in_same_month and len({item.start_time.get_day_of_month() for item in model}) == 1
        self.bind_model(model, self._create_row)

        print(self._all_items_in_same_year, self._all_items_in_same_month, self._all_items_in_same_day)

    def _create_row(self, item: WorkedTime):
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.homogenous = False
        box.show()
        row.add(box)

        box.pack_start(self._create_task_entry(item), True, True, 0)
        box.pack_start(self._create_client_entry(item), True, True, 0)
        box.pack_start(self._create_start_time_button(item), True, True, 0)
        box.pack_start(self._create_end_time_button(item), True, True, 0)
        box.pack_start(self._create_delete_button(item), True, True, 0)
        row.show()
        return row

    def _create_start_time_button(self, item):
        start_time_button = Gtk.Button()
        start_time_button.set_relief(Gtk.ReliefStyle.NONE)

        def on_start_time_clicked(*args):
            picker = DatetimePicker(item.start_time)

            picker.connect("datetime-changed", lambda picker, time: item.set_property("start-time", time))
            picker.set_relative_to(start_time_button)
            picker.show_all()
            picker.popup()

        def on_start_time_changed(*args):
            start_time_button.set_label(self._get_start_time_string(item))

        on_start_time_changed()
        item.connect("notify::start-time", on_start_time_changed)
        start_time_button.connect("clicked", on_start_time_clicked)
        start_time_button.show()
        return start_time_button

    def _create_end_time_button(self, item):
        end_time_label = Gtk.Button()
        end_time_label.set_relief(Gtk.ReliefStyle.NONE)

        def on_end_time_clicked(*args):
            picker = DatetimePicker(item.end_time)

            picker.connect("datetime-changed", lambda picker, time: item.set_property("end-time", time))
            picker.set_relative_to(end_time_label)
            picker.show_all()
            picker.popup()

        def on_end_time_changed(*args):
            end_time_label.set_label(self._get_end_time_string(item))

        on_end_time_changed()
        item.connect("notify::end-time", on_end_time_changed)
        end_time_label.connect("clicked", on_end_time_clicked)
        end_time_label.show()
        return end_time_label

    def _create_client_entry(self, item: WorkedTime):
        client_entry = Gtk.Entry(
            text=item.client,
            placeholder_text="Client",
            completion=make_completer(self._worked_time_store.clients),
        )
        client_entry.set_has_frame(False)

        def set_client(*args):
            item.client = client_entry.get_text()

        client_entry.connect("activate", set_client)
        # item.bind_property("client", client_label, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        client_entry.show()
        return client_entry

    def _create_task_entry(self, item: WorkedTime):
        task_entry = Gtk.Entry(
            text=item.task,
            placeholder_text="Task",
            completion=make_completer(self._worked_time_store.tasks),
        )
        task_entry.set_has_frame(False)

        def set_task(*args):
            item.task = task_entry.get_text()

        task_entry.connect("activate", set_task)
        # item.bind_property("task", task_label, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        task_entry.show()
        return task_entry

    def _create_delete_button(self, item: WorkedTime):
        delete_button = Gtk.Button()
        delete_button.set_relief(Gtk.ReliefStyle.NONE)
        delete_button.set_image(Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON))
        delete_button.connect("clicked", lambda *args: self._worked_time_store.remove_item(item))
        delete_button.show()
        return delete_button

    def _get_start_time_string(self, item: WorkedTime) -> str:
        if self._all_items_in_same_day:
            return item.start_time.format("%H:%M")
        elif self._all_items_in_same_month:
            return item.start_time.format("%d %H:%M")
        elif self._all_items_in_same_year:
            return item.start_time.format("%b %d %H:%M")
        else:
            return item.start_time.format("%Y-%m-%d %H:%M")

    def _get_end_time_string(self, item: WorkedTime) -> str:
        ends_on_same_year = item.end_time.get_year() == item.start_time.get_year()
        ends_on_same_month = ends_on_same_year and item.end_time.get_month() == item.start_time.get_month()
        ends_on_same_day = ends_on_same_month and item.end_time.get_day_of_month() == item.start_time.get_day_of_month()

        if ends_on_same_day:
            return item.end_time.format("%H:%M")
        elif ends_on_same_month:
            return item.end_time.format("%d %H:%M")
        elif ends_on_same_year:
            return item.end_time.format("%b %d %H:%M")
        else:
            return item.end_time.format("%Y-%m-%d %H:%M")
