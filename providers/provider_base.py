import logging
from functools import partial
from qgis.core import QgsNetworkAccessManager
from PyQt4.QtCore import QUrl, QCoreApplication, QObject, pyqtSignal
from PyQt4.QtNetwork import QNetworkRequest
import traceback

"""

Idea:
- a provider needs a provider settings object
- a provider does NOT(!) do http requests itself, but uses QgsNetworkManager to retrieve the
    data (which already does that in separate thread), because QgsNetworkManager takes care of proxies,
    authentication etc etc
- a provider implements the building of some kind of request (being POST data or GET-url with parameters)
    - create_request
- a provider implements a finished slot (to be called via the QNetworkRequest finished signal) which indicates
    data (as a list) is available for processing and/or an iterator is ready to be used
- a provider can be used both for file and http requests... QUrl can handle this ??

- ?? maybe:
- a provider implements an ssl error slot?
- a provider implements a handleResponse (? separate thread ?) to handle/process retreived data

"""

# https://pymotw.com/2/threading/
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(threadName)-10s) %(message)s',)


class ProviderConfig:
    def __init__(self):
        self._debug = None
        self.url = None

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, debug_bool):
        self._debug = debug_bool


class ProviderBase(QObject):

    finished = pyqtSignal(object)

    def __init__(self, config):

        # init superclass, needed for Threading
        QObject.__init__(self)

        if not isinstance(config, ProviderConfig):
            raise TypeError('Provider expected a Provider specific Config, got a {} instead'.format(type(config)))
        self.config = config

        if self.config.url == None:
            raise TypeError('url in config is None')
        elif self.config.url == '' or len(self.config.url) < 10:
            raise TypeError('url in config is empty or too short to be true')
        elif not (self.config.url.startswith('file://')
                  or self.config.url.startswith('http://')
                  or self.config.url.startswith('https://')):
            raise TypeError(
                'url should start with: file://, http:// or https://, but starts with %s' % self.config.url[:8])

        self.network_manager = QgsNetworkAccessManager.instance()

        self.ready = False

        # data will always be a list of something, so do 'iter(data)' if you want to iterate over the items
        self.data = None

    def is_finished(self):
        return self.ready

    def error(self, err):
        self.ready = True
        print "ERROR..."
        #raise ProviderNetworkException(traceback.format_exc())


class ProviderNetworkException(BaseException):
    #print "Exception"
    pass


class SimpleConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class SimpleProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def _data_retrieved(self, reply):
        content = unicode(reply.readAll())
        self.data = [content]
        self.ready = True
        self.finished.emit(self.data)

    def get_data(self):
        url = self.config.url
        request = QUrl(url)
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self._data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()


