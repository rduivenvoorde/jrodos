from PyQt4.QtCore import QUrl, QCoreApplication
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
from provider_base import ProviderConfig, ProviderBase, ProviderResult
import json


class JRodosProjectConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class JRodosProjectProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):
        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.request().url().toString(), 'JRodos project provider (REST)')
        else:
            content = unicode(reply.readAll())
            result._data = json.loads(content)
        self.finished.emit(result)
        self.ready = True
        reply.deleteLater()  # else timeouts on Windows

    def get_data(self, path=None):
        if path is not None:
            request = QUrl(self.config.url + path)
        else:
            request = QUrl(self.config.url)
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()
