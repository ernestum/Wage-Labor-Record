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
            month=initial_time.get_month(),
            year=initial_time.get_year(),
        )
        self.date_picker.connect("day-selected", self._emit_change_signal)
        box.add(self.date_picker)

        # Create a time picker with 10-minute increments
        self.hour_picker = Gtk.SpinButton()
        self.hour_picker.set_orientation(Gtk.Orientation.VERTICAL)
        self.hour_picker.set_range(0, 23)
        self.hour_picker.set_increments(1, 1)
        self.hour_picker.set_numeric(True)
        self.hour_picker.set_value(initial_time.get_hour())
        self.hour_picker.connect("value-changed", self._emit_change_signal)
        box.add(self.hour_picker)

        box.add(Gtk.Label(label=":"))

        self.minute_picker = Gtk.SpinButton()
        self.minute_picker.set_orientation(Gtk.Orientation.VERTICAL)
        self.minute_picker.set_range(0, 59)
        self.minute_picker.set_increments(10, 10)
        self.minute_picker.set_numeric(True)
        self.minute_picker.set_value(initial_time.get_minute())
        self.minute_picker.connect("value-changed", self._emit_change_signal)
        box.add(self.minute_picker)

    def _emit_change_signal(self, *_args):
        year, month, day = self.date_picker.get_date()
        hour = self.hour_picker.get_value_as_int()
        minute = self.minute_picker.get_value_as_int()
        self.emit("datetime-changed", GLib.DateTime.new_local(year, month + 1, day, hour, minute, 0))