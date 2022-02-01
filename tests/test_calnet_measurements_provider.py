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
