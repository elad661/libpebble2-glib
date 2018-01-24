libpebble2-glib
===============

What
----
An adapter for libpebble2 to make it usable with the BlueZ 5 DBus API and
the GLib mainloop.


Why
---
libpebble2 allows connecting to a real pebble watch over
bluetooth serial, but this means you have to use command line tools
to connect to the watch, and you have to be root to chmod the bluetooth rfcomm
device file so you can actually use it.

This is simply not good enough when you want to write an app that runs as
a regular user and uses the BlueZ 5 DBus API.


It's a bit of a hack (Usage)
----------------------------
See `example.py`.

Basically, you need to call `register_profile`, which registers a Bluetooh
profile with BlueZ 5, and start the GLib mainloop. When the watch connects,
BlueZ will use dbus to call into the profile object, at which point
a connection will be established and the callback you give `register_profile`
will be called.

Because I didn't want to re-write the entireity of libpebble2 to make it fully
asynchrounous (so it won't block the mainloop), the callback is called in
a new thread.

License
-------
GPLv3+. See COPYING for the full license text.

Written by Elad Alfassa.
