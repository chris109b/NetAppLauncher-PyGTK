#!/usr/bin/env python3

# Python standard library imports

# Imports from external modules
from gi.repository import Gtk

# Internal modules import


class MainWindow (Gtk.Window):

    def __init__(self):
        super(MainWindow, self).__init__(title="Net App Launcher")
        self.set_border_width(10)
        self.set_default_size(640, 360)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.box = Gtk.Box()
        self.add(self.box)

        self.icon_view_scroll_window = Gtk.ScrolledWindow()
        self.icon_view_scroll_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.icon_view = Gtk.IconView()
        self.icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.icon_view.set_activate_on_single_click(True)

        self.box.pack_start(self.icon_view_scroll_window, True, True, 0)
        self.icon_view_scroll_window.add(self.icon_view)
