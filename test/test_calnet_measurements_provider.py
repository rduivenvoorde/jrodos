import unittest
from providers.calnet_measurements_provider import CalnetMeasurementsConfig, CalnetMeasurementsProvider
from utils import Utils
from test_provider_base import TestProviderBase
from PyQt4.QtCore import QCoreApplication, QDateTime
from datetime import datetime

class TestCalnetMeasurementsProvider(TestProviderBase):
    #
    # http: // geoserver.dev.cal - net.nl / geoserver / radiation.measurements / ows?Count = 10000 & typeName = radiation.measurements:MEASUREMENT & version = 2.0
    # .0 & service = WFS & request = GetFeature & startIndex = 0 & CQL_FILTER = bbox(location, 49.5851036976,
    #                                                                                -1.18217557141, 53.064331682,
    #                                                                                9.61846386682) and time > '2016-09-29T03:48:45.000 00:00' and time < '2016-09-29T15:48:45.000 00:00' and endTime - startTime = 3600 and quantity = 'T-GAMMA' and substance = 'A5'

    def test_calnet_measurements_url(self):
        config = CalnetMeasurementsConfig()
        config.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
        # we have always an wps_settings.output_dir here:
        config.output_dir = Utils.jrodos_dirname('test_WFS_Meaurements', "", datetime.now().strftime("%Y%m%d%H%M%S"))
        config.page_size = 10000 # 10000
        config.endminusstart = '3600'
        #config.endminusstart = '600'
        config.quantity = 'T-GAMMA'
        config.substance = 'A5'
        config.bbox = '51,3,52,6'  # south Netherlands
        #config.bbox = '38,-8,61,30' # europe
        end_time = QDateTime.currentDateTime()  # end NOW
        start_time = end_time.addSecs(-60 * 60 * 12)  # xx hours
        # config.start_datetime = '2016-04-25T08:00:00.000+00:00'
        # config.end_datetime = '2016-04-26T08:00:00.000+00:00
        config.start_datetime = start_time.toString(config.date_time_format)
        config.end_datetime = end_time.toString(config.date_time_format)

        prov = CalnetMeasurementsProvider(config)

        # TODO!!! for now using urllib, but should move to QgsNetworkManager
        def prov_finished(result):
            print "DONE !!!"
        prov.finished.connect(prov_finished)
        prov.get_data()

        while not prov.is_finished():
            QCoreApplication.processEvents()


    # TODO: create tests for 600 NL, 3600 NL, 600 EU, 3600 EU

if __name__ == '__main__':
    unittest.main()
