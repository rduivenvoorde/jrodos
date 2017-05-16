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

from PyQt4 import uic
from PyQt4.QtGui import QDockWidget

from .. import pyqtgraph as pg
import time
import numpy as np

# , QSizePolicy, QPen, QBrush
# from PyQt4.QtCore import Qt, QSize
# from PyQt4.Qwt5 import QwtPlot, QwtPlotCurve, QwtScaleDiv, QwtSymbol, QwtLog10ScaleEngine


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

        axis = DateAxis(orientation='bottom')

        # Switch to using white background and black foreground
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        pw = pg.PlotWidget(axisItems={'bottom': axis},
                           enableMenu=False,
                           title="y: USV/H    x: time")
        #pw = pg.PlotWidget(title="y: USV/H    x: time")
        #pw.setYRange(0.06, 0.15, update=True)
        pw.show()
        self.graph = pw

        # ROI = Region Of Interest
        #r = pg.PolyLineROI([(0, 0), (10, 10)])
        #pw.addItem(r)

        self.setWidget(pw)


class DateAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strns = []
        rng = max(values) - min(values)
        # if rng < 120:
        #    return pg.AxisItem.tickStrings(self, values, scale, spacing)
        if rng < 3600 * 24:
            string = '%H:%M:%S'
            label1 = '%b %d -'
            label2 = ' %b %d, %Y'
        elif rng >= 3600 * 24 and rng < 3600 * 24 * 30:
            string = '%d'
            label1 = '%b - '
            label2 = '%b, %Y'
        elif rng >= 3600 * 24 * 30 and rng < 3600 * 24 * 30 * 24:
            string = '%b'
            label1 = '%Y -'
            label2 = ' %Y'
        elif rng >= 3600 * 24 * 30 * 24:
            string = '%Y'
            label1 = ''
            label2 = ''
        for x in values:
            try:
                strns.append(time.strftime(string, time.localtime(x)))
            except ValueError:  ## Windows can't handle dates before 1970
                strns.append('')
        try:
            label = time.strftime(label1, time.localtime(min(values))) + time.strftime(label2,
                                                                                       time.localtime(max(values)))
        except ValueError:
            label = ''
        # self.setLabel(text=label)
        return strns

