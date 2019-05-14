from qgis.core import QgsApplication  # fake import to force sip version 2
import unittest
import os
from providers.jrodos_project_provider import JRodosProjectConfig, JRodosProjectProvider
from .test_provider_base import TestProviderBase
from qgis.PyQt.QtCore import QCoreApplication


class TestJRodosProjectProvider(TestProviderBase):

    def test_jrodos_project_url(self):
        conf = JRodosProjectConfig()
        #conf.url = 'https://duif.net/project1268.json'
        #conf.url = 'http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects/1268'
        conf.url = 'http://geoserver.dev.cal-net.nl/rest/jrodos/projects/2532'
        #conf.url = 'http://geoserver.dev.cal-net.nl/rest-1.0-TEST-1/jrodos/projects/2532'
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            # get first dataitem form first task from first project
            #dataitems = result.data['project']['tasks'][0]['dataitems']
            dataitems = result.data['tasks'][0]['dataitems']
            self.assertEqual(577, len(dataitems))

            one_item = dataitems[361]
            unit = one_item['unit']
            # on rest-1.0-TEST-1 we do not have units yet
            #unitt = 'rO0ABXNyAB5qYXZheC5tZWFzdXJlLnVuaXQuUHJvZHVjdFVuaXQAAAAAAAAAAQIAAkkACV9oYXNoQ29kZVsACV9lbGVtZW50c3QAKVtMamF2YXgvbWVhc3VyZS91bml0L1Byb2R1Y3RVbml0JEVsZW1lbnQ7eHIAHmphdmF4Lm1lYXN1cmUudW5pdC5EZXJpdmVkVW5pdJ9leNEz2RhmAgAAeHIAF2phdmF4Lm1lYXN1cmUudW5pdC5Vbml0zcjeFnjNUmcCAAB4cAAAAAB1cgApW0xqYXZheC5tZWFzdXJlLnVuaXQuUHJvZHVjdFVuaXQkRWxlbWVudDscDCvnLvFoGAIAAHhwAAAAAnNyACZqYXZheC5tZWFzdXJlLnVuaXQuUHJvZHVjdFVuaXQkRWxlbWVudAAAAAAAAAABAgADSQAEX3Bvd0kABV9yb290TAAFX3VuaXR0ABlMamF2YXgvbWVhc3VyZS91bml0L1VuaXQ7eHAAAAABAAAAAXNyABtqYXZheC5tZWFzdXJlLnVuaXQuQmFzZVVuaXQAAAAAAAAAAQIAAUwAB19zeW1ib2x0ABJMamF2YS9sYW5nL1N0cmluZzt4cQB+AAN0AAFtc3EAfgAH/////wAAAAFzcQB+AAp0AAFz'
            unitt = 'mSv/h'
            self.assertEqual(unitt, unit)

        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # skipping because timeout takes too long to wait on :-)
    # @unittest.skip
    # def test_jrodos_project_url_NOK(self):
    #     conf = JRodosProjectConfig()
    #     conf.url = 'https://duif.net/project1268.foo'
    #     prov = JRodosProjectProvider(conf)
    #     def prov_finished(result):
    #         # wrong url, so should error with 203
    #         self.assertEqual(result.error(), True)
    #         self.assertEqual(result.error_code, 203)
    #     prov.finished.connect(prov_finished)
    #     prov.get_data()
    #     while not prov.is_finished():
    #         QCoreApplication.processEvents()

    def test_jrodos_project_file(self):
        conf = JRodosProjectConfig()
        # find dir of this class
        conf.url = 'file://' + os.path.join(os.path.dirname(__file__), 'project1268.json')
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_projects_url(self):
        conf = JRodosProjectConfig()
        # find dir of this class
        conf.url = 'http://geoserver.dev.cal-net.nl:8080/jrodos-rest-service/jrodos'
        conf.url = 'http://geoserver.dev.cal-net.nl/rest/jrodos'
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            self.assertIsNotNone(result.data)
            # should be dict with first attritube content, being an array of 'projects'
            #print type(result.data) # dict
            #print type(result.data['content'][0])  # list
            self.assertTrue('content' in result.data)
            #self.assertTrue('project' in result.data['content'][0])
            # what will we use (to search in?)
            self.assertTrue('projectId' in result.data['content'][0])
            self.assertTrue('name' in result.data['content'][0])
            self.assertTrue('username' in result.data['content'][0])
            self.assertTrue('modelchainname' in result.data['content'][0])

        prov.finished.connect(prov_finished)
        prov.get_data('/projects')
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_projects_file(self):
        conf = JRodosProjectConfig()
        # find dir of this class
        conf.url = 'file://' + os.path.join(os.path.dirname(__file__), 'projects.json')
        prov = JRodosProjectProvider(conf)
        def prov_finished(result):
            self.assertIsNotNone(result.data)
            # should be dict with first attritube content, being an array of 'projects'
            # print type(result.data) # dict
            # print type(result.data['content'][0])  # list
            self.assertTrue('content' in result.data)
            self.assertTrue('project' in result.data['content'][0])
            # what will we use (to search in?)
            self.assertTrue('projectId' in result.data['content'][0]['project'])
            self.assertTrue('name' in result.data['content'][0]['project'])
            self.assertTrue('username' in result.data['content'][0]['project'])
            self.assertTrue('modelchainname' in result.data['content'][0]['project'])

        prov.finished.connect(prov_finished)

        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

if __name__ == '__main__':
    unittest.main()
