# -*- coding: utf-8 -*-
import pytest
from ..providers.jrodos_model_output_provider import (
    JRodosModelOutputConfig,
    JRodosModelOutputProvider,
)
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QDateTime,
    QDate,
    QTime,
)


@pytest.fixture
def calnet_jrodos_model_config():
    conf = JRodosModelOutputConfig()
    conf.url = 'http://jrodos.dev.cal-net.nl/geoserver/wps'
    conf.jrodos_project = "project='190916_training_v4_RICHARD'"
    # a zipped
    conf.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    # conf.jrodos_path = "Model data=;=Input=;=UI-input=;=Input summary"
    conf.jrodos_format = 'application/zip'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
    # conf.jrodos_format = "text/xml; subtype=wfs-collection/1.0"
    conf.jrodos_model_time = 24*60
    conf.jrodos_model_step = 60*60  # timeStep is in seconds!!
    conf.jrodos_verticals = 0  # z / layers
    conf.jrodos_datetime_start = QDateTime(QDate(2019, 9, 16), QTime(3, 10))
    conf.units = u'Bq/m²'
    return conf


# def test_jrodos_model_output_settings(calnet_jrodos_model_config):
#     print(str(calnet_jrodos_model_config))


def test_jrodos_model_shapezip_24cols_output_url_zip(qgis, calnet_jrodos_model_config):
    # 2 zipped shapefiles of given model
    calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    #calnet_jrodos_model_config.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
    calnet_jrodos_model_config.jrodos_columns = 24
    calnet_jrodos_model_config.jrodos_format = 'application/zip'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
    prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
    assert prov is not None
    def prov_finished(result):
        #print(result)
        assert result.data is not None
        assert result.data['result'] == 'OK'
        assert len(result.data['output_dir']) > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_jrodos_model_shapezip_range_output_url_zip(qgis, calnet_jrodos_model_config):
    # one zipped shapefile of given model of a set of timesteps
    calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    # calnet_jrodos_model_config.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
    calnet_jrodos_model_config.jrodos_columns = '0-23'
    calnet_jrodos_model_config.jrodos_format = 'application/zip'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
    prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
    assert prov is not None
    def prov_finished(result):
        #print(result)
        assert result.data is not None
        assert result.data['result'] == 'OK'
        assert len(result.data['output_dir']) > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()


# Feb 2022, currently not working with taskuid's leave it as is...
#
# def test_jrodos_model_taskuid_shapezip_range_output_url_zip(qgis, calnet_jrodos_model_config):
#     def prov_finished(result):
#         #print(result)
#         assert result.data is not None
#         assert result.data['result'] == 'OK'
#         assert len(result.data['output_dir']) > 0
#     calnet_jrodos_model_config.jrodos_project = "taskuid='ab4a37a7-7f00-0001-565b-064f9ef6c494'"
#     #calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
#     calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
#     # calnet_jrodos_model_config.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
#     calnet_jrodos_model_config.jrodos_columns = '0-1'
#     calnet_jrodos_model_config.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
#     prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
#     assert prov is not None
#     prov.finished.connect(prov_finished)
#     prov.get_data()
#     while not prov.is_finished():
#         QCoreApplication.processEvents()
#
# def test_jrodos_model_taskuid_multitask_shapezip_range_output_url_zip(qgis, calnet_jrodos_model_config):
#     def prov_finished(result):
#         assert result.data is not None
#         assert result.data['result'] == 'OK'
#         assert len(result.data['output_dir']) > 0
#     calnet_jrodos_model_config.jrodos_project = "taskuid='f710658a-ac13-7293-5563-bb4080bd507e'"
#     calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
#     # calnet_jrodos_model_config.jrodos_model_time = 24*60  # modeltime = durationOfPrognosis; in Minutes
#     calnet_jrodos_model_config.jrodos_columns = '0-1'
#     calnet_jrodos_model_config.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
#     prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
#     assert prov is not None
#     prov.finished.connect(prov_finished)
#     prov.get_data()
#     while not prov.is_finished():
#         QCoreApplication.processEvents()


def test_jrodos_model_json_24cols_output_url(qgis, calnet_jrodos_model_config):
    # a set of json files of given model
    calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    calnet_jrodos_model_config.jrodos_columns = 24
    calnet_jrodos_model_config.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
    prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
    assert prov is not None
    def prov_finished(result):
        #print(result)
        assert result.data is not None
        assert result.data['result'] == 'OK'
        assert len(result.data['output_dir']) > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_jrodos_model_json_range_output_url(qgis, calnet_jrodos_model_config):
    # json of a timerange of given model
    calnet_jrodos_model_config.jrodos_path = "path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
    calnet_jrodos_model_config.jrodos_columns = '0-23'
    calnet_jrodos_model_config.jrodos_format = 'application/json'  # format = 'application/json' 'application/zip' 'text/xml; subtype=wfs-collection/1.0'
    prov = JRodosModelOutputProvider(calnet_jrodos_model_config)
    assert prov is not None
    def prov_finished(result):
        #print(result)
        assert result.data is not None
        assert result.data['result'] == 'OK'
        assert len(result.data['output_dir']) > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()

