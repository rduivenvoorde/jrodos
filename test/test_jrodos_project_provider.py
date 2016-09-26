import unittest
import os
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication


class TestJRodosProjectProvider(TestProviderBase):

    def test_jrodos_project_url(self):
        conf = JRodosProjectConfig()
        conf.url = 'https://duif.net/project1268.json'
        prov = JRodosProjectProvider(conf)
        def data_in(data):
            # data is an dict with 'project' props, whihc has 'tasks' which is a list of 'dataitems'
            self.assertIsInstance(data, dict)
            # get first dataitem form first task from first project
            dataitems = data['project']['tasks'][0]['dataitems']
            self.assertEquals(478, len(dataitems))
        prov.finished.connect(data_in)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_project_file(self):
        conf = JRodosProjectConfig()
        # find dir of this class
        conf.url = 'file://'+os.path.join('file://', os.path.dirname(__file__), 'project1268.json')
        prov = JRodosProjectProvider(conf)
        def data_in(data):
            self.assertIsNotNone(data)
        prov.finished.connect(data_in)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

if __name__ == '__main__':
    unittest.main()
