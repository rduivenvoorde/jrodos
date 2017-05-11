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
from PyQt4.QtGui import QDockWidget, QSizePolicy, QPen, QBrush
from PyQt4.QtCore import Qt, QSize

from PyQt4.Qwt5 import QwtPlot, QwtPlotCurve, QwtScaleDiv, QwtSymbol


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

        # Setup Qwt Plot Area in Widget
        #self.qwtPlot = QwtPlot()
        # self.qwtPlot.setAutoFillBackground(False)
        # self.qwtPlot.setObjectName("qwtPlot")
        # self.curve = QwtPlotCurve()
        # self.curve.setSymbol(
        #     QwtSymbol(QwtSymbol.Ellipse,
        #               QBrush(Qt.white),
        #               QPen(Qt.red, 2),
        #               QSize(9, 9)))
        # self.curve.attach(self.qwtPlot)
        #
        # # Size Policy ???
        # sizePolicy = QSizePolicy(QSizePolicy.Expanding,
        #                                QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.qwtPlot.sizePolicy().hasHeightForWidth())
        # self.qwtPlot.setSizePolicy(sizePolicy)
        # # Size Policy ???
        #
        # self.qwtPlot.updateGeometry()
        # self.addWidget(self.qwtPlot)
        # self.qwt_widgetnumber = self.stackedWidget.indexOf(self.qwtPlot)
