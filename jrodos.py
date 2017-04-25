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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, QDateTime, Qt, QUrl
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar, QStandardItemModel, QStandardItem, \
    QDesktopServices,  QColor, QSortFilterProxyModel

from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsMessageLog, QgsProject, QgsRasterLayer, QgsVectorDataProvider, QgsSymbolV2, \
    QgsRuleBasedRendererV2, edit
from qgis.utils import qgsfunction, plugins, QgsExpression

from glob import glob
from datetime import datetime
from utils import Utils
from copy import deepcopy
from ui import JRodosMeasurementsDialog, JRodosDialog, JRodosFilterDialog
from jrodos_settings import JRodosSettings
from jrodos_settings_dialog import JRodosSettingsDialog
from providers.calnet_measurements_provider import CalnetMeasurementsConfig, CalnetMeasurementsProvider
from providers.calnet_measurements_utils_provider import CalnetMeasurementsUtilsConfig, CalnetMeasurementsUtilsProvider
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from providers.jrodos_model_output_provider import JRodosModelOutputConfig, JRodosModelOutputProvider, JRodosModelProvider
from providers.utils import Utils as ProviderUtils
from timemanager.layer_settings import LayerSettings
from timemanager.timevectorlayer import TimeVectorLayer
from timemanager.raster.wmstlayer import WMSTRasterLayer

from style_utils import RangeCreator

import resources # needed for button images!

import os.path
import json
import sys
import pickle


# pycharm debugging
# COMMENT OUT BEFORE PACKAGING !!!
# import pydevd
# pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)


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
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            '{}.qm'.format(locale))

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
        self.QMODEL_ID_IDX          = 0 # IF the QStandardModel has a true ID make it column 0 (else double NAME as 0)
        self.QMODEL_NAME_IDX        = 1 # IF the QStandardModel has a short name (not unique?) (else double ID as 1)
        self.QMODEL_DESCRIPTION_IDX = 2 # IF the QStandardModel has a description (eg used in dropdowns)
        self.QMODEL_DATA_IDX        = 3 # IF the QStandardModel has other data
        self.QMODEL_SEARCH_IDX      = 4 # IF the QStandardModel has a special SEARCH/FILTER column (optional for tables)

        self.MAX_FLOAT = sys.float_info.max

        self.USER_DATA_ITEMS_PATH = self.plugin_dir + '/jrodos_user_data_items.pickle'
        self.USER_QUANTITIES_PATH = self.plugin_dir + '/jrodos_user_quantities.pickle'
        self.USER_SUBSTANCES_PATH = self.plugin_dir + '/jrodos_user_substances.pickle'

        self.settings = JRodosSettings()

        # QAbstractItems model for the datapaths in the JRodos dialog
        self.jrodos_project_data = []

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&JRodos')
        self.toolbar = self.iface.addToolBar(u'JRodos')
        self.toolbar.setObjectName(u'JRodos')

        self.jrodos_output_progress_bar = None
        self.jrodos_output_settings = None

        # dialog for measurements
        self.measurements_dlg = None
        self.measurements_progress_bar = None
        self.measurements_settings = None
        self.measurements_provider = None
        self.quantities_model = None
        self.substances_model = None

        self.measurements_layer = None
        # substances and quantitites for Measurements dialog (filled via SOAP with CalnetMeasurementsUtilsProvider)
        self.quantities = [{'code': 0, 'description': self.tr('Trying to retrieve quantities...')}]
        self.substances = [{'code': 0, 'description': self.tr('Trying to retrieve substances...')}]

        # creating a dict for a layer <-> settings mapping
        self.jrodos_settings = {}

        self.layer_group = None


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
            text=self.tr(u'JRodos'),
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

        self.BAR_LOADING_TITLE = self.tr('Loading data...')
        self.JRODOS_BAR_TITLE = self.tr('JRodos Model')
        if self.jrodos_output_progress_bar is None:
            self.jrodos_output_progress_bar = QProgressBar()
            self.jrodos_output_progress_bar.setToolTip("Model data (WPS)")
            self.jrodos_output_progress_bar.setTextVisible(True)
            self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)
            self.jrodos_output_progress_bar.setMinimum(0)
            self.jrodos_output_progress_bar.setMaximum(100)  # we will use a 'infinite progress bar' by setting max to zero when busy
            self.jrodos_output_progress_bar.setValue(0)
            self.jrodos_output_progress_bar.setFixedWidth(progress_bar_width)
            self.jrodos_output_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.toolbar.addWidget(self.jrodos_output_progress_bar)

        self.MEASUREMENTS_BAR_TITLE = self.tr('Measurements')
        if self.measurements_progress_bar is None:
            self.measurements_progress_bar = QProgressBar()
            self.measurements_progress_bar.setToolTip("Measurement data (WFS)")
            self.measurements_progress_bar.setTextVisible(True)
            self.measurements_progress_bar.setFormat(self.MEASUREMENTS_BAR_TITLE )
            self.measurements_progress_bar.setMinimum(0)
            self.measurements_progress_bar.setMaximum(100)  # we will use a 'infinite progress bar' by setting max to zero when busy
            self.measurements_progress_bar.setValue(0)
            self.measurements_progress_bar.setFixedWidth(progress_bar_width)
            self.measurements_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.toolbar.addWidget(self.measurements_progress_bar)

        # Create the dialog (after translation) and keep reference
        self.jrodosmodel_dlg = JRodosDialog()
        # connect the change of the project dropdown to a refresh of the data path
        self.jrodosmodel_dlg.combo_project.currentIndexChanged.connect(self.project_selected)
        self.jrodosmodel_dlg.combo_task.currentIndexChanged.connect(self.task_selected)
        self.jrodosmodel_dlg.btn_item_filter.clicked.connect(self.show_data_item_filter_dialog)

        # Create the filter dialog
        self.filter_dlg = JRodosFilterDialog(self.jrodosmodel_dlg)
        self.filter_dlg.le_item_filter.setPlaceholderText(self.tr('Search in items'))

        # Create the measurements dialog
        self.measurements_dlg = JRodosMeasurementsDialog()
        self.measurements_dlg.btn_quantity_filter.clicked.connect(self.show_quantity_filter_dialog)
        self.measurements_dlg.btn_substance_filter.clicked.connect(self.show_substance_filter_dialog)

        # Create the settings dialog
        self.settings_dlg = JRodosSettingsDialog()

        # Make sure that when a QGIS layer is removed it will also be removed from the plugin
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.remove_jrodos_layer)

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

    def show_quantity_filter_dialog(self):
        # set model of the generic filter dialog
        self.filter_dlg.set_model(self.quantities_model)
        self.filter_dlg.le_item_filter.setText('')
        self.filter_dlg.show()
        # OK pressed: save the clicked quantities as 'user_quantities'
        if self.filter_dlg.exec_():
            # save/pickle user quantities
            quantities = []
            # run over model, and check if SEARCH column is 1 and so collect selected quantities
            for row in range(0, self.quantities_model.rowCount()):
                if self.quantities_model.item(row, self.QMODEL_SEARCH_IDX).text() == '1':
                    # for quantities we pickle 'code' which is in QMODEL_ID_IDX
                    quantity = self.quantities_model.item(row, self.QMODEL_ID_IDX).text()
                    quantities.append(quantity)
            # pickle the user_data_items to disk
            with open(self.USER_QUANTITIES_PATH, 'wb') as f:
                pickle.dump(quantities, f)

    def show_substance_filter_dialog(self):
        # set model of the generic filter dialog
        self.filter_dlg.set_model(self.substances_model)
        self.filter_dlg.le_item_filter.setText('')
        self.filter_dlg.show()
        # OK pressed: save the clicked substances as 'user_substances'
        if self.filter_dlg.exec_():
            # save/pickle user substances
            substances = []
            # run over model, and check if SEARCH column is 1 and so collect selected substances
            for row in range(0, self.substances_model.rowCount()):
                if self.substances_model.item(row, self.QMODEL_SEARCH_IDX).text() == '1':
                    # for sustances we pickle 'code' which is in QMODEL_ID_IDX
                    substance = self.substances_model.item(row, self.QMODEL_ID_IDX).text()
                    substances.append(substance)
            # pickle the user_data_items to disk
            with open(self.USER_SUBSTANCES_PATH, 'wb') as f:
                pickle.dump(substances, f)

    def show_help(self):
        docs = os.path.join(os.path.dirname(__file__), "help/html", "index.html")
        QDesktopServices.openUrl(QUrl("file:" + docs))

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&JRodos'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove progress bars
        del self.jrodos_output_progress_bar
        del self.measurements_progress_bar
        # remove the toolbar
        del self.toolbar
        # deregister our custom QgsExpression function
        QgsExpression.unregisterFunction("measurement_values")
        QgsMapLayerRegistry.instance().layerWillBeRemoved.disconnect(self.remove_jrodos_layer)


    def run(self):

        # we REALLY need OTF enabled
        if self.iface.mapCanvas().hasCrsTransformEnabled() == False:
            QMessageBox.warning(self.iface.mainWindow(), self.MSG_TITLE, self.tr(
                "This Plugin ONLY works when you have OTF (On The Fly Reprojection) enabled for current QGIS Project.\n\n" +
                "Please enable OTF for this project or open a project with OTF enabled."),
                                QMessageBox.Ok, QMessageBox.Ok)
            return
        self.setProjectionsBehaviour()
        try:
            # we try to retrieve the quantities and substances just once, but not earlier then a user actually
            # starts using the plugin (that is call this run)...
            if len(self.quantities) == 1 or len(self.substances) == 1:  # meaning we did not retrieve anything back yet
                self.get_quantities_and_substances()  # async call, will fill dropdowns when network requests return

            # create a 'JRodos layer' group if not already there ( always on TOP == 0 )
            if self.measurements_layer is None and self.jrodos_output_settings is None:
                self.layer_group = QgsProject.instance().layerTreeRoot().insertGroup(0, self.tr('JRodos plugin layers'))
            # only show dialogs if the item is enabled in settings
            if self.settings.value('jrodos_enabled'):
                self.show_jrodos_output_dialog()
            if self.settings.value('measurements_enabled'):
                self.show_measurements_dialog()

        except JRodosError as jre:
            self.msg(None, "Exception in JRodos plugin: %s \nCheck the Log Message Panel for more info" % jre)
            return
        except Exception as e:
            self.msg(None, "Exception in JRodos plugin: %s \nCheck the Log Message Panel for more info" % e)
            raise

    def setProjectionsBehaviour(self):
        # we do NOT want the default behaviour: prompting for a crs
        # we want to set it to epsg:4326, see
        # http://gis.stackexchange.com/questions/27745/how-can-i-specify-the-crs-of-a-raster-layer-in-pyqgis
        s = QSettings()
        self.oldCrsBehaviour = s.value("/Projections/defaultBehaviour", "useGlobal")
        s.setValue("/Projections/defaultBehaviour", "useGlobal")
        self.oldCrs = s.value("/Projections/layerDefaultCrs", "EPSG:4326")
        s.setValue("/Projections/layerDefaultCrs", "EPSG:4326")

    def unsetProjectionsBehaviour(self):
        # change back to default action of asking for crs or whatever the old behaviour was!
        s = QSettings()
        s.setValue("/Projections/defaultBehaviour", self.oldCrsBehaviour)
        s.setValue("/Projections/layerDefaultCrs", self.oldCrs)

    def get_quantities_and_substances(self):

        config = CalnetMeasurementsUtilsConfig()
        config.url = self.settings.value('measurements_soap_utils_url') #'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'

        quantities_provider = CalnetMeasurementsUtilsProvider(config)
        quantities_provider.finished.connect(self.quantities_provider_finished)
        quantities_provider.get_data('Quantities')

        substance_provider = CalnetMeasurementsUtilsProvider(config)
        substance_provider.finished.connect(self.substance_provider_finished)
        substance_provider.get_data('Substances')

    def quantities_provider_finished(self, result):
        if result.error():
            self.msg(None,
             self.tr("Problem in JRodos plugin retrieving the Quantities. \nCheck the Log Message Panel for more info"))
        else:
            # QUANTITIES
            self.quantities = result.data
            self.quantities_model = QStandardItemModel()
            # load saved user data_items from pickled file
            user_quantities_from_disk = []
            if os.path.isfile(self.USER_QUANTITIES_PATH):
                with open(self.USER_QUANTITIES_PATH, 'rb') as f:
                    user_quantities_from_disk = pickle.load(f)
            for q in self.quantities:
                user_favourite = '0'
                # {'code': 'ZR-97', 'description': 'ZIRCONIUM-97 (ZR-97)'}
                # fill model setting user_favourite to 1 if in pickled file
                if q['code'] in user_quantities_from_disk:
                    user_favourite = '1'
                self.quantities_model.appendRow([
                    QStandardItem(QStandardItem(q['code'])),  # self.QMODEL_ID_IDX
                    QStandardItem(QStandardItem(q['code'])),  # self.QMODEL_NAME_IDX
                    QStandardItem(QStandardItem(q['description'])),  # self.QMODEL_DESCRIPTION_IDX
                    QStandardItem(QStandardItem(q['description'])),  # self.QMODEL_DATA_IDX, description also has code
                    QStandardItem(user_favourite)  # self.QMODEL_SEARCH_IDX
                ])
            quantities_proxy_model = QSortFilterProxyModel()
            quantities_proxy_model.setSourceModel(self.quantities_model)
            quantities_proxy_model.setFilterKeyColumn(self.QMODEL_SEARCH_IDX)
            quantities_proxy_model.setFilterFixedString('1')
            quantities_proxy_model.setDynamicSortFilter(True)  # !! ELSE you do not see the changes done in the filter dialog
            self.measurements_dlg.combo_quantity.setModel(quantities_proxy_model)
            self.measurements_dlg.combo_quantity.setModelColumn(self.QMODEL_DESCRIPTION_IDX)  # we show the description
            last_used_quantities_code = Utils.get_settings_value("measurements_last_quantity", "T_GAMMA")
            items = self.quantities_model.findItems(last_used_quantities_code, Qt.MatchExactly, self.QMODEL_ID_IDX)
            if len(items) > 0:  # that is: we do have this last used one in the dropdown model
                model_index = self.quantities_model.indexFromItem(items[0])
                self.quantities_model.setData(self.quantities_model.index(model_index.row(), self.QMODEL_SEARCH_IDX), '1')
                idx = self.measurements_dlg.combo_quantity.model().mapFromSource(model_index)
                self.measurements_dlg.combo_quantity.setCurrentIndex(idx.row())

    def substance_provider_finished(self, result):
        if result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the Substances. \nCheck the Log Message Panel for more info"))
        else:
            # SUBSTANCES
            self.substances = result.data
            self.substances_model = QStandardItemModel()
            # load saved user data_items from pickled file
            user_substances_from_disk = []
            if os.path.isfile(self.USER_SUBSTANCES_PATH):
                with open(self.USER_SUBSTANCES_PATH, 'rb') as f:
                    user_substances_from_disk = pickle.load(f)
            for s in self.substances:
                user_favourite = '0'
                # {'code': 'C501', 'description': 'JUICE - FRUIT UNSPECIFIED (C501)'}
                # fill model setting user_favourite to 1 if in pickled file
                if s['code'] in user_substances_from_disk:
                    user_favourite = '1'
                self.substances_model.appendRow([
                    QStandardItem(s['code']),  # self.QMODEL_ID_IDX (not used)
                    QStandardItem(QStandardItem(s['code'])),  # self.QMODEL_NAME_IDX
                    QStandardItem(QStandardItem(s['description'])),  # self.QMODEL_DESCRIPTION_IDX
                    QStandardItem(QStandardItem(s['description'])),  # self.QMODEL_DATA_IDX, description also has code
                    QStandardItem(user_favourite)  # self.QMODEL_SEARCH_IDX
                ])
            substances_proxy_model = QSortFilterProxyModel()
            substances_proxy_model.setSourceModel(self.substances_model)
            substances_proxy_model.setFilterKeyColumn(self.QMODEL_SEARCH_IDX)
            substances_proxy_model.setFilterFixedString('1')
            substances_proxy_model.setDynamicSortFilter(True)  # !! ELSE you do not see the changes done in the filter dialog
            self.measurements_dlg.combo_substance.setModel(substances_proxy_model)
            self.measurements_dlg.combo_substance.setModelColumn(self.QMODEL_DESCRIPTION_IDX)  # we show the description
            last_used_substance_code = Utils.get_settings_value("measurements_last_substance", "A5")
            items = self.substances_model.findItems(last_used_substance_code, Qt.MatchExactly, self.QMODEL_ID_IDX)
            if len(items) > 0:  # that is we do have this last used one in the dropdown model
                model_index = self.substances_model.indexFromItem(items[0])
                self.substances_model.setData(self.substances_model.index(model_index.row(), self.QMODEL_SEARCH_IDX), '1')
                idx = self.measurements_dlg.combo_substance.model().mapFromSource(model_index)
                self.measurements_dlg.combo_substance.setCurrentIndex(idx.row())


    def get_jrodos_projects(self):
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
                for l in project['links']:
                    if l['rel'] == 'self':
                        link = l['href']
                        break
                id = unicode(project['projectId'])
                name = project['name']
                self.projects_model.appendRow([
                    QStandardItem(id),                                # self.QMODEL_ID_IDX = 0
                    QStandardItem(name),                              # self.QMODEL_NAME_IDX = 1
                    QStandardItem(id + ' - ' + name + ' - ' + link),  # self.QMODEL_DESCRIPTION_IDX = 2
                    QStandardItem(link)])                             # self.QMODEL_DATA_IDX = 3

            # disconnect the change of the project dropdown to be able to do a refresh
            self.jrodosmodel_dlg.combo_project.currentIndexChanged.disconnect(self.project_selected)
            self.jrodosmodel_dlg.combo_project.setModel(self.projects_model)
            self.jrodosmodel_dlg.combo_project.setModelColumn(self.QMODEL_DESCRIPTION_IDX)  # we show the description
            # connect the change of the project dropdown to a refresh of the data path
            self.jrodosmodel_dlg.combo_project.currentIndexChanged.connect(self.project_selected)
            # get the last used project from the settings
            last_used_project = Utils.get_settings_value("jrodos_last_model_project", "")
            items = self.projects_model.findItems(last_used_project, Qt.MatchExactly, self.QMODEL_ID_IDX)
            if len(items) > 0:
                self.jrodosmodel_dlg.combo_project.setCurrentIndex(items[0].row())  # take first from result

    def project_selected(self, projects_model_idx):
        # temporary text in the datapath combo
        self.jrodosmodel_dlg.combo_path.clear()
        self.jrodosmodel_dlg.combo_path.addItems([self.tr("Retrieving project paths...")])
        self.jrodos_project_data = None  # ?thourough cleanup?
        self.jrodos_project_data = []
        # Now: retrieve the datapaths of this project using a JRodosProjectProvider
        url = self.projects_model.item(projects_model_idx, self.QMODEL_DATA_IDX).text()
        #self.msg(None, "{} {}".format(projects_model_idx, url))
        config = JRodosProjectConfig()
        config.url = url
        datapaths_provider = JRodosProjectProvider(config)
        datapaths_provider.finished.connect(self.datapaths_provider_finished)
        datapaths_provider.get_data()

    def datapaths_provider_finished(self, result):
        if result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the JRodos datapaths for project:\n{}.\n").format(result.url) +
                     self.tr("Check the Log Message Panel for more info"))
            # set (empty) paths_model in combo: clean up
            self.jrodosmodel_dlg.combo_path.setModel(self.jrodos_project_data)
            # cleanup the starttime, step etc in the dialog too
            self.set_dialog_project_info(None, None, None)
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
                    QStandardItem('0'),                                                  # self.QMODEL_ID_IDX
                    QStandardItem(task['modelwrappername']),                             # self.QMODEL_NAME_IDX
                    QStandardItem(task['modelwrappername'] + ' ' + task['description']), # self.QMODEL_DESCRIPTION_IDX
                    QStandardItem(task['modelwrappername'])                              # self.QMODEL_DATA_IDX
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
                            QStandardItem(data_item['datapath']),  # self.QMODEL_DESCRIPTION_IDX
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
            # Retrieve the Project timeStep, modelTime/durationOfPrognosis and ModelStartTime using a JRodosModelProvider
            conf = JRodosModelOutputConfig()
            conf.url = self.settings.value('jrodos_wps_url')
            conf.jrodos_project = "project='"+result.data['name']
            # some trickery to get: "project='wps-test-multipath'&amp;model='LSMC'" in template
            # ONLY when there is >1 task in the project add "'&amp;model='LSMC'"
            if self.task_model.rowCount()>1:
                conf.jrodos_project += "'&amp;model='LSMC'"
            conf.jrodos_path = "path='Model data=;=Input=;=UI-input=;=RodosLight'"
            conf.jrodos_format = 'application/json'
            project_info_provider = JRodosModelProvider(conf)
            #self.msg(None, "{}\n{}\n{}".format(conf.output_dir, conf.jrodos_path, conf.jrodos_project))
            project_info_provider.finished.connect(self.provide_project_info_finished)
            project_info_provider.get_data()

    def task_selected(self, tasks_model_idx):
        """
        On change of the Task in the dialog, recreate the Dataitems.combo_path combobox with the model of that Task
        :param tasks_model_idx:
        :return:
        """
        current_data_items = self.jrodos_project_data[tasks_model_idx]
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(current_data_items)
        proxy_model.setFilterKeyColumn(self.QMODEL_SEARCH_IDX) # SEARCH contains '1' and '0', show only '1'
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
                     self.tr("Problem in JRodos plugin retrieving the Project info. \nCheck the Log Message Panel for more info"))
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
            self.jrodosmodel_dlg.lbl_steps2.setText(unicode(time_step / 60) + self.tr(" minutes"))
            self.jrodosmodel_dlg.le_steps.setText(unicode(time_step))  # steptime (seconds to minutes)
        if model_time is None:
            self.jrodosmodel_dlg.lbl_model_length2.setText('-')
            self.jrodosmodel_dlg.le_model_length.setText('')
        else:
            # model time / duration of prognosis is shown in hours (as in JRodos), but retrieved in seconds!!
            self.jrodosmodel_dlg.lbl_model_length2.setText(unicode(model_time / 3600) + self.tr(" hours"))  # modeltime (seconds to hours)
            self.jrodosmodel_dlg.le_model_length.setText(unicode(model_time))  # modeltime (seconds to hours)
        if model_start is None:
            self.jrodosmodel_dlg.lbl_start2.setText('-')
            self.jrodosmodel_dlg.le_start.setText('')  # modeltime (hours)
        else:
            self.jrodosmodel_dlg.le_start.setText(unicode(model_start))  # modeltime (hours)
            if type(model_start) == int:
                # OLD model start / start of release is in milli(!)seconds since 1970 UTC like: "1477146000000"
                self.jrodosmodel_dlg.lbl_start2.setText(QDateTime.fromTime_t(model_start/1000).toUTC().toString("yyyy-MM-dd HH:mm"))
            else:
                # NEW model start / start of release is string like: "2016-04-25T08:00:00.000+0000"
                self.jrodosmodel_dlg.lbl_start2.setText(unicode(model_start))

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def info(self, msg=""):
        QgsMessageLog.logMessage(str(msg), self.MSG_TITLE, QgsMessageLog.INFO)

    def show_jrodos_output_dialog(self, jrodos_output_settings=None):

        if jrodos_output_settings is not None:
            self.jrodos_output_settings = jrodos_output_settings
            #TODO: (re)start the provider?
            self.msg(None, "REstarting provider?")
            return

        # WPS / MODEL PART
        if self.jrodos_output_settings is not None:
            self.msg(None, "Still busy retrieving Model data via WPS, please try later...")
            return

        self.jrodosmodel_dlg.show()

        # try to get fresh jrodos projects, AND put 'remembered' values in the dialog
        self.get_jrodos_projects()

        if self.jrodosmodel_dlg.exec_():  # OK was pressed
            jrodos_output_settings = JRodosModelOutputConfig()
            jrodos_output_settings.url = self.settings.value('jrodos_wps_url') #'http://localhost:8080/geoserver/wps'
            # FORMAT is fixed to zip with shapes
            jrodos_output_settings.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
            # selected project + save the project id (model col 1) to QSettings
            # +"'&amp;model='EMERSIM'"
            jrodos_output_settings.jrodos_project = "project='"+self.projects_model.item(self.jrodosmodel_dlg.combo_project.currentIndex(), self.QMODEL_NAME_IDX).text()+"'"
            jrodos_output_settings.jrodos_project += "&amp;model='{}'".format(self.task_model.item(self.jrodosmodel_dlg.combo_task.currentIndex(), self.QMODEL_DATA_IDX ).text())
            # for storing in settings we do not use the non unique name, but the ID of the project
            last_used_project = self.projects_model.item(self.jrodosmodel_dlg.combo_project.currentIndex(), self.QMODEL_ID_IDX).text()
            Utils.set_settings_value("jrodos_last_model_project", last_used_project)

            # get data_item/path from model behind the combo_path dropdown
            datapath_model = self.jrodos_project_data[self.jrodosmodel_dlg.combo_task.currentIndex()]  # QStandardItemModel
            combopath_model = self.jrodosmodel_dlg.combo_path.model()  # QSortFilterProxyModel
            current_path_index = self.jrodosmodel_dlg.combo_path.currentIndex()
            if current_path_index < 0:
                self.msg(None, "Mandatory 'Dataitem' selection missing... Please select one. ")
                return
            proxy_idx = combopath_model.index(current_path_index, self.QMODEL_DATA_IDX)
            idx = combopath_model.mapToSource(proxy_idx)
            last_used_datapath = datapath_model.item(idx.row(), self.QMODEL_DATA_IDX).text()

            # NOTE that the jrodos_output_settings.jrodos_path has single quotes around it's value!! in the settings:
            # like: 'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Ground gamma dose=;=effective'
            jrodos_output_settings.jrodos_path = "path='{}'".format(last_used_datapath)
            Utils.set_settings_value("jrodos_last_model_datapath", last_used_datapath)
            last_used_task = self.task_model.item(self.jrodosmodel_dlg.combo_task.currentIndex(), self.QMODEL_NAME_IDX).text()
            Utils.set_settings_value("jrodos_last_task", last_used_task)

            # model time / duration of prognosis is shown in hours, but retrieved in minutes, and in JRodos in hours!!
            # modeltime (seconds!)
            model_time_secs = int(self.jrodosmodel_dlg.le_model_length.text())
            jrodos_output_settings.jrodos_model_time = model_time_secs / 60  # jrodos_model_time is in minutes!!
            # model Timestep in the dialog is shown in minutes, BUT retrieved in seconds, and in JRodos in minutes!!
            # steptime (seconds!)
            model_step_secs = int(self.jrodosmodel_dlg.le_steps.text())
            jrodos_output_settings.jrodos_model_step = model_step_secs
            # vertical is fixed to 0 for now (we do not 3D models)
            jrodos_output_settings.jrodos_verticals = 0  # z / layers
            OLD_VERSION = False # old version received the start as seconds_since_epoch
            if OLD_VERSION:
                # OLD: start text was a secondssinceepoch
                jrodos_output_settings.jrodos_datetime_start = QDateTime.fromTime_t(int(self.jrodosmodel_dlg.le_start.text())/1000).toUTC() # FORCE UTC!!
                # OLD: columns = number of steps in the model (integer)
                jrodos_output_settings.jrodos_columns = model_time_secs / model_step_secs
            else:
                # NEW: time is now a string like: "2016-04-25T08:00:00.000+0000"
                jrodos_output_settings.jrodos_datetime_start = QDateTime.fromString(self.jrodosmodel_dlg.le_start.text(), 'yyyy-MM-ddTHH:mm:ss.000+0000')
                # NEW: columns = a range from 0 till number of steps in the model (range string like '0-23')
                jrodos_output_settings.jrodos_columns = '{}-{}'.format(0, model_time_secs / model_step_secs)
            self.jrodos_output_settings = jrodos_output_settings
            self.start_jrodos_model_output_provider()

    def start_jrodos_model_output_provider(self):
        self.jrodos_output_progress_bar.setMaximum(0)
        self.jrodos_output_provider = JRodosModelOutputProvider(self.jrodos_output_settings)
        self.jrodos_output_provider.finished.connect(self.finish_jrodos_model_output_provider)
        self.jrodos_output_provider.get_data()

    def finish_jrodos_model_output_provider(self, result):
        self.info(result)
        self.jrodos_output_progress_bar.setMaximum(100)
        self.jrodos_output_progress_bar.setFormat(self.BAR_LOADING_TITLE)
        QCoreApplication.processEvents() # to be sure we have the loading msg
        if result.error():
            self.msg(None,
                     self.tr("Problem in JRodos plugin retrieving the JRodos model output. \nCheck the Log Message Panel for more info"))
        else:
            # Load the received shp-zip files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None:
                s = self.jrodos_output_settings.jrodos_path[:-1]  # contains path='...' remove last quote
                layer_name = s.split('=;=')[-2]+', '+s.split('=;=')[-1]
                # TODO get unit_used from somewhere
                unit_used = 'TODO'
                self.load_jrodos_output(result.data['output_dir'], 'totalpotentialdoseeffective.qml', layer_name, unit_used)
            else:
                self.msg(None, "No Jrodos Model Output data? Got: {}".format(result.data))
        self.jrodos_output_settings = None
        self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)

    def show_measurements_dialog(self):

        if self.measurements_settings is not None:
            self.msg(None, "Still busy retrieving Measurement data via WFS, please try later...")
            return

        end_time = QDateTime.currentDateTime()  # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # -12 hours

        if self.measurements_layer is not None:
            self.measurements_settings = self.jrodos_settings[self.measurements_layer]
            start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
            end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)
        else:
            # BUT if we just received a model, INIT the measurements dialog based on this
            if self.jrodos_output_settings is not None:
                start_time = self.jrodos_output_settings.jrodos_datetime_start.toUTC()  # we REALLY want UTC
                end_time = start_time.addSecs(60 * int(self.jrodos_output_settings.jrodos_model_time))  # model time

        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        self.measurements_dlg.combo_endminusstart.setCurrentIndex(
            self.measurements_dlg.combo_endminusstart.findText(Utils.get_settings_value('endminusstart', '3600')))

        self.measurements_dlg.show()

        result = self.measurements_dlg.exec_()
        if result:  # OK was pressed

            if len(self.quantities) == 1 or len(self.substances) == 1:  # meaning we did not retrieve anything back yet
                self.msg(None, "No substances and quantities, network problem? \nSee messages panel ...")
                return
            # selected quantity + save to QSettings
            quantity_text = self.measurements_dlg.combo_quantity.itemText(self.measurements_dlg.combo_quantity.currentIndex())
            if quantity_text is None or quantity_text == '':
                self.msg(None, "No Quantity selected, or quantity is emtpy ...\nFill dropdown via 'See All' button")
                self.show_measurements_dialog()
                return
            # now find quantity_text (like: LANTANHUM-140(LA-140)' in model to find quantity_code (like 'LA-140')
            items = self.quantities_model.findItems(quantity_text, Qt.MatchExactly, self.QMODEL_DESCRIPTION_IDX)
            if len(items) == 1:
                quantity = self.quantities_model.item(items[0].row(), self.JRODOS_CODE_IDX).text()
                Utils.set_settings_value("measurements_last_quantity", quantity)
            else:
                self.msg(None, "No or duplicate quantity (%s) found in model?" % quantity_text)
                return

            # selected substance + save to QSettings
            substance_text = self.measurements_dlg.combo_substance.itemText(self.measurements_dlg.combo_substance.currentIndex())
            if substance_text is None or substance_text == '':
                self.msg(None, "No substance selected, or substance is emtpy ...\nFill dropdown via 'See All' button")
                self.show_measurements_dialog()
                return
            # now find id for quantity_text
            items = self.substances_model.findItems(substance_text, Qt.MatchExactly, self.QMODEL_DESCRIPTION_IDX)
            if len(items) == 1:
                substance = self.substances_model.item(items[0].row(), self.JRODOS_CODE_IDX).text()
                Utils.set_settings_value("measurements_last_substance", substance)
            else:
                self.msg(None, "No or duplicate substance (%s) found in model?" % substance_text)
                return

            # selected endminusstart + save to QSettings
            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            Utils.set_settings_value("endminusstart", endminusstart)

            start_date = self.measurements_dlg.dateTime_start.dateTime() # UTC
            end_date = self.measurements_dlg.dateTime_end.dateTime() # UTC
            measurements_settings = CalnetMeasurementsConfig()
            measurements_settings.url = self.settings.value('measurements_wfs_url')

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
            measurements_settings.quantity = quantity
            measurements_settings.substance = substance
            self.measurements_settings = measurements_settings
            self.update_measurements_bbox()
            self.start_measurements_provider()
        else: # cancel pressed
            self.measurements_settings = None

    def start_measurements_provider(self):
        self.measurements_progress_bar.setMaximum(0)
        self.measurements_provider = CalnetMeasurementsProvider(self.measurements_settings)
        self.measurements_provider.finished.connect(self.finish_measurements_provider)
        self.measurements_provider.get_data()
        while not self.measurements_provider.is_finished():
            QCoreApplication.processEvents()

    def finish_measurements_provider(self, result):
        self.info(result)
        self.measurements_progress_bar.setMaximum(100)
        self.measurements_progress_bar.setFormat(self.BAR_LOADING_TITLE)
        QCoreApplication.processEvents() # to be sure we have the loading msg
        # WFS response can take a long time. Time out is handled by QGIS-network settings time out
        # so IF error_code = 5 (http://doc.qt.io/qt-4.8/qnetworkreply.html#NetworkError-enum)
        # provide the user feed back to rise the timeout value
        if result.error_code == 5:
            self.msg(None, self.tr("Network timeout for Measurements-WFS request. \nConsider rising it in Settings/Options/Network. \nValue is now: {} msec".format(QSettings().value('/qgis/networkAndProxy/networkTimeout', '??'))))
        elif result.error():
            self.msg(None, result)
            self.iface.messageBar().pushMessage("Network problem: %s" % result.error_code, self.iface.messageBar().CRITICAL, 1)
        else:
            # self.iface.messageBar().pushMessage("Retrieved all measurement data, loading layer...", self.iface.messageBar().INFO, 1)
            # Load the received gml files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None and result.data['count'] > 0:
                self.load_measurements(result.data['output_dir'], 'totalpotentialdoseeffective2measurements.qml')
            else:
                self.msg(None, "No Measurements data? {}".format(result.data))
        self.measurements_settings = None
        self.measurements_progress_bar.setFormat(self.MEASUREMENTS_BAR_TITLE)

    def update_measurements_bbox(self):
            # bbox in epsg:4326
            crs_project = self.iface.mapCanvas().mapSettings().destinationCrs()
            crs_4326 = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
            crsTransform = QgsCoordinateTransform(crs_project, crs_4326)
            current_bbox_4326 = crsTransform.transform(self.iface.mapCanvas().extent())
            # bbox for wfs get measurements request, based on current bbox of mapCanvas (OR model)
            self.measurements_settings.bbox = "{},{},{},{}".format(
                current_bbox_4326.yMinimum(), current_bbox_4326.xMinimum(), current_bbox_4326.yMaximum(), current_bbox_4326.xMaximum())  # S,W,N,E

    def find_jrodos_layer(self, settings_object):
        for layer in self.jrodos_settings:
            if self.jrodos_settings[layer] == settings_object:
                return layer
        return None

    def remove_jrodos_layer(self, layer2remove):
        for layer in self.jrodos_settings.keys():
            if layer2remove == layer.id():
                if self.measurements_layer == layer:
                    self.measurements_layer = None
                del self.jrodos_settings[layer]
                return

    def load_jrodos_output(self, shape_dir, style_file, layer_name, unit_used):
        """
        Create a polygon memory layer, and load all shapefiles (named 0_0.zip -> x_0.zip)
        from given shape_dir.
        Every zip is for a certain time-period, but because the data does not containt a time column/stamp
        we will add it by creating an attribute 'Datetime' and fill that based on:
        - the x in the zip file (being a model-'step')
        - the starting time of the model (given in dialog, set in jrodos project run)
        - the model length time (24 hours)

        :param shape_dir: directory containing zips with shapefiles
        :param style_file: style (qml) to be used to style the layer in which we merged all shapefiles
        :return:
        """

        import zipfile
        zips = glob(os.path.join(shape_dir, "*.zip"))
        for zip in zips:
            zip_ref = zipfile.ZipFile(zip, 'r')
            zip_ref.extractall(shape_dir)
            zip_ref.close()

        shps = glob(os.path.join(shape_dir, "*.shp"))

        features_added = False
        features_have_valid_time = False
        features_min_value = self.MAX_FLOAT

        # give the memory layer the same CRS as the source layer
        # timestamp as first attribute, easier to config with timemanager plugin (default first column)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/vector.html  # writing-vector-layers
        # create layer
        # jrodos_output_layer = QgsVectorLayer("Polygon", layer_name+" ("+unit_used+")", "memory")
        # layer_crs = None
        # if len(shps) > 1:  # OLD way: a directory of zips
        #     # add fields to memory layer
        #     pr = jrodos_output_layer.dataProvider()
        #     pr.addAttributes([QgsField("Time", QVariant.String),
        #                       QgsField("Cell", QVariant.Int),
        #                       QgsField("Value", QVariant.Double)])
        #     jrodos_output_layer.updateFields()  # tell the vector layer to fetch changes from the provider
        #     # now for every downloaded shape file
        #     for shp in shps:
        #         (shpdir, shpfile) = os.path.split(shp)
        #         input_layer = QgsVectorLayer(shp, shpfile, "ogr")
        #         flist = []
        #         if not input_layer.isValid():
        #             self.msg(None, self.tr("Apparently no valid JRodos data received. \nFailed to load the data!"))
        #             break
        #         else:
        #             #self.msg(None, "Layer loaded %s" % shp)
        #             if layer_crs ==None:
        #                 # find out source crs of shp and set our memory layer to the same crs
        #                 layer_crs = input_layer.crs()
        #                 jrodos_output_layer.setCrs(layer_crs)
        #
        #             features = input_layer.getFeatures()
        #
        #             step = int(shpfile.split('_')[0])
        #             tstamp = QDateTime(self.jrodos_output_settings.jrodos_datetime_start)
        #             # every zip get's a column with a timestamp based on the 'step/column' from the model
        #             # so 0_0.zip is column 0, vertical 0
        #             # BUT column 0 is from the first model step!!
        #             # SO WE HAVE TO ADD ONE STEP OF SECONDS TO THE TSTAMP (step+1+
        #             #tstamp = tstamp.addSecs(60 * (step+1) * int(self.jrodos_output_settings.jrodos_model_step))
        #             tstamp = tstamp.addSecs((step + 1) * int(self.jrodos_output_settings.jrodos_model_step))
        #             tstamp = tstamp.toString("yyyy-MM-dd HH:mm")
        #             for feature in features:
        #                 # only features with Value > 0, to speed up QGIS
        #                 value = feature.attribute('Value')
        #                 if value > 0:
        #                     if value < features_min_value:
        #                         features_min_value = value
        #                     fields = feature.fields()
        #                     fields.append(QgsField("Time"))
        #                     f = QgsFeature(fields)
        #                     # timestamp as first attribute, easier to config with timemanager plugin (default first column)
        #                     f.setAttributes([tstamp, feature.attribute('Cell'), value])
        #                     f.setGeometry(feature.geometry())
        #                     flist.append(f)
        #         if len(flist)>0:
        #             features_added = True
        #         jrodos_output_layer.dataProvider().addFeatures(flist)
        #         jrodos_output_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!
        #         jrodos_output_layer.updateFields()
        #         jrodos_output_layer.updateExtents()
        #         self.iface.mapCanvas().refresh()

        # if len(shps) == 1:  # new way: one zip with one shapefile, the shape containing a column Time (seconds since epoch)
        #     for shp in shps:
        #         (shpdir, shpfile) = os.path.split(shp)
        #         jrodos_output_layer = QgsVectorLayer(shp, shpfile, "ogr")
        #         if not jrodos_output_layer.isValid():
        #             self.msg(None, self.tr("Apparently no valid JRodos data received. \nFailed to load the data!"))
        #             break
        #         else:
        #             # self.msg(None, "Layer loaded %s" % shp)
        #             f = QgsFeature()
        #             if jrodos_output_layer.getFeatures().nextFeature(f):
        #                 # checked that we have at least one feature
        #                 features_added = True # OK
        #                 # check if we have a valid time in this features
        #                 time = f.attribute('Time')
        #                 if time is not None and time != "" and time > 0:
        #                     features_have_valid_time = True
        #                 else:
        #                     self.msg(None, self.tr('Found a feature with Time value {}\nSo not registring as TimeManager layer').format(time))
        #         jrodos_output_layer.loadNamedStyle(
        #             os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
        #         jrodos_output_layer.updateFields()
        #         jrodos_output_layer.updateExtents()
        #         self.iface.mapCanvas().refresh()

        # newest way: one zip with one shapefile,
        # the shape containing a column Time (seconds since epoch)
        # we iterate over features to:
        # 1) filter out all zero value features (as currently not ALL zero values are removed by server)
        # 2) determine min and max value of Value (needed for styling purposes)
        i = 0
        j = 0

        if len(shps) == 1:
            for shp in shps:
                (shpdir, shpfile) = os.path.split(shp)
                #self.info("{}\n{}".format(shpdir, shpfile))
                if 'Empty' in shpfile: # JRodos sents an 'Empty.shp' if no features are in the model data path)
                    self.msg(None, self.tr("JRodos data received successfully. \nBut dataset '"+layer_name+"' is empty."))
                    break
                jrodos_output_layer = QgsVectorLayer(shp, layer_name+" ("+unit_used+")", "ogr")
                if not jrodos_output_layer.isValid():
                    self.msg(None, self.tr("Apparently no valid JRodos data received. \nFailed to load the data!"))
                    break
                else:
                    # TODO: determine if we really want to walk over all features just to determine class boundaries
                    #       better would be to have this (meta)data available from the jrodos service or so
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
                            if not features_have_valid_time and \
                                            time is not None and time != "" and time > 0:
                                features_have_valid_time = True
                        else:
                            # try to delete the features with Value = 0 Note that a zipped shp cannot be edited!
                            if (jrodos_output_layer.dataProvider().capabilities() & QgsVectorDataProvider.DeleteFeatures) > 0:
                                j += 1
                                jrodos_output_layer.deleteFeature(feature.id())

                # jrodos_output_layer.loadNamedStyle(
                #     os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
                self.style_layer(jrodos_output_layer)

                self.iface.mapCanvas().refresh()

        #self.msg(None, "min: {}, max: {} \ncount: {}, deleted: {}".format(features_min_value, 'TODO?', i, j))
        # ONLY when we received features back load it as a layer
        if features_added:
            # add layer to the map
            QgsMapLayerRegistry.instance().addMapLayer(jrodos_output_layer,
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

    def style_layer(self, layer):
        # create a new rule-based renderer
        symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRendererV2(symbol)
        # get the "root" rule
        root_rule = renderer.rootRule()

        rules = RangeCreator.create_rule_set(-5, 4, False, True)

        #for label, expression, color_name, scale in rules:
        for label, expression, color in rules:
            # create a clone (i.e. a copy) of the default rule
            rule = root_rule.children()[0].clone()
            # set the label, expression and color
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().symbolLayer(0).setFillColor(color)
            # outline transparent
            rule.symbol().symbolLayer(0).setOutlineColor(QColor.fromRgb(255,255,255,0))
            # set the scale limits if they have been specified
            # if scale is not None:
            #     rule.setScaleMinDenom(scale[0])
            #     rule.setScaleMaxDenom(scale[1])
            # append the rule to the list of rules
            root_rule.appendChild(rule)

        # delete the default rule
        root_rule.removeChildAt(0)
        # apply the renderer to the layer
        layer.setRendererV2(renderer)

    def add_rainradar_to_timemanager(self, layer_for_settings):

        settings = JRodosSettings()
        name = settings.value("rainradar_wmst_name")
        url = settings.value("rainradar_wmst_url")
        layers = settings.value("rainradar_wmst_layers")
        styles = settings.value("rainradar_wmst_styles")
        imgformat = settings.value("rainradar_wmst_imgformat")
        crs = settings.value("rainradar_wmst_crs")

        uri = "crs=" + crs + "&layers=" + layers + "&styles=" + styles + "&format=" + imgformat + "&url=" + url;

        rain_layer = QgsRasterLayer(uri, name, "wms")
        QgsMapLayerRegistry.instance().addMapLayer(rain_layer, False)  # False, meaning not ready to add to legend
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

        if not 'timemanager' in plugins:
            self.iface.messageBar().pushWarning ("Warning!!", "No TimeManger plugin, we REALLY need that. Please install via Plugin Manager first...")
            return

        timemanager = plugins['timemanager']

        # enable timemanager by 'clicking' on enable button (if not enabled)
        if not timemanager.getController().getTimeLayerManager().isEnabled():
            timemanager.getController().getGui().dock.pushButtonToggleTime.click()

        timelayer_settings = LayerSettings()
        timelayer_settings.layer = layer
        timelayer_settings.startTimeAttribute = time_column

        timelayer = TimeVectorLayer(timelayer_settings, self.iface)

        animationFrameLength = 2000
        frame_size = frame_size
        frame_type = frame_type
        timemanager.getController().setPropagateGuiChanges(False)
        timemanager.getController().setAnimationOptions(animationFrameLength, False, False)
        timemanager.getController().setTimeFrameType(frame_type)
        timemanager.getController().setTimeFrameSize(frame_size)

        timemanager.getController().getTimeLayerManager().registerTimeLayer(timelayer)
        # set timeslider to zero
        timemanager.getController().getGui().dock.horizontalTimeSlider.setValue(0)
        # TODO: temporarily in if clause (until upstream has it too)
        if hasattr(timemanager.getController(), 'refreshGuiTimeFrameProperties'):
            timemanager.getController().refreshGuiTimeFrameProperties()
            # set 'discrete checkbox' to True to be sure there is something to see...
            timemanager.getController().getGui().dock.checkBoxDiscrete.setChecked(True)
            # do one step to be sure there is data visible (working for hour measurements, could be based on frame_size)
            timemanager.getController().stepForward()
        else:
            timemanager.getController().refreshGuiTimeExtents(timemanager.getController().getTimeLayerManager().getProjectTimeExtents())
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
        # layer_name = "T-GAMMA, A5, 600, 17/6 23:01 - 20/6 11:01"
        layer_name = self.measurements_settings.quantity + ", " + self.measurements_settings.substance + ", " + \
                     self.measurements_settings.endminusstart + ", " + \
                     start_time.toString(self.measurements_settings.date_time_format_short) + " - " + \
                     end_time.toString(self.measurements_settings.date_time_format_short)

        register_layers = False
        if self.measurements_layer is None:
            register_layers = True
            self.set_legend_node_name(self.layer_group,
                                      self.tr('Data retrieved: ') + QDateTime.currentDateTime().toString(
                                          'MM/dd HH:mm:ss'))

            # create layer name based on self.measurements_settings
            self.measurements_layer = QgsVectorLayer("point", layer_name, "memory")

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
                              QgsField("valuemsv", QVariant.Double)
                              ])
            self.measurements_layer.updateFields()

            QgsMapLayerRegistry.instance().addMapLayer(self.measurements_layer, False) # False, meaning not ready to add to legend
            self.layer_group.insertLayer(0, self.measurements_layer) # now add to legend in current layer group

            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            # self.jrodos_settings[self.measurements_layer] = deepcopy(self.measurements_settings)
            self.jrodos_settings[self.measurements_layer] = self.measurements_settings

            self.measurements_layer.loadNamedStyle(
                os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
        else:
            # there is already a layer for this measurements_settings object, so apparently we got new data for it:
            # remove current features from the  layer
            self.measurements_layer.startEditing()
            self.measurements_layer.setSubsetString('') # first remove the query otherwise only the query result is removed
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
                    fields.append(QgsField('valuemsv'))
                    f = QgsFeature(fields)
                    if feature.geometry() is not None:
                        attributes = feature.attributes()
                        value = float(feature.attribute('value'))
                        valuemsv = -1  # set value to '-1' not sure if NULL is better...
                        # preferred unit is microSv/H, but the data contains value+unit column
                        # set all values in column valuemsv in microS/H
                        if feature.attribute('unit') == 'USV/H':
                            # value is in microS/H all OK
                            valuemsv = value
                        elif feature.attribute('unit') == 'NSV/H':
                            # value is in milliS/H, value / 1000
                            valuemsv = value / 1000
                        else:
                            if new_unit_msg:
                                self.msg(None, "New unit in data: '%s', setting valuemsv to -1" % feature.attribute('unit'))
                                new_unit_msg = False
                        attributes.append(valuemsv)
                        f.setAttributes(attributes)
                        f.setGeometry(feature.geometry())
                        flist.append(f)
                        if len(flist) > 1000:
                            self.measurements_layer.dataProvider().addFeatures(flist)
                            flist = []
                        #print "%s            gml_id: %s - %s" % (feature_count, f.geometry().exportToWkt(), f.attributes())
                    else:
                        self.msg(None, "ERROR: # %s no geometry !!! attributes: %s " % (feature_count, f.attributes()))
                        return

            if feature_count == 0:
                self.msg(None, self.tr("NO measurements found in :\n %s" % gml_file))
                return
            else:
                self.info(self.tr("%s measurements loaded from GML file, total now: %s" % (step_count, feature_count)))

            self.measurements_layer.dataProvider().addFeatures(flist)
            self.measurements_layer.updateFields()
            self.measurements_layer.updateExtents()

            timemanager = plugins['timemanager'].getController().getTimeLayerManager()
            timemanager.setTimeFrameDiscrete(timemanager.timeFrameDiscrete)

        if register_layers:
            # add this layer to the TimeManager
            self.add_layer_to_timemanager(self.measurements_layer, 'time')

            # set the display field value
            self.measurements_layer.setDisplayField('[% measurement_values()%]')
            # enable maptips if (apparently) not enabled (looking at the maptips action/button)
            if not self.iface.actionMapTips().isChecked():
                self.iface.actionMapTips().trigger()  # trigger action
            self.iface.legendInterface().setCurrentLayer(self.measurements_layer)
            #self.iface.mapCanvas().refresh()

            # add rainradar and to the TimeManager IF enabled
            if self.settings.value('rainradar_enabled'):
                self.add_rainradar_to_timemanager(self.measurements_layer)

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

    # https://nathanw.net/2012/11/10/user-defined-expression-functions-for-qgis/
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
        for field in feature.fields():
            # skip info
            if not field.name() == 'info':
                field_string += field.name() + ': ' + unicode(feature[field.name()]) + '<br/>'
        # now do the 'info'-field which is a json object
        info_string = json.loads(feature['info'])
        if 'fields' in info_string:
            for field in info_string['fields']:
                if 'mnemonic' in field:
                    field_string += field['mnemonic'] + ': ' + field['value'] + '<br/>'
                elif 'name' in field:
                    field_string += field['name'] + ': ' + field['value'] + '<br/>'
        return field_string + '</div>'

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
