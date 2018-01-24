# logging_config.py - logging functionality for libpebble2-glib
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
""" Logging functionality for slideclicker """

import logging


def configure_logging():
    fomatstr = '%(asctime)s : %(name)s: %(levelname)s: %(message)s'
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(level=logging.INFO,
                        format=fomatstr,
                        datefmt=datefmt,
                        filename="libpebble2-glib.log")

    formatter = logging.Formatter(fomatstr, datefmt=datefmt)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.getLogger('libpebble2').addHandler(console)
    logging.getLogger('libpebble2.communication').addHandler(console)


def get(name):
    """ Alias for logging.getLogger(name) """
    return logging.getLogger(name)

