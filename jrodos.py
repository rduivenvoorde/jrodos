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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, QDateTime, QDate, QTime, Qt
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar, QStandardItemModel, QStandardItem
import resources
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsMessageLog, QgsProject
from qgis.utils import qgsfunction, QgsExpression
from glob import glob
import os.path
import json
from datetime import datetime
from utils import Utils
from copy import deepcopy
from ui import JRodosMeasurementsDialog, JRodosDialog
from jrodos_settings import JRodosSettings
from jrodos_settings_dialog import JRodosSettingsDialog
from providers.calnet_measurements_provider import CalnetMeasurementsConfig, CalnetMeasurementsProvider
from providers.calnet_measurements_utils_provider import CalnetMeasurementsUtilsConfig, CalnetMeasurementsUtilsProvider
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from providers.jrodos_model_output_provider import JRodosModelOutputConfig, JRodosModelOutputProvider
from providers.utils import Utils as ProviderUtils


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
            'JRodos_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.MSG_TITLE = self.tr("JRodos Plugin")

        # NOTE !!! project names surrounded by single quotes ??????
        self.JRODOS_PROJECTS = ["wps-13sept-test"]

        self.JRODOS_MODEL_LENGTH_HOURS = ['48', '24', '12', '6', '3']

        # indexes for the data coming from Utils providers
        self.JRODOS_DESCRIPTION_IDX = 0
        self.JRODOS_CODE_IDX = 1

        # 'standard' column indexes for QStandardModels:
        self.QMODEL_ID_IDX          = 0 # IF the QStandardModel has a true ID make it column 0 (else double NAME as 0)
        self.QMODEL_NAME_IDX        = 1 # IF the QStandardModel has a short name (not unique?) (else double ID as 1)
        self.QMODEL_DESCRIPTION_IDX = 2 # IF the QStandardModel has a description (eg used in dropdowns)
        self.QMODEL_DATA_IDX        = 3 # IF the QStandardModel has other data
        self.QMODEL_SEARCH_IDX      = 4 # IF the QStandardModel has a special SEARCH column (optional for tables)

        self.JRODOS_STEP_MINUTES = ['10', '30', '60'] # as in JRodos

        self.settings = JRodosSettings()

        # Create the dialog (after translation) and keep reference
        self.jrodosmodel_dlg = JRodosDialog()
        # add current models to dropdown
        self.jrodosmodel_dlg.combo_project.addItems(self.JRODOS_PROJECTS)
        # self.jrodosmodel_dlg.combo_model.currentText()
        # add current paths to dropdown
        self.jrodosmodel_dlg.combo_steps.addItems(self.JRODOS_STEP_MINUTES)
        self.jrodosmodel_dlg.combo_model_length.addItems(self.JRODOS_MODEL_LENGTH_HOURS)

        # DEMO TIME !!!
        #self.jrodosmodel_dlg.combo_project.setCurrentIndex(1)
        self.jrodosmodel_dlg.combo_steps.setCurrentIndex(2)
        self.jrodosmodel_dlg.combo_model_length.setCurrentIndex(1)
        utcdatetime = QDateTime(QDate(2016, 10, 2), QTime(8, 0))
        self.jrodosmodel_dlg.dateTime_start.setDateTime(utcdatetime)
        # QAbstractItems model for the datapaths in the JRodos dialog
        self.jrodos_paths_model = None

        # now connect the change of the project dropdown to a refresh of the data path
        self.jrodosmodel_dlg.combo_project.currentIndexChanged.connect(self.fill_data_path_combo)

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

        self.MEASUREMENTS_BAR_TITLE = self.tr('Meaurements')
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

        # Create the measurements dialog
        self.measurements_dlg = JRodosMeasurementsDialog()

        # Create the settings dialog
        self.settings_dlg = JRodosSettingsDialog()


    def show_settings(self):
        self.settings_dlg.show()

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
        QgsExpression.unregisterFunction("$measurement_values")
        QgsExpression.unregisterFunction("measurement_values")


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
                self.get_quantities_and_substances() # async call, will fill dropdowns when network requests return

            # IF there is a layer selected in the legend
            # based on 'currentLayer' in legend, check the settings
            #self.msg(None, self.jrodos_settings)
            # if self.iface.mapCanvas().currentLayer() is not None \
            #         and self.jrodos_settings.has_key(self.iface.mapCanvas().currentLayer()):
            #     #self.msg(None, self.jrodos_settings[self.iface.mapCanvas().currentLayer()])
            #     settings = self.jrodos_settings[self.iface.mapCanvas().currentLayer()]
            #     if isinstance(settings, WpsSettings):
            #         self.show_jrodos_wps_dialog(settings)
            #     elif isinstance(settings, WfsSettings):
            #         self.show_measurements_dialog(settings)
            #     else:
            #         self.msg(None, settings)
            #     return

            # create a group always on TOP == 0
            self.layer_group = QgsProject.instance().layerTreeRoot().insertGroup(0, self.tr('Data group'))
            self.show_jrodos_output_dialog()
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
                     "Problem in JRodos plugin retrieving the Quantities. \nCheck the Log Message Panel for more info")
        else:
            # QUANTITIES
            self.quantities = result.data

            self.quantities_model = QStandardItemModel()
            for q in self.quantities:
                self.quantities_model.appendRow([QStandardItem(q['description']), QStandardItem(q['code'])])
            self.measurements_dlg.combo_quantity.setModel(self.quantities_model)

            last_used_quantities_code = Utils.get_settings_value("measurements_last_quantity", "T_GAMMA")
            items = self.quantities_model.findItems(last_used_quantities_code, Qt.MatchExactly, self.JRODOS_CODE_IDX)
            if len(items) > 0:
                self.measurements_dlg.combo_quantity.setCurrentIndex(items[self.JRODOS_DESCRIPTION_IDX].row())

    def substance_provider_finished(self, result):
        if result.error():
            self.msg(None,
                     "Problem in JRodos plugin retrieving the Substances. \nCheck the Log Message Panel for more info")
        else:
            # SUBSTANCES
            self.substances = result.data

            self.substances_model = QStandardItemModel()
            for s in self.substances:
                self.substances_model.appendRow([QStandardItem(s['description']), QStandardItem(s['code'])])
            self.measurements_dlg.combo_substance.setModel(self.substances_model)

            last_used_substance_code = Utils.get_settings_value("measurements_last_substance", "A5")
            items = self.substances_model.findItems(last_used_substance_code, Qt.MatchExactly, self.JRODOS_CODE_IDX)
            if len(items) > 0:
                self.measurements_dlg.combo_substance.setCurrentIndex(items[self.JRODOS_DESCRIPTION_IDX].row())

    def get_jrodos_projects(self):

        config = JRodosProjectConfig()
        config.url = self.settings.value('jrodos_rest_url')
        #config.url = 'http://duif.net/projects.json' # DEV
        prov = JRodosProjectProvider(config)
        def prov_projects_finished(result):
            if result.error():
                self.msg(None,
                         "Problem in JRodos plugin retrieving the JRodos projects. \nCheck the Log Message Panel for more info")
            else:
                # Projects
                self.projects_model = QStandardItemModel()
                projects = result.data['content']
                for project in projects:

                    link = "NO LINK ?????"
                    for l in project['links']:
                        if l['rel'] == 'self':
                            link = l['href']
                            break

                    #print project
                    #print project['project']
                    # print project['project']['username']
                    # print project['project']['description']
                    # print project['project']['projectId']
                    # print project['project']['name']
                    # print project['project']['modelchainname']
                    # print project['project']['dateTimeCreatedString']
                    # for key in project['project']:
                    #     print "{}: {}".format(key, project['project'][key])
                    #print link
                    #print '------------------------------------------'
                    id = unicode(project['project']['projectId'])
                    name = project['project']['name']
                    self.projects_model.appendRow([
                        QStandardItem(id),                                                      # self.QMODEL_ID_IDX = 0
                        QStandardItem(project['project']['name']),                              # self.QMODEL_NAME_IDX = 1
                        QStandardItem(id + ' - ' + project['project']['name'] + ' - ' + link),   # self.QMODEL_DESCRIPTION_IDX = 2
                        QStandardItem(link)])                                                   # self.QMODEL_DATA_IDX = 3

                self.jrodosmodel_dlg.combo_project.setModel(self.projects_model)
                self.jrodosmodel_dlg.combo_project.setModelColumn(self.QMODEL_DESCRIPTION_IDX)  # we show the description
                # get the last used project from the settings
                last_used_project = Utils.get_settings_value("jrodos_last_model_project", "")
                items = self.projects_model.findItems(last_used_project, Qt.MatchExactly, self.QMODEL_ID_IDX)
                if len(items) > 0:
                    self.jrodosmodel_dlg.combo_project.setCurrentIndex(items[0].row()) # take first from result
                    # get the data paths of that project and fill dropdown with it's data paths
                    #self.fill_data_path_combo(items[0].row())

                # now connect the change of the project dropdown to a refresh of the data path
                # self.jrodosmodel_dlg.combo_project.currentIndexChanged.connect(self.fill_data_path_combo)

        prov.finished.connect(prov_projects_finished)
        prov.get_data('/projects')
        #prov.get_data() # DEV

    def fill_data_path_combo(self, projects_model_idx):

        # temporary text in the combo
        self.jrodosmodel_dlg.combo_path.clear()
        self.jrodosmodel_dlg.combo_path.addItems([self.tr("Retrieving project paths...")])
        self.jrodos_paths_model = QStandardItemModel()  # TODO: should this declared only once?

        url = self.projects_model.item(projects_model_idx, self.QMODEL_DATA_IDX).text()
        #self.msg(None, "{} {}".format(projects_model_idx, url))
        config = JRodosProjectConfig()
        config.url = url
        datapaths_provider = JRodosProjectProvider(config)
        datapaths_provider.finished.connect(self.datapaths_provider_finished)
        datapaths_provider.get_data()

    def datapaths_provider_finished(self, result):

        # DEV
        # self.jrodosmodel_dlg.combo_path.clear()
        # jrodos_project_paths = [
        #     "Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective",
        #     "Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time",
        #     "Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135",
        #     "Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137",
        #     "Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135",
        #     "Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137"
        # ]
        # self.jrodosmodel_dlg.combo_path.addItems(jrodos_project_paths)
        # return

        if result.error():
            self.msg(None,
                     "Problem in JRodos plugin retrieving the JRodos datapaths for project:\n{}.\n".format(result.url) +
                     "Check the Log Message Panel for more info")

            self.jrodos_paths_model.appendRow([QStandardItem(
                "Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective")])
            self.jrodosmodel_dlg.combo_path.setModel(self.jrodos_paths_model)

        else:
            data_items = result.data['project']['tasks'][0]['dataitems']
            for data_item in data_items:
                # print data_item['datapath']
                # jrodos_project_paths.append(data_item['datapath'])
                self.jrodos_paths_model.appendRow([QStandardItem(data_item['datapath'])])
            self.jrodosmodel_dlg.combo_path.setModel(self.jrodos_paths_model)
            # set last used datapath or nothing if this project does not have this datapath
            last_used_datapath = Utils.get_settings_value("jrodos_last_model_datapath", "")
            items = self.jrodos_paths_model.findItems(last_used_datapath, Qt.MatchExactly, 0)
            if len(items) > 0:
                self.jrodosmodel_dlg.combo_path.setCurrentIndex(items[0].row())

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def info(self, msg=""):
        QgsMessageLog.logMessage(str(msg), self.MSG_TITLE, QgsMessageLog.INFO)

    def show_jrodos_output_dialog(self, jrodos_output_settings=None):
        # TODO ?? init dialog based on older values

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
            # TODO: get these from ?? dialog?? settings??
            jrodos_output_settings.url = self.settings.value('jrodos_wps_url') #'http://localhost:8080/geoserver/wps'
            # FORMAT is fixed to zip with shapes
            jrodos_output_settings.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
            # selected project + save the project id (model col 1) to QSettings
            jrodos_output_settings.jrodos_project = self.projects_model.item(self.jrodosmodel_dlg.combo_project.currentIndex(), self.QMODEL_NAME_IDX).text()
            # for storing in settings we do not use the non unique name, but the if of the project
            last_used_project = self.projects_model.item(self.jrodosmodel_dlg.combo_project.currentIndex(), self.QMODEL_ID_IDX).text()
            #self.msg(None, "last_used_project: " + last_used_project)
            Utils.set_settings_value("jrodos_last_model_project", last_used_project)
            jrodos_output_settings.jrodos_path = self.jrodosmodel_dlg.combo_path.itemText(self.jrodosmodel_dlg.combo_path.currentIndex())
            last_used_datapath = jrodos_output_settings.jrodos_path
            #self.msg(None, last_used_datapath)
            Utils.set_settings_value("jrodos_last_model_datapath", last_used_datapath)
            jrodos_output_settings.jrodos_model_step = self.jrodosmodel_dlg.combo_steps.itemText(self.jrodosmodel_dlg.combo_steps.currentIndex())  # steptime (minutes)
            jrodos_output_settings.jrodos_model_time = self.jrodosmodel_dlg.combo_model_length.itemText(self.jrodosmodel_dlg.combo_model_length.currentIndex()) # modeltime (hours)
            # vertical is fixed to 0 now
            jrodos_output_settings.jrodos_verticals = 0  # z / layers
            jrodos_output_settings.jrodos_datetime_start = self.jrodosmodel_dlg.dateTime_start.dateTime()
            self.jrodos_output_settings = jrodos_output_settings
            self.start_jrodos_model_output_provider()

    def start_jrodos_model_output_provider(self):
        self.jrodos_output_progress_bar.setMaximum(0)
        self.jrodos_output_settings = self.jrodos_output_settings
        self.jrodos_output_provider = JRodosModelOutputProvider(self.jrodos_output_settings)
        self.jrodos_output_provider.finished.connect(self.finish_jrodos_model_output_provider)
        self.jrodos_output_provider.get_data()
        # while not jrodos_output_provider.is_finished():
        #     QCoreApplication.processEvents()

    def finish_jrodos_model_output_provider(self, result):
        self.info(result)
        self.jrodos_output_progress_bar.setMaximum(100)
        self.jrodos_output_progress_bar.setFormat(self.BAR_LOADING_TITLE)
        QCoreApplication.processEvents() # to be sure we have the loading msg
        if result.error():
            self.iface.messageBar().pushMessage("Network problem: %s" % result.error_code, self.iface.messageBar().CRITICAL, 1)
        else:
            # Load the received shp-zip files
            # TODO: determine qml file based on something coming from the settings/result object
            if result.data is not None:
                self.load_jrodos_output(result.data['output_dir'], 'totalpotentialdoseeffective.qml')
            else:
                self.msg(None, "No Jrodos Model Output data? {}".format(result.data))
        self.jrodos_output_settings = None
        self.jrodos_output_progress_bar.setFormat(self.JRODOS_BAR_TITLE)


    def show_measurements_dialog(self, measurements_settings=None):

        if measurements_settings is not None:
            self.measurements_settings = measurements_settings
            self.find_jrodos_layer(measurements_settings)
            self.set_measurements_bbox()
            self.start_measurements_provider()
            return

        if self.measurements_settings is not None:
            self.msg(None, "Still busy retrieving Measurement data via WFS, please try later...")
            return

        self.measurements_settings = None
        end_time = QDateTime.currentDateTime() # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # -12 hours
        # INIT dialog based on earlier wps dialog
        if self.jrodos_output_settings is not None:
            start_time = self.jrodos_output_settings.jrodos_datetime_start
            end_time = start_time.addSecs(60 * 60 * int(self.jrodos_output_settings.jrodos_model_time)) # model time

        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)
        self.measurements_dlg.combo_endminusstart.setCurrentIndex(
            self.measurements_dlg.combo_endminusstart.findText(Utils.get_settings_value('endminusstart', '3600')))

        self.measurements_dlg.show()

        result = self.measurements_dlg.exec_()
        if result:  # OK was pressed

            if len(self.quantities) == 1 or len(self.substances) == 1: # meaning we did not retrieve anything back yet
                self.msg(None, "No substances and quantities, network problem? \nSee messages panel ...")
                return

            # selected endminusstart + save to QSettings
            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            Utils.set_settings_value("endminusstart", endminusstart)
            # selected quantity + save to QSettings
            quantity = self.quantities_model.item(self.measurements_dlg.combo_quantity.currentIndex(), self.JRODOS_CODE_IDX).text()
            Utils.set_settings_value("measurements_last_quantity", quantity)
            # selected substance + save to QSettings
            substance = self.substances_model.item(self.measurements_dlg.combo_substance.currentIndex(), self.JRODOS_CODE_IDX).text()
            Utils.set_settings_value("measurements_last_substance", substance)

            start_date = self.measurements_dlg.dateTime_start.dateTime()
            print "###### start: %s" % start_date
            # make it UTC
            #start_date = start_date.toUTC()
            end_date = self.measurements_dlg.dateTime_end.dateTime()
            print "######   end: %s" % end_date
            # make it UTC
            #end_date = end_date.toUTC()

            measurements_settings = CalnetMeasurementsConfig()
            # TODO make these come from config
            measurements_settings.url = self.settings.value('measurements_wfs_url') #'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'

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
            self.set_measurements_bbox()
            self.start_measurements_provider()

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
            self.msg(None, result.error_code)
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

    def set_measurements_bbox(self):
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

    # now, open all shapefiles one by one, s from 0 till x
    # starting with a startdate 20160101000000 t
    # add an attribute 'time' and set it to t+s
    def load_jrodos_output(self, shape_dir, style_file):
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
        # give the memory layer the same CRS as the source layer
        # timestamp as first attribute, easier to config with timemanager plugin (default first column)
        # TODO: epsg:32631
        # http: // docs.qgis.org / testing / en / docs / pyqgis_developer_cookbook / vector.html  # writing-vector-layers
        # create layer
        jrodos_datapath = self.jrodos_output_settings.jrodos_path
        jrodos_output_layer = QgsVectorLayer("Polygon", jrodos_datapath, "memory")
        pr = jrodos_output_layer.dataProvider()
        # add fields
        pr.addAttributes([QgsField("Datetime", QVariant.String),
                          QgsField("Cell", QVariant.Int),
                          QgsField("Value", QVariant.Double)])
        jrodos_output_layer.updateFields()  # tell the vector layer to fetch changes from the provider

        # add layer to the map
        QgsMapLayerRegistry.instance().addMapLayer(jrodos_output_layer, False)  # False, meaning not ready to add to legend
        self.layer_group.insertLayer(1, jrodos_output_layer)  # now add to legend in current layer group

        layer_crs = None

        shps = glob(os.path.join(shape_dir, "*.zip"))

        for shp in shps:
            (shpdir, shpfile) = os.path.split(shp)
            vlayer = QgsVectorLayer(shp, shpfile, "ogr")
            flist = []
            if not vlayer.isValid():
                self.msg(None, "Layer(s) failed to load!")
                break
            else:
                #self.msg(None, "Layer loaded %s" % shp)
                if layer_crs ==None:
                    # find out source crs of shp and set our memory layer to the same crs
                    layer_crs = vlayer.crs()
                    jrodos_output_layer.setCrs(layer_crs)

                features = vlayer.getFeatures()

                step = int(shpfile.split('_')[0])
                tstamp = QDateTime(self.jrodos_output_settings.jrodos_datetime_start)
                # every zip get's a column with a timestamp based on the 'step/column' from the model
                # so 0_0.zip is column 0, vertical 0
                # BUT column 0 is from the first model step!!
                # SO WE HAVE TO ADD ONE STEP OF SECONDS TO THE TSTAMP (step+1+
                tstamp = tstamp.addSecs(60 * (step+1) * int(self.jrodos_output_settings.jrodos_model_step))
                tstamp = tstamp.toString("yyyy-MM-dd HH:mm")
                for feature in features:
                    # only features with Value > 0, to speed up QGIS
                    if feature.attribute('Value') > 0:
                        fields = feature.fields()
                        fields.append(QgsField("Datetime"))
                        f = QgsFeature(fields)
                        # timestamp as first attribute, easier to config with timemanager plugin (default first column)
                        f.setAttributes([tstamp, feature.attribute('Cell'), feature.attribute('Value')])
                        f.setGeometry(feature.geometry())
                        flist.append(f)

            jrodos_output_layer.dataProvider().addFeatures(flist)
            jrodos_output_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!
            jrodos_output_layer.updateFields()
            jrodos_output_layer.updateExtents()
            self.iface.mapCanvas().refresh()

        # put a copy of the settings into our map<=>settings dict
        # IF we want to be able to load a layer several times based on the same settings
        self.jrodos_settings[jrodos_output_layer] = deepcopy(self.jrodos_output_settings)

        # add this layer to the TimeManager
        self.add_layer_to_timemanager(jrodos_output_layer, 'Datetime')

    def add_layer_to_timemanager(self, layer, time_column, frame_size=60, frame_type='minutes'):

        # TODO try catch this, and put this to top of file
        from timemanager.layer_settings import LayerSettings
        from timemanager.timevectorlayer import TimeVectorLayer
        from qgis.utils import plugins
        #from timemanager.tmlogging import info

        if not 'timemanager' in plugins:
            self.iface.messageBar().pushWarning ("Warning!!", "No TimeManger plugin, we REALLY need that. Please install via Plugin Manager first...")
            return

        timemanager = plugins['timemanager']

        #TODO click on button if not enabled
        if not timemanager.getController().getTimeLayerManager().isEnabled():
            timemanager.getController().getGui().dock.pushButtonToggleTime.click()
        # for testing: just remove all timelayers
        #timemanager.getController().timeLayerManager.clearTimeLayerList()

        jrodos_settings = self.jrodos_settings[layer] # we keep (deep)copies of the settings of the layers here

        timelayer_settings = LayerSettings()
        timelayer_settings.layer = layer
        timelayer_settings.startTimeAttribute = time_column
        #timelayer_settings.startTimeAttribute = jrodos_settings.start_datetime
        #timelayer_settings.endTimeAttribute = jrodos_settings.end_datetime

        timelayer = TimeVectorLayer(timelayer_settings, self.iface)

        print timelayer
        print timelayer.getTimeExtents()

        animationFrameLength = 2000
        frame_size = frame_size
        frame_type = frame_type
        timemanager.getController().setPropagateGuiChanges(False)
        timemanager.getController().setAnimationOptions(animationFrameLength, False, False)

        # via gui should not be nessecary!!!
        # tm.getController().getGui().setTimeFrameType(frame_type)
        timemanager.getController().setTimeFrameType(frame_type)
        # via gui should not be nessecary!!!
        # tm.getController().getGui().setTimeFrameSize(frame_size)
        timemanager.getController().setTimeFrameSize(frame_size)

        timemanager.getController().timeLayerManager.registerTimeLayer(timelayer)
        timemanager.getController().refreshGuiTimeFrameProperties()

        # set layer to zero
        timemanager.getController().getGui().dock.horizontalTimeSlider.setValue(0)
        timemanager.getController().refreshGuiTimeFrameProperties()


    def load_measurements(self, output_dir, style_file):
        """
        Load the measurements from the output_dir (as gml files), load them in a layer, and style them with style_file
        :param output_dir:
        :param style_file:
        :return:
        """

        # check if for current measurements_settings there is already a layer in the layer list
        measurements_layer = self.find_jrodos_layer(self.measurements_settings)
        # IF there is no memory/measurements layer yet: create it
        if measurements_layer is None:
            # create layer name based on self.measurements_settings
            start_time = QDateTime.fromString(self.measurements_settings.start_datetime, self.measurements_settings.date_time_format)
            end_time = QDateTime.fromString(self.measurements_settings.end_datetime, self.measurements_settings.date_time_format)
            # layer_name = "T-GAMMA, A5, 600, 17/6 23:01 - 20/6 11:01"
            layer_name = self.measurements_settings.quantity + ", " + self.measurements_settings.substance + ", " + \
                         self.measurements_settings.endminusstart + ", " + \
                         start_time.toString(self.measurements_settings.date_time_format_short) + " - " + \
                         end_time.toString(self.measurements_settings.date_time_format_short)
            measurements_layer = QgsVectorLayer("point", layer_name, "memory")
            # fields = gml_layer.fields()
            # self.msg(None, 'temp_layer.fields() %s' % temp_layer.fields())
            # for field in fields:
            #    temp_layer.addAttribute(field)
            #    temp_layer.commitChanges()
            #    temp_layer.updateFields()  # tell the vector layer to fetch changes from the provider

            # add fields
            pr = measurements_layer.dataProvider()
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
            measurements_layer.updateFields()

            QgsMapLayerRegistry.instance().addMapLayer(measurements_layer, False) # False, meaning not ready to add to legend
            self.layer_group.insertLayer(0, measurements_layer) # now add to legend in current layer group
            self.layer_group.setName('Data retrieved: ' + QDateTime.currentDateTime().toString('MM/dd HH:mm'))

            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            # self.jrodos_settings[measurements_layer] = deepcopy(self.measurements_settings)
            self.jrodos_settings[measurements_layer] = self.measurements_settings

            measurements_layer.loadNamedStyle(
                os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
        else:
            # there is already a layer for this measurements_settings object, so apparently we got new data for it:
            # remove current features from the  layer
            measurements_layer.startEditing()
            measurements_layer.selectAll()
            measurements_layer.deleteSelectedFeatures()
            measurements_layer.commitChanges()


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
                        if feature.attribute('unit') == 'USV/H':
                            # value in milliS/H, value / 1000
                            valuemsv = value/1000
                            attributes.append(valuemsv)
                        elif feature.attribute('unit') == 'NSV/H':
                            # value in milliS/H, value / 1000
                            valuemsv = value/1000000
                            attributes.append(valuemsv)
                        else:
                            attributes.append(-1) # set value to '-1' not sure if NULL is better...
                            if new_unit_msg:
                                self.msg(None, "New unit in data: '%s', setting valuemsv to -1" % feature.attribute('unit'))
                                new_unit_msg = False
                        f.setAttributes(attributes)
                        f.setGeometry(feature.geometry())
                        flist.append(f)
                        if len(flist)>1000:
                            measurements_layer.dataProvider().addFeatures(flist)
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

            measurements_layer.dataProvider().addFeatures(flist)
            measurements_layer.updateFields()
            measurements_layer.updateExtents()

            # set the display field value
            measurements_layer.setDisplayField('[% measurement_values()%]')
            # enable maptips?
            if not self.iface.actionMapTips().isChecked():
                self.iface.actionMapTips().toggle()
            self.iface.legendInterface().setCurrentLayer(measurements_layer)
            self.iface.mapCanvas().refresh()

        # add this layer to the TimeManager
        self.add_layer_to_timemanager(measurements_layer, 'time')

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
