# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JRodos
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, QDateTime, QThread, QDate, QTime, Qt
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar, QStandardItemModel, QStandardItem
import resources
# Import the code for the dialog
from qgis.gui import QgsMessageBar
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsGeometry, QgsMessageLog
from qgis.utils import qgsfunction, QgsExpression
from glob import glob
import os.path, tempfile, time, json
from datetime import date, time, datetime, timedelta
from utils import Utils
from copy import deepcopy
from data_worker import WfsDataWorker, WfsSettings, WpsDataWorker, WpsSettings
from jrodos_soap import do_jrodos_soap_call
from ui import ExtendedCombo, JRodosMeasurementsDialog, JRodosDialog



# pycharm debugging
# COMMENT OUT BEFORE PACKAGING !!!
# import pydevd
# pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

class JRodos:
    """QGIS Plugin Implementation."""

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

        self.MSG_BOX_TITLE = self.tr("JRodos Plugin")

        # NOTE !!! project names surrounded by single quotes ??????
        self.JRODOS_PROJECTS = ["'wps-13sept-test'"]

        self.JRODOS_MODEL_LENGTH_HOURS = ['24', '12', '6', '3']

        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'"  # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        self.JRODOS_PATHS = [
            "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'",
            "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'"
        ]
        self.JRODOS_STEP_MINUTES = ['10', '30', '60'] # as in JRodos

        # WFS 2.0: number of features to load when 'paging' data
        self.WFS_PAGING_SIZE = 10000

        # Create the dialog (after translation) and keep reference
        self.dlg = JRodosDialog()
        # add current models to dropdown
        self.dlg.combo_project.addItems(self.JRODOS_PROJECTS)
        # self.dlg.combo_model.currentText()
        # add current paths to dropdown
        # TODO from yaml or settings?
        self.dlg.combo_path.addItems(self.JRODOS_PATHS)
        self.dlg.combo_steps.addItems(self.JRODOS_STEP_MINUTES)
        self.dlg.combo_model_length.addItems(self.JRODOS_MODEL_LENGTH_HOURS)
        utcdatetime = QDateTime(QDate(2016, 9, 13), QTime(8, 0))
        self.dlg.dateTime_start.setDateTime(utcdatetime)
        #self.dlg.dateTime_start.setDateTime(QDateTime(QDate(2016, 05, 17), QTime(6, 0)))
        # TODO dev
        self.dlg.combo_project.setCurrentIndex(0)
        self.dlg.combo_steps.setCurrentIndex(1)

        self.development = False

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&JRodos')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'JRodos')
        self.toolbar.setObjectName(u'JRodos')
        self.wps_progress_bar = None
        self.wfs_progress_bar = None

        self.wps_settings = None
        self.wfs_settings = None
        self.wps_thread = None
        self.wfs_thread = None

        # creating a dict for a layer <-> settings mapping
        self.jrodos_settings = {}

        # dialog for measurements
        self.measurements_dlg = None

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

        progress_bar_width = 100

        if self.wps_progress_bar is None:
            self.wps_progress_bar = QProgressBar()
            self.wps_progress_bar.setToolTip("Model data (WPS)")
            self.wps_progress_bar.setMaximum(100)
            self.wps_progress_bar.setFixedWidth(progress_bar_width)
            self.wps_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.toolbar.addWidget(self.wps_progress_bar)

        if self.wfs_progress_bar is None:
            self.wfs_progress_bar = QProgressBar()
            self.wfs_progress_bar.setToolTip("Measurement data (WFS)")
            self.wfs_progress_bar.setMaximum(100)
            self.wfs_progress_bar.setFixedWidth(progress_bar_width)
            self.wfs_progress_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.toolbar.addWidget(self.wfs_progress_bar)

        self.measurements_dlg = JRodosMeasurementsDialog()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&JRodos'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove progress bars
        del self.wps_progress_bar
        del self.wfs_progress_bar
        # remove the toolbar
        del self.toolbar
        # deregister our custom QgsExpression function
        QgsExpression.unregisterFunction("$measurement_values")
        QgsExpression.unregisterFunction("measurement_values")

    def wfs_start(self):
        # WFS / MEASUREMENTS PART
        # self.msg(None, self.wfs_settings)
        if self.development:
            self.msg(None, "development!!")
            test_data_path = os.path.join(
                self.plugin_dir,
                'data',
                'testdata')
            self.wfs_finished({'output_dir':test_data_path})
            return
        self.wfs_thread = QThread(self.iface)
        self.wfs_worker = WfsDataWorker(self.wfs_settings)
        self.wfs_worker.moveToThread(self.wfs_thread)
        self.wfs_worker.finished.connect(self.wfs_finished)
        self.wfs_worker.error.connect(self.wfs_error)
        self.wfs_worker.progress.connect(self.wfs_progress)
        self.wfs_thread.started.connect(self.wfs_worker.run)
        self.wfs_progress(0.1)
        self.wfs_thread.start()

    def wfs_finished(self, result):
        self.wfs_progress_bar.setValue(0.9)
        self.iface.messageBar().pushMessage("Retrieved all measurement data, loading layer...", self.iface.messageBar().INFO, 1)
        # Load the received gml files
        # TODO: determine qml file based on something coming from the settings/result object
        self.load_measurements(result['output_dir'], 'totalpotentialdoseeffective2measurements.qml')
        if self.wfs_thread is not None:
            self.wfs_thread.quit()
        self.wfs_settings = None
        self.wfs_progress(1)
        self.check_data_received()

    def wfs_progress(self, part):
        self.wfs_progress_bar.setValue(part*100)

    def wfs_error(self, err):
        self.msg(None, err)
        self.wfs_settings = None

    def wps_start(self):
        # self.msg(None, wps_settings)
        #self.msg(None, "wps starting")
        if self.development:
            self.msg(None, "development!!")
            test_data_path = os.path.join(
                self.plugin_dir,
                'data',
                'testdata')
            self.wps_finished({'output_dir':test_data_path})
            return
        self.wps_thread = QThread(self.iface)
        self.wps_worker = WpsDataWorker(self.wps_settings)
        self.wps_worker.moveToThread(self.wps_thread)
        self.wps_worker.finished.connect(self.wps_finished)
        self.wps_worker.error.connect(self.wps_error)
        self.wps_worker.progress.connect(self.wps_progress)
        self.wps_thread.started.connect(self.wps_worker.run)
        self.wps_thread.start()
        self.wps_progress(0.1)

    def wps_finished(self, result):
        if self.wps_thread is not None:
            self.wps_thread.quit()
        # Load the received shp-zip files
        # TODO: determine qml file based on something coming from the settings/result object
        self.wps_progress(0.9)
        self.iface.messageBar().pushMessage("Retrieved all model data, loading layer...", self.iface.messageBar().INFO, 1)
        self.load_shapes(result['output_dir'], 'totalpotentialdoseeffective.qml')
        self.wps_settings = None
        self.wps_progress(1)
        self.check_data_received()

    def wps_progress(self, part):
        self.wps_progress_bar.setValue(part * 100)
        #print "wps progress: %s " % part

    def get_progress_message_bar_item(self):
        self.progress_message_bar_item = self.iface.messageBar().createMessage("Retrieving data from server ...")
        self.iface.messageBar().pushWidget(self.progress_message_bar_item, self.iface.messageBar().INFO)
        return self.progress_message_bar_item

    def wps_error(self, err):
        self.msg(None, err)
        self.wps_settings = None

    def check_data_received(self):
        wfs_is_ready = True
        wps_is_ready = True
        if self.wfs_thread is not None:
            wfs_is_ready = self.wfs_thread.isFinished()
        if self.wps_thread is not None:
            wps_is_ready = self.wps_thread.isFinished()
        if wfs_is_ready and wps_is_ready:
            # TODO
            self.iface.messageBar().pushMessage("JRodos plugin: retrieved and loaded all data ...", self.iface.messageBar().INFO, 5)
            self.wfs_progress(0)
            self.wps_progress(0)

    def run(self):
        try:
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
            # try to start wps
#            self.show_jrodos_wps_dialog()
            # try to start wfs (using wps-settings if available as self.wps_settings)
            self.show_measurements_dialog()

        except Exception as e:
            self.msg(None, "Exception: %s" % e)

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_BOX_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def show_jrodos_wps_dialog(self, wps_settings=None):
        # TODO ?? init dialog based on older values

        if wps_settings is not None:
            self.wps_settings = wps_settings
            self.wps_start()
            return

        # WPS / MODEL PART
        if self.wps_settings is not None:
            self.msg(None, "Still busy retrieving Model data via WPS, please try later...")
            return

        self.dlg.show()
        if self.dlg.exec_():  # OK was pressed
            wps_settings = WpsSettings()
            # TODO: get these from ?? dialog?? settings??
            wps_settings.url = 'http://localhost:8080/geoserver/wps'
            # FORMAT is fixed to zip with shapes
            wps_settings.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
            wps_settings.jrodos_project = self.dlg.combo_project.itemText(self.dlg.combo_project.currentIndex())
            wps_settings.jrodos_path = self.dlg.combo_path.itemText(self.dlg.combo_path.currentIndex())
            wps_settings.jrodos_model_step = self.dlg.combo_steps.itemText(self.dlg.combo_steps.currentIndex())  # steptime (minutes)
            wps_settings.jrodos_model_time = self.dlg.combo_model_length.itemText(self.dlg.combo_model_length.currentIndex()) # modeltime (hours)
            # vertical is fixed to 0 now
            wps_settings.jrodos_verticals = 0  # z / layers
            wps_settings.jrodos_datetime_start = self.dlg.dateTime_start.dateTime()
            self.wps_settings = wps_settings
            self.wps_start()

    def show_measurements_dialog(self, wfs_settings=None):

        if wfs_settings is not None:
            self.wfs_settings = wfs_settings
            self.find_jrodos_layer(wfs_settings)
            self.set_wfs_bbox()
            self.wfs_start()
            return

        if self.wfs_settings is not None:
            self.msg(None, "Still busy retrieving Measurement data via WFS, please try later...")
            return

        self.wfs_settings = None
        end_time = QDateTime.currentDateTime() # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # -12 hours
        # INIT dialog based on earlier wps dialog
        if self.wps_settings is not None:
            start_time = self.wps_settings.jrodos_datetime_start
            end_time = start_time.addSecs(60 * 60 * int(self.wps_settings.jrodos_model_time)) # model time
        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)

        DESCRIPTION_IDX = 0
        CODE_IDX = 1

        # QUANTITIES
        quantities = do_jrodos_soap_call('Quantities')

        # Replace the default ComboBox with our better ExtendedCombo
        # self.measurements_dlg.gridLayout.removeWidget(self.measurements_dlg.combo_quantity)
        self.measurements_dlg.combo_quantity.close()  # this apparently also removes the widget??
        self.measurements_dlg.combo_quantity = ExtendedCombo()
        self.measurements_dlg.gridLayout.addWidget(self.measurements_dlg.combo_quantity, 3, 1, 1, 2)

        quantities_model = QStandardItemModel()
        for q in quantities:
            quantities_model.appendRow([QStandardItem(q['description']), QStandardItem(q['code'])])
        self.measurements_dlg.combo_quantity.setModel(quantities_model)

        lastused_quantities_code = Utils.get_settings_value("measurements_last_quantity", "T_GAMMA")
        items = quantities_model.findItems(lastused_quantities_code, Qt.MatchExactly, CODE_IDX)
        if len(items)>0:
            self.measurements_dlg.combo_quantity.setCurrentIndex(items[DESCRIPTION_IDX].row())

        # SUBSTANCES
        substances = do_jrodos_soap_call('Substances')

        # Replace the default ComboBox with our better ExtendedCombo
        # self.measurements_dlg.gridLayout.removeWidget(self.measurements_dlg.combo_quantity)
        self.measurements_dlg.combo_substance.close()  # this apparently also removes the widget??
        self.measurements_dlg.combo_substance = ExtendedCombo()
        self.measurements_dlg.gridLayout.addWidget(self.measurements_dlg.combo_substance, 5, 1, 1, 2)

        substances_model = QStandardItemModel()
        for s in substances:
            substances_model.appendRow([QStandardItem(s['description']), QStandardItem(s['code'])])
        self.measurements_dlg.combo_substance.setModel(substances_model)

        lastused_substance_code = Utils.get_settings_value("measurements_last_substance", "A5")
        items = substances_model.findItems(lastused_substance_code, Qt.MatchExactly, CODE_IDX)
        if len(items)>0:
            self.measurements_dlg.combo_substance.setCurrentIndex(items[DESCRIPTION_IDX].row())

        self.measurements_dlg.show()

        result = self.measurements_dlg.exec_()
        if result:  # OK was pressed
            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            # selected quantity + save to QSettings
            quantity = quantities_model.item(self.measurements_dlg.combo_quantity.currentIndex(), CODE_IDX).text()
            Utils.set_settings_value("measurements_last_quantity", quantity)
            # selected substance + save to QSettings
            substance = substances_model.item(self.measurements_dlg.combo_substance.currentIndex(), CODE_IDX).text()
            Utils.set_settings_value("measurements_last_substance", substance)

            start_date = self.measurements_dlg.dateTime_start.dateTime()
            # make it UTC
            #start_date = start_date.toUTC()
            end_date = self.measurements_dlg.dateTime_end.dateTime()
            # make it UTC
            #end_date = end_date.toUTC()

            wfs_settings = WfsSettings()
            # TODO make these come from config
            wfs_settings.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'

            if self.wps_settings is None:
                project = "'measurements'"
                path = "'=;=wfs=;=data'"
                wfs_settings.output_dir = Utils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
            else:
                wfs_settings.output_dir = self.wps_settings.output_dir()

            wfs_settings.page_size = self.WFS_PAGING_SIZE
            wfs_settings.start_datetime = start_date.toString(wfs_settings.date_time_format)
            wfs_settings.end_datetime = end_date.toString(wfs_settings.date_time_format)
            wfs_settings.endminusstart = endminusstart
            wfs_settings.quantity = quantity
            wfs_settings.substance = substance
            self.wfs_settings = wfs_settings
            self.set_wfs_bbox()
            self.wfs_start()

    def set_wfs_bbox(self):
            # bbox in epsg:4326
            crs_project = self.iface.mapCanvas().mapSettings().destinationCrs()
            crs_4326 = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
            crsTransform = QgsCoordinateTransform(crs_project, crs_4326)
            current_bbox_4326 = crsTransform.transform(self.iface.mapCanvas().extent())
            # bbox for wfs request, based on current bbox of mapCanvas (OR model)
            self.wfs_settings.bbox = "{},{},{},{}".format(
                current_bbox_4326.yMinimum(), current_bbox_4326.xMinimum(), current_bbox_4326.yMaximum(), current_bbox_4326.xMaximum())  # S,W,N,E

    def find_jrodos_layer(self, settings_object):
        for layer in self.jrodos_settings:
            if self.jrodos_settings[layer] == settings_object:
                return layer
        return None

    # now, open all shapefiles one by one, s from 0 till x
    # starting with a startdate 20160101000000 t
    # add an attribute 'time' and set it to t+s
    def load_shapes(self, shape_dir, style_file):
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
        vector_layer = QgsVectorLayer("Polygon", "Model", "memory")
        pr = vector_layer.dataProvider()
        # add fields
        pr.addAttributes([QgsField("Datetime", QVariant.String),
                          QgsField("Cell", QVariant.Int),
                          QgsField("Value", QVariant.Double)])
        vector_layer.updateFields()  # tell the vector layer to fetch changes from the provider

        # add layer to the map
        QgsMapLayerRegistry.instance().addMapLayer(vector_layer)
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
                    vector_layer.setCrs(layer_crs)

                features = vlayer.getFeatures()

                step = int(shpfile.split('_')[0])
                tstamp = QDateTime(self.wps_settings.jrodos_datetime_start)
                # every zip get's a column with a timestamp based on the 'step/column' from the model
                # so 0_0.zip is column 0, vertical 0
                # BUT column 0 is from the first model step!!
                # SO WE HAVE TO ADD ONE STEP OF SECONDS TO THE TSTAMP (step+1+
                tstamp = tstamp.addSecs(60*(step+1)*int(self.wps_settings.jrodos_model_step))
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

            vector_layer.dataProvider().addFeatures(flist)
            vector_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!
            vector_layer.updateFields()
            vector_layer.updateExtents()
            self.iface.mapCanvas().refresh()
            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            self.jrodos_settings[vector_layer] = deepcopy(self.wps_settings)

    def load_measurements(self, output_dir, style_file):
        """
        Fire a wfs request
        :param output_dir:
        :param style_file:
        :return:
        """

        # check if for current wfs_settings there is already a layer in the layer list
        measurements_layer = self.find_jrodos_layer(self.wfs_settings)
        # IF there is no memory/measurements layer yet: create it
        if measurements_layer is None:
            # we do NOT want the default behaviour: prompting for a crs
            # we want to set it to epsg:4326, see
            # http://gis.stackexchange.com/questions/27745/how-can-i-specify-the-crs-of-a-raster-layer-in-pyqgis
            s = QSettings()
            oldCrsBehaviour = s.value("/Projections/defaultBehaviour", "useGlobal")
            s.setValue("/Projections/defaultBehaviour", "useGlobal")
            oldCrs = s.value("/Projections/layerDefaultCrs", "EPSG:4326")
            s.setValue("/Projections/layerDefaultCrs", "EPSG:4326")

            # create layer name based on self.wfs_settings
            start_time = QDateTime.fromString(self.wfs_settings.start_datetime, self.wfs_settings.date_time_format)
            end_time = QDateTime.fromString(self.wfs_settings.end_datetime, self.wfs_settings.date_time_format)
            # layer_name = "T-GAMMA, A5, 17/6 23:01 - 20/6 11:01"
            layer_name = self.wfs_settings.quantity + ", " + self.wfs_settings.substance + ", " + \
                         start_time.toString(self.wfs_settings.date_time_format_short) + " - " + \
                         end_time.toString(self.wfs_settings.date_time_format_short)
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
            QgsMapLayerRegistry.instance().addMapLayer(measurements_layer)

            # put a copy of the settings into our map<=>settings dict
            # IF we want to be able to load a layer several times based on the same settings
            # self.jrodos_settings[measurements_layer] = deepcopy(self.wfs_settings)
            self.jrodos_settings[measurements_layer] = self.wfs_settings

            # change back to default action of asking for crs or whatever the old behaviour was!
            s.setValue("/Projections/defaultBehaviour", oldCrsBehaviour)
            s.setValue("/Projections/layerDefaultCrs", oldCrs)

            measurements_layer.loadNamedStyle(
                os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!
        else:
            # there is already a layer for this wfs_settings object, so apparently we got new data for it:
            # remove current features from the  layer
            measurements_layer.startEditing()
            measurements_layer.selectAll()
            measurements_layer.deleteSelectedFeatures()
            measurements_layer.commitChanges()


        # TODO fix this: stepsize is part of settings object
        STEPSIZE = 10000
        feature_count = 0
        step_count = STEPSIZE
        flist = []
        gmls = glob(os.path.join(output_dir, "*.gml"))
        for gml_file in gmls:
            gml_layer = QgsVectorLayer(gml_file, 'only for loading', 'ogr')
            if not gml_layer.isValid():
                self.msg(None, 'GML layer NOT VALID!')
                return
            else:
                features = gml_layer.getFeatures()
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

            measurements_layer.dataProvider().addFeatures(flist)
            measurements_layer.updateFields()
            measurements_layer.updateExtents()

            # set the display field value
            measurements_layer.setDisplayField('[% measurement_values()%]')
            # enable maptips?
            if not self.iface.actionMapTips().isChecked():
                self.iface.actionMapTips().toggle()
            self.iface.mapCanvas().refresh()

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
