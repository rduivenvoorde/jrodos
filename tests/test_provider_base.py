import pytest
import os
from qgis.PyQt.QtCore import QCoreApplication
from ..providers.provider_base import (
    ProviderBase,
    SimpleProvider,
    SimpleConfig,
)

def test_qgs_OK(qgis):
    out = qgis.showSettings()
    # print(out)
    assert len(out) > 0

def test_config_None():
    conf = None
    with pytest.raises(TypeError) as e:
        ProviderBase(conf)
    assert e.typename == 'TypeError'

def test_config_NOK():
    conf = SimpleConfig()
    conf.url = None
    with pytest.raises(TypeError) as e:
        ProviderBase(conf)
    assert e.typename == 'TypeError'

# # only working if proxy is set (when at RIVM), disable for now
#@pytest.mark.skip
# IMPORTANT !!!!!! BECAUSE PROVIDER USE QGIS CLASSES YOU NEED TO HAVE QGIS AROUND VIA FIXTURE ELSE SEGFAULTS!!!!!
def test_simple_url(qgis):
    conf = SimpleConfig()
    conf.url = 'https://duif.net/'
    prov = SimpleProvider(conf)
    def prov_finished(result):
        assert result.error() is False
        assert result.data.strip() == 'ok'
        #print(' Finished test_simple_url...')
    prov.finished.connect(prov_finished)
    prov.get_data()
    # while not prov.is_finished():
    #     QCoreApplication.processEvents()

# # only working if proxy is set (when at RIVM), disable for now
#@pytest.mark.skip
# IMPORTANT !!!!!! BECAUSE PROVIDER USE QGIS CLASSES YOU NEED TO HAVE QGIS AROUND VIA FIXTURE ELSE SEGFAULTS!!!!!
def test_simple_NOK_url(qgis):
    conf = SimpleConfig()
    conf.url = 'htps://duif.net/'
    with pytest.raises(TypeError) as e:
        ProviderBase(conf)
    assert e.typename == 'TypeError'

# IMPORTANT !!!!!! BECAUSE PROVIDER USE QGIS CLASSES YOU NEED TO HAVE QGIS AROUND VIA FIXTURE ELSE SEGFAULTS!!!!!
def test_simple_file(qgis):
#@pytest.mark.skip
    conf = SimpleConfig()
    # find dir of this class
    conf.url = 'file://'+os.path.join('file://', os.path.dirname(__file__), 'duif.net')
    prov = SimpleProvider(conf)
    def prov_finished(result):
        assert result.error() is True
        assert result.error_code == 203  # NetworkError
        assert result.data is None
    prov.finished.connect(prov_finished)
    prov.get_data()
    # while not prov.is_finished():
    #     QCoreApplication.processEvents()


# OK, for now: NOT serializing to xml, as it needs modules (lxml and etree)
# https://lxml.de/objectify.html
# which are by default not packaged in QGIS...
# SO: going the json route for now...
# def test_simple_provider_to_xml():
#     conf = SimpleConfig()
#     conf.url = 'htps://duif.net/'
#     print(conf.to_xml())


def test_simple_provider_config_to_from_json():
    conf = SimpleConfig()
    conf.url = 'https://duif.net/'
    # dump config to json
    json_string = conf.to_json()
    #print(json_string)
    # create a Config from it
    conf_from_json = SimpleConfig.from_json(json_string)
    assert conf_from_json.url == 'https://duif.net/'
