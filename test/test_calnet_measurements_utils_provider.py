import unittest
from providers.provider_base import ProviderNetworkException
from providers.calnet_measurements_utils_provider import CalnetMeasurementsUtilsConfig, CalnetMeasurementsUtilsProvider
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication

class TestCalnetMeasurementsUtilsProvider(TestProviderBase):

    def setUp(self):
        TestProviderBase.setUp(self)
        self.config = CalnetMeasurementsUtilsConfig()
        self.config.url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'
        self.prov = CalnetMeasurementsUtilsProvider(self.config)

    def test_calnet_measurements_quantities(self):
        def data_in(data):
            # TODO some better testing here
            print data
        self.prov.finished.connect(data_in)
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

    def test_calnet_measurements_substances(self):
        def data_in(data):
            # TODO some better testing here
            print data

        self.prov.finished.connect(data_in)
        self.prov.get_data('Substances')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()


    def test_calnet_measurements_units(self):
        def data_in(data):
            # TODO some better testing here
            print data

        self.prov.finished.connect(data_in)
        self.prov.get_data('Units')
        while not self.prov.is_finished():
            QCoreApplication.processEvents()

if __name__ == '__main__':
    unittest.main()
