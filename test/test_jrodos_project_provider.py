import unittest
import sys
import os
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider

from PyQt4.QtCore import QThread, QCoreApplication
from PyQt4.QtGui import QApplication

from qgis.core import QgsApplication

class TestJRodosProjectProviderBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["QGIS_DEBUG"] = str(-1)
        QCoreApplication.setOrganizationName('QGIS')
        QCoreApplication.setApplicationName('QGIS2')
        QgsApplication.setPrefixPath(os.getenv("QGIS_PREFIX_PATH"), True)
        QgsApplication.setAuthDbDirPath('/home/richard/.qgis2/')

    def setUp(self):
        #print 'setting up base'
        self.ran_errored = False
        self.ran_finished = False
        self.ran_progress = False
        self.app = None
        # Duh... there can only be one QApplication at a time
        # http: // stackoverflow.com / questions / 10888045 / simple - ipython - example - raises - exception - on - sys - exit
        #self.app = QApplication.instance()  # checks if QApplication already exists
        #self.app = QgsApplication(sys.argv, False)
        if not self.app:  # create QApplication if it doesnt exist
            #self.app = QApplication(sys.argv, False)
            self.app = QgsApplication(sys.argv, False)
            self.app.initQgis()
            out = self.app.showSettings()
            print out
        self.thread = QThread()
        self.result = None

    def startThread(self):
        # self.app = QApplication(sys.argv)
        # self.thread = QThread()
        self.prov = JRodosProjectProvider(self.conf)
        self.prov.moveToThread(self.thread)
        self.prov.finished.connect(self.finished)
        self.prov.error.connect(self.error)
        self.prov.progress.connect(self.progress)
        self.thread.started.connect(self.prov.run)
        self.thread.start()

    def error(self, exception, basestring):
        self.ran_errored = True

    def finished(self, ret):
        #print('finished: {}'.format(ret))
        self.ran_finished = True
        self.result = ret
        self.thread.quit()
        self.app.quit()
        # if ret['status']==0:
        #     project = self.prov.data
        #     print project['name'] # ['project']['tasks'][0]['dataitems']
        #     for task in project['tasks']:
        #         for data_item in task['dataitems']:
        #             print data_item['datapath']

    def progress(self, part):
        #print('progress: {}'.format(part))
        self.ran_progress = True


class TestJRodosFileOK(TestJRodosProjectProviderBase):
    def runTest(self):
        self.conf = JRodosProjectConfig()
        self.conf.uri = 'file://../data/project1268.json'
        self.startThread()
        self.app.exec_()
        self.assertFalse(self.ran_errored)
        self.assertTrue(self.ran_finished)
        self.assertTrue(self.ran_progress)
        self.assertEquals(self.result['status'], 0)

class TestJRodosUriOK(TestJRodosProjectProviderBase):
    def runTest(self):
        self.conf = JRodosProjectConfig()
        self.conf.uri = 'http://www.duif.net/project1268.json'
        self.startThread()
        self.app.exec_()
        # self.assertFalse(self.ran_errored)
        # self.assertTrue(self.ran_finished)
        # self.assertTrue(self.ran_progress)
        # self.assertEquals(self.result['status'], 0)

class TestJRodosFileNOK(TestJRodosProjectProviderBase):
    def runTest(self):
        self.conf = JRodosProjectConfig()
        self.conf.uri = 'file://nonexcistingfile.json'
        self.startThread()
        self.app.exec_()
        self.assertTrue(self.ran_errored)
        self.assertTrue(self.ran_finished)
        self.assertTrue(self.ran_progress)
        self.assertEquals(self.result['status'], 1)
        self.assertTrue('No such file or directory' in self.result['msg'])

class TestJRodosUriNOK(TestJRodosProjectProviderBase):
    def runTest(self):
        self.conf = JRodosProjectConfig()
        self.conf.uri = 'foo://nonexcistingfile.json'
        self.startThread()
        self.app.exec_()
        self.assertTrue(self.ran_errored)
        self.assertTrue(self.ran_finished)
        self.assertTrue(self.ran_progress)
        self.assertEquals(self.result['status'], 1)
        self.assertTrue('uri should start with' in self.result['msg'])

if __name__ == '__main__':
    unittest.main()
