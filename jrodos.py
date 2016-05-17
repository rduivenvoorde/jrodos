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
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsFields, QgsField, QgsFeature, QgsCoordinateReferenceSystem
from jrodos_dialog import JRodosDialog
from jrodos_measurements_dialog import JRodosMeasurementsDialog
from data_worker import WfsSettings, WfsDataWorker
from glob import glob
import os.path, tempfile, time
from datetime import date, time, datetime, timedelta
import urllib, urllib2, shutil

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

        self.JRODOS_MODELS = ['wps-test-1', 'wps-test-2', 'wps-test-3']

        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'"  # 24
        self.JRODOS_PATHS = [
            "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'",
            "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'",
            "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        ]
        self.JRODOS_STEPS = ['8', '24', '48', '72']
        # Create the dialog (after translation) and keep reference
        self.dlg = JRodosDialog()
        # add current models to dropdown
        self.dlg.combo_model.addItems(self.JRODOS_MODELS)
        # self.dlg.combo_model.currentText()
        # add current paths to dropdown
        # TODO from yaml or settings?
        self.dlg.combo_path.addItems(self.JRODOS_PATHS)
        self.dlg.combo_steps.addItems(self.JRODOS_STEPS)

        self.measurements_dlg = JRodosMeasurementsDialog()
        self.MEASUREMENTS_ENDMINUSTART = ['600', '3600']
        self.measurements_dlg.combo_endminusstart.addItems(self.MEASUREMENTS_ENDMINUSTART)
        self.measurements_dlg.combo_endminusstart.setCurrentIndex(1)

        now = QDateTime.currentDateTime()
        # TODO dev
        now = QDateTime(QDate(2016, 04, 24), QTime(6, 0))
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

        self.progress = None

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
        # self.msg(None, result)
        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushSuccess("Measurements", "Retrieved all data...")
        self.progress = None
        # Load the received gml files
        # TODO: determine qml file based on something coming from the settings/result object
        self.load_measurements(result['output_dir'], 'measurements_0_180_stddev.qml')

    def wfs_progress(self, part):
        self.progress.setValue(part * 100)

    def wfs_error(self, err):
        self.msg(None, err)
        self.progress = None

    def run(self):

        self.dlg.show()
        result = self.dlg.exec_()
        if result:  # OK was pressed
            try:

                jrodos_project = "'wps-test-3'"
                # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
                # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
                # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
                # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
                # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
                jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
                jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
                jrodos_column = 2  # columns / timesteps
                jrodos_vertical = 0  # z / layers

                # create an temp working/output directory
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_dir = self.path_to_dirname(jrodos_project, jrodos_path, timestamp)

                #get data from wps and save to shp zips
                self.get_data_and_show(output_dir, jrodos_project, jrodos_path, jrodos_column, jrodos_vertical, jrodos_format)
                # load shp zips, merging to one memory layer adding timestamp
                # self.load_shapes(output_dir, 'groundcontaminationdrywet.qml')
                self.load_shapes(output_dir, 'totalpotentialdoseeffective.qml')

                # load metingen / measurements from same period via wfs getfeature paging
                #self.load_measurements(output_dir, 'totalpotentialdoseeffective.qml')

            except Exception as e:
                self.msg(None, unicode(e))


        # self.measurements_dlg.show()
        # result = self.measurements_dlg.exec_()
        # if result: # OK was pressed
        #     try:
        #
        #         wfs_settings = WfsSettings()
        #         endminusstart = self.measurements_dlg.combo_endminusstart.itemText(self.measurements_dlg.combo_endminusstart.currentIndex())
        #
        #         date_format = "yyyy-MM-ddTHH:mm:ss.000 00:00"  # '2016-04-25T08:00:00.000+00:00'
        #         start_date = self.measurements_dlg.dateTime_start.dateTime()
        #         # make it UTC
        #         start_date = start_date.toUTC()
        #         end_date = self.measurements_dlg.dateTime_end.dateTime()
        #         # make it UTC
        #         end_date = end_date.toUTC()
        #         quantity = self.measurements_dlg.le_quantity.text()
        #         substance = self.measurements_dlg.le_substance.text()
        #
        #         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        #
        #         # TODO these come from dialog later
        #         jrodos_project = "'wps-test-3'"
        #         jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        #
        #         output_dir = self.path_to_dirname(jrodos_project, jrodos_path, timestamp)
        #
        #         wfs_settings = WfsSettings()
        #         # TODO make these come from config
        #         wfs_settings.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
        #         wfs_settings.output_dir = output_dir
        #         wfs_settings.page_size = 10000
        #         # end todo
        #         wfs_settings.start_datetime = start_date.toString(date_format)
        #         wfs_settings.end_datetime = end_date.toString(date_format)
        #         wfs_settings.endminusstart = endminusstart
        #         wfs_settings.quantity = quantity
        #         wfs_settings.substance = substance
        #
        #         self.msg(None, unicode(wfs_settings))
        #
        #         wfs_thread = QThread(self.iface)
        #         wfs_worker = WfsDataWorker(wfs_settings)
        #         wfs_worker.moveToThread(wfs_thread)
        #         wfs_worker.finished.connect(self.wfs_finished)
        #         wfs_worker.error.connect(self.wfs_error)
        #         wfs_worker.progress.connect(self.wfs_progress)
        #         wfs_thread.started.connect(wfs_worker.run)
        #
        #         if self.progress == None:
        #             self.progress_message_bar = self.iface.messageBar().createMessage("Retrieving data from server ...")
        #             self.progress = QProgressBar()
        #             self.progress.setMaximum(100)
        #             self.progress.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        #             self.progress_message_bar.layout().addWidget(self.progress)
        #             self.iface.messageBar().pushWidget(self.progress_message_bar, self.iface.messageBar().INFO)
        #             self.progress.setValue(25)
        #
        #         # wps_thread.start()
        #         wfs_thread.start()
        #
        #         # NOTE: YOU REALLY NEED TO DO THIS! WITHOUT THE RUN WILL NOT BE STARTED!
        #         self.wfs_thread = wfs_thread
        #         self.wfs_worker = wfs_worker
        #
        #     except Exception as e:
        #         self.msg(None, unicode(e))

    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_BOX_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def get_data_and_show(self, output_dir, jrodos_project, jrodos_path, jrodos_column, jrodos_vertical, jrodos_format):

        # http://stackoverflow.com/questions/1517616/stream-large-binary-files-with-urllib2-to-file
        #    response = urllib2.urlopen(url)
        #    CHUNK = 16 * 1024
        #    with open(file, 'wb') as f:
        #        while True:
        #        for chunk in iter(lambda: f.read(CHUNK), ''):
        #            chunk = response.read(CHUNK)
        #            if not chunk: break
        #            f.write(chunk)

        #    def doRequest(self, url, data=None, headers=None, method='POST'):
        #        # print 'url:    ', url
        #        # print 'data:   ', data
        #        # print 'headers:', headers
        #        req = urllib2.Request(url=url, data=data, headers=headers)
        #        req.get_method = lambda: method
        #        f = self.opener.open(req)
        #        # print f.read()
        #        return f.read()

        # project: "'wps-test-1'" "'wps-test-2'"
        # format: "text/xml; subtype=wfs-collection/1.0" "application/zip"
        # path: "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"
        # path: "'Model data =;=Output =;=Prognostic Results =;=Activity concentrations =;=Air concentration, time integrated near ground surface =;=I - 135'"

#        jrodos_project="'wps-test-3'"
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
#        jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
#        jrodos_format="application/zip"
        # format="text/xml; subtype=wfs-collection/1.0"
#        jrodos_timesteps=24 # column
#        jrodos_vertical=0
#        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#        result_dir = self.path_to_dirname(jrodos_project, jrodos_path, timestamp)

        for column in range(0, jrodos_column+1):
            request = """<?xml version="1.0" encoding="UTF-8"?>
            <wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs"
              xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc"
              xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink"
              xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
              <ows:Identifier>gs:JRodosWPS</ows:Identifier>
              <wps:DataInputs>
                <wps:Input>
                  <ows:Identifier>taskArg</ows:Identifier>
                  <wps:Data>
                    <wps:LiteralData>project="{project}"</wps:LiteralData>
                  </wps:Data>
                </wps:Input>
                <wps:Input>
                  <ows:Identifier>dataitem</ows:Identifier>
                  <wps:Data>
                    <wps:LiteralData>path="{path}"</wps:LiteralData>
                  </wps:Data>
                </wps:Input>
                <wps:Input>
                  <ows:Identifier>column</ows:Identifier>
                  <wps:Data>
                    <wps:LiteralData>{column}</wps:LiteralData>
                  </wps:Data>
                </wps:Input>
                <wps:Input>
                  <ows:Identifier>vertical</ows:Identifier>
                  <wps:Data>
                    <wps:LiteralData>{vertical}</wps:LiteralData>
                  </wps:Data>
                </wps:Input>
              </wps:DataInputs>
              <wps:ResponseForm>
                <wps:RawDataOutput mimeType="{format}">
                  <ows:Identifier>result</ows:Identifier>
                </wps:RawDataOutput>
              </wps:ResponseForm>
            </wps:Execute>
            """
            post_data = request.format(project=jrodos_project,
                                       path=jrodos_path,
                                       format=jrodos_format,
                                       column=unicode(column),
                                       vertical=unicode(jrodos_vertical))
            url = 'http://localhost:8080/geoserver/wps'
            user = 'admin'
            password = 'geoserver'
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, url, user, password)
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            opener = urllib2.build_opener(handler)

            request = urllib2.Request(url=url, data=post_data, headers={'Content-Type': 'text/xml'})
            request.get_method = lambda: 'POST'
            response = opener.open(request)
            CHUNK = 16 * 1024
            filename = output_dir + '/' + unicode(column) + '_' + unicode(jrodos_vertical) + '.zip'
            # using 'with open', then file is explicitly closed
            with open(filename, 'wb') as f:
                        for chunk in iter(lambda: response.read(CHUNK), ''):
                            if not chunk: break
                            f.write(chunk)
        self.iface.messageBar().pushSuccess('OK', 'Ready receiving, All saved as zip....')

    # now, open all shapefiles one by one, s from 0 till x
    # starting with a startdate 20160101000000 t
    # add an attribute 'time' and set it to t+s
    def load_shapes(self, shape_dir, style_file):

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
        # trivial startdate/time: 1/1/2016 0:0
        timestamp = datetime.combine(date(2016, 4, 25), time(8 ,0))
        for shp in shps:
            (shpdir, shpfile) = os.path.split(shp)
            vlayer = QgsVectorLayer(shp, shpfile, "ogr")
            if not vlayer.isValid():
                self.msg(None, "Layer failed to load!")
            else:
                #self.msg(None, "Layer loaded %s" % shp)
                if layer_crs ==None:
                    # find out source crs of shp and set our memory layer to the same crs
                    layer_crs = vlayer.crs()
                    vector_layer.setCrs(layer_crs)

                features = vlayer.getFeatures()
                flist = []
                step = int(shpfile.split('_')[0])
                tstamp = timestamp + timedelta(hours=step)
                tstamp = tstamp.strftime("%Y-%m-%d %H:%M")
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
        temp_layer = None
        flist = []

        gmls = glob(os.path.join(output_dir, "*.gml"))
        for gml_file in gmls:
            gml_layer = QgsVectorLayer(gml_file, 'only for loading', 'ogr')
            if not gml_layer.isValid():
                self.msg(None, 'GML layer NOT VALID!')
                return
            # IF there is no memory layer yet: create it
            if temp_layer is None:
                temp_layer = QgsVectorLayer("point", "Measurements", "memory")

                #fields = gml_layer.fields()
                #self.msg(None, 'temp_layer.fields() %s' % temp_layer.fields())
                #for field in fields:
                #    temp_layer.addAttribute(field)
                #    temp_layer.commitChanges()
                #    temp_layer.updateFields()  # tell the vector layer to fetch changes from the provider

                # add fields
                pr = temp_layer.dataProvider()
                pr.addAttributes([QgsField("gml_id", QVariant.String),
                                  QgsField("startTime", QVariant.String),
                                  QgsField("endTime", QVariant.String),
                                  QgsField("quantity", QVariant.String),
                                  QgsField("substance", QVariant.String),
                                  QgsField("unit", QVariant.String),
                                  QgsField("value", QVariant.Double),
                                  QgsField("time", QVariant.String),
                                  QgsField("info", QVariant.String),
                                  QgsField("device", QVariant.String)])
                temp_layer.updateFields()
                QgsMapLayerRegistry.instance().addMapLayer(temp_layer)

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
                    f = QgsFeature(fields)
                    if feature.geometry() is not None:
                        f.setAttributes(feature.attributes())
                        f.setGeometry(feature.geometry())
                        flist.append(f)
                        if len(flist)>1000:
                            temp_layer.dataProvider().addFeatures(flist)
                            flist = []
                        #print "%s            gml_id: %s - %s" % (feature_count, f.geometry().exportToWkt(), f.attributes())
                    else:
                        print "%s            GEEN GEOMETRIE !!! gml_id: %s " % (feature_count, f.attributes())
                        #self.msg(None, "gmlid: %s" % (f['gml_id']))
                        #print "%s gml_id: %s" % (feature_count, f['gml_id'])
                        #break

            temp_layer.dataProvider().addFeatures(flist)
            #temp_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!

            temp_layer.updateFields()
            temp_layer.updateExtents()

            self.iface.mapCanvas().refresh()

            #self.msg(None, '%s features loaded, written in: %s' %(feature_count, file_count))
            #break

        temp_layer.loadNamedStyle(
            os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!

        self.iface.messageBar().pushSuccess('OK', 'Ready receiving measurements, feature count: ' + unicode(feature_count))

        # change back to default action of asking for crs or whatever the old behaviour was!
        s.setValue("/Projections/defaultBehaviour", oldCrsBehaviour)
        s.setValue("/Projections/layerDefaultCrs", oldCrs)

    def path_to_dirname(self, project, path, timestamp):
        # path.split('=;=')[-2]+'_'+path.split('=;=')[-1]
        dirname = tempfile.gettempdir() + os.sep
        dirname += self.slugify(unicode(project)) + '_'
        dirname += self.slugify(unicode(path.split('=;=')[-2])) + '_'
        dirname += self.slugify(unicode(path.split('=;=')[-1])) + '_'
        dirname += timestamp
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        # else:
        #    raise Exception("Directory already there????")
        return dirname

    def slugify(self, value):
        """
        Normalizes string, converts to lowercase, removes non-alpha characters,
        and converts spaces to hyphens.
        """
        import unicodedata, re
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        value = unicode(re.sub('[^\w\s-]', '', value).strip())
        value = unicode(re.sub('[-\s]+', '-', value))
        return value




def old_load_measurements(self, shape_dir, style_file):
    """
    Fire a wfs request
    :param shape_dir:
    :param style_file:
    :return:
    """

    # "http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?Count=10000&startIndex=40000&CQL_FILTER=bbox(location%2C+50%2C+0%2C+60%2C+20)+and+time+<+'2016-04-26T08%3A00%3A00.000+00%3A00'+and+time+>+'2016-04-25T08%3A00%3A00.000+00%3A00'+and+endTime-startTime%3D3600+and+quantity%3D'T-GAMMA'+and+substance+%3D+'A5'&typeName=radiation.measurements%3AMEASUREMENT&version=2.0.0&service=WFS&request=GetFeature"
    # "http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?Count=10000&startIndex=40000&CQL_FILTER=bbox(location%2C+50%2C+0%2C+60%2C+20)+and+time+<+'2016-04-26T08%3A00%3A00.000+00%3A00'+and+time+>+'2016-04-25T08%3A00%3A00.000+00%3A00'+and+endTime-startTime%3D3600+and+quantity%3D'T-GAMMA'+and+substance+%3D+'A5'&typeName=radiation.measurements%3AMEASUREMENT&version=2.0.0&service=WFS&request=GetFeature&resultType=hits"

    # we do NOT want the default behaviour: prompting for a crs
    # we want to set it to epsg:4326, see
    # http://gis.stackexchange.com/questions/27745/how-can-i-specify-the-crs-of-a-raster-layer-in-pyqgis
    s = QSettings()
    oldCrsBehaviour = s.value("/Projections/defaultBehaviour", "useGlobal")
    s.setValue("/Projections/defaultBehaviour", "useGlobal")
    oldCrs = s.value("/Projections/layerDefaultCrs", "EPSG:4326")
    s.setValue("/Projections/layerDefaultCrs", "EPSG:4326")

    STEPSIZE = 10000
    STOP_AT = 10000000
    feature_count = 0
    step_count = STEPSIZE
    file_count = 0
    temp_layer = None

    while feature_count % STEPSIZE == 0 and step_count > 0 and feature_count <= STOP_AT:
        step_count = 0
        file_count += 1
        flist = []

        wfs_url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
        params = {}
        params['Count'] = STEPSIZE
        params['startIndex'] = feature_count
        # TODO make bbox and endTime-startTime dynamic
        params[
            'CQL_FILTER'] = "bbox(location,50,0,60,20) and time > '2016-04-25T08:00:00.000+00:00' and time < '2016-04-26T08:00:00.000+00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
        params['typeName'] = "radiation.measurements:MEASUREMENT"
        params['version'] = '2.0.0'
        params['service'] = 'WFS'
        params['request'] = 'GetFeature'
        # pity, below not working :-(
        # params['resultType'] = 'hits'

        data = urllib.urlencode(params)
        request = urllib2.Request(wfs_url, data)

        response = urllib2.urlopen(request)
        CHUNK = 16 * 1024
        filename = shape_dir + '/data' + unicode(file_count) + '.gml'

        with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed
            for chunk in iter(lambda: response.read(CHUNK), ''):
                if not chunk: break
                f.write(chunk)
        f.close()

        # note: if copying with shutil.copy2 or shutil.copy, QGIS only reads gml when you touch gfs file???
        shutil.copyfile(os.path.join(self.plugin_dir, 'schemas', 'measurements.gfs'),
                        os.path.join(shape_dir, 'data' + unicode(file_count) + '.gfs'))
        # IMPORTANT !!!
        #  OGR only uses the gfs file if the modification time is >= modification time of gml file !!!
        #  set it to NOW with os.utime !!!
        os.utime(os.path.join(shape_dir, 'data' + unicode(file_count) + '.gfs'), None)

        gml_layer = QgsVectorLayer(filename, 'only loading', 'ogr')
        if not gml_layer.isValid():
            self.msg(None, 'GML layer NOT VALID!')
            return

        # QgsMapLayerRegistry.instance().addMapLayer(gml_layer)
        # IF there is no memory layer yet: create it
        if temp_layer is None:
            temp_layer = QgsVectorLayer("point", "Measurements", "memory")

            # fields = gml_layer.fields()
            # self.msg(None, 'temp_layer.fields() %s' % temp_layer.fields())
            # for field in fields:
            #    temp_layer.addAttribute(field)
            #    temp_layer.commitChanges()
            #    temp_layer.updateFields()  # tell the vector layer to fetch changes from the provider

            # add fields
            pr = temp_layer.dataProvider()
            pr.addAttributes([QgsField("gml_id", QVariant.String),
                              QgsField("startTime", QVariant.String),
                              QgsField("endTime", QVariant.String),
                              QgsField("quantity", QVariant.String),
                              QgsField("substance", QVariant.String),
                              QgsField("unit", QVariant.String),
                              QgsField("value", QVariant.Double),
                              QgsField("time", QVariant.String),
                              QgsField("info", QVariant.String),
                              QgsField("device", QVariant.String)])
            temp_layer.updateFields()
            QgsMapLayerRegistry.instance().addMapLayer(temp_layer)

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
                f = QgsFeature(fields)
                if feature.geometry() is not None:
                    f.setAttributes(feature.attributes())
                    f.setGeometry(feature.geometry())
                    flist.append(f)
                    if len(flist) > 1000:
                        temp_layer.dataProvider().addFeatures(flist)
                        flist = []
                        # print "%s            gml_id: %s - %s" % (feature_count, f.geometry().exportToWkt(), f.attributes())
                else:
                    print "%s            GEEN GEOMETRIE !!! gml_id: %s " % (feature_count, f.attributes())
                    # self.msg(None, "gmlid: %s" % (f['gml_id']))
                    #    print "%s gml_id: %s" % (feature_count, f['gml_id'])
                    # break

        temp_layer.dataProvider().addFeatures(flist)
        # temp_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'styles', style_file)) # qml!! sld is not working!!!

        temp_layer.updateFields()
        temp_layer.updateExtents()

        self.iface.mapCanvas().refresh()

        # self.msg(None, '%s features loaded, written in: %s' %(feature_count, file_count))
        # break

    temp_layer.loadNamedStyle(
        os.path.join(os.path.dirname(__file__), 'styles', style_file))  # qml!! sld is not working!!!

    self.iface.messageBar().pushSuccess('OK', 'Ready receiving measurements, feature count: ' + unicode(
        feature_count))

    # change back to default action of asking for crs or whatever the old behaviour was!
    s.setValue("/Projections/defaultBehaviour", oldCrsBehaviour)
    s.setValue("/Projections/layerDefaultCrs", oldCrs)

