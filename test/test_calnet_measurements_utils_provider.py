import unittest
from providers.calnet_measurements_utils_provider import CalnetMeasurementsUtilsConfig, CalnetMeasurementsUtilsProvider
from test_provider_base import TestProviderBase
from qgis.PyQt.QtCore import QCoreApplication

class TestCalnetMeasurementsUtilsProvider(TestProviderBase):



    def setUp(self):
        TestProviderBase.setUp(self)
        self.config = CalnetMeasurementsUtilsConfig()
        self.config.url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'
        self.prov = CalnetMeasurementsUtilsProvider(self.config)

    #@unittest.skip
    def test_calnet_measurements_quantities(self):
        def prov_finished(result):
            # TODO some better testing here
            # [{'code': 'ZR-97', 'description': 'ZIRCONIUM-97 (ZR-97)'}, ...
            print(result)
        self.prov.finished.connect(prov_finished)
        self.prov.get_data('Quantities')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()

    # @unittest.skip
    # def test_calnet_measurements_quantities_NOK(self):
    #     self.config.url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilServic'
    #     self.prov = CalnetMeasurementsUtilsProvider(self.config)
    #     def data_in(data):
    #         # TODO some better testing here
    #         print data
    #         self.assertIsNotNone(data)
    #     self.prov.finished.connect(data_in)
    #     self.prov.get_data('Quantities')
    #     # try:
    #     #     #with self.assertRaises(ProviderNetworkException):
    #     #         self.prov.get_data('Quantities')
    #     # except:
    #     #     pass
    #     while not self.prov.is_finished():
    #         QCoreApplication.processEvents()

    #@unittest.skip
    def test_calnet_measurements_substances(self):
        def prov_finished(result):
            # [{'code': 'C501', 'description': 'JUICE - FRUIT UNSPECIFIED (C501)'}, ...
            # TODO some better testing here
            print(result)
        self.prov.finished.connect(prov_finished)
        self.prov.get_data('Substances')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()

    #@unittest.skip
    def test_calnet_measurements_units(self):
        def prov_finished(result):
            # TODO some better testing here
            # [{'code': ' ', 'description': 'BLANKFIELD ( )'}, {'code': '%', 'description': 'PERCENTAGE (%)'},
            print(result)
        self.prov.finished.connect(prov_finished)
        self.prov.get_data('Units')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()

    # @unittest.skip
    def test_calnet_quantity_substance_combis(self):
        def prov_finished(result):
            # TODO some better testing here
            # [{'substance': 'T-ALFA-ART', 'description': 'OUTDOOR AIR - TOTAL ARTIFICIAL ALPHA (A11 - T-ALFA-ART)', 'quantity': 'A11'}, {'substance': 'T-ALFA-NAT', 'description': 'OUTDOOR AIR - TOTAL NATURAL ALPHA (A11 - T-ALFA-NAT)', 'quantity': 'A11'},
            # [{'substance': 'T-ALFA-ART', 'description': 'OUTDOOR AIR (A11) , TOTAL ARTIFICIAL ALPHA (T-ALFA-ART)', 'quantity': 'A11'},

            #  {"quantity":"T-GAMMA","quantity_desc":"TOTAL GAMMA","substance":"A5","substance_desc":"EXTERNAL RADIATION","unit":"NGY/H"}

            print(result)
        self.prov.finished.connect(prov_finished)
        self.prov.get_data('MeasuredCombinations', '2019-01-06T12:00:00.000Z', '2019-05-06T12:00:00.000Z')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()

if __name__ == '__main__':
    unittest.main()
