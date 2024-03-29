# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodos
                                 A QGIS plugin
 Plugin to connect to JRodos via WPS
                             -------------------
        begin                : 2016-04-18
        copyright            : (C) 2016 by Zuidt
        email                : richard@zuidt.nl
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import logging

"""
The name of logger we use in this plugin.
It is created in the plugin.py and logs to the QgsMessageLog under the 
given LOGGER_NAME tab
"""
LOGGER_NAME = 'JRodos3 Plugin'
from . import LOGGER_NAME
from qgis.core import (
    Qgis
)

class QgisLogHandler(logging.StreamHandler):
    '''
    Some magic to make it possible to use code like:

    import logging
    from . import LOGGER_NAME
    log = logging.getLogger(LOGGER_NAME)

    in all this plugin code, and it will show up in the QgsMessageLog

    '''
    def __init__(self, topic):
        logging.StreamHandler.__init__(self)
        # topic is used both as logger id and for tab
        self.topic = topic

    def emit(self, record):
        msg = self.format(record)
        # Below makes sure that logging of 'self' will show the repr of the object
        # Without this it will not be shown because it is something like
        # <qgisnetworklogger.plugin.QgisNetworkLogger object at 0x7f580dac6b38>
        # which looks like an html element so is not shown in the html panel
        msg = msg.replace('<', '&lt;').replace('>', '&gt;')
        from qgis.core import QgsMessageLog  # we need this... else QgsMessageLog is None after a plugin reload
        QgsMessageLog.logMessage('{}'.format(msg), self.topic, Qgis.Info)

log = logging.getLogger(LOGGER_NAME)
# checking below is needed, else we add this handler every time the plugin
# is reloaded (during development), then the msg is emitted several times
if not log.hasHandlers():
    log.addHandler(QgisLogHandler(LOGGER_NAME))

# set logging level (NOTSET = no, else: DEBUG or INFO)
log.setLevel(logging.DEBUG)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load JRodos class from file JRodos.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .jrodos import JRodos
    return JRodos(iface)
