from qgis.core import QgsApplication  # fake import to force sip version 2
from PyQt4.QtCore import QUrl, QCoreApplication
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
from provider_base import ProviderConfig, ProviderBase, ProviderResult
import xml.etree.ElementTree as ET

import logging
from .. import LOGGER_NAME
log = logging.getLogger(LOGGER_NAME)

class CalnetMeasurementsUtilsConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None
        self.start_datetime = ''
        self.end_datetime = ''
        self.date_time_format = 'yyyy-MM-ddTHH:mm:ss.000Z' # 2019-03-06T00:00:00.000Z



class CalnetMeasurementsUtilsProvider(ProviderBase):

    """

    curl -v -XPOST -H "Content-Type: application/soap+xml" -d '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ws="http://service.ws.calnet.rivm.nl/">
    <soap:Header/>
    <soap:Header/>
    <soap:Body>
    <ws:getQuantities/>
    </soap:Body>
    </soap:Envelope>' "http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService"

    curl -v -XPOST -H "Content-Type: application/soap+xml" -d '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ws="http://service.ws.calnet.rivm.nl/">
      <soap:Header/>
      <soap:Body>
        <ws:getMeasuredCombinations>
           <arg0>2019-04-22T00:00:00.000Z</arg0>
           <arg1>2019-04-25T12:00:00.000Z</arg1>
        </ws:getMeasuredCombinations>
      </soap:Body>
    </soap:Envelope>' "http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService"


    curl -v -XPOST -H "Content-Type: application/soap+xml" -d '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:ws="http://service.ws.calnet.rivm.nl/">
                  <soap:Header/>
                  <soap:Body>
                    <ws:getMeasuredCombinations>
                    <arg0>2019-03-01T16:46:58.000Z</arg0>
                    <arg1>2019-04-30T16:46:58.000Z</arg1>
                    </ws:getMeasuredCombinations>
                  </soap:Body>
                </soap:Envelope>' "http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService"

    """

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):
        log.debug('Data retrieved for MeasuredCombinations')
        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.url().toString(),
                             'Calnet quantities, substances, units provider')
        else:
            content = unicode(reply.readAll())
            data = []
            root = ET.fromstring(content)

            for ret in root.findall(".//return"):
                if ret.find('quantity') is not None:
                    # <return>
                    #   <quantity>
                    #     <code>A11</code>
                    #     <description>OUTDOOR AIR</description>
                    #   </quantity>
                    #   <substance>
                    #     <code>T-ALFA-ART</code>
                    #     <description>TOTAL ARTIFICIAL ALPHA</description>
                    #   </substance>
                    # </return>
                    quantity_code = ret.find('quantity').find('code').text
                    quantity_description = ret.find('quantity').find('description').text
                    substance_code = ret.find('substance').find('code').text
                    substance_description = ret.find('substance').find('description').text
                    #description = "%s (%s) , %s (%s)" % (quantity_description, quantity_code, substance_description, substance_code)
                    # '{"quantity":"T-GAMMA","quantity_desc":"TOTAL GAMMA","substance":"A5","substance_desc":"EXTERNAL RADIATION"}'
                    data.append({'quantity': quantity_code, 'quantity_desc':quantity_description, 'substance':substance_code ,'substance_desc': substance_description})
                elif ret.find('code') is not None:
                    # <return>
                    #   <code>Y-90</code>
                    #   <description>YTTRIUM-90</description>
                    # </return>
                    code = ret.find('code').text
                    desc = ret.find('description').text
                    # print code, description
                    description = "%s (%s)" % (desc, code)
                    data.append({'code': code, 'description': description})
            result.set_data(data, reply.url().toString())
        self.ready = True
        self.finished.emit(result)
        reply.deleteLater()  # else timeouts on Windows

    def get_data(self, param='Quantities', arg0=False, arg1=False):
        """

        :param param: 'Quantities', 'Substances', 'Units' or 'MeasuredCombinations'
        :param arg0: start time: '2019-03-06T00:00:00.000Z' (only 'MeasuredCombinations')
        :param arg1: end time '2019-03-06T12:00:00.000Z' (only 'MeasuredCombinations')
        :return: result in json
        """

        data = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                     xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                     xmlns:ws="http://service.ws.calnet.rivm.nl/">
                      <soap:Header/>
                      <soap:Body>
                        <ws:get%s />
                      </soap:Body>
                    </soap:Envelope>""" % param

        if param == 'MeasuredCombinations':
            data = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                xmlns:ws="http://service.ws.calnet.rivm.nl/">
                  <soap:Header/>
                  <soap:Body>
                    <ws:getMeasuredCombinations>
                    <arg0>%s</arg0>
                    <arg1>%s</arg1>
                    </ws:getMeasuredCombinations>
                  </soap:Body>
                </soap:Envelope>""" % (self.config.start_datetime, self.config.end_datetime)

        print(data)
        log.debug('Start searching for MeasuredCombinations')

        request = QNetworkRequest(QUrl(self.config.url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/soap+xml") # or? "text/xml; charset=utf-8"
        reply = self.network_manager.post(request, data)
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        # while not reply.isFinished():
        #     #QCoreApplication.processEvents()
        #     from PyQt4.QtCore import QEventLoop
        #     QCoreApplication.processEvents(QEventLoop.AllEvents, 100 )