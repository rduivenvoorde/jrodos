from qgis.core import QgsApplication  # fake import to force sip version 2
import unittest
from providers.jrodos_model_output_provider import JRodosModelOutputConfig, JRodosModelOutputProvider
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication, QDateTime, QDate, QTime


class TestJRodosModelOutputProvider(TestProviderBase):

    def setUp(self):
        TestProviderBase.setUp(self)
        self.conf = JRodosModelOutputConfig()
        #self.conf.url = 'http://localhost:8080/geoserver/wps'
        self.conf.url = 'http://172.19.115.90:8080/geoserver/wps'
        self.conf.jrodos_project = "wps-test-3"
        self.conf.jrodos_path = "Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective"
        # self.conf.jrodos_path = "Model data=;=Input=;=UI-input=;=Input summary"
        self.conf.jrodos_format = 'application/zip'  # format = 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        # self.conf.jrodos_format = "text/xml; subtype=wfs-collection/1.0"
        # self.conf.jrodos_model_time = 24
        self.conf.jrodos_model_time = 2
        self.conf.jrodos_model_step = 60
        self.conf.jrodos_verticals = 0  # z / layers
        self.conf.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))

    def test_jrodos_model_output_settings(self):
        print self.conf

    def test_jrodos_model_output_url(self):
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print result
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()


if __name__ == '__main__':
    unittest.main()
