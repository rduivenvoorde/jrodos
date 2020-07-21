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

from qgis.PyQt.QtCore import Qt, QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QTableView, QPushButton, QDialogButtonBox
from qgis.PyQt import uic

#from extended_combo import ExtendedCombo

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_measurements_dialog_base.ui'))


class JRodosMeasurementsDialog(QDialog, FORM_CLASS):
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

        self.combis_progressbar.setMaximum(100)

        # make model searchable and sortable
        self.proxy_model = None
        self.le_combis_filter.textChanged.connect(self.filter_combis)

        # Adding a SKIP button which just cancels/rejects this dialog
        self.skipped = False
        self.skip_button = QPushButton('Skip')
        self.skip_button.setCheckable(False)
        self.skip_button.setAutoDefault(False)

        self.buttonBox.addButton(self.skip_button, QDialogButtonBox.RejectRole)

    def set_model(self, item_model=None):
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(item_model)

        self.proxy_model.setFilterKeyColumn(0)
        self.tbl_combis.setModel(self.proxy_model)
        
        self.tbl_combis.setDragEnabled(False)
        self.tbl_combis.setSelectionBehavior(QTableView.SelectRows)
        self.tbl_combis.setSelectionMode(QTableView.NoSelection)
        self.tbl_combis.setEditTriggers(QTableView.NoEditTriggers)  # disable editing of table cells

        item_model.setHeaderData(0, Qt.Horizontal, self.tr("Description"))
        item_model.setHeaderData(1, Qt.Horizontal, self.tr("Quantity"))
        item_model.setHeaderData(2, Qt.Horizontal, self.tr("Substance"))
        item_model.setHeaderData(4, Qt.Horizontal, self.tr("Select"))

        self.tbl_combis.setColumnWidth(0, 400)
        self.tbl_combis.setColumnWidth(1, 300)
        self.tbl_combis.setColumnWidth(2, 300)

        self.tbl_combis.setColumnHidden(0, True)  # hiding Description column
        self.tbl_combis.setColumnHidden(3, True)
        self.tbl_combis.setColumnHidden(6, False)

        self.tbl_combis.horizontalHeader().setStretchLastSection(True)
        # sort on first column so it is clear to the user it IS sortable (little triangle is shown in header)
        self.tbl_combis.sortByColumn(0, Qt.AscendingOrder)        

    def filter_combis(self, string):
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterFixedString(string)

    def startProgressBar(self):
        self.combis_progressbar.setMaximum(0)

    def stopProgressBar(self):
        self.combis_progressbar.setMaximum(100)

