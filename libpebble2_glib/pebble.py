# pebble.py - Bridging the BlueZ 5 DBus API with libpebble2
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

""" Bridging the BlueZ 5 DBus API with libpebble2 """

# Note: I used dbus here and not pydbus like in screenshot.py because
# while pydbus is easier for simple clients, it gets messy once you want to
# export your own dbus object

from gi.repository import GLib
import dbus
import dbus.service
import libpebble2
import logging
import os
import struct
import traceback

import time
from datetime import datetime

import tzlocal
from libpebble2.communication import PebbleConnection
from libpebble2.communication.transports import BaseTransport, MessageTargetWatch
from libpebble2.protocol import SetUTC
from libpebble2.protocol import TimeMessage
from threading import Thread
import libpebble2.services.notifications

BT_UUID = '00000000-deca-fade-deca-deafdecacaff'

# Need to monkey-patch libpebble2.services.notifications to make sure time
# is an integer, because libpebble can't encode floats on the time field

origtime = time.time


def inttime():
    return int(origtime())


libpebble2.services.notifications.time.time = inttime


logger = logging.getLogger("libpebble-glib")


class PebbleGLibTransport(BaseTransport):
    """ A semi-compatible libpebble2 Transport using GLib io_watch on a file descriptor"""

    must_initialise = True

    def __init__(self, fd, read_callback):
        self.fd = fd
        self.watch_id = None
        self.hup_watch = None
        self.channel = None
        self.read_callback = read_callback

    @property
    def connected(self):
        """ Is this Transport connected """
        return (self.watch_id is not None and
                self.hup_watch is not None and
                self.channel is not None and
                self.fd is not None)

    def disconnect(self):
        """ Stop the watcher and close the file descriptor """
        if self.watch_id is not None:
            GLib.source_remove(self.watch_id)  # remove the watch
            self.watch_id = None

        if self.hup_watch is not None:
            GLib.source_remove(self.hup_watch)  # remove the watch
            self.hup_watch = None

        if self.channel is not None:
            self.channel.close()
            self.channel = None

        if self.fd is not None:
            try:
                os.close(self.fd)  # Close the file descriptor
            except OSError:
                pass  # Don't care if it's already closed
            self.fd = None

    def connect(self):
        """ Set a GLib watch on the file descriptor """
        print("starting watcher on fd " + str(self.fd))
        channel = GLib.IOChannel.unix_new(self.fd)
        self.channel = channel

        self.watch_id = GLib.io_add_watch(channel,
                                          GLib.PRIORITY_HIGH,
                                          GLib.IO_IN,
                                          self._callback_wrapper)
        self.hup_watch = GLib.io_add_watch(channel,
                                           GLib.PRIORITY_DEFAULT,
                                           GLib.IO_HUP,
                                           self.hup_callback)
        print(self.watch_id)

    def _callback_wrapper(self, channel, cond):
        if self.watch_id is None:
            # Don't call user callback if we just closed this watcher
            return False

        fd = channel.unix_get_fd()
        data = os.read(fd, 2)
        length, = struct.unpack('!H', data)
        data += os.read(fd, length + 2)
        self.read_callback(MessageTargetWatch(), data)
        return True

    def hup_callback(self, fd, cond):
        """ Called by glib when we get HUP on the fd """
        logger.info("Got HUP on the fd")
        self.disconnect()

    def send_packet(self, message):
        os.write(self.fd, message)

    def read_packet(self):
        raise AttributeError("reads are only done using a callback")


class PebbleGLibConnection(PebbleConnection):
    """ A PebbleConnection that uses the GLib event loop """
    def __init__(self, fd, log_protocol_level=None, log_packet_level=None):
        transport = PebbleGLibTransport(fd, self._read_callback)
        transport.connect()
        super().__init__(transport, log_protocol_level, log_packet_level)

    def run_sync(self):
        """ Don't use this """
        raise AttributeError("PebbleGLibConnection can only run asnchronously")

    def pump_reader(self):
        """ Don't use this """
        raise AttributeError("PebbleGLibConnection does not support this method")

    def _read_callback(self, origin, message):
        """ Handle incoming data """
        if isinstance(origin, MessageTargetWatch):
            self._handle_watch_message(message)
        else:
            self._broadcast_transport_message(origin, message)


class BluezProfile(dbus.service.Object):
    def __init__(self, user_code, conn=None, object_path=None, bus_name=None):
        super().__init__(conn, object_path, bus_name)
        self.fd = None
        self.user_code = user_code
        self.connections = {}

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}")
    def NewConnection(self, path, fd, properties):
        """ Called when a new connection is established """
        try:
            logger.info("Hello")
            self.fd = fd.take()
            pebble = PebbleGLibConnection(self.fd, True, True)
            logger.info("Connection established")
            localzone = tzlocal.get_localzone()
            pebble.send_packet(
                TimeMessage(message=SetUTC(
                    unix_time=int(time.time()),
                    utc_offset=int(localzone.utcoffset(datetime.now()).total_seconds() / 60),
                    tz_name=localzone.zone,
                )))
            logger.info("sent time packet")
            user_thread = Thread(target=self.user_code, args=[pebble])
            user_thread.start()
            self.connections[path] = pebble
        except Exception as e:
            logger.exception("Caught execption: {0}".format(e))
            print(e)
            traceback.print_exc()

    @dbus.service.method("org.bluez.Profile1", in_signature="o")
    def RequestDisconnection(self, path):
        """ Handle disconnection """
        print("disconnect")
        connection = self.connections.pop(path)
        connection.transport.disconnect()

    @dbus.service.method("org.bluez.Profile1")
    def Release(self):
        """ Called when the service daemon unregisters the profile """
        print("bye")
        for connection in self.connections.values():
            connection.transport.disconnect()


def register_profile(user_code, dbus_path):
    """ Register a new Bluez Profile"""
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"),
                             "org.bluez.ProfileManager1")

    profile = BluezProfile(user_code, bus, dbus_path)

    manager.RegisterProfile(dbus_path, BT_UUID, {"RequireAuthentication": False,
                                                 "RequireAuthorization": False,
                                                 "AutoConnect": True})
    print("registered, waiting for connections")
    return profile
