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
from qgis.PyQt.QtWidgets import QDialog, QAbstractItemView, QPushButton, QDialogButtonBox
from qgis.PyQt import uic
from ..utils import Utils

from .. constants import QMODEL_ID_IDX, QMODEL_NAME_IDX, QMODEL_DESCRIPTION_IDX, QMODEL_DATA_IDX, QMODEL_SEARCH_IDX


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_dialog_base.ui'))


class JRodosDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.proxy_model = None

        self.tbl_projects.setSelectionBehavior(self.tbl_projects.SelectRows)
        self.le_project_filter.textChanged.connect(self.filter_projects)

        # Adding a SKIP button which sets a propertye 'self.skipped' when clicked
        self.skipped = False
        self.skip_button = QPushButton('Skip')
        self.skip_button.setCheckable(False)
        self.skip_button.setAutoDefault(False)
        self.skip_button.clicked.connect(self.set_skipped)

        self.button_box.addButton(self.skip_button, QDialogButtonBox.RejectRole)

    def set_skipped(self):
        self.skipped = True

    def filter_projects(self, string):
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterFixedString(string)
        # store the filter/search string so upon showing the dialog it will show a filtered project list again
        Utils.set_settings_value("jrodos_last_project_filter", string)

    def set_model(self, item_model=None):
        self.skipped = False  # resetting
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(item_model)

        self.proxy_model.setFilterKeyColumn(QMODEL_SEARCH_IDX)
        self.tbl_projects.setModel(self.proxy_model)
        self.tbl_projects.setEditTriggers(QAbstractItemView.NoEditTriggers)

        item_model.setHeaderData(QMODEL_NAME_IDX, Qt.Horizontal, "Name")
        item_model.setHeaderData(QMODEL_DESCRIPTION_IDX, Qt.Horizontal, "Description")
        item_model.setHeaderData(QMODEL_SEARCH_IDX, Qt.Horizontal, "Search")

        self.tbl_projects.verticalHeader().setVisible(False)

        self.tbl_projects.setColumnHidden(QMODEL_ID_IDX, True)
        self.tbl_projects.setColumnHidden(QMODEL_DATA_IDX, True)
        self.tbl_projects.setColumnHidden(QMODEL_SEARCH_IDX, True)

        self.tbl_projects.setColumnWidth(QMODEL_NAME_IDX, 150)  # set name to 300px (there are some huge layernames)
        #self.tbl_projects.setColumnWidth(QMODEL_DESCRIPTION_IDX, 600)
        self.tbl_projects.horizontalHeader().setStretchLastSection(True)
