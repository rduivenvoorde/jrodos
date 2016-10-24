from provider_base import ProviderConfig, ProviderBase, ProviderResult
from PyQt4.QtCore import QUrl
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
import os
import shutil
import re
import logging


class CalnetMeasurementsConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = ''
        self.output_dir = None
        # check and set defaults
        self.page_size = 5000
        # start en endtime are strings in self.date_time_format (UTC)
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
        # page_size comes from user config
        self.page_size = self.config.page_size
        # the page_count is the number of features returned in one 'page'-request.
        # It can be found in the 'numberReturned' attribute of the gml response
        self.page_count = 1
        # total number of returned features in this run
        self.total_count = 0
        # runner number for the file numbers
        self.file_count = 1

        # create a QUrl object to use with query parameters
        self.request = QUrl(self.config.url)
        self.request.addQueryItem('Count', unicode(self.page_size))
        self.request.addQueryItem('typeName', 'radiation.measurements:MEASUREMENT')
        self.request.addQueryItem('version', '2.0.0')
        self.request.addQueryItem('service', 'WFS')
        self.request.addQueryItem('request', 'GetFeature')
        # pity, below not working :-( so we have to check ourselves by counting
        # self.request.addQueryItem('resultType', 'hits')
        self.request.addQueryItem('startIndex', unicode(self.total_count))
        # the actual cql filter, something like:
        # "bbox(location,51,3,52,6) and time > '2016-09-26T15:27:38.000 00:00' and time < '2016-09-26T19:27:38.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
        cql_filter = "bbox(location,{bbox}) and time > '{start_datetime}' and time < '{end_datetime}' and endTime-startTime={endminusstart} and quantity='{quantity}' and substance='{substance}'".format(
            bbox=self.config.bbox,
            start_datetime=self.config.start_datetime,
            end_datetime=self.config.end_datetime,
            quantity=self.config.quantity,
            substance=self.config.substance,
            endminusstart=self.config.endminusstart
        )
        self.request.addQueryItem('CQL_FILTER', cql_filter)


    def _data_retrieved(self, reply):

        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.url().toString(), 'Calnet measurements provider')
            # OK, we have an error... emit the result + error here and quit the loading loop
            self.ready = True
            self.finished.emit(result)
            return
        else:
            filename = self.config.output_dir + '/data' + unicode(self.file_count) + '.gml'
            with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed

                # first read 500 chars to check the 'numberReturned' attribute
                # Note: there is also an attribute 'numberMatched' but this returns often 'unknown'
                first500chars = reply.read(500)
                page_count = re.findall('numberReturned="([0-9.]+)"', first500chars)
                self.page_count = int(page_count[0])
                self.total_count += self.page_count
                f.write(first500chars)
                # now the rest
                f.write(reply.readAll())

            # note: if copying with shutil.copy2 or shutil.copy, QGIS only reads gml when you touch gfs file???
            shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'schemas', 'measurements.gfs'),
                            os.path.join(self.config.output_dir, 'data' + unicode(self.file_count) + '.gfs'))
            # IMPORTANT !!!
            #  OGR only uses the gfs file if the modification time is >= modification time of gml file !!!
            #  set it to NOW with os.utime !!!
            os.utime(os.path.join(self.config.output_dir, 'data' + unicode(self.file_count) + '.gfs'), None)

            # print "self.page_size %s" % self.page_size
            # print "self.page_count %s" % self.page_count
            # print "self.total_count: %s" % self.total_count

            logging.debug('Ready saving measurement features, page-size: {}, page-count: {}, total-count: {}, start {} / end {}'.format(self.page_size, self.page_count, self.total_count, self.config.start_datetime, self.config.end_datetime))

            if self.total_count % self.page_size == 0 and self.page_count > 0:
                # silly Qt way to update one query parameter
                self.request.removeQueryItem('startIndex')
                self.request.addQueryItem('startIndex', unicode(self.total_count))
                self.file_count += 1
                self.get_data()
            else:
                logging.debug('Finishing {}-minute data measurements retrieval: {} measurements received...'.format(int(self.config.endminusstart)/60 ,self.total_count))
                result.set_data({'result': 'OK', 'output_dir': self.config.output_dir, 'count': self.total_count}, reply.url().toString())
                # we nee to wait untill all pages are there before to emit the result; so: INSIDE de loop
                self.ready = True
                self.finished.emit(result)


    def get_data(self):
        logging.debug('Getting measurements {}-minute data, firing WFS request: GET {}'.format(int(self.config.endminusstart)/60 ,self.request))
        # write config for debug/checks
        config_file = self.config.output_dir + '/wfs_settings.txt'
        with open(config_file, 'wb') as f:
            f.write(unicode(self.config))

        reply = self.network_manager.get(QNetworkRequest(self.request))
        reply.finished.connect(partial(self._data_retrieved, reply))