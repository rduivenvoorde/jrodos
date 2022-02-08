import pytest
from ..providers.calnet_measurements_provider import (
    CalnetMeasurementsConfig,
    CalnetMeasurementsProvider,
)
from ..providers.utils import Utils

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QDateTime,
)
from datetime import datetime
from pathlib import Path
import json

@pytest.fixture
def bbox():
    boxes = {}
    boxes['ZEELAND_BBOX'] = '51,3,52,6'  # south Netherlands
    boxes['BENELUX_BOX'] = '50.3723647997,1.51982637865,52.3253260358,7.03980085372'  # benelux
    boxes['EU_BBOX'] = '38,-8,61,30'  # europe
    return boxes

@pytest.fixture
def calnet_measurements_config():
    config = CalnetMeasurementsConfig()
    config.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
    # we have always an jrodos_output_settings.output_dir here:
    config.output_dir = Utils.jrodos_dirname('test_WFS_Measurements', "", datetime.now().strftime("%Y%m%d%H%M%S"))
    config.page_size = 10000  # 10000
    config.quantity = 'T-GAMMA'
    config.substance = 'A5'
    return config

def test_calnet_measurements_config(calnet_measurements_config):
    assert calnet_measurements_config is not None
    assert calnet_measurements_config.page_size == 10000

#
# http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?Count=10000&typeName=radiation.measurements:MEASUREMENT&version=2.0.0&service=WFS&request=GetFeature&startIndex=0&CQL_FILTER=bbox(location,51,3,52,6) and time > '2016-10-03T04:38:08.000 00:00' and time < '2016-10-03T16:38:08.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'
#
def test_calnet_3600_measurements_zeeland_last12hours(qgis, calnet_measurements_config, bbox):
    calnet_measurements_config.endminusstart = '3600'
    calnet_measurements_config.bbox = bbox['ZEELAND_BBOX']
    end_time = QDateTime.currentDateTime()  # end NOW
    start_time = end_time.addSecs(-60 * 60 * 12)  # xx hours
    calnet_measurements_config.start_datetime = start_time.toString(calnet_measurements_config.date_time_format)
    calnet_measurements_config.end_datetime = end_time.toString(calnet_measurements_config.date_time_format)
    prov = CalnetMeasurementsProvider(calnet_measurements_config)
    def prov_finished(result):
        #print(result.data)
        assert result.error_code == 0
        assert result.data['result'] == 'OK'
        assert result.data['count'] > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_calnet_600_measurements_zeeland_last12hours(qgis, calnet_measurements_config, bbox):
    calnet_measurements_config.endminusstart = '600'
    calnet_measurements_config.bbox = bbox['ZEELAND_BBOX']
    end_time = QDateTime.currentDateTime()  # end NOW
    start_time = end_time.addSecs(-60 * 60 * 12)  # xx hours
    calnet_measurements_config.start_datetime = start_time.toString(calnet_measurements_config.date_time_format)
    calnet_measurements_config.end_datetime = end_time.toString(calnet_measurements_config.date_time_format)
    prov = CalnetMeasurementsProvider(calnet_measurements_config)
    def prov_finished(result):
        #print(result.data)
        assert result.error_code == 0
        assert result.data['result'] == 'OK'
        assert result.data['count'] > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()

def test_calnet_86400_measurements_eu_last36hours(qgis, calnet_measurements_config, bbox):

    calnet_measurements_config.endminusstart = '86400'
    calnet_measurements_config.bbox = bbox['EU_BBOX']
    end_time = QDateTime.currentDateTime()  # end NOW
    start_time = end_time.addSecs(-60 * 60 * 36)  # xx hours
    calnet_measurements_config.start_datetime = start_time.toString(calnet_measurements_config.date_time_format)
    calnet_measurements_config.end_datetime = end_time.toString(calnet_measurements_config.date_time_format)
    prov = CalnetMeasurementsProvider(calnet_measurements_config)
    def prov_finished(result):
        #print(result.data)
        assert result.error_code == 0
        assert result.data['result'] == 'OK'
        assert result.data['count'] > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()

# TODO: create tests for 600 NL, 3600 NL, 600 EU, 3600 EU

def test_measurements_provider_config_to_from_json(calnet_measurements_config):
    # dump config to json
    json_string = calnet_measurements_config.to_json()
    #print(json_string)
    # create a Config from it
    conf_from_json = CalnetMeasurementsConfig.from_json(json_string)
    assert calnet_measurements_config != conf_from_json  # should NOT be the same instance..
    assert conf_from_json.url == calnet_measurements_config.url
    # we probly have cleaned up the outputdir when creating the json
    assert conf_from_json.output_dir == None  # only None field
    assert conf_from_json.page_size == calnet_measurements_config.page_size
    assert conf_from_json.quantity == calnet_measurements_config.quantity
    assert conf_from_json.substance == calnet_measurements_config.substance
    assert conf_from_json.page_size == 10000
    assert conf_from_json.url == calnet_measurements_config.url
    assert conf_from_json.lower_bound == ''
    assert conf_from_json.upper_bound == ''
    assert conf_from_json.bbox == '50,0,60,20'

def test_measurements_provider_config_starttime_endtime(qgis, calnet_measurements_config):
    # dump config to json
    json_string = calnet_measurements_config.to_json()
    # create a Config from it
    conf_from_json = CalnetMeasurementsConfig.from_json(json_string)
    # cleanup endtime
    conf_from_json.end_datetime = ''
    conf_from_json.start_datetime = 'now-600'
    #print(conf_from_json.to_json())
    assert conf_from_json.start_datetime == 'now-600'
    # creation of real datetime strings start/end is in Provider:
    prov = CalnetMeasurementsProvider(conf_from_json)
    start = QDateTime.fromString(prov.config.start_datetime, prov.config.date_time_format)
    # end should be around NOW
    end = QDateTime.fromString(prov.config.end_datetime, prov.config.date_time_format)
    #now = QDateTime.currentDateTime()
    # print('\n'+start.toString(prov.config.date_time_format))
    # print(now.toString(prov.config.date_time_format))
    # print(end.toString(prov.config.date_time_format))
    # print(start.toSecsSinceEpoch())
    # print(now.toSecsSinceEpoch())
    # print(end.toSecsSinceEpoch())
    # print(start)
    # print(now)
    # print(end)
    # print(start)
    # print(now)
    # print(end)
    # print(end.msecsTo(now))
    # TODO FIX TEST !!!!
    #assert (end.msecsTo(now)) < 2000  # 2 secs?
    assert start.msecsTo(end) == 600*1000

def test_measurements_provider_config_zeeland_hster10_from_file(qgis):
    # get a json from the preset dir
    preset = Path(__file__).parents[1] / 'presets' / 'zeeland_laatste_uur_tgamma_a5_10min.json'
    # check if it has a title etc etc
    conf_json = json.load(preset.open())
    # check if the url is OK? OR set it to dev (for testing)
    conf_from_json = CalnetMeasurementsConfig.from_json(conf_json)
    #print(conf_from_json.to_json())

    # create an unique output dirname
    project = "'measurements'"
    path = "'=;=wfs=;=data'"
    output_dir = Utils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
    conf_from_json.output_dir = output_dir

    # try if we get measurements from it
    prov = CalnetMeasurementsProvider(conf_from_json)
    def prov_finished(result):
        #print(result.data)
        assert result.error_code == 0
        assert result.data['result'] == 'OK'
        assert result.data['count'] > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()

def test_measurements_provider_config_nl_hster10_from_file(qgis):
    # get a json from the preset dir
    preset = Path(__file__).parents[1] / 'presets' / 'nl_laatste_uur_tgamma_a5_10min.json'
    # check if it has a title etc etc
    conf_json = json.load(preset.open())
    # check if the url is OK? OR set it to dev (for testing)
    conf_from_json = CalnetMeasurementsConfig.from_json(conf_json)
    #print(conf_from_json.to_json())

    # create an unique output dirname
    project = "'measurements'"
    path = "'=;=wfs=;=data'"
    output_dir = Utils.jrodos_dirname(project, path, datetime.now().strftime("%Y%m%d%H%M%S"))
    conf_from_json.output_dir = output_dir

    # try if we get measurements from it
    prov = CalnetMeasurementsProvider(conf_from_json)
    def prov_finished(result):
        #print(result.data)
        assert result.error_code == 0
        assert result.data['result'] == 'OK'
        assert result.data['count'] > 0
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()

def test_preset_files():
    # p = Path(r'C:\Users\akrio\Desktop\Test').glob('**/*')
    # files = [x for x in p if x.is_file()]
    presets_dir = Path(__file__).parents[1] / 'presets'
    preset_paths = presets_dir.glob('*.json')
    for file in preset_paths:
        assert file.suffix == '.json'





