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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qgis.gui import QgsMessageBar
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsFields, QgsField, QgsFeature
from jrodos_dialog import JRodosDialog
from glob import glob
import os.path, tempfile, time
from datetime import date, time, datetime, timedelta
import urllib2

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

        # Create the dialog (after translation) and keep reference
        self.dlg = JRodosDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&JRodos')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'JRodos')
        self.toolbar.setObjectName(u'JRodos')

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

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # TESTING getting data and saving to shp zips
            #self.get_data_and_show()

            # TESTING loading shp zips, merging to one memory layer adding timestamp
            self.load_shapes("/tmp/wps-test-1_Ground-contamination-drywet_Cs-137_20160419095759")


    def msg(self, parent=None, msg=""):
        if parent is None:
            parent = self.iface.mainWindow()
        QMessageBox.warning(parent, self.MSG_BOX_TITLE, "%s" % msg, QMessageBox.Ok, QMessageBox.Ok)

    def get_data_and_show(self):

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

        jrodos_project="'wps-test-1'"
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        #jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
        jrodos_format="application/zip"
        # format="text/xml; subtype=wfs-collection/1.0"
        jrodos_timesteps=24 # column
        jrodos_vertical=0
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        for column in range(0, jrodos_timesteps+1):

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
            # using 'with open', then file is explicitly closed
            with open(
                    self.path_to_filename(jrodos_project, jrodos_path, column, jrodos_vertical, timestamp), 'wb') as f:
                        #while True:
                            #chunk = response.read(CHUNK)
                        for chunk in iter(lambda: response.read(CHUNK), ''):
                            if not chunk: break
                            f.write(chunk)
            # TODO progress bar?
            # self.iface.messageBar().pushSuccess('Busy', 'Receiving data, and saving to zip....')

        self.iface.messageBar().pushSuccess('OK', 'Ready receiving, All saved as zip....')

        # now, open all shapefiles one by one, s from 0 till x
        # starting with a startdate 20160101000000 t
        # add an attribute 'time' and set it to t+s

    def load_shapes(self, shp_path):

        # give the memory layer the same CRS as the source layer
        vector_layer = QgsVectorLayer(
            "Polygon?crs=epsg:32631&field=Cell:integer&field=Value:double&field=Datetime:string(20)" +
            "&index=yes",
            "TEST",
            "memory")
        # use a saved style as style
        # vector_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'sectorplot.qml'))
        # add empty layer to the map
        QgsMapLayerRegistry.instance().addMapLayer(vector_layer)

        shps = glob(os.path.join(shp_path, "*.zip"))
        #print "Loading shapes from %s" % os.path.join(shp_path, "*.zip")

        # trivial startdate/time: 1/1/2016 0:0
        timestamp = datetime.combine(date(2016, 1, 1), time(0 ,0))
        for shp in shps:
            (shpdir, shpfile) = os.path.split(shp)
            #self.iface.addVectorLayer(shp, shpfile, 'ogr')
            #vlayer = QgsVectorLayer("/tmp/wps-test-1_Ground-contamination-drywet_Cs-137_20160419095759/0_0.zip", shpfile, "ogr")
            vlayer = QgsVectorLayer(shp, shpfile, "ogr")
            if not vlayer.isValid():
                self.msg(None, "Layer failed to load!")
            else:
                #self.msg(None, "Layer loaded %s" % shp)

                # FeatureList
                #vlayer.selectAll()
                #features = vlayer.selectedFeatures()
                #self.msg(None, "len(features) %s" % len(features))

                features = vlayer.getFeatures()
                flist = []
                step = int(shpfile.split('_')[0])
                tstamp = timestamp + timedelta(hours=step)
                tstamp = tstamp.strftime("%Y-%m-%d %H:%M")
                for feature in features:
                    # only features with Value > 0, to speed up QGIS
                    if feature.attribute('Value') > 0:
                        attrs = QgsFields()
                        attrs = feature.fields()
                        attrs.append(QgsField("Datetime"))
                        f = QgsFeature(attrs)
                        f.setAttributes([feature.attribute('Cell'), feature.attribute('Value'), tstamp])
                        f.setGeometry(feature.geometry())
                        flist.append(f)

            vector_layer.dataProvider().addFeatures(flist)
            vector_layer.loadNamedStyle(os.path.join(shpdir, 'groundcontaminationdrywet.qml'))  # sld not working!!!
            vector_layer.updateFields()
            vector_layer.updateExtents()
            self.iface.mapCanvas().refresh()

    def path_to_filename(self, project, path, column, vertical, timestamp):
        # path.split('=;=')[-2]+'_'+path.split('=;=')[-1]
        dirname = tempfile.gettempdir() + os.sep
        dirname += self.slugify(unicode(project)) + '_'
        dirname += self.slugify(unicode(path.split('=;=')[-2])) + '_'
        dirname += self.slugify(unicode(path.split('=;=')[-1])) + '_'
        dirname += timestamp
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        #else:
        #    raise Exception("Directory already there????")
        filename = dirname + '/' + unicode(column) + '_' + unicode(vertical) + '.zip'
        return filename

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


