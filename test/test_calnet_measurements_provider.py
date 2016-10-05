import unittest
from providers.calnet_measurements_provider import CalnetMeasurementsConfig, CalnetMeasurementsProvider
from providers.utils import Utils
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication, QDateTime
from datetime import datetime

class TestCalnetMeasurementsProvider(TestProviderBase):


    def setUp(self):
        TestProviderBase.setUp(self)

        self.config = CalnetMeasurementsConfig()
        self.config.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
        # we have always an wps_settings.output_dir here:
        self.config.output_dir = Utils.jrodos_dirname('test_WFS_Meaurements', "", datetime.now().strftime("%Y%m%d%H%M%S"))
        self.config.page_size = 10000  # 10000
        self.config.quantity = 'T-GAMMA'
        self.config.substance = 'A5'

        self.ZEELAND_BBOX = '51,3,52,6'  # south Netherlands
        self.EU_BBOX = '38,-8,61,30' # europe

        # BBOX, start and endtime to be set in test !!!



    def test_calnet_measurements_config(self):
        c = unicode(self.config)

        self.assertIsNotNone(c)
        self.assertIsNot(len(c), 0)
        print c

    #
    # http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?Count=10000&typeName=radiation.measurements:MEASUREMENT&version=2.0.0&service=WFS&request=GetFeature&startIndex=0&CQL_FILTER=bbox(location,51,3,52,6) and time > '2016-10-03T04:38:08.000 00:00' and time < '2016-10-03T16:38:08.000 00:00' and endTime-startTime=3600 and quantity='T-GAMMA' and substance='A5'
    #
    def test_calnet_3600_measurements_zeeland_last12hours(self):

        self.config.endminusstart = '3600'
        self.config.bbox = self.ZEELAND_BBOX
        end_time = QDateTime.currentDateTime()  # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # xx hours
        self.config.start_datetime = start_time.toString(self.config.date_time_format)
        self.config.end_datetime = end_time.toString(self.config.date_time_format)

        prov = CalnetMeasurementsProvider(self.config)
        def prov_finished(result):
            self.assertFalse(result.error())
            self.assertIsNot(result.data['count'], 0, "No 3600 measurements in Zeeland, last 12 hours")
        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_calnet_600_measurements_zeeland_last12hours(self):

        self.config.endminusstart = '600'
        self.config.bbox = self.ZEELAND_BBOX
        end_time = QDateTime.currentDateTime()  # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # xx hours
        self.config.start_datetime = start_time.toString(self.config.date_time_format)
        self.config.end_datetime = end_time.toString(self.config.date_time_format)

        prov = CalnetMeasurementsProvider(self.config)

        def prov_finished(result):
            self.assertFalse(result.error())
            self.assertIsNot(result.data['count'], 0, "No 600 measurements in Zeeland, last 12 hours")

        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    def test_calnet_86400_measurements_eu_last36hours(self):

        self.config.endminusstart = '86400'
        self.config.bbox = self.EU_BBOX
        end_time = QDateTime.currentDateTime()  # end NOW
        start_time = end_time.addSecs(-60 * 60 * 36)  # xx hours
        self.config.start_datetime = start_time.toString(self.config.date_time_format)
        self.config.end_datetime = end_time.toString(self.config.date_time_format)

        prov = CalnetMeasurementsProvider(self.config)

        def prov_finished(result):
            self.assertFalse(result.error())
            self.assertIsNot(result.data['count'], 0, "No 86400 measurements in EU, last 36 hours")

        prov.finished.connect(prov_finished)
        prov.get_data()
        while not prov.is_finished():
            QCoreApplication.processEvents()

    # TODO: create tests for 600 NL, 3600 NL, 600 EU, 3600 EU

if __name__ == '__main__':
    unittest.main()
