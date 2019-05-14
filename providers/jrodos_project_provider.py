# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from functools import partial
from .provider_base import ProviderConfig, ProviderBase, ProviderResult
import json
import logging
#from .. import LOGGER_NAME
log = logging.getLogger('JRodos3 Plugin')

class JRodosProjectConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class JRodosProjectProvider(ProviderBase):
    """A provider which connects to a model REST service to retrieve information about the JRodos projects.
     Needed to show the Task-items of a project (LSMC, Emersim etc), and the Dataitems of every task)
    """
    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):
        log.debug("JRodosProjectProvider: projects retrieved, start looking into reply... ")
        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.request().url().toString(), 'JRodos project provider (REST)')
        elif reply.attribute(QNetworkRequest.RedirectionTargetAttribute) is not None:
            # !! We are being redirected
            # http://stackoverflow.com/questions/14809310/qnetworkreply-and-301-redirect
            url = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)  # returns a QUrl
            if not url.isEmpty():  # which IF NOT EMPTY contains the new url
                # find it and get it
                self.config.url = url.toString()
                self.get_data()
            # delete this reply, else timeouts on Windows
            reply.deleteLater()
            # return without emitting 'finished'
            return
        else:
            # mmm, service returns HTML instead of JSON in case of a problem
            try:
                r = reply.readAll()  # QByteArray
                content = r.data().decode('utf-8')
                result._data = json.loads(content)
            except Exception as e:
                result.set_error(-1, reply.request().url().toString(),
                    'Error converting the JRodos projects reply to json: {}'.format(e))
        self.finished.emit(result)
        self.ready = True
        log.debug("JRodosProjectProvider: projects read, finished ... ")
        reply.deleteLater()  # else timeouts on Windows

    def get_data(self, path=None):
        if path is not None:
            request = QUrl(self.config.url + path)
        else:
            request = QUrl(self.config.url)
        log.debug("JRodosProjectProvider: requesting projects from {}".format(request))
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly (NOT to be used when used as plugin)
        #while not reply.isFinished():
        #    QCoreApplication.processEvents()
