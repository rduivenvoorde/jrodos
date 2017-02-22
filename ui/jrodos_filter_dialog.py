# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodosFilterDialog
                        
 Dialog to be used to create filtered selection boxes
 
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

from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDialog, QSortFilterProxyModel, QAbstractItemView, QColor

from .. constants import QMODEL_ID_IDX, QMODEL_NAME_IDX, QMODEL_DESCRIPTION_IDX, QMODEL_DATA_IDX, QMODEL_SEARCH_IDX

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_filter_dialog_base.ui'))


class JRodosFilterDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosFilterDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.tbl_items.setDragEnabled(False)
        self.tbl_items.setSelectionBehavior(self.tbl_items.SelectRows)
        self.tbl_items.setSelectionMode(self.tbl_items.NoSelection)
        self.tbl_items.clicked.connect(self.toggle_user_filter)
        self.tbl_items.setSortingEnabled(True)
        self.le_item_filter.textChanged.connect(self.filter_items)
        self.user_data_items = None
        self.proxy_model = None

    def set_model(self, item_model=None):
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(item_model)
        self.proxy_model.setFilterKeyColumn(QMODEL_DATA_IDX)
        self.tbl_items.setModel(self.proxy_model)
        self.tbl_items.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # precolor all rows
        for row in range(0, self.tbl_items.model().rowCount()):
            self.color_model(row)

        item_model.setHeaderData(QMODEL_NAME_IDX, Qt.Horizontal, "Name")
        item_model.setHeaderData(QMODEL_DESCRIPTION_IDX, Qt.Horizontal, "Description")
        item_model.setHeaderData(QMODEL_SEARCH_IDX, Qt.Horizontal, "Show")

        self.tbl_items.setColumnHidden(QMODEL_ID_IDX, True)
        self.tbl_items.setColumnHidden(QMODEL_DATA_IDX, True)
        # self.tbl_items.setColumnHidden(QMODEL_SEARCH_IDX, True)

        self.tbl_items.setColumnWidth(QMODEL_NAME_IDX, 250)  # set name to 300px (there are some huge layernames)
        self.tbl_items.setColumnWidth(QMODEL_DESCRIPTION_IDX, 600)
        self.tbl_items.horizontalHeader().setStretchLastSection(True)

    def filter_items(self, string):
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterFixedString(string)

    def toggle_user_filter(self, model_index):
        row = model_index.row()
        idx = self.tbl_items.model().index(row, QMODEL_SEARCH_IDX)
        selected = '1'
        if self.tbl_items.model().data(idx) == '1':
            selected = '0'
        self.tbl_items.model().setData(idx, selected)
        self.color_model(row)

    def color_model(self, row):
        # color background based on selected ('1') or not
        idx = self.tbl_items.model().index(row, QMODEL_SEARCH_IDX)
        color = Qt.lightGray
        if self.tbl_items.model().data(idx) == '1':
            color = Qt.white
        for i in range(0, self.tbl_items.model().columnCount()):
            idx2 = self.tbl_items.model().index(row, i)
            self.tbl_items.model().setData(idx2, QColor(color), Qt.BackgroundRole)




