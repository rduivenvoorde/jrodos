import unittest

from data_worker import WfsSettings, WfsDataWorker
from PyQt4.QtCore import QObject, pyqtSignal, QSettings, QThread, QDate, QTime, QDateTime
from PyQt4.QtGui import QApplication
import urllib, urllib2, sys, shutil, re, signal
from datetime import date, time, datetime
from utils import Utils


class TestMeasurementsWFS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):

        wfs_settings = WfsSettings()
        wfs_settings.url = 'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'
        # we have always an wps_settings.output_dir here:
        wfs_settings.output_dir = Utils.jrodos_dirname('test_WFS_Meaurements', "", datetime.now().strftime("%Y%m%d%H%M%S")) # wps_settings.output_dir()
        wfs_settings.page_size = 10000
        #wfs_settings.start_datetime = '2016-04-25T08:00:00.000+00:00'
        #wfs_settings.end_datetime = '2016-04-26T08:00:00.000+00:00'
        # wfs_settings.start_datetime = '2016-05-16T06:52:00.000+00:00'
        # wfs_settings.end_datetime = '2016-05-17T06:52:00.000+00:00'
        wfs_settings.start_datetime = '2016-09-13T08:00:00.000+00:00'
        wfs_settings.end_datetime = '2016-09-13T11:00:00.000+00:00'
        wfs_settings.endminusstart = '3600'
        wfs_settings.quantity = 'T-GAMMA'
        wfs_settings.substance = 'A5'
        wfs_settings.bbox = '50,3,54,8' # '55,5,60,15'
        self.wfs_settings = wfs_settings

        self.wfs_progress_called = False
        self.wfs_finish_called = False


    def test_WFS_Meaurements(self):

        try:
            response = urllib2.urlopen(self.wfs_settings.url, timeout=1)
        except urllib2.URLError as err:
            self.fail('Failed to connect to %s. Reason: %s' % (self.wfs_settings.url, err.reason))
            return

        def wfs_progress(ret):
            #print('wfs progress: {}'.format(ret))
            self.assertTrue(ret > 0)
            self.assertTrue (ret <= 1)
            self.wfs_progress_called = True

        def wfs_finished(ret):
            print('wfs finished: {}'.format(ret))
            self.wfs_finish_called = True
            # ret should be something like: {'result': 'OK', 'output_dir': u'/tmp/test_WFS_Meaurements_20160913112516'}
            self.assertTrue(ret['result'] == 'OK')
            self.assertTrue(len(ret['output_dir']) > 0)

        def error(err):
            print err
            self.fail('Error in test_WFS_Meaurements')

        print self.wfs_settings

        w = WfsDataWorker(self.wfs_settings)
        w.finished.connect(wfs_finished)
        w.error.connect(error)
        w.progress.connect(wfs_progress)
        w.run()

        self.assertTrue(self.wfs_progress_called)
        self.assertTrue(self.wfs_finish_called)


if __name__ == '__main__':
    unittest.main()
