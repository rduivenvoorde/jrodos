from provider_base import ProviderConfig, ProviderBase
import os
import shutil
import re
import urllib
import urllib2
import logging


class CalnetMeasurementsConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
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
        self.date_time_format = 'yyyy-MM-ddTHH:mm:ss.000 00:00'  # '2016-04-25T08:00:00.000+00:00'
        self.date_time_format_short = 'MM/dd HH:mm'  # '17/6 23:01'

    def __str__(self):
        return """CalnetMeasurementsConfig:\n WFS url: {}\n outputdir: {}\n page_size: {}\n starttime: {}\n endtime: {}\n endminusstart: {}\n quantity: {}\n substance: {}\n bbox: {}
            """.format(self.url, self.output_dir, self.page_size, self.start_datetime, self.end_datetime,
                       self.endminusstart, self.quantity, self.substance, self.bbox)


class CalnetMeasurementsProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)


    def _data_retrieved(self, reply):
        self.data = {'result': 'OK', 'output_dir':self.config.output_dir}
        self.ready = True
        self.finished.emit(self.data)

    def get_data(self):

        # request = QUrl(self.config.url)
        # reply = self.network_manager.get(QNetworkRequest(request))
        # reply.finished.connect(partial(self._data_retrieved, reply))
        # # this part is needed to be sure we do not return immidiatly
        # while not reply.isFinished():
        #     QCoreApplication.processEvents()

        page_size = self.config.page_size
        total_count = 0
        step_count = 1
        file_count = 0

        wfs_settings_file = self.config.output_dir + '/calnet_measurements__wfs_config.txt'
        with open(wfs_settings_file, 'wb') as f:
            f.write(unicode(self.config))

        while total_count % page_size == 0 and step_count > 0:  # and feature_count <= STOP_AT:
            # for i in range(0, 10):
            step_count = 0
            file_count += 1

            wfs_url = self.config.url
            params = {}
            params['Count'] = page_size
            params['startIndex'] = total_count
            # cql_filter = "bbox(location,51,3,52,6) and time > '2016-09-26T15:27:38.000 00:00' and time < '2016-09-26T19:27:38.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
            cql_filter = "bbox(location,{bbox}) and time > '{start_datetime}' and time < '{end_datetime}' and endTime-startTime={endminusstart} and quantity='{quantity}' and substance='{substance}'".format(
                bbox=self.config.bbox,
                start_datetime=self.config.start_datetime,
                end_datetime=self.config.end_datetime,
                quantity=self.config.quantity,
                substance=self.config.substance,
                endminusstart=self.config.endminusstart
            )
            #print cql_filter
            # TODO development
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
                logging.debug('Firing WFS request: GET %s' % request.get_full_url() + request.get_data())
                response = urllib2.urlopen(request)
                CHUNK = 16 * 1024
                filename = self.config.output_dir + '/data' + unicode(file_count) + '.gml'

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
            except Exception as e:
                print e
                #pass

            # note: if copying with shutil.copy2 or shutil.copy, QGIS only reads gml when you touch gfs file???
            shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'schemas', 'measurements.gfs'),
                            os.path.join(self.config.output_dir, 'data' + unicode(file_count) + '.gfs'))
            # IMPORTANT !!!
            #  OGR only uses the gfs file if the modification time is >= modification time of gml file !!!
            #  set it to NOW with os.utime !!!
            os.utime(os.path.join(self.config.output_dir, 'data' + unicode(file_count) + '.gfs'), None)
            # fake progress because we do not know actual total count:
            # we start at 1/2 then 2/3, 3/4, 4/5 etc
            #self.progress.emit(file_count / (1.0 + file_count))

        # TODO!!! for now using urllib, but should move to QgsNetworkManager, so for now call this myself:
        self._data_retrieved(None)


# if __name__ == '__main__':
#
#     from PyQt4.QtCore import QDateTime
#     from datetime import datetime
#     from utils import Utils
#     config = CalnetMeasurementsConfig()
#     config.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
#     # we have always an wps_settings.output_dir here:
#     config.output_dir = Utils.jrodos_dirname('test_WFS_Meaurements', "", datetime.now().strftime("%Y%m%d%H%M%S"))
#     config.page_size = 10000
#     config.endminusstart = '3600'
#     config.quantity = 'T-GAMMA'
#     config.substance = 'A5'
#     config.bbox = '55,5,60,15'
#     end_time = QDateTime.currentDateTime()  # end NOW
#     start_time = end_time.addSecs(-60 * 60 * 6)  # -6 hours
#     # config.start_datetime = '2016-04-25T08:00:00.000+00:00'
#     # config.end_datetime = '2016-04-26T08:00:00.000+00:00
#     config.start_datetime = start_time.toString(config.date_time_format)
#     config.end_datetime = end_time.toString(config.date_time_format)
#
#     prov = CalnetMeasurementsProvider(config)
#     prov.get_data()

