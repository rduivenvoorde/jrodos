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
from extended_combo import ExtendedCombo

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_dialog_base.ui'))


class JRodosDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # Replace the default ComboBox's with our better ExtendedCombo widget
        self.combo_project.close()  # this apparently also removes the widget??
        self.combo_project = ExtendedCombo()
        self.gridLayout.addWidget(self.combo_project, 0, 1, 1, 4) # row, col, #rows, #cols

        # self.combo_task.close()  # this apparently also removes the widget??
        # self.combo_task = ExtendedCombo()
        # self.gridLayout.addWidget(self.combo_task, 1, 1, 1, 4) # row, col, #rows, #cols

        self.combo_path.close()  # this apparently also removes the widget??
        self.combo_path = ExtendedCombo()
        self.gridLayout.addWidget(self.combo_path, 2, 1, 1, 4) # row, col, #rows, #cols