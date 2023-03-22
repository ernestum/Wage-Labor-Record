import importlib.resources
import logging

import gi

from wage_labor_record.tracking_state import TrackingState
from wage_labor_record.utils import link_gtk_menu_item_to_gio_action
from wage_labor_record.worked_time_store import WorkedTimeStore

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import GLib, Gtk, XApp


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

        worked_time_store.connect("row-inserted", _update_menu)
        worked_time_store.connect("row-deleted", _update_menu)
