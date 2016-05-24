from PyQt4.QtCore import QObject, pyqtSignal, QSettings, QThread, QDate, QTime, QDateTime
from PyQt4.QtGui import QApplication
from utils import Utils
import traceback, logging
import urllib, urllib2, sys, shutil, re, signal
import os.path
from datetime import date, time, datetime, timedelta


class WfsSettings:
    def __init__(self):
        self.url = ''
        self.output_dir = None
        # check and set defaults
        self.page_size = 10000
        self.start_datetime = ''
        self.end_datetime = ''
        self.quantity = ''
        self.substance = ''
        self.endminusstart = ''
        self.bbox = '50,0,60,20'

    def __str__(self):
        return """WFS settings:\n WFS url: {}\n outputdir: {}\n page_size: {}\n starttime: {}\n endtime: {}\n endminusstart: {}\n quantity: {}\n substance: {}\n bbox: {}
        """.format(self.url, self.output_dir, self.page_size, self.start_datetime, self.end_datetime, self.endminusstart, self.quantity, self.substance, self.bbox)


class WfsDataWorker(QObject):
    '''
    Base Worker class to get JRodos data from service
    '''
    def __init__(self, settings):
        # init superclass
        QObject.__init__(self)

        if isinstance(settings, WfsSettings) is False:
            raise TypeError('Worker expected a WfsSettings, got a {} instead'.format(type(settings)))

        self.settings = settings

    def run(self):
        ret = None
        try:
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

            page_size = self.settings.page_size
            total_count = 0
            step_count = 1
            file_count = 0

            wfs_settings_file = self.settings.output_dir + '/wfs_settings.txt'
            with open(wfs_settings_file, 'wb') as f:
                f.write(unicode(self.settings))

            while total_count % page_size == 0 and step_count > 0: # and feature_count <= STOP_AT:
            #for i in range(0, 10):
                step_count = 0
                file_count += 1

                wfs_url = self.settings.url
                params = {}
                params['Count'] = page_size
                params['startIndex'] = total_count
                # cql_filter = "bbox(location,50,0,60,20) and time > '2016-04-25T08:00:00.000+00:00' and time < '2016-04-26T08:00:00.000+00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
                cql_filter = "bbox(location,{bbox}) and time > '{start_datetime}' and time < '{end_datetime}' and endTime-startTime={endminusstart} and quantity='{quantity}' and substance='{substance}'".format(
                    bbox=self.settings.bbox,
                    start_datetime=self.settings.start_datetime,
                    end_datetime=self.settings.end_datetime,
                    quantity=self.settings.quantity,
                    substance=self.settings.substance,
                    endminusstart=self.settings.endminusstart
                )
                # TODO development
                # cql_filter = "bbox(location,50,0,60,20) and time > '2016-04-25T08:00:00.000+00:00' and time < '2016-04-26T08:00:00.000+00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
                # cql_filter = "bbox(location,50,0,60,20) and time > '2016-04-25T08:02:02.000+00:00' and time < '2016-04-25T10:00:00.000+00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
                params[
                    'CQL_FILTER'] = cql_filter
                params['typeName'] = "radiation.measurements:MEASUREMENT"
                params['version'] = '2.0.0'
                params['service'] = 'WFS'
                params['request'] = 'GetFeature'
                # pity, below not working :-(
                # params['resultType'] = 'hits'

                try:

                    data = urllib.urlencode(params)
                    request = urllib2.Request(wfs_url, data)
                    logging.debug('Firing WFS request: %s' % request.get_full_url()+request.get_data())
                    response = urllib2.urlopen(request)
                    CHUNK = 16 * 1024
                    filename = self.settings.output_dir + '/data' + unicode(file_count) + '.gml'

                    with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed
                        found = False
                        for chunk in iter(lambda: response.read(CHUNK), ''):
                            if not chunk:
                                break
                            if not found:
                                finds = re.findall('numberReturned="([0-9.]+)"', chunk)
                                if len(finds) > 0:
                                    step_count = int(finds[0])
                                    total_count += step_count
                                    found = True
                            f.write(chunk)
                except:
                    pass

                # note: if copying with shutil.copy2 or shutil.copy, QGIS only reads gml when you touch gfs file???
                shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schemas', 'measurements.gfs'),
                                os.path.join(self.settings.output_dir, 'data' + unicode(file_count) + '.gfs'))
                # IMPORTANT !!!
                #  OGR only uses the gfs file if the modification time is >= modification time of gml file !!!
                #  set it to NOW with os.utime !!!
                os.utime(os.path.join(self.settings.output_dir, 'data' + unicode(file_count) + '.gfs'), None)
                # fake progress because we do not know actual total count:
                # we start at 1/2 then 2/3, 3/4, 4/5 etc
                self.progress.emit(file_count/(1.0 + file_count))

                #break      #DEVELOPMENT
        except Exception, e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())

        ret = {'result': 'OK', 'output_dir': self.settings.output_dir}
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    progress = pyqtSignal(float)



class WpsSettings:
    def __init__(self):
        self.url = 'http://localhost:8080/geoserver/wps'
        self.user = 'admin'
        self.password = 'geoserver'
        self.jrodos_project = "'wps-test-3'"
        self.jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        self.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
        self.jrodos_model_time = 24 # hours now fixed 24 hrs
        self.jrodos_model_step = 60 # minutes 10, 30, 60
        # self.jrodos_columns # now calculated!!
        self.jrodos_verticals = 0  # z / layers
        self.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))
        self.jrodos_datetime_format = "yyyy-MM-ddTHH:mm:ss.000 00:00"  # '2016-04-25T08:00:00.000+00:00'
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    def output_dir(self):
        return Utils.jrodos_dirname(self.jrodos_project, self.jrodos_path, self.timestamp)

    def jrodos_columns(self):
        return (int(self.jrodos_model_time) * 60) / int(self.jrodos_model_step)  # modeltime*60 / timesteps

    def __str__(self):
        return """WPS settings:\n WPS url: {}\n outputdir: {}\n user: {}\n password: {}\n project: {}\n path: {}\n format: {}\n model(hrs): {}\n step(min): {}\n columns: {}\n verticals: {}\n format: {}\n start : {}
        """.format(self.url, self.output_dir(), self.user, self.password, self.jrodos_project, self.jrodos_path,
                   self.jrodos_format, self.jrodos_model_time, self.jrodos_model_step, self.jrodos_columns(), self.jrodos_verticals, self.jrodos_datetime_format,
                   self.jrodos_datetime_start.toString(self.jrodos_datetime_format))

class WpsDataWorker(QObject):
    '''
    Base Worker class to get JRodos data from service
    '''

    def __init__(self, settings):
        # init superclass
        QObject.__init__(self)

        if isinstance(settings, WpsSettings) is False:
            raise TypeError('Worker expected a WpsSettings, got a {} instead'.format(type(settings)))

        self.settings = settings

    def run(self):

        ret = None
        try:

            # get_data_and_show(self, output_dir, jrodos_project, jrodos_path, jrodos_column, jrodos_vertical, jrodos_format):

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
            # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
            # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
            # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
            # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
            # jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
            #        jrodos_path="'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
            #        jrodos_format="application/zip"
            # format="text/xml; subtype=wfs-collection/1.0"
            #        jrodos_timesteps=24 # column
            #        jrodos_vertical=0
            #        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            #        result_dir = self.path_to_dirname(jrodos_project, jrodos_path, timestamp)

            wps_settings_file = self.settings.output_dir() + '/wps_settings.txt'

            with open(wps_settings_file, 'wb') as f:
                f.write(unicode(self.settings))

            for column in range(0, self.settings.jrodos_columns()):
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
                post_data = request.format(project=self.settings.jrodos_project,
                                           path=self.settings.jrodos_path,
                                           format=self.settings.jrodos_format,
                                           column=unicode(column),
                                           vertical=unicode(self.settings.jrodos_verticals))
                url = self.settings.url #'http://localhost:8080/geoserver/wps'
                user = self.settings.user
                password = self.settings.password
                password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(None, url, user, password)
                handler = urllib2.HTTPBasicAuthHandler(password_mgr)
                opener = urllib2.build_opener(handler)

                request = urllib2.Request(url=url, data=post_data, headers={'Content-Type': 'text/xml'})
                request.get_method = lambda: 'POST'
                logging.debug('Firing WPS request')
                response = opener.open(request)
                CHUNK = 16 * 1024
                filename = self.settings.output_dir() + '/' + unicode(column) + '_' + unicode(self.settings.jrodos_verticals) + '.zip'
                # using 'with open', then file is explicitly closed
                with open(filename, 'wb') as f:
                    for chunk in iter(lambda: response.read(CHUNK), ''):
                        if not chunk: break
                        f.write(chunk)
                # fake progress because we do not know actual total count:
                # we start at 1/2 then 2/3, 3/4, 4/5 etc
                #self.progress.emit(column / (1.0 + column))
                self.progress.emit((1.0 + column) / self.settings.jrodos_columns())

        except Exception, e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())

        ret = {'result': 'OK', 'output_dir': self.settings.output_dir()}
        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    progress = pyqtSignal(float)


# https://pymotw.com/2/threading/
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(threadName)-10s) %(message)s',)


def test():

    def error(err):
        print err

    def wfs_finished(ret):
        print('wfs finished: {}'.format(ret))
        wfs_thread.quit()
        if both_finished:
            app.quit()

    def wps_finished(ret):
        print('wps finished: {}'.format(ret))
        wps_thread.quit()
        if both_finished:
            app.quit()

    def both_finished():
        return wps_thread.isFinished() and wfs_thread.isFinished()

    def wps_progress(part):
        print('wps progress: {}'.format(part))

    def wfs_progress(part):
        print('wfs progress: {}'.format(part))

    app = QApplication(sys.argv)

    wps_settings = WpsSettings()
    wps_settings.url = 'http://localhost:8080/geoserver/wps'
    # jrodos_path=  "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
    # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
    # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
    # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
    # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
    # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    wps_settings.jrodos_project = "'wps-test-3'"
    wps_settings.jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    wps_settings.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
    wps_settings.jrodos_model_time = 24
    wps_settings.jrodos_model_step = 60
    wps_settings.jrodos_verticals = 0  # z / layers
    wps_settings.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))

    wps_thread = QThread()
    w2 = WpsDataWorker(wps_settings)
    w2.moveToThread(wps_thread)
    w2.finished.connect(wps_finished)
    w2.error.connect(error)
    w2.progress.connect(wps_progress)
    wps_thread.started.connect(w2.run)

    print wps_settings
    wps_thread.start()

    wfs_settings = WfsSettings()
    wfs_settings.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
    # we have always an wps_settings.output_dir here:
    wfs_settings.output_dir = wps_settings.output_dir()
    wfs_settings.page_size = 10000
    wfs_settings.start_datetime = '2016-04-25T08:00:00.000+00:00'
    wfs_settings.end_datetime = '2016-04-26T08:00:00.000+00:00'
    #wfs_settings.start_datetime = '2016-05-16T06:52:00.000+00:00'
    #wfs_settings.end_datetime = '2016-05-17T06:52:00.000+00:00'
    wfs_settings.endminusstart =  '3600'
    wfs_settings.quantity = 'T-GAMMA'
    wfs_settings.substance = 'A5'
    wfs_settings.bbox = '55,5,60,15'

    wfs_thread = QThread()
    w = WfsDataWorker(wfs_settings)
    w.moveToThread(wfs_thread)
    w.finished.connect(wfs_finished)
    w.error.connect(error)
    w.progress.connect(wfs_progress)
    wfs_thread.started.connect(w.run)

    print wfs_settings
    wfs_thread.start()

    # NOT WORKING in parallel neither
    # combined_thread = QThread()
    # w.moveToThread(combined_thread)
    # w2.moveToThread(combined_thread)
    # combined_thread.started.connect(w2.run)
    # combined_thread.started.connect(w.run)
    # combined_thread.start()

    sys.exit(app.exec_())


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    test()
