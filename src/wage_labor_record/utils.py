import os
import sys
import warnings
from pathlib import Path
from typing import Iterable, Optional

from gi.repository import GLib, Gio, Gtk


def user_data_dir(app_name: str) -> Path:
    r"""
    Get OS specific data directory path for SwagLyrics.
    Typical user data directories are:
        macOS:    ~/Library/Application Support/<app_name>
        Unix:     ~/.local/share/<app_name>   # or in $XDG_DATA_HOME, if defined
        Win 10:   C:\Users\<username>\AppData\Local\<app_name>
    For Unix, we follow the XDG spec and support $XDG_DATA_HOME if defined.
    :return: full path to the user-specific data dir
    """

    # get os specific path
    if sys.platform.startswith("win"):
        os_path = os.getenv("LOCALAPPDATA")
    elif sys.platform.startswith("darwin"):
        os_path = "~/Library/Application Support"
    else:
        # linux
        os_path = os.getenv("XDG_DATA_HOME", "~/.local/share")

    # append app name
    path = Path(os_path) / app_name
    return path.expanduser()


def get_idle_time():
    # TODO: maybe this is a better way to do idle time detection:
    #  https://stackoverflow.com/questions/217157/how-can-i-determine-the-display-idle-time-from-python-in-windows-linux-and-mac
    if sys.platform=="win32":
        import ctypes
        return ctypes.windll.user32.GetLastInputInfo() / 1000
    elif sys.platform=="linux":
        import subprocess
        return int(subprocess.check_output(["xprintidle"])) / 1000
    else:
        warnings.warn(f"No idle time detection for platform {sys.platform}")
        return 0


def link_gtk_menu_item_to_gio_action(menu_item: Gtk.MenuItem, action: Gio.SimpleAction, parameter: Optional[GLib.Variant] = None):
    """
    Links a Gtk.MenuItem to a Gio.SimpleAction.
    This is an ugly hack needed because Gtk.MenuItem does not support Gio.SimpleAction.
    However, we can't use Gio.Menu because it does not support Xapp.StatusIcon.
    And we need Xapp.StatusIcon because it is supported by awesome-wm as opposed to Gtk.StatusIcon.
    """
    menu_item.connect("activate", lambda _0: action.activate(parameter))
    menu_item.set_sensitive(action.get_enabled())
    action.connect("notify::enabled", lambda _0, _1: menu_item.set_sensitive(action.get_enabled()))


def make_completer(items: Iterable[str]):
    model = Gtk.ListStore(str)
    for item in items:
        model.append([item])
    completer = Gtk.EntryCompletion(
        model=model,
        inline_completion=True,
        inline_selection=True,
        popup_completion=True,
        minimum_key_length=0,
    )
    # we cant set it in the constructor, otherwise the
    # completions are not properly rendered
    completer.set_text_column(0)
    return completer
