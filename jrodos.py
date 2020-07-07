# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodos
                                 A QGIS plugin
 Plugin to connect to JRodos via WPS and Retrieve measurements via WFS
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
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QVariant, \
    QCoreApplication, QDateTime, Qt, QUrl, QSortFilterProxyModel, QLocale
from qgis.PyQt.QtGui import QIcon, QStandardItemModel, QStandardItem, \
    QDesktopServices,  QColor, QFont
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QProgressBar, QToolBar, \
    QFileDialog, QTableView, QCheckBox
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, Qgis, \
    QgsRasterLayer, QgsFeatureRequest, QgsGeometry, \
    QgsExpression, QgsRuleBasedRenderer, QgsSymbol, QgsProject, QgsApplication

from qgis.utils import qgsfunction, plugins
from qgis.gui import QgsVertexMarker

from .pyqtgraph import CurvePoint, TextItem, PlotCurveItem

from glob import glob
import re
from datetime import datetime
from copy import deepcopy

import os.path
import json
import sys
import pickle

from .utils import Utils
from .ui import JRodosMeasurementsDialog, JRodosDialog, JRodosFilterDialog, JRodosGraphWidget
from .jrodos_settings import JRodosSettings
from .jrodos_settings_dialog import JRodosSettingsDialog
from .providers.calnet_measurements_provider import CalnetMeasurementsConfig, CalnetMeasurementsProvider
from .providers.calnet_measurements_utils_provider import CalnetMeasurementsUtilsConfig, CalnetMeasurementsUtilsProvider
from .providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from .providers.jrodos_model_output_provider import JRodosModelOutputConfig, JRodosModelOutputProvider, JRodosModelProvider
from .providers.utils import Utils as ProviderUtils

from .style_utils import RangeCreator

from . import resources  # needed for button images!

# silly try catch around this one, because
# IF user has timemanager installed it can be loaded here
# IF NOT timemanager installed this raises an exception
# the late import in the run method apparently does not work??
# noinspection PyBroadException
try:
    from timemanager.layers.layer_settings import LayerSettings
    from timemanager.layers.timevectorlayer import TimeVectorLayer
    from timemanager.raster.wmstlayer import WMSTRasterLayer
except Exception as e:
    pass

# pycharm debugging
# COMMENT OUT BEFORE PACKAGING !!!
# import pydevd
# pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)

import logging
from . import LOGGER_NAME
log = logging.getLogger(LOGGER_NAME)


class JRodos:
    """QGIS Plugin Implementation."""

    """ DEV modus for development
    in case of failing of needed network services, will try to load dummy or demo data
    """
    DEV = False

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize Language
        language = QSettings().value('locale/userLocale', QLocale().name())
        if language and len(language) >= 2:
            locale_path = os.path.join(
                self.plugin_dir,
                'i18n',
                '{}.qm'.format(language))

            if os.path.exists(locale_path):
                self.translator = QTranslator()
                self.translator.load(locale_path)
                if qVersion() > '4.3.3':
                    QCoreApplication.installTranslator(self.translator)

        self.MSG_TITLE = self.tr("JRodos Plugin")

        # NOTE !!! project names surrounded by single quotes ??????
        self.JRODOS_PROJECTS = ["wps-13sept-test"]

        # indexes for the data coming from Utils providers
        self.JRODOS_DESCRIPTION_IDX = 0
        self.JRODOS_CODE_IDX = 1

        # TODO: remove these in favour of constants-versions (from constants import ... like in jrodos_filter_dialog.py)
        # 'standard' column indexes for QStandardModels to be used instead of magic numbers for data columns:
        self.QMODEL_ID_IDX = 0  # IF the QStandardModel has a true ID make it column 0 (else double NAME as 0)
        self.QMODEL_NAME_IDX = 1  # IF the QStandardModel has a short name (not unique?) (else double ID as 1)
        self.QMODEL_DESCRIPTION_IDX = 2  # IF the QStandardModel has a description (eg used in dropdowns)
        self.QMODEL_DATA_IDX = 3  # IF the QStandardModel has other data
        self.QMODEL_SEARCH_IDX = 4  # IF the QStandardModel has a special SEARCH/FILTER column (optional for tables)

        self.MAX_FLOAT = sys.float_info.max

        self.USER_DATA_ITEMS_PATH = self.plugin_dir + '/jrodos_user_data_items.pickle'
        self.USER_QUANTITIES_SUBSTANCES_PATH = self.plugin_dir + '/jrodos_user_quanties_substances.pickle'

        self.BAR_LOADING_TITLE = self.tr('Loading data...')
        self.JRODOS_BAR_TITLE = self.tr('JRodos Model')

        self.MEASUREMENTS_BAR_TITLE = self.tr('Measurements')

        self.settings = JRodosSettings()

        # QAbstractItems model for the datapaths in the JRodos dialog
        self.jrodos_project_data = []

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&JRodos')
        self.toolbar = self.get_rivm_toolbar()

        self.jrodos_output_progress_bar = None
        self.jrodos_output_settings = None
        self.jrodos_output_provider = None

        # JRodos model dialog
        self.jrodosmodel_dlg = None
        self.project_info_provider = None
        # dialog for measurements
        self.measurements_dlg = None
        self.measurements_progress_bar = None
        self.measurements_settings = None
        self.measurements_provider = None
        self.measurements_layer_featuresource = None
        self.quantities_model = None
        self.substances_model = None
        self.projects_model = None
        self.quantities_substances_model = None
        self.task_model = None

        self.measurements_layer = None
        self.start_time = None
        self.end_time = None
        self.combis = None
        self.combi_descriptions = None
        # substances and quantitites for Measurements dialog (filled via SOAP with CalnetMeasurementsUtilsProvider)
        self.quantities = [{'code': 0, 'description': self.tr('Trying to retrieve quantities...')}]
        self.substances = [{'code': 0, 'description': self.tr('Trying to retrieve substances...')}]
        # dialog to filter long lists
        self.filter_dlg = None

        # graph widget
        self.graph_widget = None
        self.graph_widget_checkbox = None
        # QgsVertexMarker used to highlight the measurement device shown in the GraphWidget
        self.graph_device_pointer = None
        self.curves = {}  # a curve <-> device,feature mapping as lookup for later use

        # settings dialog
        self.settings_dlg = None
        # creating a dict for a layer <-> settings mapping
        self.jrodos_settings = {}

        self.layer_group = None

        self.oldCrsBehavior = 'useGlobal'
        self.oldCrs = 'EPSG:4326'

        self.date_time_format_short = 'yyyy/MM/dd HH:mm'  # '17/6 23:01'

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('JRodos', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/JRodos/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Show Measurements and JRodos ModelDialog'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # settings
        icon_path = ':/plugins/JRodos/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Show Settings'),
            callback=self.show_settings,
            add_to_toolbar=False,
            parent=self.iface.mainWindow())

        # documentation
        icon_path = ':/plugins/JRodos/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Documentation'),
            callback=self.show_help,
            add_to_toolbar=False,
            parent=self.iface.mainWindow())

        progress_bar_width = 100

        if self.jrodos_output_progress_bar is None:
            self.jrodos_output_progress_bar = QProgressBar()
            self.jrodos_output_progress_bar.setToolTip(self.tr("Model data (WPS)"))
            self.jrodos_output_progress_bar.setTextVisible(True)
            self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)
            self.jrodos_output_progress_bar.setMinimum(0)
            self.jrodos_output_progress_bar.setMaximum(100)  # we will use a 'infinite progress bar' by setting max to zero when busy
            self.jrodos_output_progress_bar.setValue(0)
            self.jrodos_output_progress_bar.setFixedWidth(progress_bar_width)
            self.jrodos_output_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # to be able to remove the progressbar (by removing the action), we 'catch' the action and add it to self.actions
            action = self.toolbar.addWidget(self.jrodos_output_progress_bar)
            self.actions.append(action)

        if self.measurements_progress_bar is None:
            self.measurements_progress_bar = QProgressBar()
            self.measurements_progress_bar.setToolTip(self.tr("Measurement data (WFS)"))
            self.measurements_progress_bar.setTextVisible(True)
            self.measurements_progress_bar.setFormat(self.MEASUREMENTS_BAR_TITLE)
            self.measurements_progress_bar.setMinimum(0)
            self.measurements_progress_bar.setMaximum(100)  # we will use a 'infinite progress bar' by setting max to zero when busy
            self.measurements_progress_bar.setValue(0)
            self.measurements_progress_bar.setFixedWidth(progress_bar_width)
            self.measurements_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # to be able to remove the progressbar (by removing the action), we 'catch' the action and add it to self.actions
            action = self.toolbar.addWidget(self.measurements_progress_bar)
            self.actions.append(action)

        if self.graph_widget_checkbox is None:
            self.graph_widget_checkbox = QCheckBox(self.tr('Show Time Graph'))
            self.graph_widget_checkbox.setToolTip(self.tr('Selecting features will be shown in Graph'))
            # to be able to remove the progressbar (by removing the action), we 'catch' the action and add it to self.actions
            action = self.toolbar.addWidget(self.graph_widget_checkbox)
            self.actions.append(action)
            self.graph_widget_checkbox.clicked.connect(self.show_graph_widget)

        # loading a JRodos Shapefile + sld
        # icon_path = ':/plugins/JRodos/icon.png'
        # self.add_action(
        #     icon_path,
        #     text=self.tr(u'Load JRodos Shapefile (.shp) and Style (.sld)'),
        #     callback=self.load_jrodos_shape,
        #     add_to_toolbar=True,
        #     parent=self.iface.mainWindow())

        # Create the dialog (after translation) and keep reference
        self.jrodosmodel_dlg = JRodosDialog(self.iface.mainWindow())
        # connect the change of the project dropdown to a refresh of the data path
        self.jrodosmodel_dlg.tbl_projects.clicked.connect(self.project_selected)
        self.jrodosmodel_dlg.combo_task.currentIndexChanged.connect(self.task_selected)
        self.jrodosmodel_dlg.btn_item_filter.clicked.connect(self.show_data_item_filter_dialog)

        # Create the filter dialog
        self.filter_dlg = JRodosFilterDialog(self.jrodosmodel_dlg)
        self.filter_dlg.le_item_filter.setPlaceholderText(self.tr('Search in items'))

        # Create the measurements dialog
        self.measurements_dlg = JRodosMeasurementsDialog(self.iface.mainWindow())
        self.measurements_dlg.btn_get_combis.clicked.connect(self.get_quantities_and_substances_combis)
        self.measurements_dlg.tbl_combis.clicked.connect(self.quantities_substances_toggle)
        self.measurements_dlg.btn_now.clicked.connect(self.set_measurements_time)
        # self.quantities_substance_provider_finished(None)  # development
        # to be able to retrieve a reasonable quantities-substance combination
        # in the background, we HAVE TO set the start/end dates to a reasonable
        # value BEFORE the dlg is already shown...
        end_time = QDateTime.currentDateTimeUtc()  # end is NOW
        start_time = end_time.addSecs(-60 * 60 * 30 * 24)  # minus 24 hour
        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        self.measurements_dlg.cb_a1.clicked.connect(self.cb_a1_clicked)
        self.measurements_dlg.cb_a2.clicked.connect(self.cb_a2_clicked)
        self.measurements_dlg.cb_a3.clicked.connect(self.cb_a3_clicked)
        self.measurements_dlg.cb_a4.clicked.connect(self.cb_a4_clicked)
        self.measurements_dlg.cb_a5.clicked.connect(self.cb_a5_clicked)
        self.measurements_dlg.cb_unknown.clicked.connect(self.cb_unknown_clicked)
        self.filter_dlg.le_item_filter.setPlaceholderText(self.tr('Filter project list'))

        self.measurements_dlg.btn_all_combis.clicked.connect(lambda: self.quantities_substances_set_all(True))
        self.measurements_dlg.btn_no_combis.clicked.connect(lambda: self.quantities_substances_set_all(False))

        # Create the settings dialog
        self.settings_dlg = JRodosSettingsDialog(self.iface.mainWindow())

        # Create GraphWidget
        self.graph_widget = JRodosGraphWidget()

        # Make sure that when a QGIS layer is removed it will also be removed from the plugin
        QgsProject.instance().layerWillBeRemoved.connect(self.remove_jrodos_layer)

    # TODO: move this to a commons class/module
    def get_rivm_toolbar(self):
        toolbar_title = 'RIVM Cal-Net Toolbar'  # TODO get this from commons and make translatable
        toolbars = self.iface.mainWindow().findChildren(QToolBar, toolbar_title)
        if len(toolbars) == 0:
            toolbar = self.iface.addToolBar(toolbar_title)
            toolbar.setObjectName(toolbar_title)
        else:
            toolbar = toolbars[0]
        return toolbar

    def show_settings(self):
        self.settings_dlg.show()

    def show_data_item_filter_dialog(self):
        # load saved user data_items from pickled file
        self.filter_dlg.le_item_filter.setText('')
        self.filter_dlg.show()
        # OK pressed:
        if self.filter_dlg.exec_():
            # save user data_items
            data_items = []
            for task_model in self.jrodos_project_data:
                # run over model, and check if SEARCH column is 1
                for row in range(0, task_model.rowCount()):
                    if task_model.item(row, self.QMODEL_SEARCH_IDX).text() == '1':
                        data_item = task_model.item(row, self.QMODEL_DATA_IDX).text()
                        data_items.append(data_item)
            # pickling the user_data_items to disk
            with open(self.USER_DATA_ITEMS_PATH, 'wb') as f:
                pickle.dump(data_items, f)

    @staticmethod
    def show_help():
        docs = os.path.join(os.path.dirname(__file__), "help/html", "index.html")
        QDesktopServices.openUrl(QUrl("file:" + docs))

    def show_graph_widget(self, checked):
        if checked:
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.graph_widget)
        else:
            self.graph_widget.hide()

    # noinspection PyBroadException
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&JRodos'),
                action)
            # self.iface.removeToolBarIcon(action)
            self.toolbar.removeAction(action)

        # deregister our custom QgsExpression function
        QgsExpression.unregisterFunction("measurement_values")
        QgsProject.instance().layerWillBeRemoved.disconnect(self.remove_jrodos_layer)
        # remove pointer
        self.remove_device_pointer()

        # IF there is a measurement layer disconnect selectionChanged signal
        if self.measurements_layer is not None:
            self.measurements_layer.selectionChanged.disconnect(self.measurement_selection_change)

        # IF there is a JRodos group... try to remove it (sometimes deleted?)
        try:
            if self.layer_group is not None:
                root = QgsProject.instance().layerTreeRoot()
                root.removeChildNode(self.layer_group)
        except Exception:
            pass

        # delete the graph widget
        del self.graph_widget

    def run(self):

        try:

            if 'RIVM_PluginConfigManager' not in plugins:
                QMessageBox.warning(self.iface.mainWindow(),
                                    self.MSG_TITLE,
                                    self.tr("Missing 'RIVM PluginConfigManager' plugin,\n we REALLY need that one.\n Please install via Plugin Manager first..."),
                                    QMessageBox.Ok,
                                    QMessageBox.Ok)
                return

            if 'timemanager' not in plugins:
                QMessageBox.warning(self.iface.mainWindow(),
                                    self.MSG_TITLE, self.tr("Missing 'TimeManager' plugin,\n we REALLY need that one.\n Please install via Plugin Manager first..."),
                                    QMessageBox.Ok,
                                    QMessageBox.Ok)

                return
            # Because we check for timemanager, not earlier then now
            # we import timemanager modules here (else module import error)
            from timemanager.layers.layer_settings import LayerSettings
            from timemanager.layers.timevectorlayer import TimeVectorLayer
            from timemanager.raster.wmstlayer import WMSTRasterLayer

            self.setProjectionsBehavior()
            
            # create a 'JRodos layer' group if not already there ( always on TOP == 0 )
            if self.measurements_layer is None and self.jrodos_output_settings is None:
                group_name = self.tr('JRodos plugin layers')
                # BUT only if there isn't already such a group:
                if QgsProject.instance().layerTreeRoot().findGroup(group_name) is None:
                    self.layer_group = QgsProject.instance().layerTreeRoot().insertGroup(0, group_name)
                    
            # only show dialogs if the item is enabled in settings
            # but show settings in case both are disabled
            if not self.settings.value('jrodos_enabled') and not self.settings.value('measurements_enabled'):
                self.msg(None, self.tr("Both dialogs are disabled in your settings.\n Either select 'JRodos Geoserver WPS' or 'Measurements WFS' in the following settings dialog."))
                self.show_settings()

            if self.settings.value('jrodos_enabled'):

                if self.jrodos_output_settings is not None:  # flag to tell us we are busy
                    self.msg(None, self.tr("Still busy retrieving Model data via WPS, please try later...\nOr disable/enable plugin if you want to abort that run."))
                    return False

                # try to get fresh jrodos projects, AND put 'remembered' values in the dialog
                self.get_jrodos_projects()

                # disable 'Skip' button if Measurements WFS is disabled
                self.jrodosmodel_dlg.skip_button.setEnabled(self.settings.value('measurements_enabled'))
                # show dialog for input, untill OK is clicked
                ok = False
                while self.jrodosmodel_dlg.exec():  # OK was pressed = 1, Cancel = 0
                    if self.handle_jrodos_output_dialog():  # returns True IF succefully handled, else false
                        ok = True
                        break

                # if we are here, we either succesfully handled jrodos model OR we skipped or cancelled
                # if skip, go on, else Cancel: return
                if not self.jrodosmodel_dlg.skipped and not ok:
                    return

            if self.settings.value('measurements_enabled'):
                finished = False
                while not finished:
                    finished = self.show_measurements_dialog()

        except JRodosError as jre:
            self.msg(None, "Exception in JRodos plugin: %s \nCheck the Log Message Panel for more info" % jre)
            return
        except Exception as ex:
            self.msg(None, "Exception in JRodos plugin: %s \nCheck the Log Message Panel for more info" % ex)
            raise

    def setProjectionsBehavior(self):
        # we do NOT want the default behavior: prompting for a crs
        # we want to set it to epsg:4326, see
        # http://gis.stackexchange.com/questions/27745/how-can-i-specify-the-crs-of-a-raster-layer-in-pyqgis
        s = QSettings()
        self.oldCrsBehavior = s.value("/Projections/defaultBehavior", "useGlobal")
        s.setValue("/Projections/defaultBehavior", "useGlobal")
        self.oldCrs = s.value("/Projections/layerDefaultCrs", "EPSG:4326")
        s.setValue("/Projections/layerDefaultCrs", "EPSG:4326")

    def unsetProjectionsBehavior(self):
        # change back to default action of asking for crs or whatever the old behavior was!
        s = QSettings()
        s.setValue("/Projections/defaultBehavior", self.oldCrsBehavior)
        s.setValue("/Projections/layerDefaultCrs", self.oldCrs)

    def get_quantities_and_substances_combis(self):
        log.debug("Getting Quantity/Substance combi's")
        self.measurements_dlg.lbl_retrieving_combis.setText("Searching possible Quantity/Substance combi's in this period ....")
        self.measurements_dlg.startProgressBar()
        config = CalnetMeasurementsUtilsConfig()
        config.url = self.settings.value('measurements_soap_utils_url')  # 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'

        start_date = self.measurements_dlg.dateTime_start.dateTime()  # UTC
        end_date = self.measurements_dlg.dateTime_end.dateTime()      # UTC

        config.start_datetime = start_date.toString(config.date_time_format)
        config.end_datetime = end_date.toString(config.date_time_format)

        quantities_substance_provider = CalnetMeasurementsUtilsProvider(config)
        quantities_substance_provider.finished.connect(self.quantities_substance_provider_finished)

        quantities_substance_provider.get_data('MeasuredCombinations')

    def quantities_substance_provider_finished(self, result):

        self.measurements_dlg.stopProgressBar()

        if hasattr(result, "error") and result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the Quantities-Substance combi's. \nCheck the Log Message Panel for more info"))
            self.measurements_dlg.lbl_retrieving_combis.setText("Nothing received, please try again.")
        else:
            self.combis = result.data
            self.combi_descriptions = {}

            # LOAD saved user data_items from pickled file
            user_quantities_substances_from_disk = []
            if os.path.isfile(self.USER_QUANTITIES_SUBSTANCES_PATH):
                with open(self.USER_QUANTITIES_SUBSTANCES_PATH, 'rb') as f:
                    user_quantities_substances_from_disk = pickle.load(f)
            self.measurements_dlg.lbl_retrieving_combis.setText(self.tr("Please select one or more combination(s)"))

            self.quantities_substances_model = QStandardItemModel()
            for combi in self.combis:
                description = '{}, {} - ({}, {})'.format(combi['quantity_desc'],
                                                        combi['substance_desc'],
                                                        combi['quantity'],
                                                        combi['substance'])
                self.combi_descriptions[combi['quantity']+'_'+combi['substance']] = f"{combi['quantity_desc']} - {combi['substance_desc']}"
                selected = False
                if [combi['quantity'], combi['substance']] in user_quantities_substances_from_disk:
                    selected = True
                data_item = QStandardItem("{}{}".format(combi['quantity'], combi['substance']))
                data_item.setData([combi['quantity'], combi['substance']])
                selected_item = QStandardItem(True)
                selected_item.setData(True)
                quantity_item = QStandardItem('{} ({})'.format(combi['quantity_desc'], combi['quantity']))
                substance_item = QStandardItem('{} ({})'.format(combi['substance_desc'], combi['substance']))
                # set tooltips to be able to read long description lines easier
                quantity_item.setData('{} ({})'.format(combi['quantity_desc'], combi['quantity']), Qt.ToolTipRole)
                substance_item.setData('{} ({})'.format(combi['substance_desc'], combi['substance']), Qt.ToolTipRole)
                self.quantities_substances_model.appendRow([
                    QStandardItem(description),
                    quantity_item,
                    substance_item,
                    data_item,
                    selected_item
                ])
                self.quantities_substances_model.setData(self.quantities_substances_model.indexFromItem(selected_item), selected)

            self.measurements_dlg.set_model(self.quantities_substances_model)
            # pre color rows
            for row in range(0, self.quantities_substances_model.rowCount()):
                self.quantities_substance_color_model(row)

    def quantities_substances_toggle(self, model_index):
        row = model_index.row()
        model = self.measurements_dlg.tbl_combis.model()
        idx = model.index(row, self.QMODEL_SEARCH_IDX)
        selected = True
        if model.data(idx):
            selected = False
        model.setData(idx, selected)
        self.quantities_substance_color_model(row)

    def quantities_substance_color_model(self, row):
        # color background based on selected (True) or not
        # incoming row is from proxy
        model = self.measurements_dlg.tbl_combis.model()
        idx = model.index(row, self.QMODEL_SEARCH_IDX)
        color = Qt.lightGray  # = 6
        if model.data(idx):
            color = Qt.white  # = 3
        for i in range(0, model.columnCount()):
            idx2 = model.index(row, i)
            model.setData(idx2, QColor(color), Qt.BackgroundRole)

    def quantities_substances_set_all(self, checked):
        model = self.measurements_dlg.tbl_combis.model()
        for row in range(0, model.rowCount()):
            idx = model.index(row, self.QMODEL_SEARCH_IDX)
            model.setData(idx, checked)
            self.quantities_substance_color_model(row)
        self.measurements_dlg.cb_a1.setChecked(checked)
        self.measurements_dlg.cb_a2.setChecked(checked)
        self.measurements_dlg.cb_a3.setChecked(checked)
        self.measurements_dlg.cb_a4.setChecked(checked)
        self.measurements_dlg.cb_a5.setChecked(checked)
        self.measurements_dlg.cb_unknown.setChecked(checked)

    def quantities_substances_toggle_selection_group(self, text, checked):
        model = self.measurements_dlg.tbl_combis.model()
        for row in range(0, model.rowCount()):
            idx = model.index(row, 3)
            data = model.data(idx)
            if text in data:
                idx = model.index(row, self.QMODEL_SEARCH_IDX)
                model.setData(idx, checked)
                self.quantities_substance_color_model(row)

    def cb_a1_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('A1', checked)

    def cb_a2_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('A2', checked)

    def cb_a3_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('A3', checked)

    def cb_a4_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('A4', checked)

    def cb_a5_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('A5', checked)

    def cb_unknown_clicked(self, checked):
        self.quantities_substances_toggle_selection_group('unknown', checked)

    def get_jrodos_projects(self):
        """Retrieve all JRodos projects via REST interface url like:
        http://geoserver.prd.cal-net.nl/rest-1.0-TEST-1/jrodos/projects

        If retrieved call 'projects_provider_finished' which will create a model from the result
        and try to fill the dialog with the last project used.

        """
        config = JRodosProjectConfig()
        config.url = self.settings.value('jrodos_rest_url')
        projects_provider = JRodosProjectProvider(config)
        projects_provider.finished.connect(self.projects_provider_finished)
        projects_provider.get_data('/projects')

    def projects_provider_finished(self, result):
        if result.error():
            self.msg(None,
                     self.tr(
                         "Problem in JRodos plugin retrieving the JRodos projects. \nCheck the Log Message Panel for more info"))
        else:
            # Projects: create a dropdown with name, description, id and link for every project

            # {
            #     "links"    [Object { rel="self",  href="http://jrodos.dev.cal-ne...service/jrodos/projects"}]
            #       0
            #         rel                   "self"
            #         href                  "http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects"
            #     "content"  [Object { projectId=142,  uid="0af53237-ac13-7293-0e16-2a357943d075",  name="test",  more...}, 216 more...]
            #       0 Object { projectId=142,  uid="0af53237-ac13-7293-0e16-2a357943d075",  name="test",  more...}
            #         projectId             142
            #         uid                   "0af53237-ac13-7293-0e16-2a357943d075"
            #         name                  "test"
            #         description	          ""
            #         username              "heezenp"
            #         modelchainname        "Emergency"
            #         tasks                 []
            #         dateTimeCreatedString "2015-06-19T10:35:18.200+02:00"
            #         dateTimeModifiedString"2015-06-19T10:35:18.200+02:00"
            #         links                 [Object { rel="self",  href="http://jrodos.dev.cal-ne...ice/jrodos/projects/142"}]
            #           0  	Object { rel="self",  href="http://jrodos.dev.cal-ne...ice/jrodos/projects/142"}
            #             rel   "self"
            #             href  "http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects/142"
            #       1 Object { projectId=143,  uid="0af53237-ac13-7293-0e16-2a357943d078",  name="test",  more...}
            #     ...
            # }
            self.projects_model = QStandardItemModel()
            # content in output is an array of projects
            projects = result.data['content']
            for project in projects:
                # retrieve the link of this project
                link = "NO LINK ?????"
                for link in project['links']:
                    if link['rel'] == 'self':
                        link = link['href']
                        break
                project_id = '{}'.format(project['projectId'])
                project_name = project['name']
                user_name = project['username']
                description = project['description']
                datetime_created = project['dateTimeCreated']  # isotimestring
                if QDateTime.fromString(datetime_created, Qt.ISODateWithMs).isValid():
                    datetime_created = QDateTime.fromString(datetime_created, Qt.ISODateWithMs).toString(self.date_time_format_short)
                else:
                    'no datetime_created?'

                # QStandardItems keep data as string, meaning we would not be able to sort these numeric ids
                # so we use a 'Qt.UserRole' for the sortable data: format all integer id's as zero padded 8 length numbers
                # BUT because you define which (data)-role you use for the sorting (model.setSortRole(Qt.UserRole))
                #   we have to setData(..., Qt.UserRole) for all columns
                project_id_item = QStandardItem(project_id)
                project_id_item.setData('{0:08d}'.format(int(project_id)), Qt.UserRole)

                project_name_item = QStandardItem(project_name)
                project_name_item.setData(project_name, Qt.UserRole)
                project_name_item.setData(description, Qt.ToolTipRole)

                project_description_item = QStandardItem(description)
                project_description_item.setData(description, Qt.UserRole)
                project_description_item.setData(description, Qt.ToolTipRole)

                user_item = QStandardItem(user_name)
                user_item.setData(user_name, Qt.UserRole)
                user_item.setData(description, Qt.ToolTipRole)

                datetime_created_item = QStandardItem(datetime_created)
                datetime_created_item.setData(datetime_created, Qt.UserRole)
                datetime_created_item.setData(datetime_created, Qt.ToolTipRole)

                self.projects_model.appendRow([
                    project_name_item,
                    user_item,
                    project_description_item,
                    datetime_created_item,
                    project_id_item,
                    QStandardItem(project_id + ' - ' + datetime_created + ' - ' + user_name + ' - ' + project_name + ' - ' + description),
                    QStandardItem(link)
                ])

            # disconnect the change of the project click to be able to do a refresh
            # it IS possible that there was nothing connected
            # try:
            #     self.jrodosmodel_dlg.tbl_projects.clicked.disconnect(self.project_selected)
            # except:
            #     pass
            
            self.projects_model.setHeaderData(0, Qt.Horizontal, self.tr("Project Name"))
            self.projects_model.setHeaderData(1, Qt.Horizontal, self.tr("User"))
            self.projects_model.setHeaderData(2, Qt.Horizontal, self.tr("Description"))
            self.projects_model.setHeaderData(3, Qt.Horizontal, self.tr("Time Created"))
            self.projects_model.setHeaderData(4, Qt.Horizontal, self.tr("Project ID"))
            # 5 = search
            # 6 = link

            self.jrodosmodel_dlg.set_model(self.projects_model)
            # connect the change of the project dropdown to a refresh of the data path
            jrodos_last_project_filter = Utils.get_settings_value('jrodos_last_project_filter', '')
            self.jrodosmodel_dlg.le_project_filter.setText(jrodos_last_project_filter)
            self.jrodosmodel_dlg.filter_projects(jrodos_last_project_filter)

            # get the last used project from the settings...
            # not sure if we want this: I think it is better to just show the last filtered list
            # and user can click on the right project (instead of doing this automagically)

            # last_used_project = Utils.get_settings_value("jrodos_last_model_project", "")
            # items = self.projects_model.findItems(last_used_project, Qt.MatchExactly, self.QMODEL_ID_IDX)
            # if len(items) > 0:
            #     # we found a 'last_model_project', remove the search string, as it could make the selected one invisible?
            #     self.jrodosmodel_dlg.le_project_filter.setText('')
            #     self.jrodosmodel_dlg.tbl_projects.selectRow(items[0].row())
            #     # the index comes from the real projects model, map to proxy model
            #     idx = self.jrodosmodel_dlg.proxy_model.mapFromSource(items[0].index())
            #     self.project_selected(idx)
            #     self.jrodosmodel_dlg.tbl_projects.scrollTo(idx)

    def project_selected(self, model_idx):
        if not model_idx.isValid():
            # NO project selected, do not use the index to set the other combo's
            return
        # temporary text in the datapath combo
        self.jrodosmodel_dlg.combo_path.clear()
        self.jrodosmodel_dlg.combo_path.addItems([self.tr("Retrieving project datapaths...")])
        self.jrodos_project_data = None  # ? thorough cleanup?
        self.jrodos_project_data = []
        # Now: retrieve the datapaths of this project using a JRodosProjectProvider
        idx = self.jrodosmodel_dlg.proxy_model.mapToSource(model_idx)
        url = self.projects_model.item(idx.row(), 6).text()
        log.debug(f'Selected: {url}')
        config = JRodosProjectConfig()
        config.url = url
        datapaths_provider = JRodosProjectProvider(config)
        datapaths_provider.finished.connect(self.datapaths_provider_finished)
        datapaths_provider.get_data()

    def datapaths_provider_finished(self, result):
        if result.error():
            self.msg(None,
                     self.tr("Problem retrieving the JRodos datapaths for project:\n\n{}.").format(
                         result.url) +
                     self.tr("\n\nCheck the Log Message Panel for more info, \nor replay this url in a browser."))
            # set (empty) paths_model/None in combo: clean up
            self.jrodosmodel_dlg.combo_path.setModel(None)
            self.jrodosmodel_dlg.combo_path.clear()
            # cleanup the start time, step etc in the dialog too
            self.set_dialog_project_info(None, None, None)
            self.task_model = None  # is used as flag for problems
            # let's remove this project from the user settings, as it apparently has datapath problems
            # and keeping this project as last project we stay in this loop of retrieving faulty datapaths
            Utils.set_settings_value("jrodos_last_model_project", "")
        else:
            # load saved user data_items from pickled file
            data_items_from_disk = []
            if os.path.isfile(self.USER_DATA_ITEMS_PATH):
                with open(self.USER_DATA_ITEMS_PATH, 'rb') as f:
                    data_items_from_disk = pickle.load(f)

            # a project has 1-4 tasks (model calculations?)
            # every task has dataitems (both output and input)
            # a dataitem is actually a 'path' to an 'output-node' in the output tree of JRodos
            self.task_model = QStandardItemModel()
            for task in result.data['tasks']:
                # "uid": "527fcd2c-ac13-7293-5563-bb409a0362f5",
                # "modelwrappername": "LSMC",
                # "description": "run:Tameka",
                # "state": "successful",
                # "rootresultnode": "eAHtV81OF...",
                # "dataitem_id": 0,
                # "id": 1251
                self.task_model.appendRow([
                    QStandardItem('0'),                                                   # self.QMODEL_ID_IDX
                    QStandardItem(task['modelwrappername']),                              # self.QMODEL_NAME_IDX
                    QStandardItem(task['modelwrappername'] + ' ' + task['description']),  # self.QMODEL_DESCRIPTION_IDX
                    QStandardItem(task['modelwrappername'])                               # self.QMODEL_DATA_IDX
                ])
                # create a QStandardItemModel per task
                data_items_model = QStandardItemModel()
                data_items = task['dataitems']
                for data_item in data_items:
                    # print data_item['datapath']
                    # dataitem_id		    1
                    # dataitem_type		    "Complex"
                    # groupname		        null
                    # name			        "Model data"
                    # description		    "Root of model DEPOM, pro...-7293-5563-bb40a1e2cfb0"
                    # unit			        "rO0ABXNyAB5qYXZheC5tZWFz...CvnLvFoGAIAAHhwAAAAAA=="
                    # substance		        ""
                    # datapath		        "Model data"
                    # reporttable		    null
                    # showunit		        false
                    # showparents		    0
                    # parent_dataitem_id	0
                    # grid_id			    0
                    # dataitem_index		0

                    # Some hardcoded 'filtering' of the datapaths # unfiltered  '123 478 39 131'
                    # ONLY if the data_item has a reporttable?                  '99 429 21 93'
                    # if data_item['reporttable'] is not None:
                    # ONLY if dataitem_type is 'GridSeries' or 'Series'         '93 409 13 91'
                    if data_item['dataitem_type'] in ['GridSeries', 'Series']:
                        # example datapath:
                        # Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Ground gamma dose=;=effective
                        name = data_item['datapath'].split('=;=')[-2]+', '+data_item['datapath'].split('=;=')[-1]
                        user_favourite = '0'
                        if data_item['datapath'] in data_items_from_disk:
                            user_favourite = '1'
                        data_items_model.appendRow([
                            QStandardItem('0'),                    # self.QMODEL_ID_IDX (not used)
                            QStandardItem(name),                   # self.QMODEL_NAME_IDX
                            QStandardItem(data_item['unit']),      # self.QMODEL_DESCRIPTION_IDX  # misuse for holding the unit used, like Bq/m²
                            QStandardItem(data_item['datapath']),  # self.QMODEL_DATA_IDX
                            QStandardItem(user_favourite)          # self.QMODEL_SEARCH_IDX
                        ])
                # add the task model to the project data
                self.jrodos_project_data.append(data_items_model)

            self.jrodosmodel_dlg.combo_task.setModel(self.task_model)
            self.jrodosmodel_dlg.combo_task.setModelColumn(self.QMODEL_NAME_IDX)  # what we show in dropdown
            # check the last remembered Task
            last_used_task = Utils.get_settings_value("jrodos_last_task", "")
            items = self.task_model.findItems(last_used_task, Qt.MatchExactly, self.QMODEL_NAME_IDX)
            if len(items) > 0:
                self.jrodosmodel_dlg.combo_task.setCurrentIndex(items[0].row())

            # 201907 REST output now also contains timestep, duration and release information
            if 'extendedProjectInfo' in result.data:
                extended_project_info = result.data['extendedProjectInfo']
                self.set_dialog_project_info(
                    extended_project_info['timestepOfPrognosis'],
                    extended_project_info['durationOfPrognosis'],
                    extended_project_info['startOfRelease'])
            else:
                # TODO: can BE REMOVED after all WPS-instances provide extendedProjectInfo information
                # Retrieve some metadata of the model, like
                #  timeStep, modelTime/durationOfPrognosis and ModelStartTime using a JRodosModelProvider
                conf = JRodosModelOutputConfig()
                # NOTE: only wps endpoint 'gs:JRodosWPS' has currently this project info ('gs:JRodosGeopkgWPS' does not)
                # in future we can hopefully use 'gs:JRodosMetadataWPS' to get model info
                conf.wps_id = "gs:JRodosWPS"
                conf.url = self.settings.value('jrodos_wps_url')
                conf.jrodos_project = "project='"+result.data['name']+"'"
                # some trickery to get: "project='wps-test-multipath'&amp;model='LSMC'" in template
                # ONLY when there is >1 task in the project add "'&amp;model='LSMC'"
                if self.task_model.rowCount() > 1:
                    conf.jrodos_project += "&amp;model='LSMC'"
                conf.jrodos_path = "path='Model data=;=Input=;=UI-input=;=RodosLight'"
                conf.jrodos_format = 'application/json'
                # saving handle of project_info_provider to self, as it seems that the provide is garbage collected sometimes
                self.project_info_provider = JRodosModelProvider(conf)
                # self.msg(None, "{}\n{}\n{}\n{}".format(conf.wps_id, conf.output_dir, conf.jrodos_path, conf.jrodos_project))
                self.project_info_provider.finished.connect(self.provide_project_info_finished)
                self.project_info_provider.get_data()

    def task_selected(self, tasks_model_idx):
        """
        On change of the Task in the dialog, recreate the Dataitems.combo_path combobox with the model of that Task
        :param tasks_model_idx:
        :return:
        """
        current_data_items = self.jrodos_project_data[tasks_model_idx]
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(current_data_items)
        proxy_model.setFilterKeyColumn(self.QMODEL_SEARCH_IDX)  # SEARCH contains '1' and '0', show only '1'
        proxy_model.setFilterFixedString('1')
        proxy_model.setDynamicSortFilter(True)
        self.jrodosmodel_dlg.combo_path.setModel(proxy_model)
        self.jrodosmodel_dlg.combo_path.setModelColumn(self.QMODEL_NAME_IDX)  # what we show
        self.filter_dlg.set_model(current_data_items)
        # set last used datapath or the first item if this project/task does not have this datapath
        last_used_datapath = Utils.get_settings_value("jrodos_last_model_datapath", "")
        items = current_data_items.findItems(last_used_datapath, Qt.MatchExactly, self.QMODEL_DATA_IDX)
        if len(items) > 0:
            # get the model index
            model_idx = current_data_items.index(items[0].row(), self.QMODEL_NAME_IDX)
            # map to the proxymodel index
            idx = self.jrodosmodel_dlg.combo_path.model().mapFromSource(model_idx)
            # show it
            self.jrodosmodel_dlg.combo_path.setCurrentIndex(idx.row())

    def provide_project_info_finished(self, result):
        """
        Called when the WPS service returns the JRodos project information about the used timeStep,
        durationOfPrognosis and releaseStart times (ALL in seconds)
        :param result: JSON object like:
            {u'type': u'FeatureCollection',
             u'features': [
               {u'type': u'Feature',
                u'properties': {u'Value': u'{timeStep:3600,durationOfPrognosis:21600,releaseStart:1433224800000}'},
                u'id': u'RodosLight'}]
            }
        :return:
        """
        if result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the Project info for selected project. "
                             "\nSelect another project, and/or check the Log Message Panel for more info..."))
        else:
            self.set_dialog_project_info(
                result.data['timeStep'],
                result.data['durationOfPrognosis'],
                result.data['releaseStart'])

    def set_dialog_project_info(self, time_step, model_time, model_start):
        """
        Used to set AND REset (to None) the 3 params in the dialog
        :param time_step: model Timestep in the dialog is shown in minutes (as in JRodos), but retrieved seconds!!
        :param model_time: model time / duration of prognosis is shown in hours (as in JRodos), but retrieved in seconds!!
        :param model_start: model start / start of release is in milli(!)seconds since 1970 UTC
        :return:
        """
        if time_step is None:
            self.jrodosmodel_dlg.lbl_steps2.setText('-')
            self.jrodosmodel_dlg.le_steps.setText('')
        else:
            # model Timestep in the dialog is shown in minutes (as in JRodos), but retrieved seconds!!
            self.jrodosmodel_dlg.lbl_steps2.setText('{}'.format(time_step / 60) + self.tr(" minutes"))
            self.jrodosmodel_dlg.le_steps.setText('{}'.format(time_step))  # steptime (seconds to minutes)
        if model_time is None:
            self.jrodosmodel_dlg.lbl_model_length2.setText('-')
            self.jrodosmodel_dlg.le_model_length.setText('')
        else:
            # model time / duration of prognosis is shown in hours (as in JRodos), but retrieved in seconds!!
            self.jrodosmodel_dlg.lbl_model_length2.setText('{}'.format(model_time / 3600) + self.tr(" hours"))  # modeltime (seconds to hours)
            self.jrodosmodel_dlg.le_model_length.setText('{}'.format(model_time))  # modeltime (seconds to hours)
        if model_start is None:
            self.jrodosmodel_dlg.lbl_start2.setText('-')
            self.jrodosmodel_dlg.le_start.setText('')  # modeltime (hours)
        else:
            self.jrodosmodel_dlg.le_start.setText('{}'.format(model_start))  # modeltime (hours)
            if type(model_start) == int:
                # OLD model start / start of release is in milli(!)seconds since 1970 UTC like: "1477146000000"
                self.jrodosmodel_dlg.lbl_start2.setText(QDateTime.fromTime_t(model_start/1000).toUTC().toString("yyyy-MM-dd HH:mm"))
            else:
                # NEW model start / start of release is string like: "2016-04-25T08:00:00.000+0000"
                self.jrodosmodel_dlg.lbl_start2.setText('{}'.format(model_start))

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def handle_jrodos_output_dialog(self):
        """
        Actual retrieving of measurements after clicking OK in JRodos dialog

        :return: True if successful or False if there was an issue with input or result
        """
        if not self.jrodosmodel_dlg.tbl_projects.currentIndex().isValid():
            self.msg(None, self.tr(
              "Did you select one of the projects in the table?\nLooks like nothing was selected... "))
            # let's remove this project from the user settings
            Utils.set_settings_value("jrodos_last_model_project", "")
            return False
        # Get data_item/path from model behind the combo_path dropdown, BUT only if we have a valid task_model.
        # Else there was a problem retrieving the project information
        if not hasattr(self, 'task_model') or self.task_model is None:
            self.msg(None, self.tr(
              "There is a problem with this project (no tasks),\nquitting retrieving this model's parameters... "))
            # let's remove this project from the user settings
            Utils.set_settings_value("jrodos_last_model_project", "")
            return False

        jrodos_output_config = JRodosModelOutputConfig()
        jrodos_output_config.wps_id = 'gs:JRodosGeopkgWPS'  # defaulting to GeoPackage
        if self.jrodosmodel_dlg.rb_shp_output.isChecked():
            jrodos_output_config.wps_id = 'gs:JRodosWPS'
        jrodos_output_config.url = self.settings.value('jrodos_wps_url')
        # FORMAT is fixed to zip with shapes or zip with geopackage
        jrodos_output_config.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
        # selected project + save the project id (model col 1) to QSettings
        # +"'&amp;model='EMERSIM'"
        current_project_idx = self.jrodosmodel_dlg.proxy_model.mapToSource(self.jrodosmodel_dlg.tbl_projects.currentIndex())
        jrodos_output_config.jrodos_project = "project='" + self.projects_model.item(current_project_idx.row(), 0).text() + "'"
        jrodos_output_config.jrodos_project += "&amp;model='{}'".format(self.task_model.item(self.jrodosmodel_dlg.combo_task.currentIndex(), self.QMODEL_DATA_IDX).text())

        # for storing in settings we do not use the non unique name, but the ID of the project
        last_used_project = self.projects_model.item(current_project_idx.row(), self.QMODEL_ID_IDX).text()
        log.debug(f'Storing {last_used_project} as "jrodos_last_model_project"')
        Utils.set_settings_value("jrodos_last_model_project", last_used_project)

        task_index = self.jrodosmodel_dlg.combo_task.currentIndex()
        if task_index < 0:  # on Windows I've seen that apparently there was NO selected index...
            task_index = 0
        datapath_model = self.jrodos_project_data[task_index]  # QStandardItemModel
        combopath_model = self.jrodosmodel_dlg.combo_path.model()  # QSortFilterProxyModel
        current_path_index = self.jrodosmodel_dlg.combo_path.currentIndex()
        if current_path_index < 0:
            self.msg(None, self.tr("Mandatory 'Dataitem' input is missing...\nPlease select one from the dropdown.\nOr fill the dropdown via the 'See All' button.\nIf that list is empty, then this project is not ready yet or not saved...\nPlease try another project or make sure JRodos is finished."))
            return False
        proxy_idx = combopath_model.index(current_path_index, self.QMODEL_DATA_IDX)
        idx = combopath_model.mapToSource(proxy_idx)
        last_used_datapath = datapath_model.item(idx.row(), self.QMODEL_DATA_IDX).text()

        units = datapath_model.item(idx.row(), self.QMODEL_DESCRIPTION_IDX)  # we did put the units in description..
        if units is not None:
            jrodos_output_config.units = units.text()

        # NOTE that the jrodos_output_settings.jrodos_path has single quotes around it's value!! in the settings:
        # like: 'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Ground gamma dose=;=effective'
        jrodos_output_config.jrodos_path = "path='{}'".format(last_used_datapath)
        Utils.set_settings_value("jrodos_last_model_datapath", last_used_datapath)
        last_used_task = self.task_model.item(self.jrodosmodel_dlg.combo_task.currentIndex(), self.QMODEL_NAME_IDX).text()
        Utils.set_settings_value("jrodos_last_task", last_used_task)

        # model time / duration of prognosis is shown in hours, but retrieved in minutes, and in JRodos in hours!!
        # modeltime (seconds!)
        model_time_secs = int(self.jrodosmodel_dlg.le_model_length.text())
        jrodos_output_config.jrodos_model_time = model_time_secs / 60  # jrodos_model_time is in minutes!!
        # model Timestep in the dialog is shown in minutes, BUT retrieved in seconds, and in JRodos in minutes!!
        # steptime (seconds!)
        model_step_secs = int(self.jrodosmodel_dlg.le_steps.text())
        jrodos_output_config.jrodos_model_step = model_step_secs
        # vertical is fixed to 0 for now (we do not 3D models)
        jrodos_output_config.jrodos_verticals = 0  # z / layers
        # NEW: time is now a string like: "2016-04-25T08:00:00.000+0000"
        jrodos_output_config.jrodos_datetime_start = QDateTime.fromString(self.jrodosmodel_dlg.le_start.text(), 'yyyy-MM-ddTHH:mm:ss.000+0000')
        if not jrodos_output_config.jrodos_datetime_start.isValid():
            # try UTC with the Z notation
            jrodos_output_config.jrodos_datetime_start = QDateTime.fromString(self.jrodosmodel_dlg.le_start.text(), 'yyyy-MM-ddTHH:mm:ss.000Z')
        # NEW: columns = a range from 0 till number of steps in the model (range string like '0-23')
        jrodos_output_config.jrodos_columns = '{}-{}'.format(0, model_time_secs / model_step_secs)
        self.jrodos_output_settings = jrodos_output_config
        self.start_jrodos_model_output_provider()
        return True

    def start_jrodos_model_output_provider(self):
        self.jrodos_output_progress_bar.setMaximum(0)  # run progress
        self.jrodos_output_provider = JRodosModelOutputProvider(self.jrodos_output_settings)
        self.jrodos_output_provider.finished.connect(self.finish_jrodos_model_output_provider)
        self.jrodos_output_provider.get_data()

    def finish_jrodos_model_output_provider(self, result):
        log.debug(result)
        self.jrodos_output_progress_bar.setMaximum(100)  # stop progress
        self.jrodos_output_progress_bar.setFormat(self.BAR_LOADING_TITLE)
        QCoreApplication.processEvents()  # to be sure we have the loading msg
        if result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the JRodos model output. \nCheck the Log Message Panel for more info"))
        else:
            # Load the received shp-zip files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None:
                unit_used = self.jrodos_output_settings.units
                s = self.jrodos_output_settings.jrodos_path[:-1]  # contains path='...' remove last quote
                layer_name = unit_used + ' - ' + s.split('=;=')[-2]+', '+s.split('=;=')[-1]
                self.load_jrodos_output(
                    result.data['output_dir'], 'totalpotentialdoseeffective.qml', layer_name, unit_used)
            else:
                self.msg(None, self.tr("No Jrodos Model Output data? Got: {}").format(result.data))
        self.jrodos_output_settings = None
        self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)

    def set_measurements_time(self):
        """ Set the endtime to NOW (UTC) and change starttime such
        that the timeframe stays the same
        """
        # first check wat current timeframe is that user is using
        start_date = self.measurements_dlg.dateTime_start.dateTime()  # UTC
        end_date = self.measurements_dlg.dateTime_end.dateTime()  # UTC
        old_timeframe = end_date.toSecsSinceEpoch() - start_date.toSecsSinceEpoch()
        end_time = QDateTime.currentDateTimeUtc()  # end is NOW
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        start_time = end_time.addSecs(-old_timeframe)
        self.measurements_dlg.dateTime_start.setDateTime(start_time)

    def show_measurements_dialog(self):

        if self.measurements_settings is not None:
            self.msg(None, self.tr("Still busy retrieving Measurement data via WFS, please try later..."))
            # stop this session
            return True

        if self.measurements_layer is not None:
            # that is we have measurements from an earlier run
            self.measurements_settings = self.jrodos_settings[self.measurements_layer]
            self.start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
            self.end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)
        elif self.jrodos_output_settings is not None:
            # BUT if we just received a model, INIT the measurements dialog based on this
            self.start_time = self.jrodos_output_settings.jrodos_datetime_start.toUTC()  # we REALLY want UTC
            self.end_time = self.start_time.addSecs(60 * int(self.jrodos_output_settings.jrodos_model_time))  # model time
        elif Utils.get_settings_value('startdatetime', False) and Utils.get_settings_value('enddatetime', False):
            self.start_time = Utils.get_settings_value('startdatetime', '')
            self.end_time = Utils.get_settings_value('enddatetime', '')
            # log.debug(f'Got start and end from settings: {self.start_time} {self.end_time}')
        elif self.start_time is None:
            hours = 1  # h
            self.end_time = QDateTime.currentDateTimeUtc()  # end NOW
            self.start_time = self.end_time.addSecs(-60 * 60 * hours)  # minus h hours

        self.measurements_dlg.dateTime_start.setDateTime(self.start_time)
        self.measurements_dlg.dateTime_end.setDateTime(self.end_time)
        self.measurements_dlg.combo_endminusstart.setCurrentIndex(
            self.measurements_dlg.combo_endminusstart.findText(Utils.get_settings_value('endminusstart', '3600')))

        self.measurements_dlg.le_project_id.setText(Utils.get_settings_value('projectid', ''))

        if self.combis is None:
            with open(self.plugin_dir + '/measurement_start_combis.json', 'rb') as f:
                self.combis = json.load(f)
                result = lambda: None  # 'empty' object
                result.data = self.combis
                self.quantities_substance_provider_finished(result)
            # but also retrieve a fresh list in the background
            # self.get_quantities_and_substances_combis()

        self.measurements_dlg.show()

        result = self.measurements_dlg.exec_()
        if result:  # OK was pressed
            # selected endminusstart + save to QSettings
            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            Utils.set_settings_value("endminusstart", endminusstart)

            quantities = []
            substances = []
            quantity_substance_combis = []
            # run over model, and check if SEARCH column is True and so collect selected quantities
            for row in range(0, self.quantities_substances_model.rowCount()):
                if self.quantities_substances_model.item(row, self.QMODEL_SEARCH_IDX).text() == 'true':
                    # data is an combi array like: ['T-GAMMA', 'A1']
                    data = self.quantities_substances_model.item(row, self.QMODEL_DATA_IDX).data()
                    # we pickle the data for later use
                    quantity_substance_combis.append(data)
                    # we make the two arrays unique, so no doublures in the array (no ['A5', 'A5']
                    # as this makes that we receive records double..
                    # TODO: fix in sql/stored-procedure in postgres
                    if not data[0] in quantities:
                        quantities.append(data[0])
                    if not data[1] in substances:
                        substances.append(data[1])

            #log.debug(f'Length quantities: {len(quantities)}')
            #log.debug(f'Length substances: {len(substances)}')
            #log.debug(f'Length quantity_substance_combis: {len(quantity_substance_combis)}')

            if len(quantity_substance_combis) == 0:
                # mmm, nothing selected... show message
                self.msg(None, self.tr('Please select at least ONE quantity-substance combination'))
                return False

            # dumping/pickling selected quantity/substance combi's to disk
            with open(self.USER_QUANTITIES_SUBSTANCES_PATH, 'wb') as f:
                #log.debug("Dumping to disk:\n".format(quantity_substance_combis))
                pickle.dump(quantity_substance_combis, f)

            start_date = self.measurements_dlg.dateTime_start.dateTime()  # UTC
            Utils.set_settings_value("startdatetime", start_date)
            end_date = self.measurements_dlg.dateTime_end.dateTime()  # UTC
            Utils.set_settings_value("enddatetime", end_date)
            measurements_settings = CalnetMeasurementsConfig()
            measurements_settings.url = self.settings.value('measurements_wfs_url')

            project_id = self.measurements_dlg.le_project_id.text().strip()
            if not project_id == '' and not project_id.isdigit():
                # User tries to use a string in this projectid field
                self.msg(None, self.tr('Project number is a single CalWeb project number (or empty)'))
                return False
            if len(project_id) != 0:
                log.info(f'Project_id: {project_id} found! Adding to CQL in WFS request')
                # setting it in the config as a String (although it will end up as an integer in DB)
                measurements_settings.projectid = project_id # is text anyway at this moment
                Utils.set_settings_value("projectid", project_id)
            else:
                Utils.set_settings_value("projectid", '')

            lower_bound = self.measurements_dlg.le_lowerbound.text()
            if len(lower_bound) != 0:
                log.info(f'Lower bound: {lower_bound} found! Adding to CQL in WFS request')
                measurements_settings.lower_bound = lower_bound
                Utils.set_settings_value("lower_bound", lower_bound)
            else:
                Utils.set_settings_value("lower_bound", '')
            upper_bound = self.measurements_dlg.le_upperbound.text()
            if len(upper_bound) != 0:
                log.info(f'Upper bound: {upper_bound} found! Adding to CQL in WFS request')
                measurements_settings.upper_bound = upper_bound
                Utils.set_settings_value("upper_bound", upper_bound)
            else:
                Utils.set_settings_value("upper_bound", '')

            if self.jrodos_output_settings is None:
                project = "'measurements'"
                path = "'=;=wfs=;=data'"
                measurements_settings.output_dir = ProviderUtils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
            else:
                measurements_settings.output_dir = self.jrodos_output_settings.output_dir

            measurements_settings.page_size = self.settings.value('measurements_wfs_page_size')
            measurements_settings.start_datetime = start_date.toString(measurements_settings.date_time_format)
            measurements_settings.end_datetime = end_date.toString(measurements_settings.date_time_format)
            measurements_settings.endminusstart = endminusstart
            measurements_settings.quantity = ','.join(quantities)
            measurements_settings.substance = ','.join(substances)
            self.measurements_settings = measurements_settings
            self.update_measurements_bbox()
            self.start_measurements_provider()
            return True
        else:  # cancel pressed
            self.measurements_settings = None
            return True

    def start_measurements_provider(self):
        self.measurements_progress_bar.setMaximum(0)
        self.measurements_provider = CalnetMeasurementsProvider(self.measurements_settings)
        self.measurements_provider.finished.connect(self.finish_measurements_provider)
        self.measurements_provider.get_data()

    def finish_measurements_provider(self, result):
        #log.debug(result.data)
        self.measurements_progress_bar.setMaximum(100)
        self.measurements_progress_bar.setFormat(self.BAR_LOADING_TITLE)
        QCoreApplication.processEvents()  # to be sure we have the loading msg
        # WFS response can take a long time. Time out is handled by QGIS-network settings time out
        # so IF error_code = 5 (http://doc.qt.io/qt-4.8/qnetworkreply.html#NetworkError-enum)
        # provide the user feed back to rise the timeout value
        if result.error_code == 5:
            self.msg(None, self.tr("Network timeout for Measurements-WFS request. \nConsider rising it in Settings/Options/Network. \nValue is now: {} msec".format(QSettings().value('/qgis/networkAndProxy/networkTimeout', '??'))))
        elif result.error():
            self.msg(None, result)
            self.iface.messageBar().pushMessage(self.tr("Network problem"), self.tr(f'{result.error_code} see messages'), level=Qgis.Critical)
        else:
            # Load the received gml files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None and result.data['count'] > 0:
                now = QDateTime.currentMSecsSinceEpoch()
                self.load_measurements(result.data['output_dir'], 'measurements_rotation.qml')
                log.debug('Loading gml data file(s) took {} secs'.format((QDateTime.currentMSecsSinceEpoch()-now)/1000))
            else:
                self.msg(None, self.tr("No data using this filters?\n\n{}\n{}").format(self.measurements_settings, result.data))
        self.measurements_settings = None
        self.measurements_progress_bar.setFormat(self.MEASUREMENTS_BAR_TITLE)

    def update_measurements_bbox(self):
        # bbox in url should be epsg:4326 !
        crs_project = self.iface.mapCanvas().mapSettings().destinationCrs()
        crs_4326 = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
        crs_transform = QgsCoordinateTransform(crs_project, crs_4326, QgsProject.instance())
        current_bbox_4326 = crs_transform.transform(self.iface.mapCanvas().extent())
        # bbox for wfs get measurements request, based on current bbox of mapCanvas (OR model)
        self.measurements_settings.bbox = "{},{},{},{}".format(
            current_bbox_4326.yMinimum(), current_bbox_4326.xMinimum(), current_bbox_4326.yMaximum(), current_bbox_4326.xMaximum())  # S,W,N,E

    def measurement_selection_change(self):
        """Select changed action when a selection of features changes in the measurements layer.

        Signal is only connected when the user ticks the 'Show Time Graph' checkbox
        Here used to create the line plot/graphic of the measurements.

        """
        self.remove_device_pointer()
        # we do not use these selected_ids etc because selectedFeaturesIds is easier to use with CTRL-selects
        selected_features_ids = self.measurements_layer.selectedFeatureIds()
        # Disconnect signal (temporarily), to be able to set the subsetstring to ''.
        # With a connected signal measurement_selection_change function would have been called again because
        # timemanager set's the subsetstring again
        self.measurements_layer.selectionChanged.disconnect(self.measurement_selection_change)
        # remember current (timemanager-based) subset string to be able to add it later
        subset_string = self.measurements_layer.dataProvider().subsetString()
        self.measurements_layer.setSubsetString('')
        self.graph_widget.graph.clear()
        font = QFont()
        font.setPixelSize(10)
        self.curves = {}
        first = True
        selected_feature = None
        handled_devices = []
        for fid in selected_features_ids:
            features = self.measurements_layer.getFeatures(QgsFeatureRequest(fid))
            for selected_feature in features:
                # log.debug(selected_feature['device'])  # strings like: NL1212
                # 'casting' device to a string, because from postgres we get a PyQtNullVariant in case of null device
                device = '{}'.format(selected_feature['device'])
                quantity = '{}'.format(selected_feature['quantity'])
                unit = '{}'.format(selected_feature['unit'])
                # log.debug('device: >{}< type: {}'.format(device, type(device)))
                # HACKY: disable current time-filter, to be able to find all features from same device
                if device is None or device == '' or device == 'NULL':
                    log.debug('Feature does not contain a device(id), so NOT shown in Time Graph')
                else:
                    # some devices have several sensors/quantities
                    if selected_feature['device']+quantity+unit in handled_devices:
                        # ok handled already, go on...
                        #log.debug(f'Skipping: {selected_feature["device"]+quantity+unit}')
                        continue
                    handled_devices.append(selected_feature['device']+quantity+unit)

                    fr = QgsFeatureRequest()
                    fr.disableFilter()
                    # we can only create graphs from ONE DEVICE if UNIT and QUANTITY are the same, hence the filter below:
                    fr.setFilterExpression(u'"device" = \'{}\' AND "quantity" = \'{}\' AND "unit" = \'{}\''.format(device, quantity, unit))
                    # log.debug('\nDevice {}'.format(device))
                    x = []
                    y = []
                    time_sorted_features = sorted(self.measurements_layer.getFeatures(fr), key=lambda f: f['time'])
                    for feature in time_sorted_features:
                        # log.debug(feature['gml_id'])
                        t = QDateTime.fromString(feature['time'], 'yyyy-MM-ddTHH:mm:ssZ').toMSecsSinceEpoch()
                        x.append(t/1000)
                        #y.append(feature['unitvalue'])
                        y.append(feature['value'])
                        # log.debug('{} - {} - {} - {} - {}'.format(t/1000, feature['unitvalue'], feature['device'], feature['quantity'], feature['unit']))

                    # plot curve item symbols: x, o, +, d, t, t1, t2, t3, s, p, h, star
                    # curve = self.graph_widget.graph.plot(x=x, y=y, pen='ff000099')
                    # NOT using shortcut notation above, because we want to keep a reference to the PlotCurveItem for click
                    curve = PlotCurveItem(x=x, y=y, pen='ff000099', mouseWidth=0)
                    curve.setClickable(True, 6)
                    curve.sigClicked.connect(self.curve_click)
                    self.graph_widget.graph.addItem(curve)
                    # create a curve <-> device,feature mapping as lookup for later use
                    self.curves[curve] = (device, selected_feature)

                    label_point = CurvePoint(curve)
                    self.graph_widget.graph.addItem(label_point)

                    # for T-GAMMA we always show microSv/h, for other it is quantity dependent
                    quantity = feature['quantity']
                    if quantity.upper() == 'T-GAMMA' and feature['unit'] in ['NSV/H', 'USV/H']:
                        unit = 'µSv/h' # 'USV/H' we (apr2020 NOT) keep notation as eurdep data: USV/H == microSv/h
                    else:
                        unit = feature['unit']  # for other

                    label = TextItem('{} {} {}'.format(device, quantity, unit), anchor=(0, 0), color='0000ff')
                    label.setFont(font)
                    label_point.setPos(0)
                    label.setParentItem(label_point)
            if first:
                self.set_device_pointer(selected_feature.geometry())
                first = False
            else:
                self.remove_device_pointer()

        # RE-apply old (timemanager-based) subset_string again to make layer work for timemanager again
        self.measurements_layer.dataProvider().setSubsetString(subset_string)
        # AND apply the selection again because resetting the subsetString removed it
        self.measurements_layer.selectByIds(selected_features_ids)
        # and connect measurement_selection_change  again
        self.measurements_layer.selectionChanged.connect(self.measurement_selection_change)

    def curve_click(self, item):
        device, feature = self.curves[item]
        self.set_device_pointer(feature.geometry())

    def set_device_pointer(self, geom):
        self.remove_device_pointer()
        self.graph_device_pointer = QgsVertexMarker(self.iface.mapCanvas())
        self.graph_device_pointer.setColor(QColor(255, 0, 0))
        self.graph_device_pointer.setIconSize(20)
        self.graph_device_pointer.setPenWidth(3)
        self.graph_device_pointer.setIconType(QgsVertexMarker.ICON_CIRCLE)
        to_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        from_crs = self.measurements_layer.crs()
        crs_transformer = QgsCoordinateTransform(from_crs, to_crs, QgsProject.instance())
        copy_geom = QgsGeometry(geom)  # doing transformation on the copy, else the original is transformed
        copy_geom.transform(crs_transformer)

        self.graph_device_pointer.setCenter(copy_geom.asPoint())

    def remove_device_pointer(self):
        if self.graph_device_pointer is not None:
            self.iface.mapCanvas().scene().removeItem(self.graph_device_pointer)
            self.iface.mapCanvas().refresh()
            self.graph_device_pointer = None

    def find_jrodos_layer(self, settings_object):
        for layer in self.jrodos_settings:
            if self.jrodos_settings[layer] == settings_object:
                return layer
        return None

    def remove_jrodos_layer(self, layer2remove):
        for layer in self.jrodos_settings.keys():
            if layer2remove == layer.id():
                if self.measurements_layer == layer:
                    self.graph_widget.graph.clear()
                    self.measurements_layer = None
                    self.remove_device_pointer()
                del self.jrodos_settings[layer]
                return

    # noinspection PyBroadException
    def load_jrodos_output(self, output_dir, style_file, layer_name, unit_used):
        """
        Create a polygon memory layer, and load all shapefiles (named
        0_0.zip -> x_0.zip)
        from given shape_dir.
        Every zip is for a certain time-period, but because the data does
        not containt a time column/stamp
        we will add it by creating an attribute 'Datetime' and fill that
        based on:
        - the x in the zip file (being a model-'step')
        - the starting time of the model (given in dialog, set in jrodos
        project run)
        - the model length time (24 hours)

        :param unit_used:
        :param layer_name:
        :param output_dir: directory containing zips with shapefiles
        :param style_file: style (qml) to be used to style the layer in
        which we merged all shapefiles
        :return:
        """

        try:
            import zipfile
            zips = glob(os.path.join(output_dir, "*.zip"))
            for zip_file in zips:
                zip_ref = zipfile.ZipFile(zip_file, 'r')
                zip_ref.extractall(output_dir)
                zip_ref.close()
        except Exception:
            self.msg(None, self.tr(
                'Received Data. \nBut no ZIP file..\nTry other model or Check log for more information '))
            log.debug('PROBLEM unpacking ZIP from "{}"\nProbably no ZIP received?'.format(output_dir))
            return

        shps = glob(os.path.join(output_dir, "*.shp"))
        gpkgs = glob(os.path.join(output_dir, "*.gpkg"))
        slds = glob(os.path.join(output_dir, "*.sld"))

        features_added = False
        features_have_valid_time = False
        features_min_value = self.MAX_FLOAT

        i = 0
        if len(gpkgs) > 0:
            (gpkgdir, gpkgfile) = os.path.split(gpkgs[0])
            # log.debug("{}\n{}".format(gpkgdir, gpkgfile))
            if 'Empty' in gpkgfile:  # JRodos sents an 'Empty.gpkg' if no features are in the model data path)
                self.msg(None, self.tr("JRodos data received successfully. \nBut dataset '"+layer_name+"' is empty."))
            else:
                uri = gpkgs[0] + '|layername=view'
                jrodos_output_layer = QgsVectorLayer(uri, layer_name, 'ogr')
        elif len(shps) > 0:
            (shpdir, shpfile) = os.path.split(shps[0])
            # log.debug("{}\n{}".format(shpdir, shpfile))
            if 'Empty' in shpfile:  # JRodos sents an 'Empty.shp' if no features are in the model data path)
                self.msg(None, self.tr("JRodos data received successfully. \nBut dataset '"+layer_name+"' is empty."))
            else:
                jrodos_output_layer = QgsVectorLayer(shps[0], layer_name, 'ogr')

        if not jrodos_output_layer.isValid():
            self.msg(None, self.tr("Apparently no valid JRodos data received. \nFailed to load the data!"))
        else:
            # TODO: determine if we really want to walk over all features just to determine class boundaries
            #       better would be to have this (meta)data available from the jrodos service or so
            pass
            for feature in jrodos_output_layer.getFeatures():
                # Ok, apparently we have at least one feature
                features_added = True
                i += 1
                # only features with Value > 0, to speed up QGIS
                value = feature.attribute('Value')
                # check if we have a valid time in this features
                time = feature.attribute('Time')
                if value > 0:
                    if value < features_min_value:
                        features_min_value = value
                    # only check when still no valid times found...
                    if not features_have_valid_time and time is not None and time != "" and time > 0:
                        features_have_valid_time = True
                        break  # we break here, as we apparently have valid features WITH valid times
                # else:
                #     # try to delete the features with Value = 0, Note that a zipped shp cannot be edited!
                #     if (jrodos_output_layer.dataProvider().capabilities() & QgsVectorDataProvider.DeleteFeatures) > 0:
                #         j += 1
                #         jrodos_output_layer.deleteFeature(feature.id())
        sld_loaded_ok = False
        if len(slds) > 0:
            log.debug(slds[0])
            # /tmp/201909030816650371_R1LongReleaseLongRunHighRelease_NPKPUFF_Dose-rates_Ground-gamma-total-dose-rate/doserate.sld
            result = jrodos_output_layer.loadSldStyle(slds[0])
            if not result[1]:
                log.debug('Problem loading sld: {}: {}'.format(slds[0], result[0]))
                fixed = self.fix_jrodos_style_sld(slds[0])
                log.debug('Trying {} now'.format(fixed))
                result = jrodos_output_layer.loadSldStyle(fixed)
                if not result[1]:
                    log.debug('Also problem loading sld: {}: {}'.format(fixed, result[0]))
                else:
                    # problem loading the sld, BUT we can try to fix the JRodos styles...
                    sld_loaded_ok = True
                    jrodos_output_layer.setName(jrodos_output_layer.name() + ' (JRodos-styled)')
                    log.debug('Layer styled using sld from zip: {}'.format(fixed))
            else:
                sld_loaded_ok = True
                jrodos_output_layer.setName(jrodos_output_layer.name()+' (JRodos-styled)')
                log.debug('Layer styled using sld from zip: {}'.format(slds[0]))
        # sld_loaded_ok = False
        if not sld_loaded_ok:
            self.style_layer(jrodos_output_layer)
        self.iface.mapCanvas().refresh()

        # self.msg(None, "min: {}, max: {} \ncount: {}, deleted: {}".format(features_min_value, 'TODO?', i, j))
        # ONLY when we received features back load it as a layer
        if features_added:
            # add layer to the map
            QgsProject.instance().addMapLayer(jrodos_output_layer,
                                              False)  # False, meaning not ready to add to legend
            self.layer_group.insertLayer(1, jrodos_output_layer)  # now add to legend in current layer group
        # ONLY when we received features back AND the time component is valid: register the layer to the timemanager etc
        if features_have_valid_time:
            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            self.jrodos_settings[jrodos_output_layer] = deepcopy(self.jrodos_output_settings)
            # add this layer to the TimeManager
            step_minutes = self.jrodos_output_settings.jrodos_model_step/60  # jrodos_model_step is in seconds!!!
            self.add_layer_to_timemanager(jrodos_output_layer, 'Time', step_minutes, 'minutes')

    @staticmethod
    def fix_jrodos_style_sld(jrodos_style_sld):
        """
        JRodos sld's can be old styles, that is do not
        :return: File (full path) to 'fixed' sld
        """
        with open(jrodos_style_sld, 'r') as f:
            original = f.read()

        before = """<?xml version="1.0" encoding="UTF-8"?>
        <sld:StyledLayerDescriptor version="1.0.0"
         xmlns:sld="http://www.opengis.net/sld"
         xmlns:ogc="http://www.opengis.net/ogc"
         xmlns:xlink="http://www.w3.org/1999/xlink"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <sld:NamedLayer>
          <sld:Name>Fixed style</sld:Name>"""

        after = """
          </sld:NamedLayer>
        </sld:StyledLayerDescriptor>"""

        # HACK: should be a regular expression
        # remove '<?xml version="1.0" encoding="UTF-8" .... ?> header
        original_no_header = re.sub('<\?.*\?>', 'xxx', original)

        fixed = "{}{}{}".format(before, original_no_header, after)

        sld_file_fixed = jrodos_style_sld + '.fixed'

        with open(sld_file_fixed, 'w') as f:  # using 'with open', then file is explicitly closed
            f.write(fixed)

        return sld_file_fixed

    @staticmethod
    def style_layer(layer):
        # create a new rule-based renderer
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        # get the "root" rule
        root_rule = renderer.rootRule()

        # create a nice 'Full Cream' color ramp ourselves
        rules = RangeCreator.create_rule_set(-5, 4, False, True)

        for label, expression, color in rules:
            # create a clone (i.e. a copy) of the default rule
            rule = root_rule.children()[0].clone()
            # set the label, expression and color
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().symbolLayer(0).setFillColor(color)
            # outline transparent
            rule.symbol().symbolLayer(0).setStrokeColor(QColor.fromRgb(255, 255, 255, 0))
            # set the scale limits if they have been specified
            # if scale is not None:
            #     rule.setScaleMinDenom(scale[0])
            #     rule.setScaleMaxDenom(scale[1])
            # append the rule to the list of rules
            root_rule.appendChild(rule)

        # delete the default rule
        root_rule.removeChildAt(0)
        # apply the renderer to the layer
        layer.setRenderer(renderer)

    @staticmethod
    def enable_timemanager(enable):
        """
        Enable OR disable the timemanager
        :param enable: 
        :return: 
        """
        timemanager = None
        if 'timemanager' in plugins:
            timemanager = plugins['timemanager']
        # enable timemanager by 'clicking' on enable button (if not enabled)
        if enable and not timemanager.getController().getTimeLayerManager().isEnabled():
            timemanager.getController().getGui().dock.pushButtonToggleTime.click()
        elif not enable and timemanager.getController().getTimeLayerManager().isEnabled():
            timemanager.getController().getGui().dock.pushButtonToggleTime.click()

    def add_rainradar_to_timemanager(self, layer_for_settings):
        settings = JRodosSettings()
        name = settings.value("rainradar_wmst_name")
        url = settings.value("rainradar_wmst_url")
        layers = settings.value("rainradar_wmst_layers")
        styles = settings.value("rainradar_wmst_styles")
        imgformat = settings.value("rainradar_wmst_imgformat")
        crs = settings.value("rainradar_wmst_crs")

        uri = "crs=" + crs + "&layers=" + layers + "&styles=" + styles + "&format=" + imgformat + "&url=" + url

        rain_layer = QgsRasterLayer(uri, name, "wms")
        QgsProject.instance().addMapLayer(rain_layer, False)  # False, meaning not ready to add to legend
        self.layer_group.insertLayer(len(self.layer_group.children()), rain_layer)  # now add to legend in current layer group on bottom

        measurements_settings = self.jrodos_settings[layer_for_settings]  # we keep (deep)copies of the settings of the layers here
        timelayer_settings = LayerSettings()
        timelayer_settings.layer = rain_layer
        start = QDateTime.fromString(measurements_settings.start_datetime, measurements_settings.date_time_format)
        datetime_format = 'yyyy-MM-ddThh:mm:ss'
        timelayer_settings.startTimeAttribute = start.toString(datetime_format)
        end = QDateTime.fromString(measurements_settings.end_datetime, measurements_settings.date_time_format)
        timelayer_settings.endTimeAttribute = end.toString(datetime_format)

        timelayer = WMSTRasterLayer(timelayer_settings, self.iface)

        timemanager = plugins['timemanager']
        timemanager.getController().timeLayerManager.registerTimeLayer(timelayer)

    def add_layer_to_timemanager(self, layer, time_column=None, frame_size=60, frame_type='minutes'):

        if 'timemanager' not in plugins:
            self.iface.messageBar().pushWarning("Warning!!", "No TimeManger plugin, we REALLY need that. Please install via Plugin Manager first...")
            return

        self.enable_timemanager(True)

        timemanager = plugins['timemanager']
        timelayer_settings = LayerSettings()
        timelayer_settings.layer = layer
        timelayer_settings.startTimeAttribute = time_column
        timelayer = TimeVectorLayer(timelayer_settings, self.iface)
        animation_frame_length = 2000
        frame_size = frame_size
        frame_type = frame_type
        timemanager.getController().setPropagateGuiChanges(False)
        timemanager.getController().setAnimationOptions(animation_frame_length, False, False)
        timemanager.getController().guiControl.setTimeFrameType(frame_type)
        timemanager.getController().guiControl.setTimeFrameSize(frame_size)
        timemanager.getController().getTimeLayerManager().registerTimeLayer(timelayer)
        # set timeslider to zero, moving it to 1 and back, thereby calling some event?
        timemanager.getController().getGui().dock.horizontalTimeSlider.setValue(1)
        timemanager.getController().getGui().dock.horizontalTimeSlider.setValue(0)
        # TODO: temporarily in if clause (until upstream has it too)
        if hasattr(timemanager.getController(), 'refreshGuiTimeFrameProperties'):
            timemanager.getController().refreshGuiTimeFrameProperties()
            # set 'discrete checkbox' to True to be sure there is something to see...
            timemanager.getController().getGui().dock.checkBoxDiscrete.setChecked(True)
        else:
            #log.debug('JRodos time: refreshing gui times: {}'.format(timemanager.getController().getTimeLayerManager().getProjectTimeExtents()))
            timemanager.getController().refreshGuiTimeExtents(timemanager.getController().getTimeLayerManager().getProjectTimeExtents())
        # do one step to be sure there is data visible (working for hour measurements, could be based on frame_size)
        timemanager.getController().stepForward()
        timemanager.getController().getTimeLayerManager().refreshTimeRestrictions()

    def load_measurements(self, output_dir, style_file):
        """
        Load the measurements from the output_dir (as gml files), load them in a layer, and style them with style_file
        :param output_dir:
        :param style_file:
        :return:
        """
        start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
        end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)

        # layer_display_name = self.measurements_settings.quantity + ", " + self.measurements_settings.substance + ", " + \
        #    self.measurements_settings.endminusstart + ", " + \
        #    start_time.toString(self.measurements_settings.date_time_format_short) + " - " + \
        #    end_time.toString(self.measurements_settings.date_time_format_short)
        layer_display_name = "Measurements " + \
            start_time.toString(self.measurements_settings.date_time_format_short) + " - " + \
            end_time.toString(self.measurements_settings.date_time_format_short)

        #log.debug('self.measurements_settings.quantity {}'.format(self.measurements_settings.quantity))
        #log.debug('self.measurements_settings.substance {}'.format(self.measurements_settings.substance))

        register_layers = False
        if self.measurements_layer is None:
            register_layers = True
            self.set_legend_node_name(self.layer_group,
                                      self.tr('Data retrieved: ') + QDateTime.currentDateTime().toString(
                                          'MM/dd HH:mm:ss'))

            # create layer name based on self.measurements_settings
            self.measurements_layer = QgsVectorLayer("point", layer_display_name, "memory")

            # add fields
            pr = self.measurements_layer.dataProvider()
            pr.addAttributes([QgsField("gml_id", QVariant.String),
                              QgsField("startTime", QVariant.String),
                              QgsField("endTime", QVariant.String),
                              QgsField("quantity", QVariant.String),
                              QgsField("substance", QVariant.String),
                              QgsField("unit", QVariant.String),
                              QgsField("value", QVariant.Double),
                              QgsField("time", QVariant.String),
                              QgsField("info", QVariant.String),
                              QgsField("device", QVariant.String),
                              QgsField("projectid", QVariant.String),
                              QgsField("quantity_substance", QVariant.String),
                              #QgsField("unitvalue", QVariant.Double),
                              ])
            self.measurements_layer.updateFields()

            QgsProject.instance().addMapLayer(self.measurements_layer, False)  # False, meaning not ready to add to legend
            self.layer_group.insertLayer(0, self.measurements_layer)  # now add to legend in current layer group

            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            # self.jrodos_settings[self.measurements_layer] = deepcopy(self.measurements_settings)
            self.jrodos_settings[self.measurements_layer] = self.measurements_settings

            self.measurements_layer.loadNamedStyle(
                os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
            self.measurements_layer_featuresource = self.measurements_layer.dataProvider().featureSource()
            self.measurements_layer.selectionChanged.connect(self.measurement_selection_change)
        else:
            # there is already a layer for this measurements_settings object, so apparently we got new data for it:
            # remove current features from the  layer
            self.measurements_layer.startEditing()
            self.measurements_layer.setSubsetString('')  # first remove the query otherwise only the query result is removed
            self.measurements_layer.beginEditCommand("Delete Selected Features")
            self.measurements_layer.selectAll()
            self.measurements_layer.deleteSelectedFeatures()
            self.measurements_layer.endEditCommand()
            self.measurements_layer.commitChanges()
            # set current timestamp in the group node of the legend
            self.set_legend_node_name(self.layer_group,
                                      self.tr('Data refreshed: ') + QDateTime.currentDateTime().toString('MM/dd HH:mm:ss'))
            # self.measurements_layer.setName(layer_name) # only in 2.16

        feature_count = 0
        flist = []
        gmls = glob(os.path.join(output_dir, "*.gml"))
        for gml_file in gmls:
            gml_layer = QgsVectorLayer(gml_file, 'only for loading', 'ogr')
            if not gml_layer.isValid():
                self.msg(None, 'GML layer NOT VALID!')
                return
            else:
                features = gml_layer.getFeatures()

                step_count = 0
                new_unit_msg = True
                for feature in features:
                    if features.isClosed():
                        self.msg(None, 'Iterator CLOSED !!!!')
                        break
                    feature_count += 1
                    step_count += 1
                    fields = feature.fields()
                    fields.append(QgsField('quantity_substance'))
                    f = QgsFeature(fields)
                    if feature.geometry() is not None:
                        attributes = feature.attributes()
                        quantity = feature.attribute('quantity')
                        substance = feature.attribute('substance')
                        quantity_substance = self.get_quantity_and_substance_description(quantity, substance)
                        attributes.append(quantity_substance)
                        f.setAttributes(attributes)
                        f.setGeometry(feature.geometry())
                        flist.append(f)
                        if len(flist) > 1000:
                            self.measurements_layer.dataProvider().addFeatures(flist)
                            flist = []
                    else:
                        self.msg(None, self.tr("ERROR: # %s no geometry !!! attributes: %s ") % (feature_count, f.attributes()))
                        return

                # step_count = 0
                # new_unit_msg = True
                # for feature in features:
                #     if features.isClosed():
                #         self.msg(None, 'Iterator CLOSED !!!!')
                #         break
                #     feature_count += 1
                #     step_count += 1
                #     fields = feature.fields()
                #     fields.append(QgsField('unitvalue'))
                #     f = QgsFeature(fields)
                #     if feature.geometry() is not None:
                #         attributes = feature.attributes()
                #         value = float(feature.attribute('value'))
                #         # preferred unit is microSv/h, but the data contains value+unit column
                #         # set all values in column unitvalue in microSv/H
                #         if feature.attribute('unit') == 'USV/H':
                #             # value is in microSv/h all OK
                #             unitvalue = value
                #         elif feature.attribute('unit') == 'NSV/H':
                #             # value is in nanoSv/h, value / 1000
                #             unitvalue = value / 1000
                #         else:
                #             unitvalue = value
                #             if new_unit_msg:
                #                 new_unit_msg = False
                #         attributes.append(unitvalue)
                #         f.setAttributes(attributes)
                #         f.setGeometry(feature.geometry())
                #         flist.append(f)
                #         if len(flist) > 1000:
                #             self.measurements_layer.dataProvider().addFeatures(flist)
                #             flist = []
                #     else:
                #         self.msg(None, self.tr("ERROR: # %s no geometry !!! attributes: %s ") % (feature_count, f.attributes()))
                #         return

            if feature_count == 0:
                self.msg(None, self.tr("NO measurements found in :\n %s" % gml_file))
                return
            else:
               log.debug(self.tr("%s measurements loaded from GML file, total now: %s" % (step_count, feature_count)))

            self.measurements_layer.dataProvider().addFeatures(flist)
            #self.measurements_layer.dataProvider().addFeatures(features)
            self.measurements_layer.updateFields()
            self.measurements_layer.updateExtents()

        if register_layers:
            # add this layer to the TimeManager
            self.add_layer_to_timemanager(self.measurements_layer, 'time')

            # set the display field value
            self.measurements_layer.setMapTipTemplate('[% measurement_values()%]')
            # self.measurements_layer.setDisplayField('Measurements')
            # enable maptips if (apparently) not enabled (looking at the maptips action/button)
            if not self.iface.actionMapTips().isChecked():
                self.iface.actionMapTips().trigger()  # trigger action
            self.iface.layerTreeView().setCurrentLayer(self.measurements_layer)
            self.iface.mapCanvas().refresh()

            # add rainradar and to the TimeManager IF enabled
            if self.settings.value('rainradar_enabled'):
                self.add_rainradar_to_timemanager(self.measurements_layer)

    def get_quantity_and_substance_description(self, quantity, substance):
        if f'{quantity}_{substance}' in self.combi_descriptions:
            return f'{self.combi_descriptions[quantity+"_"+substance]}<br/> ({quantity}, {substance})'
        else:
            # mmm our lookup object does not have this combi, no description returned
            # this can happen if user uses older combinations list for this request
            return f'No Description (Please update combinations) <br/> ({quantity}, {substance})'

    def set_legend_node_name(self, treenode, name):
        """
        This is a workaround for this issue: http://hub.qgis.org/issues/15844
        :param treenode: treenode to change
        :param name:     new name
        :return:
        """
        model = self.iface.layerTreeView().model()
        index = model.node2index(treenode)
        model.setData(index, name)

    # TODO remove all shape file loading related code
    def load_jrodos_shape(self):
        shape_file = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            self.tr("Esri Shape (.shp) bestand openen..."),
            # os.path.realpath(filename),
            filter=self.tr("JRodos Esri Shape files (*.shp)"))

        if shape_file == "":  # user choose cancel
            return

        file_name, extension = os.path.splitext('{}'.format(shape_file))

        layer = QgsVectorLayer(shape_file, file_name, "ogr")

        # sld_file = '/home/richard/z/17/rivm/20170906_JRodosOutputBeverwijk/test.sld'
        sld_file = file_name + '.sld'

        sld_file_fixed = self.fix_jrodos_style_sld(sld_file)
        layer.loadSldStyle(sld_file_fixed)

        if not layer.isValid():
            print("Layer failed to load!")

        else:
            print("Layer was loaded successfully!")

        QgsProject.instance().addMapLayer(layer)

    # https://nathanw.net/2012/11/10/user-defined-expression-functions-for-qgis/

    # noinspection PyBroadException
    @qgsfunction(0, "RIVM")
    def measurement_values(values, feature, parent):
        """
        This is a specific function to be used as 'QgsExpression'.
        The function is to be used in the MapTips:
        It takes the feature, and creates a simple html with name/value pairs of the attributes.
        One special field is: 'info', this is actually a json string like:
           {
              "fields": [
                {
                  "name": "background",
                  "mnemonic": "Achtergrondniveau",
                  "value": "-"
                },
                {
                  "name": "reference_date",
                  "mnemonic": "Geldigheidsdatum/tijd",
                  "value": "-"
                }, ...
            }
        Which will be decoded and also shown as name/value pairs.
        """
        field_string = '<div style="width:300px; font-family: Sans-Serif;font-size: small" >'
        value = -99999
        unit = ''
        quantity_substance = ''
        for field in feature.fields():
            # skip info
            if not field.name() in ('Info', 'info'):
                # field we do not show
                if field.name().upper() in ('GML_ID', 'SUBSTANCE', 'QUANTITY'):
                    pass
                elif field.name().upper() in ('PROJECTID') and feature[field.name()] in ['-1', -1]:
                    # do not show projectid if -1
                    pass
                elif field.name().upper() in ('VALUE'):
                    value = feature[field.name()]
                elif field.name().upper() in ('UNIT'):
                    unit = feature[field.name()]
                elif field.name().upper() in ('QUANTITY_SUBSTANCE'):
                    quantity_substance = feature[field.name()]
                elif feature[field.name()] == '-': # VALUE = '-' ?  skip it
                    pass
                elif 'TIME' in field.name().upper():
                    field_string += field.name().title() + ': ' + '{}'.format(QDateTime.fromString(feature[field.name()], Qt.ISODateWithMs).toString('yyyy/MM/dd HH:mm (UTC)')) + '<br/>'
                else:
                    field_string += field.name().title() + ': ' + '{}'.format(feature[field.name()]) + '<br/>'
            else:
                # try to do the 'info'-field which is a json object
                try:
                    info_string = json.loads(feature['info'])
                    if len(info_string) == 0:
                        info_string = json.loads(feature['Info'])
                    if 'fields' in info_string:
                        v = ''
                        u = ''
                        for info_field in info_string['fields']:
                            # if there is not value, ignore
                            # original_value and original_unit are hanldled separated
                            if info_field['value'] == '-' or 'original' in info_field:
                                pass
                            elif info_field['name'] == 'value_original':
                                v = info_field['mnemonic'].title() + ': {:.6f}'.format(float(info_field['value']))
                            elif info_field['name'] == 'unit_original':
                                u = info_field['value'] + '<br/>'
                            elif 'mnemonic' in info_field:
                                field_string += info_field['mnemonic'].title() + ': ' + info_field['value'] + '<br/>'
                            elif 'name' in info_field:
                                field_string += info_field['name'].title() + ': ' + info_field['value'] + '<br/>'
                    field_string = '{} {} {}'.format(v, u, field_string)
                except Exception as e2:
                    field_string += "Failed to parse the 'info'-json field <br/>"
                    log.error('Tooltip function; Unable to parse this json: {}\nException: {}'.format(feature['info'], e2))
        return '<b>VALUE: {} {}<br/>{}</b><br/>'.format(value, unit, quantity_substance) + field_string + '</div>'

class JRodosError(Exception):
    """JRodos Exception for errors in the plugin.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

# this is a way to catch an exception from another (for example networking) thread.
# https://riverbankcomputing.com/pipermail/pyqt/2009-May/022961.html
# not shure if this has other implications, note that in qgis/python/utils.py this is also done...
# import sys
# def excepthook(excType, excValue, tracebackobj):
#     print excType
#     print excValue
#     print tracebackobj
#
# sys.excepthook = excepthook
