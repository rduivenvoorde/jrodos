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
from qgis.PyQt.QtCore import (
    qVersion,
    QSettings,
    QTranslator,
    QVariant,
    QCoreApplication,
    QDateTime,
    Qt,
    QUrl,
    QSortFilterProxyModel,
    QLocale,
)
from qgis.PyQt.QtGui import (
    QIcon,
    QStandardItemModel,
    QStandardItem,
    QDesktopServices,
    QColor,
    QFont,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QCheckBox,
    QComboBox,
)
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDateTimeRange,
    QgsExpression,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsInterval,
    QgsProcessingFeatureSourceDefinition,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsTemporalNavigationObject,
    QgsTemporalUtils,
    QgsLayerTreeUtils,
    QgsUnitTypes,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsVectorLayerTemporalContext,
    QgsVectorLayerTemporalProperties,
    QgsVectorLayerUtils,
)

from qgis.utils import qgsfunction, plugins
from qgis.gui import QgsVertexMarker

from .pyqtgraph import CurvePoint, TextItem, PlotCurveItem, PlotDataItem

from glob import glob
import re
from datetime import datetime
from copy import deepcopy
from pathlib import Path

import os.path
import json
import sys
import pickle
import copy

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

import sip

from . import resources  # needed for button images!

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

        self.MSG_TITLE = self.tr("RIVM JRodos Plugin")
        self.MENU_TITLE = self.tr('RIVM JRodos')

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
        self.BAR_STYLING_TITLE = self.tr('Styling data...')
        self.JRODOS_BAR_TITLE = self.tr('JRodos Model')

        self.MEASUREMENTS_BAR_TITLE = self.tr('Measurements')

        self.settings = JRodosSettings()

        # QAbstractItems model for the datapaths in the JRodos dialog
        self.jrodos_project_data = []

        # Declare instance attributes
        self.actions = []
        self.menu = self.MENU_TITLE
        self.toolbar = None

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
        self.completer = None

        self.calweb_project_id = None  # the actual Calweb project ID (integer)
        self.calweb_project = None  # this is an Object holding current project variables

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
        self.points = {}  # a points <-> device,feature mapping as lookup for later use

        # favorite measurements
        self.favorite_measurements_combo = None

        # settings dialog
        self.settings_dlg = None
        # creating a dict for a layer <-> settings mapping
        self.jrodos_settings = {}

        self.layer_group = None

        self.oldCrsBehavior = 'useGlobal'
        self.oldCrs = 'EPSG:4326'

        self.date_time_format_short = 'MM/dd HH:mm'  # '17/6 23:01'

        self.use_temporal_controller = True

        self.rivm_plugin_config_manager = None  # to be able to connect to it's signal

        # voronoi
        self.voronoi_layer = None
        self.do_voronoi = False
        self.voronoi_checkbox = None

        # cloud arrival time
        self.style_cloud_arrival_connected = False

        # BELOW CAN be used to time requests
        # TOTAL time of (paging) request(s)
        self.time_total = 0
        # time of one page / getdata
        self.time = QDateTime.currentMSecsSinceEpoch()

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
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.toolbar = self.get_rivm_toolbar()

        icon_path = ':/plugins/JRodos/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Show Measurements and JRodos ModelDialog'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # settings
        icon_path = ':/images/themes/default/mActionOptions.svg'
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

        icon_abort_path = os.path.join(os.path.dirname(__file__), 'icon_abort.png')
        self.add_action(
            icon_abort_path,
            text=self.tr(u'STOP Current Requests'),
            callback=self.abort_requests,
            parent=self.iface.mainWindow())

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

        if self.favorite_measurements_combo is None:
            self.favorite_measurements_combo = QComboBox()
            presets_dir = Path(__file__).parent / 'presets'
            # globbing all *.json files an sorting them (on filename!)
            preset_paths = list(presets_dir.glob('*.json'))
            preset_paths.sort(reverse=True)
            for file in preset_paths:
                # use title of the preset as text in the combo, and add the actual config as data
                f = file.open()
                conf_from_json = CalnetMeasurementsConfig.from_json(json.load(f))
                f.close()
                log.debug(f'Adding {conf_from_json.title} to presets')
                self.favorite_measurements_combo.insertItem(0, self.tr(conf_from_json.title), userData=conf_from_json)
            self.favorite_measurements_combo.insertItem(0, self.tr("Choose a preset"), userData={})
            # now connect the index changed (we could also only fire the request when user pushes button)
            preset = Utils.get_settings_value("jrodos_last_measurements_preset", None)
            if preset:
                self.favorite_measurements_combo.setCurrentText(preset)
            else:
                self.favorite_measurements_combo.setCurrentIndex(0)  # set to first item
            self.favorite_measurements_combo.currentIndexChanged.connect(self.load_measurements_favourite)
            # to be able to remove the progressbar (by removing the action), we 'catch' the action and add it to self.actions
            action = self.toolbar.addWidget(self.favorite_measurements_combo)
            self.actions.append(action)
        # reload chosen favorite
        self.add_action(
            icon_path=os.path.join(self.plugin_dir, 'images/reload.svg'),
            text=self.tr(u'Load favourite data (in new layer)'),
            callback=self.load_measurements_favourite,
            add_to_toolbar=True,
            parent=self.iface.mainWindow())

        # Create the dialog (after translation) and keep reference
        self.jrodosmodel_dlg = JRodosDialog(self.iface.mainWindow())
        # connect the change of the project dropdown to a refresh of the data path
        #self.jrodosmodel_dlg.tbl_projects.clicked.connect(self.project_selected)  # RD 20200727 Better to connect to the selection change of the selection model
        self.jrodosmodel_dlg.combo_task.currentIndexChanged.connect(self.task_selected)
        self.jrodosmodel_dlg.btn_item_filter.clicked.connect(self.show_data_item_filter_dialog)

        # Create the filter dialog
        self.filter_dlg = JRodosFilterDialog(self.jrodosmodel_dlg)
        self.filter_dlg.le_item_filter.setPlaceholderText(self.tr('Search in items'))

        # Create the measurements dialog
        self.measurements_dlg = JRodosMeasurementsDialog(self.iface.mainWindow())
        self.measurements_dlg.btn_get_combis.clicked.connect(self.get_quantities_and_substances_combis)
        self.measurements_dlg.tbl_combis.clicked.connect(self.quantities_substances_toggle)
        self.measurements_dlg.btn_now.clicked.connect(self.set_measurements_time_to_now)
        # self.quantities_substance_provider_finished(None)  # development
        # to be able to retrieve a reasonable quantities-substance combination
        # in the background, we HAVE TO set the start/end dates to a reasonable
        # value BEFORE the dlg is already shown...
        end_time = QDateTime.currentDateTimeUtc()  # end is NOW
        start_time = end_time.addSecs(-60 * 60 * 30 * 24)  # minus 24 hour
        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        self.measurements_dlg.cb_a1.stateChanged.connect(self.cb_a1_clicked)
        self.measurements_dlg.cb_a2.stateChanged.connect(self.cb_a2_clicked)
        self.measurements_dlg.cb_a3.stateChanged.connect(self.cb_a3_clicked)
        self.measurements_dlg.cb_a4.stateChanged.connect(self.cb_a4_clicked)
        self.measurements_dlg.cb_a5.stateChanged.connect(self.cb_a5_clicked)
        self.measurements_dlg.cb_unknown.stateChanged.connect(self.cb_unknown_clicked)
        self.measurements_dlg.cb_tgamma_a5.stateChanged.connect(self.cb_tgamma_a5_clicked)

        self.measurements_dlg.btn_all_combis.clicked.connect(lambda: self.quantities_substances_set_all(True))
        self.measurements_dlg.btn_no_combis.clicked.connect(lambda: self.quantities_substances_set_all(False))
        # on first start always start without calweb_project_id
        self.measurements_dlg.le_calweb_project_id.setText('-')

        # Create the settings dialog
        self.settings_dlg = JRodosSettingsDialog(self.iface.mainWindow())

        # Create GraphWidget
        self.graph_widget = JRodosGraphWidget()

        # Voronoi layer
        icon_abort_path = os.path.join(os.path.dirname(__file__), 'voronoi.svg')
        self.add_action(
            icon_abort_path,
            text=self.tr(u'Voronoi'),
            callback=self.switch_voronoi,
            parent=self.iface.mainWindow())
        if self.voronoi_checkbox is None:
            self.voronoi_checkbox = QCheckBox(self.tr('Show Voronoi'))
            self.voronoi_checkbox.setToolTip(self.tr('A Voronoi Polygon layer will be created during stepping'))
            # to be able to remove the progressbar (by removing the action), we 'catch' the action and add it to self.actions
            action = self.toolbar.addWidget(self.voronoi_checkbox)
            self.actions.append(action)
            self.voronoi_checkbox.clicked.connect(self.show_voronoi)

        # Make sure that when a QGIS layer is removed it will also be removed from the plugin
        QgsProject.instance().layerWillBeRemoved.connect(self.remove_jrodos_layer)

        self.iface.initializationCompleted.connect(self.qgis_initialization_completed)

    def abort_requests(self):
        log.debug('Aborting all Requests!!!')
        try:
            if self.measurements_provider and self.measurements_provider.reply:
                self.measurements_provider.reply.abort()
        except Exception as e:
            log.debug(f'Silent Exception when aborting the WFS measurements request: {e}')
        try:
            if self.jrodos_output_provider and self.jrodos_output_provider.reply:
                self.jrodos_output_provider.reply.abort()
        except Exception as e:
            log.debug(f'Silent Exception when aborting the JRodos WPS model output request: {e}')

    def debug(self, msg):
        msg = msg.replace('<', '&lt;').replace('>', '&gt;')
        from qgis.core import QgsMessageLog  # we need this... else QgsMessageLog is None after a plugin reload
        QgsMessageLog.logMessage('{}'.format(msg), 'JRodos3 debuginfo',  Qgis.Info)

    ###########################################
    # TODO: move this to a commons class/module
    ###########################################

    # self.LAST_ENVIRONMENT_KEY = 'rivm_config/last_environment'
    # self.LAST_PROJECT_ID = 'rivm_config/last_project_id'
    # self.LAST_PROJECT_ID = 'rivm_config/last_project_id'
    # self.TOOLBAR_NAME = 'RIVM Cal-Net Toolbar'

    def get_rivm_toolbar(self):
        self.TOOLBAR_NAME = 'RIVM Cal-Net Toolbar'
        toolbar_title = self.TOOLBAR_NAME  # TODO get this from commons and make translatable
        toolbars = self.iface.mainWindow().findChildren(QToolBar, toolbar_title)
        if len(toolbars) == 0:
            toolbar = self.iface.addToolBar(toolbar_title)
            toolbar.setObjectName(toolbar_title)
        else:
            toolbar = toolbars[0]
        return toolbar

    def qgis_initialization_completed(self):
        # get current/latest environment and project id from settings
        self.set_calweb_project(QSettings().value('rivm_config/last_project_id', '-'))

        # connect to the signals of the config manager
        if self.rivm_plugin_config_manager is None:  # if the rivm_environment_changed is already connected or not
            if 'RIVM_PluginConfigManager' not in plugins:
                # no need to go further, the RIVM_PluginConfigManager is not available yet... gonna try later
                self.msg(f'(no?) RIVM_PluginConfigManager in plugins: {plugins}???\nThis should not happen!')
                return
            self. rivm_plugin_config_manager = plugins['RIVM_PluginConfigManager']
            log.debug(f'Connecting to signals from configmanager: {self.rivm_plugin_config_manager}')
            self.rivm_plugin_config_manager.rivm_environment_changed.connect(self.environment_change)
            self.rivm_plugin_config_manager.rivm_project_id_changed.connect(self.project_id_change)

    ###########################################
    # TODO: END commons class/module
    ###########################################

    def show_settings(self):
        self.settings_dlg.show()

    # def current_layer_changed(self, layer):
    #     #log.debug(f'Current layer changed to: {layer}')
    #     pass

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
        docs = os.path.join(os.path.dirname(__file__), "help", "html", "index.html")
        log.debug(f'Trying to open HELP: {docs}')
        QDesktopServices.openUrl(QUrl("file://" + docs))

    def show_graph_widget(self, checked):
        if checked:
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.graph_widget)
        else:
            self.graph_widget.hide()

    # noinspection PyBroadException
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.MENU_TITLE,
                action)
            # self.iface.removeToolBarIcon(action)
            self.toolbar.removeAction(action)

        # deregister our custom QgsExpression function
        QgsExpression.unregisterFunction("measurement_values")

        # disconnecting sometimes creates havoc when changing environments
        # silently fail on errors
        try:
            # IF there is a measurement layer disconnect selectionChanged signal
            self.measurements_disconnect_selection_changed()
            QgsProject.instance().layerWillBeRemoved.disconnect(self.remove_jrodos_layer)
        except:
            pass

        # remove pointer
        self.remove_device_pointer()

        # IF there is a JRodos group... try to remove it (sometimes deleted?)
        try:
            if self.layer_group is not None:
                root = QgsProject.instance().layerTreeRoot()
                root.removeChildNode(self.layer_group)
        except Exception:
            pass

        # try to remove the updateTemporalRange signal
        try:
            self.iface.mapCanvas().temporalController().updateTemporalRange.disconnect(self.voronoi)
        except Exception:
            pass

        # try to remove the  signal
        try:
            self.iface.mapCanvas().temporalController().updateTemporalRange.disconnect(self.style_cloud_arrival)
        except Exception:
            pass

        # delete the graph widget
        del self.graph_widget

    def environment_change(self, environment):
        log.error(f'rivm ENVIRONMENT changed tO: {environment}')

    def project_id_change(self, calweb_project_id, calweb_project):
        """
        This slot is called when the rivm config manager emits the rivm_project_id_changed signal

        :param calweb_project_id: a (textual) number
        :param calweb_project: a dict with all project information
        """
        log.error(f'rivm PROJECT ID changed to: {calweb_project_id}')
        log.error(f'rivm PROJECT changed to: {calweb_project}')
        self.set_calweb_project(calweb_project_id, calweb_project)

    def run(self):
        try:
            self.setProjectionsBehavior()
            self.create_jrodos_layer_group()

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

    def create_jrodos_layer_group(self):
        """
        Both after getting the JRodos results or getting measurements the results
        will be placed in a 'JRodos'-layer group (for now)
        :return: True if a new one is created, False if an existing one is used
        """
        # create a 'JRodos layer' group if not already there ( always on TOP == 0 )
        #if self.measurements_layer is None and self.jrodos_output_settings is None:
        group_name = self.tr('JRodos plugin layers')
        # BUT only if there isn't already such a group:
        if QgsProject.instance().layerTreeRoot().findGroup(group_name) is None:
            self.layer_group = QgsProject.instance().layerTreeRoot().insertGroup(0, group_name)
            return True
        else:
            log.debug(f'RE-using available group {group_name}: {QgsProject.instance().layerTreeRoot().findGroup(group_name)}')
            self.layer_group = QgsProject.instance().layerTreeRoot().findGroup(group_name)
            return False

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

        start_date = self.measurements_dlg.dateTime_start.dateTime()  # UTC
        end_date = self.measurements_dlg.dateTime_end.dateTime()  # UTC
        if start_date >= end_date:
            self.msg(None, self.tr(
                '"Start time" is later then "End time" of selected '
                'period.\nPlease fix the dates in the Measurements dialog.'))
            return False

        self.measurements_dlg.lbl_retrieving_combis.setText("Searching possible Quantity/Substance combi's in this period ....")
        self.measurements_dlg.startProgressBar()
        config = CalnetMeasurementsUtilsConfig()
        config.url = self.settings.value('measurements_soap_utils_url')  # 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'

        config.start_datetime = start_date.toString(config.date_time_format)
        config.end_datetime = end_date.toString(config.date_time_format)

        quantities_substance_provider = CalnetMeasurementsUtilsProvider(config)
        quantities_substance_provider.finished.connect(self.quantities_substance_provider_finished)

        quantities_substance_provider.get_data('MeasuredCombinations')

    def quantities_substance_provider_finished(self, result):

        self.measurements_dlg.stopProgressBar()

        if hasattr(result, "error") and result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the Quantities-Substance combi's.\nNote: this can be a one-time issue... Please click the button again. \nor Check the Log Message Panel for more info."))
            self.measurements_dlg.lbl_retrieving_combis.setText("Nothing received, please try again.")
        else:
            self.combis = result.data
            self.combi_descriptions = {}
            user_quantities_substances_from_disk = []

            if self.combis is None or len(self.combis) == 0:
                self.msg(None,
                     self.tr("No Quantities-Substance combi's found for your time selection.\nPlease provide a bigger timeframe. \nNote that we only store 2 months of historical Eurdep data. "))
                self.load_default_combis()

            # LOAD saved user data_items from pickled file
            if os.path.isfile(self.USER_QUANTITIES_SUBSTANCES_PATH):
                with open(self.USER_QUANTITIES_SUBSTANCES_PATH, 'rb') as f:
                    user_quantities_substances_from_disk = pickle.load(f)
            self.measurements_dlg.lbl_retrieving_combis.setText(self.tr("Please select one or more combination(s)"))

            self.quantities_substances_model = QStandardItemModel()

            for combi in self.combis:
                if combi['quantity'] is None:
                    combi_key = combi['substance']
                elif combi['substance'] is None:
                    combi_key = combi['quantity']
                else:
                    combi_key = combi['quantity']+'_'+combi['substance']
                if combi_key in self.combi_descriptions:
                    log.debug(f'{combi_key} already in combinations list: ignoring...')
                else:
                    self.combi_descriptions[combi_key] = f"{combi['quantity_desc']} - {combi['substance_desc']}"
                    selected = False
                    if [combi['quantity'], combi['substance']] in user_quantities_substances_from_disk:
                        selected = True
                    data_item = QStandardItem("{}{}".format(combi['quantity'], combi['substance']))
                    data_item.setData([combi['quantity'], combi['substance']])
                    selected_item = QStandardItem(True)
                    selected_item.setData(True)
                    # sometimes descriptions are missing, then use code as description too:
                    if combi['quantity_desc'] in ('', None):
                        combi['quantity_desc'] = combi['quantity']
                    if combi['substance_desc'] in ('', None):
                        combi['substance_desc'] = combi['substance']
                    description = '{}, {} - ({}, {})'.format(combi['quantity_desc'],
                                                            combi['substance_desc'],
                                                            combi['quantity'],
                                                            combi['substance'])
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
        # only DEselect the tgamma-a5 cb else it will mess up the selecting all
        if not checked:
            self.measurements_dlg.cb_tgamma_a5.setChecked(checked)

    def quantities_substances_toggle_selection_group(self, text, checked, others_checked=None):
        if checked == 0:
            checked = False
        else:
            checked = True
        model = self.measurements_dlg.tbl_combis.model()
        for row in range(0, model.rowCount()):
            idx = model.index(row, 3)
            data = model.data(idx)  # 'T-GAMMAA5' etc etc
            idx = model.index(row, self.QMODEL_SEARCH_IDX)
            if text in data:
                model.setData(idx, checked)
                self.quantities_substance_color_model(row)
            elif others_checked is not None:
                model.setData(idx, others_checked)
                self.quantities_substance_color_model(row)

    def cb_tgamma_a5_clicked(self, checked):
        # First uncheck all checkboxes IF checked
        if checked:
            self.quantities_substances_set_all(False)
            # check tgamma a5 again (as it was being unchecked)
            self.measurements_dlg.cb_tgamma_a5.setChecked(checked)
        self.quantities_substances_toggle_selection_group('T-GAMMAA5', checked, False)

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
        self.projects_provider = JRodosProjectProvider(config)
        self.projects_provider.finished.connect(self.projects_provider_finished)
        self.projects_provider.get_data('/projects')

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
            # connect to selectionChanged of the selectionModel (!)
            self.jrodosmodel_dlg.tbl_projects.selectionModel().selectionChanged.connect(self.project_selected)

    def project_selected(self, selection_idx):
        if len(selection_idx.indexes()) == 0 or not selection_idx.indexes()[0].isValid():
            # nothing selected, do not use the index to set the other combo's
            self.datapaths_provider_finished(None)  # called with Result=one will clean up dialog widgets
            return
        model_idx = selection_idx.indexes()[0]
        # temporary text in the datapath combo
        self.jrodosmodel_dlg.combo_path.clear()
        self.jrodosmodel_dlg.combo_path.addItems([self.tr("Retrieving project datapaths...")])
        self.jrodos_project_data = None  # ? thorough cleanup?
        self.jrodos_project_data = []
        # Now: retrieve the datapaths of this project using a JRodosProjectProvider
        idx = self.jrodosmodel_dlg.proxy_model.mapToSource(model_idx)
        url = self.projects_model.item(idx.row(), 6).text()
        config = JRodosProjectConfig()
        config.url = url
        self.datapaths_provider = JRodosProjectProvider(config)
        self.datapaths_provider.finished.connect(self.datapaths_provider_finished)
        self.datapaths_provider.get_data()

    def datapaths_provider_finished(self, result=None):
        if result and not result.error():
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
                self.project_info_provider.finished.connect(self.provider_project_info_finished)
                self.project_info_provider.get_data()
            return
        else:
            self.jrodosmodel_dlg.combo_path.clear()
            # cleanup the start time, step etc in the dialog too
            self.set_dialog_project_info(None, None, None)
            self.task_model = None  # is used as flag for problems
            # let's remove this project from the user settings, 
            # as it apparently has datapath problems
            # and keeping this project as last project we stay in this 
            # loop of retrieving faulty datapaths
            Utils.set_settings_value("jrodos_last_model_project", "")
            if result is not None:
                self.msg(None,
                         self.tr(
                             "Problem retrieving the JRodos datapaths "
                             "for project:\n\n{}.").format(
                             result.url) +
                         self.tr(
                             "\n\nCheck the Log Message Panel for more "
                             "info, \nor replay this url in a browser."))
            return

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

    def provider_project_info_finished(self, result):
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

    def set_dialog_project_info(self, time_step, model_time, release_start):
        """
        Used to set AND REset (to None) the 3 params in the dialog
        :param time_step: model Timestep in the dialog is shown in minutes (
        as in JRodos), but retrieved seconds!!
        :param model_time: model time / duration of prognosis is shown in
        hours (as in JRodos), but retrieved in seconds!!
        :param release_start: start of release in ISO timestring
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
        if release_start is None:
            self.jrodosmodel_dlg.lbl_start2.setText('-')
            self.jrodosmodel_dlg.le_start.setText('')  # modeltime (hours)
        else:
            self.jrodosmodel_dlg.le_start.setText('{}'.format(release_start))  # modeltime (hours)
            # model start / start of release is string like: "2016-04-25T08:00:00.000+0000"
            datetime_utc = QDateTime.fromString(release_start, Qt.ISODate)
            datetime_local = datetime_utc.toTimeSpec(Qt.LocalTime)
            self.jrodosmodel_dlg.lbl_start2.setText('{}'.format(datetime_local.toString(self.date_time_format_short+' t')))  # localtime + timezone

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
        log.debug(f'Store {last_used_project} as "jrodos_last_model_project"')
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
        if result.error_code == 5:
            self.msg(None, self.tr("Request(s) Cancelled\nOR\nA Network timeout for JRodos model output. \nConsider rising it in Settings/Options/Network. \nValue is now: {} msec".format(QSettings().value('/qgis/networkAndProxy/networkTimeout', '??'))))
        elif result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the JRodos model output. \nCheck the Log Message Panel for more info"))
        else:
            # Load the received shp-zip files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None:
                unit_used = self.jrodos_output_settings.units
                s = self.jrodos_output_settings.jrodos_path[:-1]  # contains path='...' remove last quote
                s2 = self.jrodos_output_settings.jrodos_project
                layer_name = unit_used + ' - ' + s.split('=;=')[-2]+', '+s.split('=;=')[-1]+', '+s2.split("'")[1]
                self.load_jrodos_output(
                    result.data['output_dir'], 'totalpotentialdoseeffective.qml', layer_name, unit_used)
            else:
                self.msg(None, self.tr("No Jrodos Model Output data? Got: {}").format(result.data))
        self.jrodos_output_settings = None
        self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)

    def set_measurements_time_to_now(self):
        """ Set the endtime to NOW (UTC) and change starttime such
        that the timeframe length stays the same,
        """
        # first check wat current timeframe is that user is using
        start_date = self.measurements_dlg.dateTime_start.dateTime()  # UTC
        end_date = self.measurements_dlg.dateTime_end.dateTime()  # UTC
        old_timeframe = end_date.toSecsSinceEpoch() - start_date.toSecsSinceEpoch()
        end_time = QDateTime.currentDateTimeUtc()  # end is NOW
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        # ONLY reset starttime if it has a positive value (== BEFORE NOW)
        if old_timeframe > 0:
            start_time = end_time.addSecs(-old_timeframe)
            self.measurements_dlg.dateTime_start.setDateTime(start_time)
        else:
            log.debug("Mmm, negative timeframe... setting start to -6 hours")
            start_time = end_time.addSecs(-(60*60*6))
            self.measurements_dlg.dateTime_start.setDateTime(start_time)

    def set_calweb_project(self, calweb_project_id, calweb_project={}):
        if str(calweb_project_id) == str(self.calweb_project_id) and calweb_project == self.calweb_project:
            log.debug(f'set_calweb_project called, but nothing seemed to have changed ({calweb_project_id}), ignoring...')
            return
        if not str(calweb_project_id).isnumeric() and not calweb_project_id == '':
            log.debug(f'set_calweb_project called, but using a non-numeric value: ({calweb_project_id}), ignoring...')
            return

        log.debug(f'Set Calweb Project to: {calweb_project}')
        self.calweb_project = calweb_project
        log.debug(f'Set Calweb Project Id to: {calweb_project_id}')
        self.calweb_project_id = calweb_project_id
        # make sure the right calweb project id is shown in the measurements dialog
        self.measurements_dlg.le_calweb_project_id.setText(f'{self.calweb_project_id}')

        # try to get the start (and optional) end time from the project
        # note: "2021-09-28T12:42:52.000+02:00" return a local time, so you need toUTC() !!
        if 'isostarttime' in self.calweb_project:
            starttime = QDateTime.fromString(self.calweb_project['isostarttime'], Qt.ISODateWithMs).toUTC()
            log.debug(f'Setting starttime, based on starttime from project {self.calweb_project_id} to {starttime}')
            self.measurements_dlg.dateTime_start.setDateTime(starttime)
        # Is there an endtime in the result? Else set end to NOW()
        if 'isoendtime' in self.calweb_project:
            if self.calweb_project['isoendtime'] is not None:
                endtime = QDateTime.fromString(self.calweb_project['isoendtime'], Qt.ISODateWithMs).toUTC()
                log.debug(f'Setting endtime, based on endtime from project {self.calweb_project_id} to {endtime}')
            else:
                endtime = QDateTime.currentDateTimeUtc()
                log.debug(f'NOT setting endtime, as project {self.calweb_project_id} appears to not have one (yet)')
            self.measurements_dlg.dateTime_end.setDateTime(endtime)

    def show_measurements_dialog(self):

        if self.measurements_settings is not None:
            self.msg(None, self.tr("Still busy retrieving Measurement data via WFS, please try later..."))
            # stop this session
            return True
        if self.measurements_layer is not None:
            #log.debug('### 1 self.measurements_layer is not None')
            # that is we have measurements from an earlier run
            self.measurements_settings = self.jrodos_settings[self.measurements_layer]
            self.start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
            self.end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)
        elif self.jrodos_output_settings is not None:
            #log.debug('### 2 show_measurements_dialog: self.jrodos_output_settings is not None')
            # BUT if we just received a model, INIT the measurements dialog based on this
            self.start_time = self.jrodos_output_settings.jrodos_datetime_start.toUTC()  # we REALLY want UTC
            self.end_time = self.start_time.addSecs(60 * int(self.jrodos_output_settings.jrodos_model_time))  # model time
            #log.debug(f'### 2  self.start_time={self.start_time} self.end_time={self.end_time}')
        elif Utils.get_settings_value('startdatetime', False) and Utils.get_settings_value('enddatetime', False):
            #log.debug('### 3 settings values...')
            self.start_time = Utils.get_settings_value('startdatetime', '')
            self.end_time = Utils.get_settings_value('enddatetime', '')
            # log.debug(f'Got start and end from settings: {self.start_time} {self.end_time}')
        elif self.start_time is None:
            #log.debug('### 4 self.start_time is None...')
            hours = 1  # h
            self.end_time = QDateTime.currentDateTimeUtc()  # end NOW
            self.start_time = self.end_time.addSecs(-60 * 60 * hours)  # minus h hours

        self.measurements_dlg.dateTime_start.setDateTime(self.start_time)
        self.measurements_dlg.dateTime_end.setDateTime(self.end_time)
        self.load_default_combis()
        self.measurements_dlg.show()

        result = self.measurements_dlg.exec_()
        if result:  # OK was pressed
            # selected endminusstart + save to QSettings
            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            # if user selected 'alles', set the endminusstart (= $3 in db procedures) to -1
            # endminusstart value of -1 will NOT use the interval/integration time
            if 'ALLES' == endminusstart:
                endminusstart = '-1'
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

            if start_date >= end_date:
                self.msg(None, self.tr('"Start time" is later then "End time" of selected period.\nPlease fix the dates in the Measurements dialog.'))
                return False

            measurements_settings = CalnetMeasurementsConfig()
            measurements_settings.url = self.settings.value('measurements_wfs_url')
            # replacing the '-' because when NO projectid is given we show '-'
            project_id = self.measurements_dlg.le_calweb_project_id.text().replace('-', '').strip()
            # if project_id == 0, it means there is no current project: set it to '' so project id will not be sent to WFS
            if str(project_id) == '0':
                project_id = ''
            if not project_id == '' and not project_id.isdigit():
                # User tries to use a string in this projectid field
                self.msg(None, self.tr('Project number is a single CalWeb project number (or empty)'))
                return False
            if len(project_id) != 0:
                log.info(f'Project_id: {project_id} found! Adding to CQL in WFS request')
                # setting it in the config as a String (although it will end up as an integer in DB)
                measurements_settings.projectid = project_id  # is text anyway at this moment
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

    def load_default_combis(self):
        with open(self.plugin_dir + '/measurement_start_combis.json', 'rb') as f:
            self.combis = json.load(f)
            result = lambda: None  # 'empty' object
            result.data = self.combis
            self.quantities_substance_provider_finished(result)

    def start_measurements_provider(self):
        if self.jrodos_output_settings is None:
            project = "'measurements'"
            path = "'=;=wfs=;=data'"
            self.measurements_settings.output_dir = ProviderUtils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
        else:
            self.measurements_settings.output_dir = self.jrodos_output_settings.output_dir
        self.create_jrodos_layer_group()  # if not there, create a JRodos layer group first
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
            self.msg(None, self.tr("Request(s) Cancelled\nOR\nA Network timeout for Measurements-WFS request. \nConsider rising it in Settings/Options/Network. \nValue is now: {} msec".format(QSettings().value('/qgis/networkAndProxy/networkTimeout', '??'))))
        elif result.error():
            self.msg(None, result)
            self.iface.messageBar().pushMessage(self.tr("Network problem"), self.tr(f'{result.error_code} see messages'), level=Qgis.Critical)
        else:
            # Load the received gml files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None and result.data['count'] > 0:
                now = QDateTime.currentMSecsSinceEpoch()
                #self.load_measurements(result.data['output_dir'], 'measurements_rotation.qml')
                self.load_measurements(result.data['output_dir'], 'measurements_rotation_labeled.qml')
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
        selected_features_ids = self.measurements_layer.selectedFeatureIds()
        #log.debug(f'Measurements selection change!: {selected_features_ids}')

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
                        #t = QDateTime.fromString(feature['time'], 'yyyy-MM-ddTHH:mm:ssZ').toMSecsSinceEpoch()
                        # mmm, attribute can show up as QDateTime OR as str depending on OperatingSystem or QGIS version...
                        time = feature['time']
                        if isinstance(time, QDateTime):  # QDateTime
                            t = time.toMSecsSinceEpoch()
                        else:  # str
                            t = QDateTime.fromString(feature['time'], 'yyyy-MM-ddTHH:mm:ssZ').toMSecsSinceEpoch()
                        x.append(t/1000)
                        #y.append(feature['unitvalue'])
                        y.append(feature['value'])
                        #log.debug('XXX {} - {} - {} - {} - {} - {}'.format(feature['time'], t/1000, feature['value'], feature['device'], feature['quantity'], feature['unit']))

                    # curve = self.graph_widget.graph.plot(x=x, y=y, pen='ff000099')
                    # NOT using shortcut notation above, because we want to keep a reference to the PlotCurveItem for click

                    # plot curve item symbols: x, o, +, d, t, t1, t2, t3, s, p, h, star
                    # t=triangle, s=square, p=pentagon, h=hexagon
                    if len(x) < 20:
                        point = PlotDataItem(x=x, y=y, symbol='+', color='0000ff99', symbolPen='0000ff99')
                        point.sigPointsClicked.connect(self.curve_or_point_click)
                        self.points[point] = (device, selected_feature)
                        self.graph_widget.graph.addItem(point)

                    curve = PlotCurveItem(x=x, y=y, pen='ff000099', mouseWidth=0)
                    curve.setClickable(True, 6)
                    curve.sigClicked.connect(self.curve_or_point_click)
                    self.graph_widget.graph.addItem(curve)

                    # create a curve <-> device,feature mapping as lookup for later use
                    self.curves[curve] = (device, selected_feature)

                    label_point = CurvePoint(curve)
                    self.graph_widget.graph.addItem(label_point)

                    # for T-GAMMA we always show microSv/h, for other it is quantity dependent
                    quantity = feature['quantity']
                    if quantity.upper() == 'T-GAMMA' and feature['unit'] in ['NSV/H', 'USV/H']:
                        unit = 'µSv/h'  # 'USV/H' we (apr2020 NOT) keep notation as eurdep data: USV/H == microSv/h
                    else:
                        unit = feature['unit']  # for other

                    label = TextItem('{} {} {}'.format(device, quantity, unit), anchor=(0, 0), color='0000ff')
                    label.setFont(font)
                    label_point.setPos(0)
                    label.setParentItem(label_point)
            if first:
                if selected_feature is not None:
                    self.set_device_pointer(selected_feature.geometry())
                first = False
            else:
                self.remove_device_pointer()

    def curve_or_point_click(self, item):
        if item in self.curves:
            device, feature = self.curves[item]
        elif item in self.points:
            device, feature = self.points[item]
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

    def remove_jrodos_layer(self, layer2remove):
        arrival_layers = 0
        for layer in self.jrodos_settings.keys():
            # go over all layer names, and (HACK) if 'arrival' is in the name, disconnect the updateTemporalRange signal
            #   which calls 'style_cloud_arrival'...
            if not sip.isdeleted(layer) and 'ARRIVAL' in layer.name().upper():
                arrival_layers += 1
            if not sip.isdeleted(layer) and layer2remove == layer.id():
                if self.measurements_layer == layer:
                    if self.graph_widget and not sip.isdeleted(self.graph_widget):
                        self.graph_widget.graph.clear()
                    self.measurements_layer = None
                    self.remove_device_pointer()
                    # sometimes C++ layer is already deleted...
                    # sometimes I see:     for layer in self.jrodos_settings.keys():  # RuntimeError: dictionary changed size during iteration
                    # could it te that this is the boosdoener??
#                    del self.jrodos_settings[layer]
        # disconnect if there are no 'arrival' layers anymore...
        if arrival_layers == 1 and self.style_cloud_arrival_connected:
            log.debug('NO apparent cloud arrival layers anymore... DIS-connecting updateTemporalRange signal...')
            self.iface.mapCanvas().temporalController().updateTemporalRange.disconnect(self.style_cloud_arrival)
            self.style_cloud_arrival_connected = False

    # noinspection PyBroadException
    def load_jrodos_output(self, output_dir, style_file, layer_name, unit_used):
        """
        Load the data (and optional style) from the (from the WPS retrieved) zip file.

        :param output_dir: directory containing zips with shapefiles
        :param style_file: style (qml) to be used to style the layer in
        :param layer_name:
        :param unit_used:
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
                try:
                    # https://jira.cal-net.nl/browse/QGIS-81
                    log.debug(f"START trying to create a DATETIME column in {gpkgfile} in {gpkgdir}")
                    md = QgsProviderRegistry.instance().providerMetadata('ogr')
                    conn = md.createConnection(gpkgs[0], {})

                    queries = [
                    'ALTER TABLE data RENAME Datetime TO Datetimestring;',
                    'ALTER TABLE data ADD Datetime DATETIME;',
                    'UPDATE data SET Datetime = Datetimestring;',
                    'DROP VIEW view;',
                    'CREATE VIEW view AS SELECT data.fid AS OGC_FID, data.Cell, data.Datetime, data.Value, grid.grid_geom AS geom FROM data JOIN grid ON data.Cell = grid.Cell;',
                    'DROP INDEX data_time_index;',
                    'CREATE INDEX data_time_index ON data(Datetime);'
                    ]
                    for q in queries:
                        conn.executeSql(q)
                    log.debug(f"Successfully created a DATETIME column in {gpkgfile} in {gpkgdir}")
                    #raise Exception('test')

                except Exception as e:
                    log.debug(f"ERROR trying to create a DATETIME column in {gpkgfile} in {gpkgdir}")
                    # go with the string-datetime column: working (but only when user does NOT adjust the layer/style)

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
                time = feature.attribute('Datetime')
                if value > 0:
                    if value < features_min_value:
                        features_min_value = value
                    # only check when still no valid times found...
                    if not features_have_valid_time and time is not None and time != "":# and time > 0:
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
        if not sld_loaded_ok and 'ARRIVAL' in jrodos_output_layer.name().upper():
            log.debug(f"'ARRIVAL' in layername: {jrodos_output_layer.name().upper()} will create style for every time step..")
            if not self.style_cloud_arrival_connected:
                log.debug('CONNECT style_cloud_arrival to the updateTemporalRange signal...')
                self.iface.mapCanvas().temporalController().updateTemporalRange.connect(self.style_cloud_arrival)
                self.style_cloud_arrival_connected = True
            else:
                log.debug('NOT connecting style_cloud_arrival to the updateTemporalRange signal, as it apparently is already...')
        elif not sld_loaded_ok:
            log.debug('No sld found in JRodos result, will style the Layer automagically')
            self.style_jrodos_layer(jrodos_output_layer)

        # self.msg(None, "min: {}, max: {} \ncount: {}, deleted: {}".format(features_min_value, 'TODO?', i, j))
        # ONLY when we received features back load it as a layer
        if features_added:
            # add layer to the map
            QgsProject.instance().addMapLayer(jrodos_output_layer,
                                              False)  # False, meaning not ready to add to legend
            self.layer_group.insertLayer(1, jrodos_output_layer)  # now add to legend in current layer group
        # ONLY when we received features back AND the time component is valid: register the layer to the timemanager etc
        if features_have_valid_time:
            # put a copy of the settings into our layer<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            self.jrodos_settings[jrodos_output_layer] = deepcopy(self.jrodos_output_settings)

            if self.use_temporal_controller:
                 # SO: we use an iso datetime text (which works in the Temporal Controller)
                log.debug('Using DateTime (iso-datetime as TEXT) from table...')
                self.add_layer_to_timecontroller(jrodos_output_layer,
                                                 time_column='Datetime',
                                                 frame_size_seconds=self.jrodos_output_settings.jrodos_model_step)
        # let's repaint the canvas (another time?) because apparently adding the cloud arrival styling does not?
        self.iface.mapCanvas().redrawAllLayers()

    def cloud_arrival_for_layer(self, layer: QgsVectorLayer):
        """
        The style to be used for cloud arrival is to be determined by the Maximum (arrival time) value.

        So we first determine the max value.
        Then we have 2 strategies:
        - is to create 5 (in case the max < 1.0 hr) or (mostly) 10 classes exactly as JRodos does it
        - use some predefined styles from Jasper, based on the number of hours the model has gone

        :param QgsVectorLayer: JRodos (vector) output layer
        """

        jrodos_styles = False

        # select features based on current temporal filter
        temporal_filter = self.temporal_filter_for_layer(layer, self.iface.mapCanvas())
        if temporal_filter:
            # log.debug(f'Temporal Filter: {temporal_filter}')
            # layer.selectByExpression(temporal_filter, Qgis.SelectBehavior.SetSelection)
            # values = QgsVectorLayerUtils.getValues(layer, 'Value', selectedOnly=True)[0]
            # max_value = max(values)


            # BEGIN of current filter  -- JRODOS: UTC
            # iface.mapCanvas().temporalRange().begin()
            # PyQt5.QtCore.QDateTime(2019, 9, 1, 7, 0, 0, 0, PyQt5.QtCore.Qt.TimeSpec(1))  # 1 == UTC !!!
            # iface.mapCanvas().temporalRange().begin().toTimeSpec(Qt.LocalTime)
            # PyQt5.QtCore.QDateTime(2019, 9, 1, 9, 0)

            # BEGIN of total time range of Temporal Controler  -- LOCAL TIME
            # QgsTemporalUtils.calculateTemporalRangeForProject(QgsProject.instance()).begin()
            # PyQt5.QtCore.QDateTime(2019, 9, 1, 7, 0)
            # QgsTemporalUtils.calculateTemporalRangeForProject(QgsProject.instance()).begin().toTimeSpec(Qt.LocalTime)
            # PyQt5.QtCore.QDateTime(2019, 9, 1, 7, 0)

            # ARGH, something's going wrong...
            # The temporal controller is in LOCAL time
            # While the (JRodos/Measurement)data is actually in UTC, BUT(!!!!) seen by QGIS as LOCAL !!
            # So the HACK is to substract the hours of LOCAL from UTC
            # OFFset localtime from UTC
            # https://stackoverflow.com/questions/24281744/how-to-find-out-the-utc-offset-of-my-current-location-in-qt-5-1
            # QDateTime.currentDateTime().timeZone().offsetFromUtc(QDateTime.currentDateTime())( in seconds)

            # calculate localtime-utc offset in hours
            begin = QgsTemporalUtils.calculateTemporalRangeForProject(QgsProject.instance()).begin()
            utc_offset_hours = begin.timeZone().offsetFromUtc(begin)/3600
            # substract that from the difference in start of project range and slider current end
            max_value = (begin.secsTo(self.iface.mapCanvas().temporalRange().end())/3600) - utc_offset_hours
            #log.debug(f'max_value (hours): {max_value}')
        else:
            idx = layer.fields().indexFromName('Value')
            max_value = layer.maximumValue(idx)
        # log.debug(f'min: {min_value} max: {max_value}')
        # max_value < 1.0: 5 classes, else: 10 classes
        steps = 10
        if max_value <= 1.0:
            steps = 5
        # create a new rule-based renderer
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        # get the "root" rule
        root_rule = renderer.rootRule()

        if jrodos_styles:
            # create a nice 'Full Cream' color ramp ourselves NOTE: we start at 0 (though the min_value is probably higher)
            rules = RangeCreator.create_rule_set(0, max_value, class_count=steps, min_inf=False, max_inf=False, reverse=True)
        else:
            rules = RangeCreator.create_cloud_ruleset(max_value)

        for label, expression, color in rules:
            # create a clone (i.e. a copy) of the default rule
            rule = root_rule.children()[0].clone()
            # set the label, expression and color
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().symbolLayer(0).setFillColor(color)
            # outline transparent
            rule.symbol().symbolLayer(0).setStrokeColor(QColor.fromRgb(255, 255, 255, 0))
            # append the rule to the list of rules
            root_rule.appendChild(rule)

        # delete the default rule
        root_rule.removeChildAt(0)
        # apply the renderer to the layer
        layer.setRenderer(renderer)

    def style_cloud_arrival(self, temporal_range):
        #log.debug(f'STYLING CLOUD ARRIVAL... will take some time')
        self.jrodos_output_progress_bar.setFormat(self.BAR_STYLING_TITLE)
        QCoreApplication.processEvents()  # to be sure we have the styling msg
        for layer in self.jrodos_settings.keys():
            # go over all layer names, and (HACK) if 'arrival' is in the name, style it for cloud_arrival
            if not sip.isdeleted(layer) and 'ARRIVAL' in layer.name().upper():
                # get min and max for current temporal_range (frame)
                self.cloud_arrival_for_layer(layer)
        self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)

    @staticmethod
    def fix_jrodos_style_sld(jrodos_style_sld):
        """
        JRodos sld's can be old styles, that is do not have the StyledLayerDescriptor part
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
    def copy_measurements_style(target_layer, source_layer=None):
        """
        This method tries to copy the (RuleBased) Styling-rules from one layer to
        another.
        Mostly used to copy the styling from a point (measurements) layer to
        a polygon (voronoi of measurements) layer

        :param target_layer:
        :param source_layer:
        :return: None
        """
        # create a NEW rule-based renderer
        symbol = QgsSymbol.defaultSymbol(target_layer.geometryType())
        target_renderer = QgsRuleBasedRenderer(symbol)
        # get the "root" rule
        target_root_rule = target_renderer.rootRule()

        if source_layer:
            # make sure this is also a RuleBased rendered layer
            # https://qgis.org/pyqgis/master/core/QgsRuleBasedRenderer.html
            # https://snorfalorpagus.net/blog/2014/03/04/symbology-of-vector-layers-in-qgis-python-plugins/
            renderer_type = source_layer.renderer().type()
            log.debug(f'Styling Target layer {target_layer} with rendertype {target_renderer.type()} To Source layer: {source_layer} with rendertype {renderer_type}')
            if renderer_type in ('RuleRenderer',):  # ?? type() returns a string, using 'in' to make it possible to also use Categorized Renderers if needed
                #source_renderer = source_layer.renderer()
                #for s in source_renderer.symbols(QgsRenderContext()):
                source_root_rule = source_layer.renderer().rootRule()
                for child_rule in source_root_rule.children():
                    # log.debug(child_rule.symbol())
                    # log.debug(child_rule.filterExpression())
                    # log.debug(child_rule.symbol().color())
                    # log.debug(child_rule.label())
                    # create a clone (i.e. a copy) of the default TARGET rule
                    rule = target_root_rule.children()[0].clone()

                    # # set the label, expression and color
                    rule.setLabel(child_rule.label())
                    rule.setFilterExpression(child_rule.filterExpression())
                    rule.symbol().symbolLayer(0).setFillColor(child_rule.symbol().color())

                    outline = True
                    if outline:
                        # visible outline
                        rule.symbol().symbolLayer(0).setStrokeColor(QColor.fromRgb(0, 0, 0, 50))
                    else:
                        # (invisible) outline transparent
                        rule.symbol().symbolLayer(0).setStrokeColor(QColor.fromRgb(255, 255, 255, 0))

                    # # set the scale limits if they have been specified
                    # # if scale is not None:
                    # #     rule.setScaleMinDenom(scale[0])
                    # #     rule.setScaleMaxDenom(scale[1])
                    # # append the rule to the list of rules
                    target_root_rule.appendChild(rule)
            else:
                raise Exception('Trying to create a new style, but source layer is NOT rule based styled!!')
        # delete the default rule
        target_root_rule.removeChildAt(0)
        # apply the renderer to the layer
        target_layer.setRenderer(target_renderer)

    @staticmethod
    def style_jrodos_layer(layer):
        # create a new rule-based renderer
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        # get the "root" rule
        root_rule = renderer.rootRule()

        # create a nice 'Full Cream' color ramp ourselves
        rules = RangeCreator.create_log_rule_set(-5, 4, False, True)

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
    def temporal_filter_for_layer(layer, canvas):
        if canvas.mapSettings().isTemporal():
            if not layer.temporalProperties().isVisibleInTemporalRange(canvas.temporalRange()):
                return "FALSE"  # nothing is visible
            temporal_context = QgsVectorLayerTemporalContext()
            temporal_context.setLayer(layer)
            return layer.temporalProperties().createFilterString(temporal_context, canvas.temporalRange())
        else:
            return None

    def switch_voronoi(self):
        """
        Used to check/uncheck the Voronoi checkbox
        :return:
        """
        self.voronoi_checkbox.click()

    def show_voronoi(self, checked):
        # always try to remove a (potential) connected signal
        try:
            self.iface.mapCanvas().temporalController().updateTemporalRange.disconnect(self.voronoi)
        except Exception as e:
            pass
        # try to remove a potential available voronoi layer
        try:
            if self.voronoi_layer:
                QgsProject.instance().removeMapLayer(self.voronoi_layer.id())
                self.iface.mapCanvas().refresh()
        except Exception as e:
            pass
        if checked:
            # create a voronoi for current timestep
            self.voronoi()
            # connect the temporal steps to the voronoi creation
            self.iface.mapCanvas().temporalController().updateTemporalRange.connect(self.voronoi)

    def voronoi(self, temporal_range=None):
        """
        :return:
        """
        #log.debug(f'RANGE RANGE {temporal_range}')
        self.time = QDateTime.currentMSecsSinceEpoch()
        self.time_total = self.time
        try:
            #https://gis.stackexchange.com/questions/329715/algorithm-not-found-by-pyqgis
            from qgis.analysis import QgsNativeAlgorithms
            import processing
            from plugins.processing.core.Processing import Processing
            Processing.initialize()
            QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(),
                                self.MSG_TITLE,
                                self.tr("Missing 'Processing' plugin,\n we REALLY need that one.\n Please enable it in Plugin Manager first..."),
                                QMessageBox.Ok,
                                QMessageBox.Ok)
            return

        point_layer = None
        try:
            if self.measurements_layer:
                point_layer = self.measurements_layer
        except Exception as e:
            pass

        if point_layer is None:
            log.debug('Still missing Measurements Layer, we REALLY need that one...')
            # try current active layer ? development/tests
            if self.iface.mapCanvas().currentLayer():
                point_layer = self.iface.mapCanvas().currentLayer()
            else:
                return

        #log.debug(f'Voronoi: loading modules took: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        # remove an already available voronoi layer (as potentially we do this for every timestep)
        try:
            if self.voronoi_layer:
                QgsProject.instance().removeMapLayer(self.voronoi_layer.id())
        except Exception as e:
            pass

        #log.debug(f'Voronoi: loading/removing layer took: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        # select features based on current temporal filter
        temporal_filter = self.temporal_filter_for_layer(point_layer, self.iface.mapCanvas())
        if temporal_filter:
            # let's disconnect the selectionChange event, as that slows down the selection below considerably
            self.measurements_disconnect_selection_changed()
            point_layer.selectByExpression(temporal_filter, Qgis.SelectBehavior.SetSelection)
        else:
            # this selects EVERYTHING!!!  :-(
            log.debug(f'NO Temporal Filter! Selecting ALL Features in measurement layer before Voronoi creation')
            point_layer.selectByRect(point_layer.extent(), Qgis.SelectBehavior.SetSelection)

        #log.debug(f'Voronoi: selecting features took: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        # The voronoi algorithm will throw an exception if:
        # - the number of points < 4
        # - the extent of the points is the so called Null-rectangle (QgsRectangle(0,0 0,0)
        # so we check for both (Null-rectangle you can check with QgsRectangle.isNull())
        selection_feature_count = point_layer.selectedFeatureCount()
        selection_extent = point_layer.boundingBoxOfSelected()
        if selection_feature_count < 4 or selection_extent.isNull():
            #log.debug(f'Voronoi IMPOSSIBLE: current selection contains: {selection_feature_count} features, extent = {selection_extent}, aborting...')
            return
        else:
            log.debug(f'Voronoi: feature_count: {selection_feature_count}, bbox of selected: {point_layer.boundingBoxOfSelected()} ISNULL: {point_layer.boundingBoxOfSelected().isNull()} ')

        # Voronoing ONLY the selected
        # NOTE: the colon (:) behind 'memory' in the 'OUTPUT' param is mandatory,
        # else QGIS will create a geopackage!
        selected = True
        params = {
            'INPUT': QgsProcessingFeatureSourceDefinition(point_layer.id(), selectedFeaturesOnly=selected),
            'OUTPUT': 'memory:',
            'BUFFER': 5,
        }
        result = processing.run("qgis:voronoipolygons", params)

        #log.debug(f'Voronoi: processing run took: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        result_layer = result['OUTPUT']
        result_layer_name = 'Voronoi'
        if temporal_range:
            result_layer_name = f'Voronoi: {temporal_range.begin().toString(self.date_time_format_short)} - {temporal_range.end().toString(self.date_time_format_short)}'
        result_layer.setName(result_layer_name)
        QgsProject.instance().addMapLayer(result_layer, False)  # False, meaning not ready to add to legend

        self.voronoi_layer = result_layer
        # QgsLayerTreeUtils.insertLayerBelow is not working below 32207 see: https://github.com/qgis/QGIS/issues/47909
        if Qgis.QGIS_VERSION_INT >= 32207:
            QgsLayerTreeUtils.insertLayerBelow(QgsProject.instance().layerTreeRoot(), point_layer, self.voronoi_layer)  # now add to legend below the point layer
        else:
            tree_node = QgsProject.instance().layerTreeRoot().findLayer(point_layer)
            if tree_node and tree_node in QgsProject.instance().layerTreeRoot().children():
                index = QgsProject.instance().layerTreeRoot().children().index(tree_node)
                QgsProject.instance().layerTreeRoot().insertLayer(index+1, result_layer)  # now add to legend in current layer group
            elif tree_node:
                group_node = self.layer_group  # QgsProject.instance().layerTreeRoot().findGroup(self.layer_group)
                if group_node:
                    index = group_node.children().index(tree_node)
                    group_node.insertLayer(index+1, result_layer)  # now add to legend in current layer group
                    self.voronoi_layer = result_layer
                else:
                    log.debug('????')
            else:
                log.debug(f'???? tree_node: {tree_node} tree_node in QgsProject.instance().layerTreeRoot().children() = {tree_node in QgsProject.instance().layerTreeRoot().children()}')

        #log.debug(f'Voronoi: insert layer in layertree: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        self.copy_measurements_style(result_layer, point_layer)

        #log.debug(f'Voronoi: copying the measurement style: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        if temporal_filter:
            point_layer.selectByExpression(temporal_filter, Qgis.SelectBehavior.RemoveFromSelection)
            # AND connect again to the selectionChange signal...
            self.measurements_connect_selection_changed()

        #log.debug(f'Voronoi: DEselecting the features: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        self.time = QDateTime.currentMSecsSinceEpoch()

        # Trying to set the point layer back to 'active layer'
        self.iface.layerTreeView().setCurrentLayer(point_layer)
        self.iface.mapCanvas().refresh()

        #log.debug(f'Voronoi: Refresh/Repaint: {(QDateTime.currentMSecsSinceEpoch()-self.time)/1000} seconds')
        log.debug(f'Voronoi: Total: {(QDateTime.currentMSecsSinceEpoch()-self.time_total)/1000} seconds for {point_layer}')


    def add_rainradar_to_timecontroller(self, layer_for_settings):
        settings = JRodosSettings()
        name = settings.value("rainradar_wmst_name")
        url = settings.value("rainradar_wmst_url")
        layers = settings.value("rainradar_wmst_layers")
        styles = settings.value("rainradar_wmst_styles")
        imgformat = settings.value("rainradar_wmst_imgformat")
        #crs = settings.value("rainradar_wmst_crs")
        # better to get the crs from current project to get best image results
        crs = self.iface.mapCanvas().mapSettings().destinationCrs().authid()

        # uri = 'type=wmst&allowTemporalUpdates=true&temporalSource=provider' \
        #       '&timeDimensionExtent=2021-03-31T09:25:00Z/2021-05-03T12:20:00Z/PT5M' \
        #       '&type=wmst&layers=RAD_NL25_PCP_CM&styles=precip-blue-transparent' \
        #       '/nearest&crs=EPSG:3857&format=image/png&url=https://geoservices' \
        #       '.knmi.nl/adagucserver?dataset%3DRADAR%26VERSION%3D1.1.1%26request%3Dgetcapabilities'

        #current_temporal_extent = QgsTemporalUtils.calculateTemporalRangeForProject(QgsProject.instance())
        # it's better to get the temporal extents from the controller, as these are already 'fixed' (to reasonable/nice begin/end)
        current_temporal_extent = self.iface.mapCanvas().temporalController().temporalExtents()
        tformat = 'yyyy-MM-ddTHH:mm:ssZ'
        uri = f'timeDimensionExtent={current_temporal_extent.begin().toString(tformat)}/{current_temporal_extent.end().toString(tformat)}/PT5M&' \
            f'type=wmst&allowTemporalUpdates=true&temporalSource=provider' \
            f'&type=wmst&layers={layers}&styles={styles}' \
            f'&crs={crs}&format={imgformat}&url={url}'

        log.debug(f'uri: {uri}')

        rain_layer = QgsRasterLayer(uri, name, "wms")
        QgsProject.instance().addMapLayer(rain_layer, False)  # False, meaning not ready to add to legend
        self.layer_group.insertLayer(len(self.layer_group.children()), rain_layer)  # now add to legend in current layer group on bottom

    def add_layer_to_timecontroller(self, layer, time_column=None, frame_size_seconds=3600):
        # get the temporal properties of the time layer
        layer_temporal_props = layer.temporalProperties()
        # set the temporal mode to 'DateTime comes from one attribute field'
        layer_temporal_props.setMode(QgsVectorLayerTemporalProperties.ModeFeatureDateTimeInstantFromField)
        # set the 'start' of the event to be the (virtual) datetime field
        layer_temporal_props.setStartField(time_column)

        # tell the layer props that the 'events' last about frame_size_seconds seconds
        layer_temporal_props.setDurationUnits(QgsUnitTypes.TemporalUnit.TemporalSeconds)
        # get measurementlayer integration time from self.measurements_settings
        default_integration_time = frame_size_seconds
        timestep = QgsInterval()
        layer_temporal_props.setFixedDuration(int(frame_size_seconds))  # setting the LAYERS event duration (in s)
        #layer_temporal_props.setFixedDuration(0)  # setting the LAYERS event duration (in s) to ZERO !!!!
        timestep.setSeconds(float(frame_size_seconds))

        # NOW enable the layer as 'temporal enabled'
        layer_temporal_props.setIsActive(True)  # OK

        # get a handle to current project and determine start and end range of ALL current temporal enabled layers
        project = QgsProject.instance()
        # get the current  responsible for the mapCanvas behaviour and Temporal Controller gui
        navigator = self.iface.mapCanvas().temporalController()
        # update the 'range' of the object (so the limits) to reflect the range of our current project
        temporal_range = QgsTemporalUtils.calculateTemporalRangeForProject(project)
        log.debug(f'Total Temporal Range: {temporal_range.begin()}')
        # if we are stepping in 1 hour steps (3600 secs), start the controller on a whole hour
        #log.debug(f'{frame_size_seconds} type: {type(frame_size_seconds)}')
        if int(frame_size_seconds) >= 3600:
            start_time = temporal_range.begin().time()
            # update begin to start at whole hour
            start_time.setHMS(start_time.hour(), 0, 0, 0)
            end_time = temporal_range.end().time()
            # update end time to set to :00  (round to the next hour) IF not :00
            if end_time.minute() != 0:
                end_time.setHMS(end_time.hour()+1, 0, 0, 0)
            temporal_range = QgsDateTimeRange(
                QDateTime(temporal_range.begin().date(), start_time),
                QDateTime(temporal_range.end().date(), end_time),
                temporal_range.includeBeginning(),
                temporal_range.includeEnd())

        navigator.setTemporalExtents(temporal_range)
        # set timestep
        navigator.setFrameDuration(timestep)

        # OK, all setup now. let's show Temporal controller, `rewind to start and play one loop
        navigator.setNavigationMode(QgsTemporalNavigationObject.Animated)  # will show controller
        navigator.rewindToStart()
        # play one step
        #navigator.next()

    def load_measurements_favourite(self):
        log.debug(f'Loading favourite measurements: ...{self.favorite_measurements_combo.currentText()}')
        #log.debug(f'Loading favourite measurements: ...{self.favorite_measurements_combo.itemData(self.favorite_measurements_combo.currentIndex())}')
        measurements_settings = self.favorite_measurements_combo.itemData(self.favorite_measurements_combo.currentIndex())
        if isinstance(measurements_settings, CalnetMeasurementsConfig):
            # create a deepcopy else we will edit the config which lives in the combobox...
            self.measurements_settings = copy.deepcopy(self.favorite_measurements_combo.itemData(self.favorite_measurements_combo.currentIndex()))
            # in the plugin we ignore the WFS-url from these settings, as dev/acc/prd is set by the user
            self.measurements_settings.url = self.settings.value('measurements_wfs_url')
            # IF bbox is emtpy, it means we do not use a predefined bbox, but use the current mapcanvas one
            if self.measurements_settings.bbox in (None, '', ' ', 'None', '-'):
                self.update_measurements_bbox()
                log.debug(f'BBOX in preset was empty, using current map extent: {self.measurements_settings.bbox}')
            else:
                log.debug(f'BBOX in preset was NOT empty, using current map extent: {self.measurements_settings.bbox}')
            # IF there is not project id in the settings (there probably SHOULD not), add current project_id
            if self.measurements_settings.projectid in ('', None) and self.calweb_project_id not in ('', 0, '0', None):
                log.debug(f'Adding projectid "{self.calweb_project_id}" to the measurement settings')
                self.measurements_settings.projectid = self.calweb_project_id
            Utils.set_settings_value("jrodos_last_measurements_preset", self.measurements_settings.title)
            self.start_measurements_provider()
        else:
            log.debug(f'{measurements_settings} is NOT instance of "CalnetMeasurementsConfig", ignoring...')

    def measurements_disconnect_selection_changed(self):
        """
        This method tries to disconnect the selectionChanged signal from a
        hopefully available measurements layer...
        """
        try:
            if self.measurements_layer:
                self.measurements_layer.selectionChanged.disconnect(self.measurement_selection_change)
        except Exception as e:
            pass

    def measurements_connect_selection_changed(self):
        """
        This method tries to disconnect the selectionChanged signal from a
        hopefully available measurements layer...
        """
        try:
            if self.measurements_layer:
                self.measurements_layer.selectionChanged.connect(self.measurement_selection_change)
        except Exception as e:
            pass

    def load_measurements(self, output_dir, style_file):
        """
        Load the measurements from the output_dir (as gml files), load them in a layer, and style them with style_file
        :param output_dir:
        :param style_file:
        :return:
        """
        start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
        end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)

        selected_features_ids = []

        if float(self.measurements_settings.endminusstart) < 0:
            interval = 'ALLES'
        else:
            interval = f'{self.measurements_settings.endminusstart} s'
        layer_display_name = f'{start_time.toString(self.measurements_settings.date_time_format_short)} - {end_time.toString(self.measurements_settings.date_time_format_short)}'

        register_layers = True

        try:
            # clean up IF there is a measurement layer disconnect selectionChanged signal
            self.measurements_disconnect_selection_changed()
            # remove pointer
            self.remove_device_pointer()
            # remove actual layer
            QgsProject.instance().removeMapLayer(self.measurements_layer.id())
        except Exception as e:
            pass

        # create layer name based on self.measurements_settings
        self.measurements_layer = QgsVectorLayer('point', layer_display_name, 'memory')

        # if this layer is a preset, use it's 'title' as abstract
        if self.measurements_settings.title == CalnetMeasurementsConfig.DEFAULT_TITLE:
            abstract = f"""Project: {self.measurements_settings.projectid}
            Quantities: {self.measurements_settings.quantity}
            Substances: {self.measurements_settings.substance}
            Integration period: {self.measurements_settings.endminusstart} sec"""
            self.measurements_layer.setAbstract(abstract)
        else:
            self.measurements_layer.setAbstract(self.measurements_settings.title)

        # add fields
        # see #QGIS-85 now using startTime for Temporal Controller
        pr = self.measurements_layer.dataProvider()
        pr.addAttributes([QgsField('gml_id', QVariant.String),
                          QgsField('startTime', QVariant.DateTime),
                          QgsField('endTime', QVariant.String),
                          QgsField('quantity', QVariant.String),
                          QgsField('substance', QVariant.String),
                          QgsField('unit', QVariant.String),
                          QgsField('value', QVariant.Double),
                          QgsField('time', QVariant.String),  # QgsField('time', QVariant.String), or QgsField('time', QVariant.DateTime)
                          QgsField('info', QVariant.String),
                          QgsField('device', QVariant.String),
                          QgsField('projectid', QVariant.String),
                          QgsField('quantity_substance', QVariant.String),
                          #QgsField("unitvalue", QVariant.Double),
                          ])
        self.measurements_layer.updateFields()

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

            if feature_count == 0:
                self.msg(None, self.tr("NO measurements found in :\n %s" % gml_file))
                return
            else:
                log.debug(self.tr("%s measurements loaded from GML file, total now: %s" % (step_count, feature_count)))

            self.measurements_layer.dataProvider().addFeatures(flist)
            self.measurements_layer.selectByIds(selected_features_ids)
            self.measurements_layer.updateFields()
            self.measurements_layer.updateExtents()

        gpkg_name = f'{output_dir}/measurements.gpkg'
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        transform_context = QgsProject.instance().transformContext()
        error = QgsVectorFileWriter.writeAsVectorFormatV3(self.measurements_layer,
                                                          gpkg_name,
                                                          transform_context,
                                                          save_options)
        if error[0] == QgsVectorFileWriter.NoError:
            log.debug(f'Succesfully saved a gpkg to: {gpkg_name}')
        else:
            log.debug(f'Error saving gpkg ({gpkg_name}): {error}')

        self.measurements_layer = QgsVectorLayer(f'{gpkg_name}|layername=measurements', layer_display_name, 'ogr')
        if not self.measurements_layer.isValid():
            log.error(f'ERROR loading measurements gpkg: {gpkg_name}')


        # put a copy of the settings into our map<=>settings dict
        # IF we want to be able to load a layer several times based on the same settings
        # self.jrodos_settings[self.measurements_layer] = deepcopy(self.measurements_settings)
        self.jrodos_settings[self.measurements_layer] = self.measurements_settings

        QgsProject.instance().addMapLayer(self.measurements_layer, False)  # False, meaning not ready to add to legend
        self.layer_group.insertLayer(0, self.measurements_layer)  # now add to legend in current layer group

        self.measurements_layer.loadNamedStyle(
            os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
        self.measurements_connect_selection_changed()

        if register_layers:
            if self.use_temporal_controller:
                # Temporal Controller !
                # endminusstart can be zero for meetwagen metingen
                # but we cannot set the stepsize to zero (as is NO step...)
                # so IF endminusstart==0, we set the stepsize to 600
                # 20220308: there is also endminusstart = -1 (show ALL frames)
                # also set to 600
                frame_size = self.measurements_settings.endminusstart
                if frame_size in [0, '0', -1, '-1']:
                    frame_size = 600
                self.add_layer_to_timecontroller(self.measurements_layer,
                                                 time_column='startTime',  # see #QGIS-85
                                                 frame_size_seconds=frame_size)

            # # set the display field value
            # self.measurements_layer.setMapTipTemplate('[% measurement_values()%]')
            # # self.measurements_layer.setDisplayField('Measurements')
            # # enable maptips if (apparently) not enabled (looking at the maptips action/button)
            # if not self.iface.actionMapTips().isChecked():
            #     self.iface.actionMapTips().trigger()  # trigger action

            self.iface.layerTreeView().setCurrentLayer(self.measurements_layer)
            self.iface.mapCanvas().refresh()

            # add rainradar and to the Temporal controller IF enabled
            if self.settings.value('rainradar_enabled'):
                self.add_rainradar_to_timecontroller(self.measurements_layer)

            log.debug(f'Adding "rivm_measurements" custom prop in layer: {str(self.measurements_settings.to_json())}')
            self.measurements_layer.setCustomProperty('rivm_measurements', self.measurements_settings.to_json())

    def get_quantity_and_substance_description(self, quantity, substance):
        if self.combi_descriptions and f'{quantity}_{substance}' in self.combi_descriptions:
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
        #print(model)
        #index = model.node2index(treenode)
        #model.setData(index, name)

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
                elif feature[field.name()] == '-':  # VALUE = '-' ?  skip it
                    pass
                # TODO: het weergeven van de TIME in UTC gaat helemaal fout, lijkt een QGIS issue te zijn...
                #elif 'TIME' in field.name().upper():
                #    print('1 *********************************************************')
                #    print(feature[field.name()])
                    #print(feature[field.name()].toString('yyyy/MM/dd HH:mm (UTC)'))
                    #dt = feature[field.name()]
                #    dt = QDateTime.fromString(feature[field.name()], Qt.ISODateWithMs)
                #    print(type(dt))
                    #print(dt.toString('yyyy MM dd HH:mm (UTC)'))
                #    print('2 *********************************************************')
                    #field_string += field.name().title() + ': ' + '{}'.format(QDateTime.fromString(feature[field.name()], Qt.ISODateWithMs).toString('yyyy/MM/dd HH:mm (UTC)')) + '<br/>'
                #    field_string += field.name().title() + ': ' + feature[field.name()].toString('yyyy/MM/dd HH:mm (UTC)') + '<br/>'
                #    field_string += field.name().title() + ': ' + '{}'.format(dt.toString('yyyy MM dd HH:mm (UTC)')) + '<br/>'
                elif 'TIME' in field.name().upper():
                    time = feature[field.name()]
                    if isinstance(time, QDateTime):  # QDateTime
                        field_string += field.name().title() + ': ' + '{}'.format(time.toTimeSpec(Qt.LocalTime).toString('yyyy/MM/dd HH:mm')) + '<br/>'
                        field_string += field.name().title() + ': ' + '{}'.format(time.toString('yyyy/MM/dd HH:mm (UTC)')) + '<br/>'
                    else:  # str, create a QDateTime here to format string
                        field_string += field.name().title() + ': ' + '{}'.format(QDateTime.fromString(feature[field.name()], Qt.ISODateWithMs).toTimeSpec(Qt.LocalTime).toString('yyyy/MM/dd HH:mm')) + '<br/>'
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
