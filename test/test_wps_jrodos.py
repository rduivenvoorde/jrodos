import unittest

from data_worker import WpsSettings, WpsDataWorker
from PyQt4.QtCore import QObject, pyqtSignal, QSettings, QThread, QDate, QTime, QDateTime
from PyQt4.QtGui import QApplication
import urllib, urllib2, sys, shutil, re, signal
from datetime import date, time, datetime
from utils import Utils


class TestJRodosWPS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        wps_settings = WpsSettings()
        wps_settings.url = 'http://localhost:8080/geoserver/wps'
        # jrodos_path=  "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        wps_settings.jrodos_project = "'wps-test-3'"
        wps_settings.jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        wps_settings.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
        #wps_settings.jrodos_model_time = 24
        wps_settings.jrodos_model_time = 2
        wps_settings.jrodos_model_step = 60
        wps_settings.jrodos_verticals = 0  # z / layers
        wps_settings.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))

        self.wps_settings = wps_settings

    # def test_WPS_is_up(self):
    #     try:
    #         response = urllib2.urlopen(self.wps_settings.url, timeout=1)
    #     except urllib2.URLError as err:
    #         self.fail('Error in TestJRodosWPS.test_WPS_JRodos %s' % err.reason)


    @unittest.skip
    def test_WPS_JRodos(self):

        try:
            response = urllib2.urlopen(self.wps_settings.url, timeout=1)
        except urllib2.URLError as err:
            self.fail('Failed to connect to %s. Reason: %s' % (self.wps_settings.url, err.reason))
            return


        def wps_progress(ret):
            print('wps progress: {}'.format(ret))
            self.assertEquals(True, True)

        def wps_finished(ret):
            print('wps finished: {}'.format(ret))
            self.assertEquals(True, True)

        def error(err):
            print err
            self.fail('Error in TestJRodosWPS.test_WPS_JRodos')

        w2 = WpsDataWorker(self.wps_settings)
        w2.progress.connect(wps_progress)
        w2.finished.connect(wps_finished)

        w2.run()

if __name__ == '__main__':
    unittest.main()
