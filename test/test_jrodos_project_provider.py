from qgis.core import QgsApplication  # fake import to force sip version 2
import unittest
import os
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication


class TestJRodosProjectProvider(TestProviderBase):

    def test_jrodos_project_url(self):
        conf = JRodosProjectConfig()
        conf.url = 'https://duif.net/project1268.json'
        # conf.url = 'http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects/1268'
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            # get first dataitem form first task from first project
            dataitems = result.data['project']['tasks'][0]['dataitems']
            self.assertEquals(478, len(dataitems))
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_project_url_NOK(self):
        conf = JRodosProjectConfig()
        conf.url = 'https://duif.net/project1268.foo'
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            # wrong url, so should error with 203
            self.assertEquals(result.error(), True)
            self.assertEquals(result.error_code, 203)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_project_file(self):
        conf = JRodosProjectConfig()
        # find dir of this class
        conf.url = 'file://'+os.path.join('file://', os.path.dirname(__file__), 'project1268.json')
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

if __name__ == '__main__':
    unittest.main()
