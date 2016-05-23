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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, QDateTime, QThread, Qt, QDate, QTime
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QProgressBar
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qgis.gui import QgsMessageBar
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry
from glob import glob
import os.path, tempfile, time
from datetime import date, time, datetime, timedelta
import urllib, urllib2, shutil
from jrodos_dialog import JRodosDialog
from jrodos_measurements_dialog import JRodosMeasurementsDialog
from utils import Utils
from data_worker import WfsDataWorker, WfsSettings, WpsDataWorker, WpsSettings

# pycharm debugging
# COMMENT OUT BEFORE PACKAGING !!!
#import pydevd
#pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

# uit gridcreator ??
#sys.path.append('/home/richard/apps/pycharm-3.4.1/pycharm-debug.egg')
#import pydevd

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
        self.JRODOS_PROJECTS = ["'wps-test-5'", "'wps-test-3'", "'wps-test-2'", "'wps-test-1'"]

        self.JRODOS_MODEL_LENGTH_HOURS = ['24']

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
        utcdatetime = QDateTime(QDate(2016, 04, 25), QTime(8, 0))
        self.dlg.dateTime_start.setDateTime(utcdatetime)
        #self.dlg.dateTime_start.setDateTime(QDateTime(QDate(2016, 05, 17), QTime(6, 0)))
        # TODO dev
        self.dlg.combo_project.setCurrentIndex(1)
        self.dlg.combo_steps.setCurrentIndex(2)


        self.measurements_dlg = JRodosMeasurementsDialog()
        self.MEASUREMENTS_ENDMINUSTART = ['600', '3600']
        self.measurements_dlg.combo_endminusstart.addItems(self.MEASUREMENTS_ENDMINUSTART)
        self.measurements_dlg.combo_endminusstart.setCurrentIndex(1)
        now = QDateTime.currentDateTime().toUTC()
        # TODO dev
        now = QDateTime(QDate(2016, 05, 17), QTime(8, 0))

        # TODO dev
        self.measurements_dlg.dateTime_start.setDateTime(now.addDays(-1))
        self.measurements_dlg.dateTime_start.setDateTime(now.addSecs(-(60 * 60 * 6)))
        self.measurements_dlg.dateTime_end.setDateTime(now)




        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&JRodos')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'JRodos')
        self.toolbar.setObjectName(u'JRodos')

        self.progress_message_bar = None
        self.wps_progress_bar = None
        self.wfs_progress_bar = None
        self.wps_settings = None
        self.wfs_settings = None

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

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&JRodos'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def wfs_finished(self, result):
        self.wfs_progress_bar.setValue(100)
        self.iface.messageBar().pushMessage("Retrieved all measurement data, loading layer...", 0, 5)
        # Load the received gml files
        # TODO: determine qml file based on something coming from the settings/result object
        self.load_measurements(result['output_dir'], 'totalpotentialdoseeffective2measurements.qml')
        self.wfs_thread.quit()
        #del self.wfs_progress_bar
        self.check_data_received()
        self.wfs_settings = None
        self.wfs_progress_bar = None

    def wfs_progress(self, part):
        self.wfs_progress_bar.setValue(part*100)

    def wfs_error(self, err):
        self.msg(None, err)
        del self.wfs_progress_bar
        self.wfs_progress_bar = None
        self.wfs_settings = None

    def wps_finished(self, result):
        self.wps_progress_bar.setValue(100)
        self.wps_thread.quit()
        #del self.wps_progress_bar
        #self.iface.messageBar().pushSuccess("Modeldata", "Retrieved all model data...")
        self.iface.messageBar().pushSuccess("Modeldata", "Retrieved all model data, loading layer...")
        # Load the received shp-zip files
        # TODO: determine qml file based on something coming from the settings/result object
        self.iface.messageBar().pushMessage("Retrieved all model data, loading layer...", 0, 5)
        self.load_shapes(result['output_dir'], 'totalpotentialdoseeffective.qml')
        self.check_data_received()
        self.wps_settings = None
        self.wps_progress_bar = None

    def wps_progress(self, part):
        self.wps_progress_bar.setValue(part * 100)

    def wps_error(self, err):
        self.msg(None, err)
        del self.wps_progress_bar
        self.wps_progress_bar = None
        self.wps_settings = None

    def check_data_received(self):
        if self.wfs_thread.isFinished() and self.wps_thread.isFinished():
            self.iface.messageBar().clearWidgets()

    def run(self):
        self.iface.messageBar().clearWidgets()
        try:
            # WPS / MODEL PART
            wps_settings = self.show_jrodos_wps_dialog()
            if wps_settings is None or self.wps_settings is not None:
                #self.msg(None, "Either a wps-thread is busy, OR we got no wps_settings from dialog")
                #return
                pass
            else:
                self.wps_settings = wps_settings
                #self.msg(None, wps_settings)
                wps_thread = QThread(self.iface)
                wps_worker = WpsDataWorker(wps_settings)
                wps_worker.moveToThread(wps_thread)
                wps_worker.finished.connect(self.wps_finished)
                wps_worker.error.connect(self.wps_error)
                wps_worker.progress.connect(self.wps_progress)
                wps_thread.started.connect(wps_worker.run)

                if self.progress_message_bar == None:
                    self.progress_message_bar = self.iface.messageBar().createMessage("Retrieving data from server ...")
                    self.iface.messageBar().pushWidget(self.progress_message_bar, self.iface.messageBar().INFO)

                self.wps_progress_bar = QProgressBar()
                self.wps_progress_bar.setMaximum(100)
                self.wps_progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.progress_message_bar.layout().addWidget(self.wps_progress_bar)

                # NOTE: YOU REALLY NEED TO DO THIS! WITHOUT THE RUN WILL NOT BE STARTED!
                self.wps_thread = wps_thread
                self.wps_worker = wps_worker

                wps_thread.start()

            # WFS / MEASUREMENTS PART
            wfs_settings = self.show_measurements_dialog(wps_settings)
            if wfs_settings is None or self.wfs_settings is not None:
                #self.msg(None, "Either a wfs-thread is busy, OR we got no wfs_settings from dialog")
                return
            self.wfs_settings = wfs_settings
            #self.msg(None, wfs_settings)
            wfs_thread = QThread(self.iface)
            wfs_worker = WfsDataWorker(wfs_settings)
            wfs_worker.moveToThread(wfs_thread)
            wfs_worker.finished.connect(self.wfs_finished)
            wfs_worker.error.connect(self.wfs_error)
            wfs_worker.progress.connect(self.wfs_progress)
            wfs_thread.started.connect(wfs_worker.run)

            if self.progress_message_bar == None:
               self.progress_message_bar = self.iface.messageBar().createMessage("Retrieving data from server ...")
               self.iface.messageBar().pushWidget(self.progress_message_bar, self.iface.messageBar().INFO)

            self.wfs_progress_bar = QProgressBar()
            self.wfs_progress_bar.setMaximum(100)
            self.wfs_progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.progress_message_bar.layout().addWidget(self.wfs_progress_bar)

            wfs_thread.start()

            # NOTE: YOU REALLY NEED TO DO THIS! WITHOUT THE RUN WILL NOT BE STARTED!
            self.wfs_thread = wfs_thread
            self.wfs_worker = wfs_worker

        except Exception as e:
            self.msg(None, "Exception: %s" % e)

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_BOX_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def show_jrodos_wps_dialog(self):
        # TODO ?? init dialog based on older values
        self.dlg.show()
        result = self.dlg.exec_()
        settings = None
        if result:  # OK was pressed
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
            settings = wps_settings
        return settings

    def show_measurements_dialog(self, wps_settings=None):

        end_time = QDateTime.currentDateTime() # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # -12 hours
        # INIT dialog based on earlier wps dialog
        if wps_settings is not None:
            start_time = wps_settings.jrodos_datetime_start
            end_time = start_time.addSecs(60 * 60 * int(wps_settings.jrodos_model_time)) # model time
        self.measurements_dlg.dateTime_start.setDateTime(start_time)
        self.measurements_dlg.dateTime_end.setDateTime(end_time)

        self.measurements_dlg.show()
        result = self.measurements_dlg.exec_()
        settings = None
        if result:  # OK was pressed

            endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
            quantity = self.measurements_dlg.le_quantity.text()
            substance = self.measurements_dlg.le_substance.text()
            date_format = "yyyy-MM-ddTHH:mm:ss.000 00:00"  # '2016-04-25T08:00:00.000+00:00'
            start_date = self.measurements_dlg.dateTime_start.dateTime()

            # make it UTC
            #start_date = start_date.toUTC()
            end_date = self.measurements_dlg.dateTime_end.dateTime()
            # make it UTC
            #end_date = end_date.toUTC()

            wfs_settings = WfsSettings()
            # TODO make these come from config
            wfs_settings.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'

            if wps_settings is None:
                project = "'measurements'"
                path = "'=;=wfs=;=data'"
                wfs_settings.output_dir = Utils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
            else:
                wfs_settings.output_dir = wps_settings.output_dir()

            wfs_settings.page_size = 10000
            wfs_settings.start_datetime = start_date.toString(date_format)
            wfs_settings.end_datetime = end_date.toString(date_format)
            wfs_settings.endminusstart = endminusstart
            wfs_settings.quantity = quantity
            wfs_settings.substance = substance

            # bbox in epsg:4326
            crs_project = self.iface.mapCanvas().mapRenderer().destinationCrs()
            crs_4326 = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
            crsTransform = QgsCoordinateTransform(crs_project, crs_4326)
            bbox_4326 = crsTransform.transform(self.iface.mapCanvas().extent())
            # bbox for wfs request based mapCanvas (OR model)
            #wfs_settings.bbox = '51,1,61,21' # S,W,N,E
            #wfs_settings.bbox = '51,3,53,6'
            wfs_settings.bbox = "{},{},{},{}".format(
                bbox_4326.yMinimum(), bbox_4326.xMinimum(), bbox_4326.yMaximum(), bbox_4326.xMaximum()) # S,W,N,E
            settings = wfs_settings
        return settings


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

    def load_measurements(self, output_dir, style_file):
        """
        Fire a wfs request
        :param output_dir:
        :param style_file:
        :return:
        """

        # we do NOT want the default behaviour: prompting for a crs
        # we want to set it to epsg:4326, see
        # http://gis.stackexchange.com/questions/27745/how-can-i-specify-the-crs-of-a-raster-layer-in-pyqgis
        s = QSettings()
        oldCrsBehaviour = s.value("/Projections/defaultBehaviour", "useGlobal")
        s.setValue("/Projections/defaultBehaviour", "useGlobal")
        oldCrs = s.value("/Projections/layerDefaultCrs", "EPSG:4326")
        s.setValue("/Projections/layerDefaultCrs", "EPSG:4326")

        # TODO fix this: stepsize is part of settings object
        STEPSIZE = 10000
        feature_count = 0
        step_count = STEPSIZE
        measurements_layer = None
        flist = []

        gmls = glob(os.path.join(output_dir, "*.gml"))
        for gml_file in gmls:
            gml_layer = QgsVectorLayer(gml_file, 'only for loading', 'ogr')
            if not gml_layer.isValid():
                self.msg(None, 'GML layer NOT VALID!')
                return
            # IF there is no memory layer yet: create it
            if measurements_layer is None:
                measurements_layer = QgsVectorLayer("point", "Measurements", "memory")

                #fields = gml_layer.fields()
                #self.msg(None, 'temp_layer.fields() %s' % temp_layer.fields())
                #for field in fields:
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
                                  QgsField("device", QVariant.String)
                                  ,QgsField("valuemsv", QVariant.Double)
                                  ])
                measurements_layer.updateFields()
                QgsMapLayerRegistry.instance().addMapLayer(measurements_layer)

            if not gml_layer.isValid():
                self.msg(None, 'Layer failed to load!')
            else:
                features = gml_layer.getFeatures()
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
                            self.msg(None, "New unit in data: %s" % feature.attribute('unit'))
                        f.setAttributes(attributes)
                        f.setGeometry(feature.geometry())
                        flist.append(f)
                        if len(flist)>1000:
                            measurements_layer.dataProvider().addFeatures(flist)
                            flist = []
                        #print "%s            gml_id: %s - %s" % (feature_count, f.geometry().exportToWkt(), f.attributes())
                    else:
                        print "%s            GEEN GEOMETRIE !!! gml_id: %s " % (feature_count, f.attributes())
                        #self.msg(None, "gmlid: %s" % (f['gml_id']))
                        #print "%s gml_id: %s" % (feature_count, f['gml_id'])
                        #break

            measurements_layer.dataProvider().addFeatures(flist)
            #temp_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!

            measurements_layer.updateFields()
            measurements_layer.updateExtents()

            self.iface.mapCanvas().refresh()

            #self.msg(None, '%s features loaded, written in: %s' %(feature_count, file_count))
            #break

        measurements_layer.loadNamedStyle(
            os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!

        #self.iface.messageBar().pushSuccess('OK', 'Ready receiving measurements, feature count: ' + unicode(feature_count))

        # change back to default action of asking for crs or whatever the old behaviour was!
        s.setValue("/Projections/defaultBehaviour", oldCrsBehaviour)
        s.setValue("/Projections/layerDefaultCrs", oldCrs)
    #
    # def path_to_dirname(self, project, path, timestamp):
    #     # path.split('=;=')[-2]+'_'+path.split('=;=')[-1]
    #     dirname = tempfile.gettempdir() + os.sep
    #     dirname += self.slugify(unicode(project)) + '_'
    #     dirname += self.slugify(unicode(path.split('=;=')[-2])) + '_'
    #     dirname += self.slugify(unicode(path.split('=;=')[-1])) + '_'
    #     dirname += timestamp
    #     if not os.path.exists(dirname):
    #         os.mkdir(dirname)
    #     # else:
    #     #    raise Exception("Directory already there????")
    #     return dirname
    #
    # def slugify(self, value):
    #     """
    #     Normalizes string, converts to lowercase, removes non-alpha characters,
    #     and converts spaces to hyphens.
    #     """
    #     import unicodedata, re
    #     value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    #     value = unicode(re.sub('[^\w\s-]', '', value).strip())
    #     value = unicode(re.sub('[-\s]+', '-', value))
    #     return value
