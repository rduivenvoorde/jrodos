# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodosGraphWidget

 DockedWidget to be used to show plots/graps of measurement periods

                             -------------------
        begin                : 2017-05-11
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Zuidt
        email                : richard@zuidt.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt import uic

from .. import pyqtgraph as pg
import time

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_graph_widget.ui'))


class JRodosGraphWidget(QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosGraphWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # RD: hopefully fix exit errors from pyqtgraph
        pg.setConfigOptions(exitCleanup=False)

        x_axis = DateAxis(orientation='bottom', pen='333333')
        y_axis = pg.AxisItem(orientation='left', pen='333333')

        font = QFont()
        font.setPixelSize(10)
        x_axis.tickFont = font
        y_axis.tickFont = font

        # Switch to using white background and black foreground
        pg.setConfigOption('background', 'ffffff')
        pg.setConfigOption('foreground', '000000')

        pw = pg.PlotWidget(axisItems={'bottom': x_axis, 'left': y_axis},
                           enableMenu=False,
                           title="y: Values  -   x: Time")

        pw.show()
        self.graph = pw

        # ROI = Region Of Interest
        r = pg.PolyLineROI([(0, 0), (10, 10)])
        pw.addItem(r)

        self.setWidget(pw)


class DateAxis(pg.AxisItem):

    def tickStrings(self, values, scale, spacing):
        tick_strings = []

        if len(values) == 0:
            return tick_strings
        elif len(values) == 1:
            # just one value... probably a 'major tick':
            # do date / time
            string = '%d/%m %H:%M'
            label1 = '%b - '
            label2 = '%b, %Y'
        else:
            rng = max(values) - min(values)

            if rng < 3600 * 1:  # < 1 hour
                string = '%H:%M:%S'
                label1 = '%b %d -'
                label2 = ' %b %d, %Y'
            elif rng >= 3600 * 1 and rng < 3600 * 24 * 5:  # 1 hour - 5 day
                string = '%H:%M'
                label1 = '%b %d -'
                label2 = ' %b %d, %Y'
            elif rng >= 3600 * 24 * 5 and rng < 3600 * 24 * 30:  # 5 day - 1 month
                string = '%d/%m %H:%M'
                label1 = '%b - '
                label2 = '%b, %Y'
            elif rng >= 3600 * 24 * 30 and rng < 3600 * 24 * 30 * 24:  # 1 month  - 2 years
                string = '%b'
                label1 = '%Y -'
                label2 = ' %Y'
            elif rng >= 3600 * 24 * 30 * 24:  # > 2 years
                string = '%Y'
                label1 = ''
                label2 = ''

        for x in values:
            try:
                tick_strings.append(time.strftime(string, time.localtime(x)))
            except ValueError:  ## Windows can't handle dates before 1970
                tick_strings.append('')

        # try:
        #     label = time.strftime(label1, time.localtime(min(values))) + time.strftime(label2, time.localtime(max(values)))
        # except ValueError:
        #     label = '@'
        # self.setLabel(text=label)

        return tick_strings

