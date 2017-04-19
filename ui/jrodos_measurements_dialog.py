# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodosDialog
                                 A QGIS plugin
 Plugin to connect to JRodos via WPS
                             -------------------
        begin                : 2016-04-18
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Zuidt
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

from PyQt4 import QtGui, uic
from extended_combo import ExtendedCombo

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_measurements_dialog_base.ui'))


class JRodosMeasurementsDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosMeasurementsDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/ designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.MEASUREMENTS_ENDMINUSTART = ['0', '600', '3600', '86400']
        self.combo_endminusstart.addItems(self.MEASUREMENTS_ENDMINUSTART)
        self.combo_endminusstart.setCurrentIndex(1)

        # Replace the default ComboBox with our better ExtendedCombo
        # self.measurements_dlg.gridLayout.removeWidget(self.measurements_dlg.combo_quantity)
        self.combo_quantity.close()  # this apparently also removes the widget??
        self.combo_quantity = ExtendedCombo()
        self.gridLayout.addWidget(self.combo_quantity, 3, 1, 1, 1)  # row, col, #rows, #cols

        # Replace the default ComboBox with our better ExtendedCombo
        # self.measurements_dlg.gridLayout.removeWidget(self.measurements_dlg.combo_quantity)
        self.combo_substance.close()  # this apparently also removes the widget??
        self.combo_substance = ExtendedCombo()
        self.gridLayout.addWidget(self.combo_substance, 4, 1, 1, 1)  # row, col, #rows, #cols


