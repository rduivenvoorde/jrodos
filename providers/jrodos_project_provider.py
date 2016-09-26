from qgis.core import QgsNetworkAccessManager, QgsApplication
from PyQt4.QtCore import QThread, QUrl, QCoreApplication
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
from provider_base import ProviderConfig, ProviderBase
import json


class JRodosProjectConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class JRodosProjectProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):
        content = unicode(reply.readAll())
        self.data = json.loads(content)
        self.ready = True
        self.finished.emit(self.data)

    def get_data(self):
        request = QUrl(self.config.url)
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()
