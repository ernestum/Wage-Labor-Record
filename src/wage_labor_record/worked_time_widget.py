import gi

from wage_labor_record.worked_time_store import WorkedTime, WorkedTimeStore

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib

class WorkedTimeWindow(Gtk.Window):
    def __init__(self, work_time_store: WorkedTimeStore):
        super().__init__(title="Worked time")
        self.set_default_size(200, 100)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.show()
        self.add(box)

        # Add selector for ""today", "this week", "this month", "last month"
        action_bar = Gtk.ActionBar()
        action_bar.show()

        buttons = []

        def on_button_toggled(button: Gtk.ToggleButton):
            if not button.get_active():
                return
            for b in buttons:
                if b is not button:
                    b.set_active(False)

        today_button = Gtk.ToggleButton(label="Today")
        today_button.set_active(True)

        def on_today_button_clicked(button: Gtk.ToggleButton):
            if button.get_active():
                now = GLib.DateTime.new_now_local()
                start_of_day = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), now.get_day_of_month(), 0, 0, 0)
                self.worked_time_widget.set_model(work_time_store[start_of_day:])
        today_button.connect("toggled", on_today_button_clicked)
        buttons.append(today_button)



        this_week_button = Gtk.ToggleButton(label="This Week")
        def on_this_week_button_clicked(button: Gtk.ToggleButton):
            if button.get_active():
                now = GLib.DateTime.new_now_local()
                start_of_day = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), now.get_day_of_month(), 0, 0, 0)
                start_of_week = start_of_day.add_days(-start_of_day.get_day_of_week()+1)  # Week starts on Monday
                print(f"Start of Week: {start_of_week.format_iso8601()}")
                self.worked_time_widget.set_model(work_time_store[start_of_week:])
        this_week_button.connect("toggled", on_this_week_button_clicked)
        buttons.append(this_week_button)

        this_month_button = Gtk.ToggleButton(label="This Month")
        def on_this_month_button_clicked(button: Gtk.ToggleButton):
            if button.get_active():
                now = GLib.DateTime.new_now_local()
                start_of_month = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), 1, 0, 0, 0)
                print(f"Start of Month: {start_of_month.format_iso8601()}")
                self.worked_time_widget.set_model(work_time_store[start_of_month:])
        this_month_button.connect("toggled", on_this_month_button_clicked)
        buttons.append(this_month_button)

        last_month_button = Gtk.ToggleButton(label="Last Month")
        def on_last_month_button_clicked(button: Gtk.ToggleButton):
            if button.get_active():
                now = GLib.DateTime.new_now_local()
                start_of_month = GLib.DateTime.new(now.get_timezone(), now.get_year(), now.get_month(), 1, 0, 0, 0)
                start_of_prev_month = start_of_month.add_months(-1)
                print(f"Start of Prev Month: {start_of_prev_month.format_iso8601()}")
                print(f"Start of Month: {start_of_month.format_iso8601()}")
                self.worked_time_widget.set_model(work_time_store[start_of_prev_month:start_of_month])
        last_month_button.connect("toggled", on_last_month_button_clicked)
        buttons.append(last_month_button)

        all_button = Gtk.ToggleButton(label="All")
        def on_all_button_clicked(button: Gtk.ToggleButton):
            if button.get_active():
                self.worked_time_widget.set_model(work_time_store)
        all_button.connect("toggled", on_all_button_clicked)
        buttons.append(all_button)

        for button in buttons:
            button.show()
            action_bar.pack_start(button)
            button.connect("toggled", on_button_toggled)

        box.add(action_bar)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.show()
        box.pack_start(scrolled_window, True, True, 0)  # Expand=True

        self.worked_time_widget = WorkedTimeWidget()
        self.worked_time_widget.show()
        scrolled_window.add(self.worked_time_widget)


class WorkedTimeWidget(Gtk.ListBox):

    def __init__(self):
        super().__init__()
        self.show()

    def set_model(self, model: WorkedTimeStore):
        self.bind_model(model, self._create_row)

    def _create_row(self, item: WorkedTime):
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.show()
        row.add(box)

        task_label = Gtk.Entry()
        item.bind_property("task", task_label, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        task_label.show()
        box.add(task_label)

        client_label = Gtk.Entry()
        item.bind_property("client", client_label, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        client_label.show()
        box.add(client_label)

        time = Gtk.Label()
        time.set_text("\t" + item.start_time.format_iso8601() + "\t" + item.end_time.format_iso8601())
        time.show()
        box.add(time)

        row.show()
        return row
