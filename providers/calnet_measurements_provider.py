from .provider_base import ProviderConfig, ProviderBase, ProviderResult
from qgis.PyQt.QtCore import QUrl, QUrlQuery, QDateTime
from qgis.PyQt.QtNetwork import QNetworkRequest
from functools import partial
import os
import shutil
import re
import json

import logging
log = logging.getLogger('JRodos3 Plugin')


class CalnetMeasurementsConfig(ProviderConfig):

    DEFAULT_TITLE = 'No title set (yet) for this config/preset'

    def __init__(self):
        ProviderConfig.__init__(self)
        self.title = self.DEFAULT_TITLE
        self.url = ''
        self.output_dir = None
        # check and set defaults
        self.page_size = 5000
        # start- and end- time are strings in self.date_time_format (UTC)
        self.start_datetime = ''
        self.end_datetime = ''
        self.quantity = ''
        self.substance = ''
        self.projectid = ''  # in DB projectid is an Integer, but let's keep it strings here to be able to test for len()
        self.lower_bound = ''
        self.upper_bound = ''
        self.endminusstart = 0
        self.bbox = ''  # defaulting to an empty string now (was '50,0,60,20'), to be able to create a config without bbox, to be able to trigger a 'use current bbox'
        self.date_time_format = 'yyyy-MM-ddTHH:mm:ss.000+00:00'  # '2016-04-25T08:00:00.000+00:00'
        self.date_time_format_short = 'MM/dd HH:mm'  # '17/6 23:01'

    def __str__(self):
        return """CalnetMeasurementsConfig:\n WFS url: {}\n outputdir: {}\n page_size: {}\n starttime: {}\n endtime: {}\n endminusstart: {}\n quantity: {}\n substance: {}\n projectid: {}\n lower_bound: {}\n upper_bound: {}\n bbox: {}\n""" \
            .format(self.url, self.output_dir, self.page_size, self.start_datetime, self.end_datetime,
                    self.endminusstart, self.quantity, self.substance, self.projectid, self.lower_bound, self.upper_bound, self.bbox)

    def __bytes__(self):
        return str(self).encode('utf-8')


    def from_json(config_as_json):
        """
        Overriding the from_json of the Baseclasse to have all fields
        :return: CalnetMeasurementsConfig
        """
        prov = CalnetMeasurementsConfig()
        if isinstance(config_as_json, str):
            obj = json.loads(config_as_json)
        elif isinstance(config_as_json, dict):
            obj = config_as_json
        else:
            raise ValueError
        for key, value in obj.items():
            prov.__dict__[key] = value
        return prov

class CalnetMeasurementsProvider(ProviderBase):

    BOXES = {
        'ZEELAND': '51.170,3.349,51.778,4.289',
        'NL': '50.652,3.309,53.657,7.275',
        'EU': '38,-8,61,30'
    }

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
        query = QUrlQuery()
        query.addQueryItem('typeName', 'radiation.measurements:MEASUREMENT')
        query.addQueryItem('version', '2.0.0')
        query.addQueryItem('service', 'WFS')
        query.addQueryItem('request', 'GetFeature')
        # pity, below not working :-( so we have to check ourselves by counting
        # self.request.addQueryItem('resultType', 'hits')

        # it is possible to define self.config.start_datetime
        # is defined with something like: 'now-600' (meaning: now minus 600 seconds)
        # in THAT case we will use 'now().addSecs(-600)' as starttime and 'now' as end time
        start_datetime = self.config.start_datetime
        end_datetime = self.config.end_datetime
        if 'now-' in self.config.start_datetime.lower():
            end_datetime = QDateTime.currentDateTimeUtc()
            # removing 'now' from a string like 'now-600') to end up with a negative int -600 (note MINUS)
            start_datetime = QDateTime(end_datetime).addSecs(int(start_datetime.replace('now', '')))
            self.config.start_datetime = start_datetime.toString(self.config.date_time_format)
            self.config.end_datetime = end_datetime.toString(self.config.date_time_format)

        # bbox can be either a commasep.strting of W,S,E,N (latlon coords
        # OR a string like 'ZEELAND', 'NL' or 'EU'
        if self.config.bbox in self.BOXES.keys():
            self.config.bbox = self.BOXES[self.config.bbox]
        cql_filter = f"bbox(location,{self.config.bbox})"

        # the actual cql filter, something like:
        # "bbox(location,51,3,52,6) and time > '2016-09-26T15:27:38.000 00:00' and time < '2016-09-26T19:27:38.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'"
        cql_filter += f" and time > '{self.config.start_datetime}' and time < '{self.config.end_datetime}' "
        cql_filter += f" and quantity='{self.config.quantity}' and substance='{self.config.substance}'"
        cql_filter += f" and endTime-startTime={self.config.endminusstart}"
        if len(self.config.lower_bound) > 0:
            cql_filter += f" and value > {self.config.lower_bound}"
        if len(self.config.upper_bound) > 0:
            cql_filter += f" and value < {self.config.upper_bound}"
        if len(self.config.projectid) > 0:
            # IMPORTANT! projectid is ONE(!) int, NOT a string (or comma separated string) anymore!!
            cql_filter += f" and projectid={int(self.config.projectid)}"
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
            s = self.config
            f.write(bytes(s))
            f.write(b'\nHuman Readable:\n')
            f.write(bytes(self.request.url(), 'utf-8'))
            f.write(b'\n\nEncoded:\n')
            f.write(self.request.toEncoded())
            f.write(b'\n\nJSON:\n')
            f.write(bytes(self.config.to_json(), 'utf-8'))
            f.write(b'\n\n')
        self.reply = self.network_manager.get(QNetworkRequest(self.request))
        self.reply.finished.connect(partial(self._data_retrieved, self.reply))
