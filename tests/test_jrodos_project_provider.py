import pytest
import os
from ..providers.jrodos_project_provider import (
    JRodosProjectConfig,
    JRodosProjectProvider,
)
from qgis.PyQt.QtCore import QCoreApplication

"""
To test the WPS:

Create a valid request.xml (see below or in your /tmp/ dir)
Use curl:
  # NOTE the @-sign in the -d option (meaning FILE)
  # NOTE because a binary ZIP is returned, use --output to save to file 
  curl -v -XPOST -H "Content-Type: Content-Type: text/xml" -d @request.xml --output data.zip "http://geoserver.dev.cal-net.nl/geoserver/wps"
"""


def test_jrodos_project_url(qgis):
    def prov_finished(result):
        # check for extendedProjectInfo
        assert 'extendedProjectInfo' in result.data
        extendedProjectInfo = result.data['extendedProjectInfo']
        assert 'startOfRelease' in extendedProjectInfo
        assert 'startOfPrognosis' in extendedProjectInfo
        # get first dataitem form first task from first project
        dataitems = result.data['tasks'][0]['dataitems']
        assert 577 == len(dataitems)
        one_item = dataitems[361]
        unit = one_item['unit']
        assert unit == 'mSv/h'
    conf = JRodosProjectConfig()
    conf.url = 'http://jrodos.dev.cal-net.nl/rest/jrodos/projects/2532'
    prov = JRodosProjectProvider(conf)
    prov.finished.connect(prov_finished)
    prov.get_data()
    # IMPORTANT without this the provider finishes immidiatly without errors.... SO IT SEEMS ALL IS FINE THEN???!!!
    while not prov.is_finished():
        QCoreApplication.processEvents()


# skipping because timeout takes too long to wait on :-)
def test_jrodos_project_url_NOK(qgis):
    conf = JRodosProjectConfig()
    conf.url = 'https://duif.net/project1268.foo'
    prov = JRodosProjectProvider(conf)
    def prov_finished(result):
        # wrong url, so should error with 203
        assert result.error() is True
        assert result.error_code == 203
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_jrodos_project_file(qgis):
    conf = JRodosProjectConfig()
    # find dir of this class
    conf.url = 'file://' + os.path.join(os.path.dirname(__file__), 'project1268.json')
    prov = JRodosProjectProvider(conf)
    def prov_finished(result):
        # check for extendedProjectInfo
        assert 'extendedProjectInfo' in result.data
        extendedProjectInfo = result.data['extendedProjectInfo']
        assert 'startOfRelease' in extendedProjectInfo
        assert 'startOfPrognosis' in extendedProjectInfo
        # get first dataitem form first task from first project
        dataitems = result.data['tasks'][0]['dataitems']
        assert 569 == len(dataitems)
        one_item = dataitems[42]
        unit = one_item['unit']
        assert unit == 'Bq/m²'
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_jrodos_projects_url(qgis):
    conf = JRodosProjectConfig()
    # something going on here with redirects
    conf.url = 'http://jrodos.dev.cal-net.nl/rest/jrodos/'
    prov = JRodosProjectProvider(conf)
    def prov_finished(result):
        assert result.data is not None
        assert 'content' in result.data
        assert 'projectId' in result.data['content'][0]
        assert 'name' in result.data['content'][0]
        assert 'username' in result.data['content'][0]
        assert 'modelchainname' in result.data['content'][0]
    prov.finished.connect(prov_finished)
    prov.get_data('/projects')
    while not prov.is_finished():
        QCoreApplication.processEvents()


def test_jrodos_projects_file(qgis):
    conf = JRodosProjectConfig()
    # find dir of this class
    conf.url = 'file://' + os.path.join(os.path.dirname(__file__), 'projects.json')
    prov = JRodosProjectProvider(conf)
    def prov_finished(result):
        assert result.data is not None
        assert 'content' in result.data
        assert 'projectId' in result.data['content'][0]
        assert 'name' in result.data['content'][0]
        assert 'username' in result.data['content'][0]
        assert 'modelchainname' in result.data['content'][0]
    prov.finished.connect(prov_finished)
    prov.get_data()
    while not prov.is_finished():
        QCoreApplication.processEvents()

