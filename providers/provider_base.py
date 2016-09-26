from PyQt4.QtCore import QObject, pyqtSignal
import signal
import sys
import traceback
import logging

"""
Idea:

- a provider needs a provider settings object
- these providers get data from somewhere, via separate worker thread
- some signals: started progress finished error iteravailable
- the default implementation just logs or prints, implementations can do other stuff
- after getting the data, and 'parsing' it if needed, returns an appropriate iterator?
- finished could return some default dict like {status: 0/1 (=OK,NOK), msg: "some human readable stuff", id:<someid?>}

"""

# https://pymotw.com/2/threading/
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(threadName)-10s) %(message)s',)


class ProviderConfig:
    def __init__(self):
        self._debug = None
        self.debug = False

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, debug_bool):
        self._debug = debug_bool


class ProviderBase(QObject):

    progress = pyqtSignal(float)
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)

    def __init__(self, config):
        # init superclass, needed for Threading
        QObject.__init__(self)

        if not isinstance(config, ProviderConfig):
            raise TypeError('Provider expected a Provider specific Config, got a {} instead'.format(type(config)))

        self.config = config

    # def run(self):
    #
    #     ret = {'status': 1, 'msg': 'ProviderBase', 'id': -1}
    #     try:
    #             self.progress.emit(1.0)
    #     except Exception, e:
    #         # forward the exception upstream
    #         self.error.emit(e, traceback.format_exc())
    #         ret = {'status': 0, 'msg': 'Problem in ProviderBase', 'id': -1}
    #
    #     self.finished.emit(ret)

    def iter(self):
        return None

