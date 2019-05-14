# -*- coding: utf-8 -*-
import unittest
from providers.jrodos_model_output_provider import JRodosModelOutputConfig, JRodosModelOutputProvider, JRodosModelProvider
from .test_provider_base import TestProviderBase
from qgis.PyQt.QtCore import QCoreApplication, QDateTime, QDate, QTime


class TestJRodosModelOutputProvider(TestProviderBase):

    def setUp(self):
        TestProviderBase.setUp(self)
        self.conf = JRodosModelOutputConfig()
        #self.conf.url = 'http://localhost:8080/geoserver/wps'
        self.conf.url = 'http://geoserver.dev.cal-net.nl/geoserver/wps'
        self.conf.jrodos_project = "project='wps-test-3'"
        # a zipped
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # self.conf.jrodos_path = "Model data=;=Input=;=UI-input=;=Input summary"
        self.conf.jrodos_format = 'application/zip' # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        # self.conf.jrodos_format = "text/xml; subtype=wfs-collection/1.0"
        self.conf.jrodos_model_time = 24*60
        self.conf.jrodos_model_step = 60*60  # timeStep is in seconds!!
        self.conf.jrodos_verticals = 0  # z / layers
        self.conf.jrodos_datetime_start = QDateTime(QDate(2016, 5, 17), QTime(6, 0))
        self.conf.units = u'Bq/m²'

    def test_jrodos_model_output_settings(self):
        print(str(self.conf))

    # To run just this test:
    # nosetests test / test_jrodos_model_output_provider.py:TestJRodosModelOutputProvider.test_jrodos_model_shapezip_24cols_output_url_zip
    def test_jrodos_model_shapezip_24cols_output_url_zip(self):
        # 2 zipped shapefiles of given model
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        #self.conf.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
        self.conf.jrodos_columns = 24
        self.conf.jrodos_format = 'application/zip' # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # To run just this test:
    # nosetests test / test_jrodos_model_output_provider.py:TestJRodosModelOutputProvider.test_jrodos_model_shapezip_range_output_url_zip
    def test_jrodos_model_shapezip_range_output_url_zip(self):
        # one zipped shapefile of given model of a set of timesteps
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # self.conf.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
        self.conf.jrodos_columns = '0-23'
        self.conf.jrodos_format = 'application/zip'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_model_taskuid_shapezip_range_output_url_zip(self):
        self.conf.jrodos_project = "taskuid='527fcd2c-ac13-7293-5563-bb409a0362f5'"
        #self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # self.conf.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
        self.conf.jrodos_columns = '0-1'
        self.conf.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_jrodos_model_taskuid_multitask_shapezip_range_output_url_zip(self):
        self.conf.jrodos_project = "taskuid='f710658a-ac13-7293-5563-bb4080bd507e'"
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # self.conf.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
        self.conf.jrodos_columns = '0-1'
        self.conf.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)

        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)

        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # To run just this test:
    # nosetests test / test_jrodos_model_output_provider.py:TestJRodosModelOutputProvider.test_jrodos_model_json_24cols_output_url
    def test_jrodos_model_json_24cols_output_url(self):
        # a set of json files of given model
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        self.conf.jrodos_columns = 24
        self.conf.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # To run just this test:
    # nosetests test / test_jrodos_model_output_provider.py:TestJRodosModelOutputProvider.test_jrodos_model_json_range_output_url
    def test_jrodos_model_json_range_output_url(self):
        # json of a timerange of given model
        self.conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        self.conf.jrodos_columns = '0-23'
        self.conf.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelOutputProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # To run just this test:
    # nosetests test / test_jrodos_model_output_provider.py:test_jrodos_model_info_url
    def test_jrodos_model_info_url(self):
        # the information of given project
        #self.conf.jrodos_model_time = 0
        self.conf.jrodos_path = "path='Model data=;=Input=;=UI-input=;=RodosLight'"
        self.conf.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
        prov = JRodosModelProvider(self.conf)
        self.assertIsNotNone(prov)
        def prov_finished(result):
            print(result)
            self.assertIsNotNone(result.data)
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()


if __name__ == '__main__':
    unittest.main()
