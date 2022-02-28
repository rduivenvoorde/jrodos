import pytest
from qgis.PyQt.QtCore import QCoreApplication
from ..providers.calnet_measurements_utils_provider import (
    CalnetMeasurementsUtilsConfig,
    CalnetMeasurementsUtilsProvider,
)
from ..providers.provider_base import (
    ProviderResult,
)

@pytest.fixture
def calnet_measurements_utils_provider():
    config = CalnetMeasurementsUtilsConfig()
    config.url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'
    prov = CalnetMeasurementsUtilsProvider(config)
    return prov


def test_calnet_measurements_quantities(qgis, calnet_measurements_utils_provider):
    def prov_finished(result):
        # [{'code': 'ZR-97', 'description': 'ZIRCONIUM-97 (ZR-97)'}, ...
        assert result.error_code == 0
        assert isinstance(result, ProviderResult)
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        assert len(result.data) == 121
        #print(result)
    calnet_measurements_utils_provider.finished.connect(prov_finished)
    calnet_measurements_utils_provider
    calnet_measurements_utils_provider.get_data('Quantities')
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not calnet_measurements_utils_provider.is_finished():
        QCoreApplication.processEvents()

def test_calnet_measurements_quantities_NOK(qgis):
    def data_in(data):
        # TODO some better testing here
        #print(data)
        assert data is not None
        assert data.error_code == 203
        assert data.url == 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilServicxxx'
    config = CalnetMeasurementsUtilsConfig()
    config.url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilServicxxx'
    prov = CalnetMeasurementsUtilsProvider(config)
    prov.finished.connect(data_in)
    prov.get_data('Quantities')
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_calnet_measurements_substances(qgis, calnet_measurements_utils_provider):
    def prov_finished(result):
        # [{'code': 'C501', 'description': 'JUICE - FRUIT UNSPECIFIED (C501)'}, ...
        #print(result)
        assert result.error_code == 0
        assert isinstance(result, ProviderResult)
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        assert len(result.data) == 804
        #print(f'FINISHED: {len(result.data)} items!')
    calnet_measurements_utils_provider.finished.connect(prov_finished)
    calnet_measurements_utils_provider.get_data('Substances')
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not calnet_measurements_utils_provider.is_finished():
        QCoreApplication.processEvents()


def test_calnet_measurements_units(qgis, calnet_measurements_utils_provider):
    def prov_finished(result):
        # [{'code': ' ', 'description': 'BLANKFIELD ( )'}, {'code': '%', 'description': 'PERCENTAGE (%)'},
        assert result.error_code == 0
        assert isinstance(result, ProviderResult)
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        assert len(result.data) == 63
        #print(result)
    calnet_measurements_utils_provider.finished.connect(prov_finished)
    calnet_measurements_utils_provider.get_data('Units')
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not calnet_measurements_utils_provider.is_finished():
        QCoreApplication.processEvents()

def test_calnet_quantity_substance_combis(qgis, calnet_measurements_utils_provider):
    def prov_finished(result):
        # [{'substance': 'T-ALFA-ART', 'description': 'OUTDOOR AIR (A11) , TOTAL ARTIFICIAL ALPHA (T-ALFA-ART)', 'quantity': 'A11'},
        #  {"quantity":"T-GAMMA","quantity_desc":"TOTAL GAMMA","substance":"A5","substance_desc":"EXTERNAL RADIATION","unit":"NGY/H"},
        #  ...
        #  ]
        # actual returned data is XML, but parsed to object tree / json like structure
        assert result.error_code == 0
        assert isinstance(result, ProviderResult)
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        #assert len(result.data) == 6  # off course depending on time of asking?
    calnet_measurements_utils_provider.finished.connect(prov_finished)
    calnet_measurements_utils_provider.get_data('MeasuredCombinations', '2022-01-06T12:00:00.000Z', '2022-05-06T12:00:00.000Z')
    while not calnet_measurements_utils_provider.is_finished():
        QCoreApplication.processEvents()

