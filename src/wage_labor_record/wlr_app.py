import logging
import sys

import gi

from wage_labor_record.actions import AbortTrackingAction, SetCurrentTaskAction, StartTrackingAction, StopTrackingAction
from wage_labor_record.time_tracker_tray_icon import TimeTrackerTrayIcon
from wage_labor_record.time_tracker_window import TimeTrackerWindow
from wage_labor_record.worked_time_store import WorkedTimeStore
from wage_labor_record.tracking_state import TrackingState
from wage_labor_record.utils import get_idle_time, user_data_dir

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

logging.basicConfig(level=logging.INFO)


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

        stop_tracking_action.connect("worked-time", lambda _, worked_time: worked_time_store.append(worked_time))
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
                    dialog.add_button("Continue but discard (not implemented)", Gtk.ResponseType.APPLY).set_sensitive(False)
                    dialog.add_button("Stop and discard (not implemented)", Gtk.ResponseType.NO).set_sensitive(False)
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


if __name__ == "__main__":
    app = TimerTrackerApplication()
    try:
        app.run(sys.argv)
    except KeyboardInterrupt:
        pass
