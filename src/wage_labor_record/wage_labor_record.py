import datetime
import importlib.resources
import logging
import sys
import time

import gi

from wage_labor_record.actions import AbortTrackingAction, SetCurrentTaskAction, StartTrackingAction, StopTrackingAction
from wage_labor_record.tracked_time_store import WorkedTimeStore
from wage_labor_record.tracking_state import TrackingState
from wage_labor_record.utils import get_idle_time, link_gtk_menu_item_to_gio_action, make_completer, user_data_dir

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, GObject, XApp

logging.basicConfig(level=logging.INFO)


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


class TimeTrackerTrayIcon(XApp.StatusIcon):
    def __init__(self, tracking_state: TrackingState, worked_time_store: WorkedTimeStore, application: Gtk.Application):
        super().__init__()
        self.set_name("Time Tracker")

        def _update_tooltip(*_):
            task = tracking_state.task
            client = tracking_state.client
            is_tracking = tracking_state.is_tracking()

            tooltip_text = (
                    ("Working\n" if is_tracking else "Not working\n") +
                    (f"On: {task}\n" if task != "" else "") +
                    (f"For: {client}\n" if client != "" else "")
            ).strip()
            self.set_tooltip_text(tooltip_text)

        _update_tooltip()
        tracking_state.connect("notify::start-time", _update_tooltip)
        tracking_state.connect("notify::task", _update_tooltip)
        tracking_state.connect("notify::client", _update_tooltip)

        start_tracking_action = application.lookup_action("start_tracking")
        start_tracking_task_action = application.lookup_action("start_tracking_task")
        stop_tracking_action = application.lookup_action("stop_tracking")
        abort_tracking_action = application.lookup_action("abort_tracking")

        def on_left_click(*_):
            logging.debug("Left click")
            if start_tracking_action.get_enabled():
                start_tracking_action.activate()
            elif stop_tracking_action.get_enabled():
                stop_tracking_action.activate()
            else:
                application.activate()

        self.connect("activate", on_left_click)

        def _update_icon(*_):
            logging.debug("Update icon")
            if start_tracking_action.get_enabled():
                icon_name = "start-tracking"
            elif stop_tracking_action.get_enabled():
                icon_name = "stop-tracking"
            else:
                icon_name = "stop-tracking-disabled"

            with importlib.resources.path("wage_labor_record.resources", f"{icon_name}.svg") as p:
                self.set_icon_name(str(p))

        _update_icon()
        start_tracking_action.connect("notify::enabled", _update_icon)
        stop_tracking_action.connect("notify::enabled", _update_icon)

        # Add menu to the tray icon
        def _update_menu(*_):
            # NOTE: This is not the most efficient way to do this, but it works for now
            menu = Gtk.Menu()

            # CLIENT ----------------------------
            client_item = Gtk.MenuItem(label="")

            def _update_client_menu_item(*_):
                client = tracking_state.client
                client_item.set_label("Set Client" if client == "" else f"Client: {client}")

            _update_client_menu_item()
            tracking_state.connect("notify::client", _update_client_menu_item)
            client_item.connect("activate", lambda _0: application.activate())
            menu.append(client_item)

            # TASK ----------------------------
            task_item = Gtk.MenuItem(label="")

            def _update_task_menu_item(*_):
                task = tracking_state.task
                task_item.set_label("Set Task" if task=="" else f"Task: {task}")

            _update_task_menu_item()
            tracking_state.connect("notify::task", _update_task_menu_item)
            task_item.connect("activate", lambda _0: application.activate())
            menu.append(task_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # WORKED ITEMS -------------------------
            for task, client in worked_time_store.most_recent_worked_tasks_and_clients(5):

                worked_time_item = Gtk.MenuItem(label=f"\u25B6 {client} - {task}")
                worked_time_item.client = client
                worked_time_item.task = task

                link_gtk_menu_item_to_gio_action(worked_time_item, start_tracking_task_action, GLib.Variant("(ss)", (client, task)))
                menu.append(worked_time_item)

            # SEPARATOR ----------------------------
            menu.append(Gtk.SeparatorMenuItem())

            # ABORT ----------------------------
            abort_item = Gtk.MenuItem(label="Abort")
            link_gtk_menu_item_to_gio_action(abort_item, abort_tracking_action)
            menu.append(abort_item)

            # QUIT ----------------------------
            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", lambda _0: application.quit())
            menu.append(quit_item)

            menu.show_all()
            self.set_secondary_menu(menu)

        _update_menu()

        stop_tracking_action.connect("worked-time", _update_menu)


class TimerTrackerApplication(Gtk.Application):

    def __init__(self):
        super().__init__(
            register_session=True,
            application_id="net.ernestum.wage_labor_record",
        )

        data_dir = user_data_dir("Wage Labor Record")
        data_dir.mkdir(parents=True, exist_ok=True)

        self.tracking_state = tracking_state = TrackingState(data_dir / "state.json")
        self.start_tracking_action = start_tracking_action = StartTrackingAction(tracking_state)
        self.start_tracking_task_action = start_tracking_task_action = SetCurrentTaskAction(tracking_state)
        self.stop_tracking_action = stop_tracking_action = StopTrackingAction(tracking_state)
        self.abort_tracking_action = abort_tracking_action = AbortTrackingAction(tracking_state)
        self.add_action(start_tracking_action)
        self.add_action(start_tracking_task_action)
        self.add_action(stop_tracking_action)
        self.add_action(abort_tracking_action)

        self.worked_time_store = worked_time_store = WorkedTimeStore(data_dir / "worked_times.json")

        stop_tracking_action.connect("worked-time", lambda _, worked_time: worked_time_store.add_worked_time(worked_time))
        self.tray_icon = TimeTrackerTrayIcon(tracking_state, worked_time_store, self)

        def _check_for_idle(*_):
            if tracking_state.is_tracking():
                idle_time = get_idle_time()
                logging.debug(f"Idle time: {idle_time}")
                if idle_time > 60 * 15:  # when idle for 15 minutes
                    # show dialog to ask whether to continue tracking, stopping tracking and discarding the time or stopping tracking and saving the time
                    dialog = Gtk.MessageDialog(
                        transient_for=self.get_active_window(),
                        modal=True,
                        message_type=Gtk.MessageType.QUESTION,
                        buttons=Gtk.ButtonsType.NONE,
                        text="You have been idle for 15 minutes. Do you want to continue tracking?",
                    )
                    dialog.add_button("Continue", Gtk.ResponseType.YES)
                    dialog.add_button("Continue but discard", Gtk.ResponseType.APPLY)
                    dialog.add_button("Stop and discard", Gtk.ResponseType.NO)
                    dialog.add_button("Stop and save", Gtk.ResponseType.CANCEL).set_action_name("app.abort-tracking")
                    response = dialog.run()
                    # TODO: what do we do if the task has not been set yet? then we could not stop tracking
                    # TODO: add option to enter task in dialog
                    if response == Gtk.ResponseType.YES:
                        pass
                    elif response == Gtk.ResponseType.APPLY:
                        pass  # TODO: implement
                    elif response == Gtk.ResponseType.NO:
                        pass  # TODO: implement
                    elif response == Gtk.ResponseType.CANCEL:
                        stop_tracking_action.activate()

                    dialog.destroy()
            return True

        GLib.timeout_add(1000, _check_for_idle)

    def do_activate(self):
        self.hold()  # Keep the application running until we explicitly quit
        self.show_window()

    def show_window(self):
        if len(self.get_windows())==0:
            TimeTrackerWindow(
                tracking_state=self.tracking_state,
                worked_time_store=self.worked_time_store,
                application=self, title="Working Labor Record").present()

    def on_quit(self, action, param):
        self.worked_time_store.save()
        self.quit()


if __name__=="__main__":
    app = TimerTrackerApplication()
    app.run(sys.argv)
