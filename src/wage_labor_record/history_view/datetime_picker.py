import datetime

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject


class DatetimePicker(Gtk.Popover):

    datetime_changed = GObject.Signal("datetime-changed", arg_types=(GLib.DateTime,))

    def __init__(self, initial_time: GLib.DateTime):
        Gtk.Popover.__init__(self)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_border_width(10)

        # create horizontal box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(box)

        # Create a date picker
        self.date_picker = Gtk.Calendar(
            day=initial_time.get_day_of_month(),
            month=initial_time.get_month()-1,
            year=initial_time.get_year(),
        )
        self.date_picker.connect("day-selected", self._emit_change_signal)
        box.add(self.date_picker)

        # Create a time picker with 10-minute increments
        self.hour_picker = Gtk.SpinButton()
        self.hour_picker.set_orientation(Gtk.Orientation.VERTICAL)
        self.hour_picker.set_range(-1, 24)
        self.hour_picker.set_increments(1, 1)
        self.hour_picker.set_numeric(True)
        self.hour_picker.set_value(initial_time.get_hour())
        self.hour_picker.connect("value-changed", self._on_hour_changed)
        box.add(self.hour_picker)

        box.add(Gtk.Label(label=":"))

        self.minute_picker = Gtk.SpinButton()
        self.minute_picker.set_orientation(Gtk.Orientation.VERTICAL)
        self.minute_picker.set_range(-1, 60)
        self.minute_picker.set_increments(10, 10)
        self.minute_picker.set_numeric(True)
        self.minute_picker.set_value(initial_time.get_minute())
        self.minute_picker.connect("value-changed", self._on_minute_changed)
        box.add(self.minute_picker)

    def _on_minute_changed(self, *_args):
        minute = self.minute_picker.get_value_as_int()
        if minute == 60:
            self.minute_picker.set_value(0)
            self.hour_picker.set_value(self.hour_picker.get_value_as_int() + 1)
        elif minute == -1:
            self.minute_picker.set_value(59)
            self.hour_picker.set_value(self.hour_picker.get_value_as_int() - 1)
        self._emit_change_signal()

    def _on_hour_changed(self, *_args):
        hour = self.hour_picker.get_value_as_int()
        if hour == 24:
            self.hour_picker.set_value(0)
            year, month, day = self.date_picker.get_date()
            next_day = datetime.date(year, month+1, day) + datetime.timedelta(days=1)
            self.date_picker.select_day(next_day.day)
            self.date_picker.select_month(next_day.month-1, next_day.year)
        elif hour == -1:
            self.hour_picker.set_value(23)
            year, month, day = self.date_picker.get_date()
            prev_day = datetime.date(year, month+1, day) - datetime.timedelta(days=1)
            self.date_picker.select_day(prev_day.day)
            self.date_picker.select_month(prev_day.month-1, prev_day.year)
        self._emit_change_signal()

    def _emit_change_signal(self, *_args):
        year, month, day = self.date_picker.get_date()
        hour = self.hour_picker.get_value_as_int()
        minute = self.minute_picker.get_value_as_int()
        self.emit("datetime-changed", GLib.DateTime.new_local(year, month + 1, day, hour, minute, 0))