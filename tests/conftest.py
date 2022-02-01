import pytest
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsApplication

# the qgis fixture is shared as module fixture here over all tests
@pytest.fixture(scope='module')
def qgis():
    # to see how to setup a qgis app in pyqgis
    # https://hub.qgis.org/issues/13494#note-19
    os.environ["QGIS_DEBUG"] = str(-1)
    QCoreApplication.setOrganizationName('QGIS')
    QCoreApplication.setApplicationName('QGIS3')
    QgsApplication.setPrefixPath(os.getenv("QGIS_PREFIX_PATH"), True)
    #QgsApplication.setAuthDbDirPath('/home/richard/.qgis2/')

    # ARGH... proxy, be sure that you have proxy enabled in QGIS IF you want to test within rivm (behind proxy)
    # else it keeps hanging/running after the tests

    # Duh... there can only be one QApplication at a time
    # http://stackoverflow.com/questions/10888045/simple-ipython-example-raises-exception-on-sys-exit
    # if you do create >1 QgsApplications (QtApplications) then you will have non exit code 0
    qgs = QgsApplication([], False)
    qgs.initQgis()  # nessecary for opening auth db etc etc
    return qgs
