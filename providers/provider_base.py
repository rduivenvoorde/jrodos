import copy
from functools import partial
from qgis.core import QgsNetworkAccessManager

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QUrl,
    QObject,
    pyqtSignal,
    QDateTime,
)
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
)
import json
import logging
log = logging.getLogger('JRodos3 Plugin')

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

    # OK, for now: NOT serializing to xml, as it needs modules (lxml and etree)
    # https://lxml.de/objectify.html
    # which are by default not packaged in QGIS...
    # SO: going the json route for now...
    # def to_xml(self):
    #     root = objectify.Element('root')
    #     for field, value in self.__dict__.items():
    #         objectify.SubElement(root, field)
    #     print(objectify.dump(root))

    def to_json(self, ignore_empty_values=True) -> str:
        # NOTE: you cannot pop keys during an iteration! So below is NOT working
        # fields = copy.deepcopy(self.__dict__)
        # for key, value in fields.items():
        keys = copy.deepcopy(self.__dict__).keys()
        fields = copy.deepcopy(self.__dict__)
        for key in keys:
            if isinstance(key, str) and (key[0] == '_' or key in ('output_dir', 'date_time_format', 'date_time_format_short')):
                # this is a 'private field' don't copy it into json
                # OR it is one of the keys that we do not want to have in the json/presets
                fields.pop(key)
            elif ignore_empty_values and (fields[key] is None or fields[key] in ('',)):
                # leave out the keys without value IF the value is empty or None
                fields.pop(key)
        return json.dumps(fields, indent=2)

    def from_json(config_as_json):
        prov = ProviderConfig()
        if isinstance(config_as_json, str):
            obj = json.loads(config_as_json)
        # elif isinstance(config_as_json, json):
        #     obj = json.load(config_as_json)
        for key, value in obj.items():
            prov.__dict__[key] = value
        return prov


class ProviderResult:
    def __init__(self):
        # errors, see: https://doc.qt.io/qt-5/qnetworkreply.html
        self.error_code = 0
        self.error_msg = ''
        self.url = ''
        self._data = None

    def __str__(self):
        if self.error_code:
            return "ProviderError:\n error_code: {}\n error_msg: {}\n url: {}".\
                format(self.error_code, self.error_msg, self.url)
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
        if code == 0 and msg == '':
            code = -1  # just to be sure we do not have a 0 code
        self.error_code = code
        self.error_msg = msg
        if self.error_msg == '':
            self.error_msg = self.network_error_msg(self.error_code)
        else:
            self.error_msg = "{} ... {}".format(self.error_msg, self.network_error_msg(self.error_code))
        self.url = url
        #log.debug(self.error_msg)
        log.debug(self)

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
        elif network_error == 1:
            return "ConnectionRefusedError (server not accepting requests, is it up?)"
        elif network_error == 2:
            return "RemoteHostClosedError (server returned 500)"
        elif network_error == 3:
            return "HostNotFoundError"
        elif network_error == 4:
            return "TimeoutError"
        elif network_error == 5:
            # both Aborting this request, AND an actual network timout result in a 5 error...
            return "OperationCanceledError"
        elif network_error == 202:
            return "ContentOperationNotPermittedError"
        elif network_error == 203:
            return "ContentNotFoundError (server returned 404)"
        elif network_error == 299:
            return "UnknownContentError (server returned 500)"
        elif network_error == 301:
            return "ProtocolUnknownError"
        elif network_error == 302:
            return "Geoserver throws exception or returns error (replay URL from logs)"
        elif network_error == 401:
            return "The server encountered an unexpected condition which prevented it from fulfilling the request."
        elif network_error == 499:
            return "An unknown error related to the server response was detected."
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

        # reply of the providers
        self.reply = None

        # BELOW CAN be used to time requests
        # TOTAL time of (paging) request(s)
        self.time_total = 0
        # time of one page / getdata
        self.time = QDateTime.currentMSecsSinceEpoch()

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
            r = reply.readAll()
            content = str(r, 'utf-8')
            result._data = content
        self.finished.emit(result)
        self.ready = True
        reply.deleteLater()  # else timeouts on Windows

    def get_data(self):
        url = self.config.url
        request = QUrl(url)
        reply = self.network_manager.get(QNetworkRequest(request))
        reply.finished.connect(partial(self.data_retrieved, reply))
        # this part is needed to be sure we do not return immidiatly
        while not reply.isFinished():
            QCoreApplication.processEvents()


