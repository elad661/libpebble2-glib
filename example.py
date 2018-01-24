#!/bin/python3
# example.py - And example showing how to use libpebble2-glib
#
# Copyright (C) 2018 Elad Alfassa <elad@fedoraproject.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import dbus
import dbus.mainloop.glib
import logging
from libpebble2_glib import configure_logging, register_profile
from gi.repository import GLib
from libpebble2.services.notifications import Notifications


DBUS_PATH = '/com/eladalfassa/pebblething/BluetoothProfile'


def connect_callback(pebble):
    """ This callback is called when the watch is connected.
    The only parameter is the PebbleConnection. You can use it to
    send and recive data from the watch. Read the libpebble2
    documentation for more details """
    notifications_service = Notifications(pebble)
    notifications_service.send_notification("Hello world!", "testing")


def main():
    configure_logging()
    logging.getLogger("main").info("Starting...")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    profile = register_profile(connect_callback, DBUS_PATH)
    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    finally:
        profile.Release()  # make sure all file descriptors are closed


if __name__ == "__main__":
    main()
