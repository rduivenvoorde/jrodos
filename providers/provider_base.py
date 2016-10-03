import logging
from functools import partial
from qgis.core import QgsNetworkAccessManager, QgsMessageLog
from PyQt4.QtCore import QUrl, QCoreApplication, QObject, pyqtSignal
from PyQt4.QtNetwork import QNetworkRequest

"""

Idea:
- a provider provides data services over the network by using QgsNetworkManager
- a provider needs a provider settings object
- a provider does NOT(!) do http requests itself, but uses QgsNetworkManager to retrieve the
    data (which already does that in separate thread), because QgsNetworkManager takes care of proxies,
    authentication etc etc
- a provider implements the building of some kind of request (being POST data or GET-url with parameters)
    - create_request
- a provider implements a finished slot (to be called via the QNetworkRequest finished signal) which indicates
    data (as a list) is available for processing and/or an iterator is ready to be used
- a provider can be used both for file and http requests...
- a provider ALWAYS finishes, that is fires a 'finished' signal (just like the QNetworkReply!!)
- a user of a provider should ALWAYS check for errors, the error-property of the provider will be a QNetworkReply error

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


class ProviderResult:
    def __init__(self):
        # errors, see: http://doc.qt.io/qt-4.8/qnetworkreply.html#NetworkError-enum
        self.error_code = 0
        self.error_msg = ''
        self.url = ''
        self._data = None

    def __str__(self):
        if self.error_code:
            return "ProviderError:\n  error_code: {}\n  error_msg: {}\n  url: {}".format(self.error_code,
                                                                                         self.error_msg,
                                                                                         self.url)
        else:
            return "ProviderResult:\n  data: {}\n  url: {}".format(self._data, self.url)


    def set_error(self, code, url='', msg=''):
        """
        IF a provider had an error after the 'finish', call this to save it for layer
        :param code: The QNetwork error code (or -1 if not a QNetwork error code)
                     see: http://doc.qt.io/qt-4.8/qnetworkreply.html#NetworkError-enum
        :param url:  Preferably also set the url used (for checking)
        :param msg:  Either a descriptive message, or ''. In case of '' we will try to find a msg based on code
        :return:
        """
        if code ==0 and msg == '':
            code = -1 # just to be sure we do not have a 0 code
        self.error_code = code
        self.error_msg = msg
        if self.error_msg == '':
            self.error_msg = self.network_error_msg(self.error_code)
        else:
            self.error_msg = self.error_msg+' ... '+self.network_error_msg(self.error_code)
        self.url = url
        QgsMessageLog.logMessage(unicode(self), 'Network providers', QgsMessageLog.INFO)

    def set_data(self, data, url=''):
        self.url = url
        self._data = data

    @property
    def data(self):
        return self._data

    def error(self):
        return not(self.error_code == 0 and self.error_msg == '')

    def network_error_msg(self, network_error):
        # http://doc.qt.io/qt-4.8/qnetworkreply.html#NetworkError-enum
        if network_error == 0:
            return "NOT a network error (Qt returned 0)"
        elif network_error == -1:
            return "UnknownError"
        elif network_error == 3:
            return "HostNotFoundError"
        elif network_error == 4:
            return "TimeoutError"
        elif network_error == 5:
            return "OperationCanceledError"
        elif network_error == 203:
            return "ContentNotFoundError (server returned 404)"
        elif network_error == 299:
            return "UnknownContentError (server returned 500)"
        else:
            raise TypeError("New NetworkError: {} ?".format(network_error))


class ProviderBase(QObject):

    finished = pyqtSignal(object)

    def __init__(self, config):

        # init superclass, needed for Threading
        QObject.__init__(self)

        if not isinstance(config, ProviderConfig):
            raise TypeError('Provider expected a Provider specific Config, got a {} instead'.format(type(config)))
        self.config = config
        if self.config.url is None:
            raise TypeError('url in config is None')
        elif self.config.url == '' or len(self.config.url) < 10:
            raise TypeError('url in config is empty or too short to be true')
        elif not (self.config.url.startswith('file://')
                  or self.config.url.startswith('http://')
                  or self.config.url.startswith('https://')):
            raise TypeError(
                'url should start with: file://, http:// or https://, but starts with %s' % self.config.url[:8])

        self.network_manager = QgsNetworkAccessManager.instance()

        # while this provider is not ready, keep processing Qt events!!
        self.ready = False

        # data will always be a list of something, so do 'iter(data)' if you want to iterate over the items
        self.data = None

    def is_finished(self):
        return self.ready


class SimpleConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = None


class SimpleProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)

    def data_retrieved(self, reply):
        result = ProviderResult()
        if reply.error():
            self.error = reply.error()
            result.error_code = reply.error()
        else:
            content = unicode(reply.readAll())
            result._data = content
        self.finished.emit(result)
        self.ready = True

    def get_data(self):
        url = self.config.url
        request = QUrl(url)
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self.data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()


