from .provider_base import ProviderConfig, ProviderBase, ProviderResult
from qgis.PyQt.QtCore import QUrl, QUrlQuery, QDateTime
from qgis.PyQt.QtNetwork import QNetworkRequest
from functools import partial
import os
import shutil
import re

import logging
log = logging.getLogger('JRodos3 Plugin')


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
        self.projectid = ''  # in DB projectid is an Integer, but let's keep it strings here to be able to test for len()
        self.lower_bound = ''
        self.upper_bound = ''
        self.endminusstart = 0
        self.bbox = '50,0,60,20'
        self.date_time_format = 'yyyy-MM-ddTHH:mm:ss.000 00:00'  # '2016-04-25T08:00:00.000+00:00'
        self.date_time_format_short = 'MM/dd HH:mm'  # '17/6 23:01'

    def __str__(self):
        return """CalnetMeasurementsConfig:\n WFS url: {}\n outputdir: {}\n page_size: {}\n starttime: {}\n endtime: {}\n endminusstart: {}\n quantity: {}\n substance: {}\n projectid: {}\n lower_bound: {}\n upper_bound: {}\n bbox: \n {}
            """.format(self.url, self.output_dir, self.page_size, self.start_datetime, self.end_datetime,
                       self.endminusstart, self.quantity, self.substance, self.projectid, self.lower_bound, self.upper_bound, self.bbox)

    def __bytes__(self):
        return str(self).encode('utf-8')

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

        # moved to provider_base:
        # TOTAL time of (paging) request(s)
        #self.time_total = 0
        # time of one page / getdata
        #self.time = QDateTime.currentMSecsSinceEpoch()

        # create a QUrl object to use with query parameters
        self.request = QUrl(self.config.url)
        query = QUrlQuery()
        query.addQueryItem('typeName', 'radiation.measurements:MEASUREMENT')
        query.addQueryItem('version', '2.0.0')
        query.addQueryItem('service', 'WFS')
        query.addQueryItem('request', 'GetFeature')
        # pity, below not working :-( so we have to check ourselves by counting
        # self.request.addQueryItem('resultType', 'hits')
        # the actual cql filter, something like:
        # "bbox(location,51,3,52,6) and time > '2016-09-26T15:27:38.000 00:00' and time < '2016-09-26T19:27:38.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
        cql_filter = "bbox(location,{bbox}) and time > '{start_datetime}' and time < '{end_datetime}' and quantity='{quantity}' and substance='{substance}'".format(
            bbox=self.config.bbox,
            start_datetime=self.config.start_datetime,
            end_datetime=self.config.end_datetime,
            quantity=self.config.quantity,
            substance=self.config.substance
        )
        cql_filter += " and endTime-startTime={}".format(self.config.endminusstart)
        if len(self.config.lower_bound) > 0:
            cql_filter += " and value > {}".format(self.config.lower_bound)
        if len(self.config.upper_bound) > 0:
            cql_filter += " and value < {}".format(self.config.upper_bound)
        if len(self.config.projectid) > 0:
            # IMPORTANT! projectid is ONE(!) int, NOT a string (or comma separated string) anymore!!
            cql_filter += " and projectid={}".format(int(self.config.projectid))
        query.addQueryItem('CQL_FILTER', cql_filter)

        # putting these last so it is clearly visible in logs we are 'paging'
        query.addQueryItem('count', f'{self.config.page_size}')
        query.addQueryItem('startIndex', str(self.total_count))
        self.request.setQuery(query)

    def _data_retrieved(self, reply):
        #log.debug('CalnetMeasurementsProvider, data retrieved from: {}'.format(self.request.url()))
        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.url().toString(), 'Calnet measurements provider')
            # OK, we have an error... emit the result + error here and quit the loading loop
            self.ready = True
            self.finished.emit(result)
            reply.deleteLater()  # else timeouts on Windows
            return
        elif reply.attribute(QNetworkRequest.RedirectionTargetAttribute) is not None:
            # !! We are being redirected
            # http://stackoverflow.com/questions/14809310/qnetworkreply-and-301-redirect
            url = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)  # returns a QUrl
            log.debug('Redirecting !!!!!!!')
            if not url.isEmpty():  # which IF NOT EMPTY contains the new url
                # find it and get it
                self.config.url = url.toString()
                self.request.setUrl(self.config.url)  # <= IMPORTANT, we are NOT REreading the config
                self.get_data()

            # delete this reply, else timeouts on Windows
            reply.deleteLater()
            # return without emitting 'finished' (and setting self.ready)
            return
        else:
            filename = self.config.output_dir + '/data' + str(self.file_count) + '.gml'
            log.debug("Saving to: {}".format(filename))
            with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed

                # first read 1500 chars to check some stuff, like the 'numberReturned' attribute or an 'ExceptionText' element
                first1500chars = reply.read(1500)
                first1500chars_str = first1500chars.decode('utf-8')

                # could be an exception
                # <ows:ExceptionReport version="2.0.0" xsi:schemaLocation="http://www.opengis.net/ows/1.1 http://geoserver.dev.cal-net.nl:80/geoserver/schemas/ows/1.1.0/owsAll.xsd">
                #     <ows:Exception exceptionCode="OperationProcessingFailed" locator="GetFeature">
                #     <ows:ExceptionText>Error occurred getting features The end instant must be greater or equal to the start
                #     </ows:ExceptionText>
                #     </ows:Exception>
                # </ows:ExceptionReport>
                exception = re.findall('<ows:ExceptionText>', first1500chars_str)
                if len(exception) > 0:
                    # oops WFS returned an exception
                    result.set_error(-1, reply.url().toString(), first1500chars_str)
                    self.ready = True
                    self.finished.emit(result)
                    reply.deleteLater()  # else timeouts on Windows
                    return
                else:
                    # if all OK we should have a page count:
                    # Note: there is also an attribute 'numberMatched' but this returns often 'unknown'
                    #log.debug('First 1500 chars in result: {}'.format(first1500chars_str))
                    page_count = re.findall('numberReturned="([0-9.]+)"', first1500chars_str)
                    if len(page_count) == 0:
                        # dit trad op wanneer de server redirect, nu maar laten staan om evt probleem met de page_count op te vangen (en dus te stoppen)
                        result.set_error(-1, reply.url().toString(), f'Something went wrong: page_count in data is emtpy: {page_count}\n')
                        self.ready = True
                        self.finished.emit(result)
                        reply.deleteLater()  # else timeouts on Windows
                        return
                    else:
                        self.page_count = int(page_count[0])
                        self.total_count += self.page_count
                f.write(first1500chars)
                # now the rest
                f.write(reply.readAll())


            # NOTE: if copying with shutil.copy2 or shutil.copy, QGIS only reads gml when you touch gfs file (see below!!!
            shutil.copyfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'schemas', 'measurements.gfs'),
                            os.path.join(self.config.output_dir, 'data' + str(self.file_count) + '.gfs'))
            # IMPORTANT !!!
            #  OGR only uses the gfs file if the modification time is >= modification time of gml file !!!
            #  set it to NOW with os.utime !!!
            os.utime(os.path.join(self.config.output_dir, 'data' + str(self.file_count) + '.gfs'), None)

            # print "self.page_size %s" % self.page_size
            # print "self.page_count %s" % self.page_count
            # print "self.total_count: %s" % self.total_count

            log.debug('Received {} measurements in {} secs, page-size: {}, total count: {}'.format(
                self.page_count, (QDateTime.currentMSecsSinceEpoch()-self.time)/1000, self.page_size, self.total_count))

            if self.total_count % self.page_size == 0 and self.page_count > 0:
                # silly Qt way to update one query parameter
                query = QUrlQuery(self.request.query())
                query.removeQueryItem('startIndex')
                query.addQueryItem('startIndex', str(self.total_count))
                self.request.setQuery(query)
                self.file_count += 1
                self.get_data()
            else:
                now = QDateTime.currentMSecsSinceEpoch()
                log.debug('Finished All measurements. A total of {} measurements received, in {} seconds'.format(self.total_count, (now-self.time_total)/1000))
                result.set_data({'result': 'OK', 'output_dir': self.config.output_dir, 'count': self.total_count}, reply.url().toString())
                # we nee to wait until all pages are there before to emit the result; so: INSIDE de loop
                self.ready = True
                self.finished.emit(result)
                reply.deleteLater()  # else timeouts on Windows


    def get_data(self):
        self.time = QDateTime.currentMSecsSinceEpoch()
        if self.time_total == 0:
            self.time_total = QDateTime.currentMSecsSinceEpoch()
        log.debug('Get (more) measurements... firing WFS request: GET {}'.format(self.request.url()))
        # write config for debug/checks
        config_file = self.config.output_dir + '/wfs_settings.txt'
        with open(config_file, 'ab+') as f:
            # f.write(str(self.config))
            # f.write('\n')
            # f.write(self.request.toString())
            s = self.config
            f.write(bytes(s))
            f.write(b'\nHuman Readable:\n')
            f.write(bytes(self.request.url(), 'utf-8'))
            f.write(b'\n\nEncoded:\n')
            f.write(self.request.toEncoded())
            f.write(b'\n\n\n')

        self.reply = self.network_manager.get(QNetworkRequest(self.request))
        self.reply.finished.connect(partial(self._data_retrieved, self.reply))
