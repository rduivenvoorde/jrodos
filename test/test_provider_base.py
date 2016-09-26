import unittest
import sys
import os

from providers.provider_base import ProviderBase, ProviderConfig, SimpleProvider, SimpleConfig

from PyQt4.QtCore import QCoreApplication

from qgis.core import QgsApplication


class TestProviderBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # to see how to setup a qgis app in pyqgis
        # https://hub.qgis.org/issues/13494#note-19
        os.environ["QGIS_DEBUG"] = str(-1)
        QCoreApplication.setOrganizationName('QGIS')
        QCoreApplication.setApplicationName('QGIS2')
        QgsApplication.setPrefixPath(os.getenv("QGIS_PREFIX_PATH"), True)
        QgsApplication.setAuthDbDirPath('/home/richard/.qgis2/')

        # argh... proxy, be sure that you have proxy enabled in QGIS IF you want to test within rivm (behind proxy)


    def setUp(self):
        self.ran_errored = False
        self.ran_finished = False
        self.ran_progress = False
        self.qgs = None
        # Duh... there can only be one QApplication at a time
        # http://stackoverflow.com/questions/10888045/simple-ipython-example-raises-exception-on-sys-exit
        # if you do create >1 QgsApplications (QtApplications) then you will have non exit code 0
        self.qgs = QgsApplication.instance()  # checks if QApplication already exists
        if not self.qgs:  # create QApplication if it doesnt exist
            self.qgs = QgsApplication(sys.argv, False)
            self.qgs.initQgis()  # nessecary for opening auth db etc etc
            # out = self.qgs.showSettings()
            # print out

    def test_qgs_OK(self):
        out = self.qgs.showSettings()
        self.assertGreater(len(out), 0)

    def test_config_None(self):
        conf = None
        with self.assertRaises(TypeError):
            ProviderBase(conf)

    def test_config_NOK(self):
        conf = SimpleConfig()
        conf.url = None
        with self.assertRaises(TypeError):
            ProviderBase(conf)

    def test_simple_url(self):
        conf = SimpleConfig()
        conf.url = 'https://duif.net/'
        prov = SimpleProvider(conf)
        def data_in(data):
            self.assertEquals(len(data), 1)
            it = iter(data)
            self.assertEquals(it.next().strip(), "ok")
        prov.finished.connect(data_in)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_simple_file(self):
        conf = SimpleConfig()
        # find dir of this class
        conf.url = 'file://'+os.path.join('file://', os.path.dirname(__file__), 'duif.net')
        prov = SimpleProvider(conf)
        def data_in(data):
            self.assertEquals(len(data), 1)
            it = iter(data)
            self.assertEquals(it.next().strip(), "ok")
        prov.finished.connect(data_in)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_simple_NOK_url(self):
        conf = SimpleConfig()
        conf.url = 'htps://duif.net/'
        with self.assertRaises(TypeError):
            ProviderBase(conf)

if __name__ == '__main__':
    unittest.main()
