from qgis.core import QgsNetworkAccessManager, QgsApplication
from PyQt4.QtCore import QThread, QUrl, QCoreApplication
from PyQt4.QtNetwork import QNetworkRequest
from functools import partial
import signal
import sys
import traceback
import logging
import json
import os
from provider_base import ProviderConfig, ProviderBase

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


class JRodosProjectConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.uri = None


class JRodosProjectProvider(ProviderBase):

    def __init__(self, config):
        ProviderBase.__init__(self, config)
        self.data = None
        self.manager = None
        #self.reply = None

    def handle_response(self, response):
        print response
        print response.url()
        print response.isReadable()
        print response.isOpen()
        print response.size()
        #print response.read(1000)
        content = unicode(response.readAll())
        print content
        response.deleteLater()
        #print 'ready'

    def run(self):
        ret = {'status': 1, 'msg': '', 'id': -1}
        try:
            if self.config.uri == None:
                raise Exception('uri in config is None')
            elif self.config.uri == '' or len(self.config.uri)<10:
                raise Exception('uri in config is empty or too short to be true')
            elif not (self.config.uri.startswith('file://')
                      or self.config.uri.startswith('http://')
                      or self.config.uri.startswith('https://')):
                raise Exception('uri should start with: file://, http:// or https://, but starts with %s' % self.config.uri[:8])
            else:
                self.progress.emit(0.5)

            if self.config.uri.startswith('file://'): # local file
                f = open(self.config.uri[7:])
                self.data = json.loads(f.read())
                self.data = self.data['project']
                ret['status'] = 0
            else:
                #print 'start'
                request = QUrl(self.config.uri)
                print 'creating manager'

                # QCoreApplication.setOrganizationName('QGIS')
                # QCoreApplication.setApplicationName('QGIS2')
                # QgsApplication.setPrefixPath(os.getenv("QGIS_PREFIX_PATH"), True)
                # QgsApplication.setAuthDbDirPath('/home/richard/.qgis2')
                # qgs = QgsApplication([], False).instance()
                # qgs.initQgis()
                # self.manager = QgsNetworkAccessManager.instance()

                print 'created manager'
                self.reply = self.manager.get(QNetworkRequest(request))
                self.reply.finished.connect(partial(self.handle_response, self.reply))
                # nodig? of niet?
                while not self.reply.isFinished():
                    #print 'not ready yet...'
                    QCoreApplication.processEvents()

        except Exception, e:
            # forward the exception upstream
            print "errorr: {}".format(e)
            ret['msg'] = 'Problem in JRodosProjectProvider: {}'.format(e)
            self.error.emit(e, traceback.format_exc())
            #print ret

        self.finished.emit(ret)
        # create internal data structure
        self.progress.emit(1.0)


#####################
# TESTING
#####################

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    print sig
    print frame
    sys.exit(1)


def test():

    conf = JRodosProjectConfig()
    #conf.uri = 'file://../data/project1268.json'
    conf.uri = 'http://duif.net/project1268.json'

    prov = JRodosProjectProvider(conf)

    if False:
        # Running in main thread
        prov.run()
        print prov.data
    else:
        # Run in a separate Thread
        def error(err):
            print 'error: %s' % err
            thread.quit()
            sys.exit(1)

        def finished(ret):
            print('finished: {}'.format(ret))
            thread.quit()
            qgs.quit()
            if ret['status']==0:
                project = prov.data
                print project['name'] # ['project']['tasks'][0]['dataitems']
                for task in project['tasks']:
                    for data_item in task['dataitems']:
                        print data_item['datapath']

        def progress(part):
            print('progress: {}'.format(part))

        thread = QThread()
        prov.moveToThread(thread)
        prov.finished.connect(finished)
        prov.error.connect(error)
        prov.progress.connect(progress)
        # start the provider in it's separate thread
        thread.started.connect(prov.run)
        thread.start()
        sys.exit(qgs.exec_())

if __name__ == '__main__':

    signal.signal(signal.SIGINT, signal_handler)

    # TEST
    QCoreApplication.setOrganizationName('QGIS')
    QCoreApplication.setApplicationName('QGIS2')
    QgsApplication.setPrefixPath(os.getenv("QGIS_PREFIX_PATH"), True)
    QgsApplication.setAuthDbDirPath('/home/richard/.qgis2')
    qgs = QgsApplication(sys.argv, True)
    qgs.initQgis()

    test()



