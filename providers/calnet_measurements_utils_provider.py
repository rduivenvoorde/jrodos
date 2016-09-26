from qgis.core import QgsNetworkAccessManager, QgsApplication
from PyQt4.QtCore import QThread, QUrl, QCoreApplication
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
from provider_base import ProviderConfig, ProviderBase
import xml.etree.ElementTree as ET



class CalnetMeasurementsUtilsConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class CalnetMeasurementsUtilsProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):

        content = unicode(reply.readAll())

        self.data = []
        root = ET.fromstring(content)
        for ret in root.findall(".//return"):
            code = ret.find('code').text
            desc = ret.find('description').text
            # print code, description
            description = "%s (%s)" % (desc, code)
            self.data.append({'code': code, 'description': description})

        self.ready = True
        self.finished.emit(self.data)

    def get_data(self, param='Quantities'):

        data = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                     xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                     xmlns:ws="http://service.ws.calnet.rivm.nl/">
                      <soap:Header/>
                      <soap:Body>
                        <ws:get%s />
                      </soap:Body>
                    </soap:Envelope>""" % param

        request = QNetworkRequest(QUrl(self.config.url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/soap+xml") # or? "text/xml; charset=utf-8"
        reply = self.network_manager.post(request, data)
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()
