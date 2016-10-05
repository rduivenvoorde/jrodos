from PyQt4.QtCore import QUrl, QCoreApplication, QDate, QTime, QDateTime
from PyQt4.QtNetwork import QNetworkRequest
from datetime import datetime
from functools import partial
from provider_base import ProviderConfig, ProviderBase, ProviderResult
from utils import Utils
import logging


class JRodosModelOutputConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        #self.url = 'http://localhost:8080/geoserver/wps'
        self.url = 'http://172.19.115.90:8080/geoserver/wps'
        self.user = 'admin'
        self.password = 'geoserver'
        # jrodos_path=  "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"

        # taskArg parameter:
        self.jrodos_project = "'wps-test-3'"
        # dataitem parameter:
        self.jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # this 3 props define the column parameter
        self.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))
        self.jrodos_model_time = 24
        self.jrodos_model_step = 60
        # vertical parameter:
        self.jrodos_verticals = 0  # z / layers
        # actual output format for WPS
        self.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
        self.jrodos_datetime_start = QDateTime(QDate(2016, 05, 17), QTime(6, 0))
        self.jrodos_datetime_format = "yyyy-MM-ddTHH:mm:ss.000 00:00"  # '2016-04-25T08:00:00.000+00:00'
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    def __str__(self):
        return """WPS settings:\n WPS url: {}\n outputdir: {}\n user: {}\n password: {}\n project: {}\n path: {}\n format: {}\n model(hrs): {}\n step(min): {}\n columns: {}\n verticals: {}\n format: {}\n start : {}
        """.format(self.url, self.output_dir, self.user, self.password, self.jrodos_project, self.jrodos_path,
                   self.jrodos_format, self.jrodos_model_time, self.jrodos_model_step, self.jrodos_columns, self.jrodos_verticals, self.jrodos_datetime_format,
                   self.jrodos_datetime_start.toString(self.jrodos_datetime_format))

    @property
    def output_dir(self):
        return Utils.jrodos_dirname(self.jrodos_project, self.jrodos_path, self.timestamp)

    @property
    def jrodos_columns(self):
        return (int(self.jrodos_model_time) * 60) / int(self.jrodos_model_step)  # modeltime*60 / timesteps


class JRodosModelOutputProvider(ProviderBase):
    """A provider which connects using the WPS interface to a Geoserver-enabled JRodos WPS to retrieve
    model output data from projects.

    The JRodos WPS is a normal Geoserver with the addition of a jar and a mount to the JRodos output files
    So often running on something like: http://localhost:8080/geoserver/wps

    The JRodos WPS interface needs 4 parameters:
    taskArg: being the 'project name' from JRodos (WITH single quotes around it !!!)
    dataitem: being the 'datapath' from JRodos (WITH single quotes around it !!!, found via rightclick in JRodos)
    column: being the modelstep, so the first model/time step is column 0 etc etc
    vertical: being the vertical layers of a model (IF applicable, in this case always 0)

    The actual request is a WPS XML-request sent as a http-POST

    Using the WPS plugin you can for example test the WPS interface. Note the WPS can have different return format:
    For example GML or zipped shapefiles.
    Would be nice if in future we could retrieve all columns in one geopackage format :-)

    Current implementation uses zipped shapefiles, and saves these in a uniquely named directory in the temp-dir of the
    user, named as: column_vertical.zip (so 0_0.zip, 1_0.zip etc etc)

    Note that the WPS outputs one zipfile being a (model) grid with cells with just two columns: Cell and Value
    So the application is actually responsible for adding a time-column to the data. That is why for the loading of
    the shapefiles we actually need a 'Datetime' AND the number of timesteps AND the length (in minutes) of the
    modelsteps. The application adds this information in a column named 'Datetime'

    There is also a 'self.txt' text file saved in the directory, to see/check which parameters are used.


    """
    def __init__(self, config):
        ProviderBase.__init__(self, config)
        self.column = 0

    def _data_retrieved(self, reply, filename):
        """
        Private method which concurrently calls the get_data while not all needed timesteps are in.
        Note: looks like in this signal method the self.config is not available anymore in the last run... That is
        why we add the full filename in the call
        :param reply: ProviderResult object
        :param filename: is build earlier and added here in the call because it got cleaned up (by garbage collection?)
        :return:
        """
        result = ProviderResult()
        if reply.error():
            result.set_error(reply.error(), reply.request().url().toString(), 'JRodos model output provider (WPS)')
            # OK, we have an error... emit the result + error here and quit the loading loop
            self.ready = True
            self.finished.emit(result)
            return
        else:
            with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed
                f.write(reply.readAll())

        # note self.column will live long enough to be used here
        self.column += 1
        if self.column < self.config.jrodos_columns:
            self.get_data()
        else:
            logging.debug('All model steps received; stop fetching, start loading...')
            result.set_data({'result': 'OK', 'output_dir': self.config.output_dir}, reply.url().toString())
            # we need to wait untill all pages are there before to emit the result; so: INSIDE de loop
            self.ready = True
            self.finished.emit(result)

    def get_data(self):

        if self.column == 0:
            # write settings to file in output dir to be able to do some checking
            wps_settings_file = self.config.output_dir + '/wps_settings.txt'
            with open(wps_settings_file, 'wb') as f:
                f.write(unicode(self.config))

        # NOTE 1 !!! 'project' parameter surrounded by single quotes in this request ??????
        # NOTE 2 !!! 'path' parameter surrounded by single quotes in this request ??????

        xml = """<?xml version="1.0" encoding="UTF-8"?>
                <wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs"
                  xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1"
                  xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc"
                  xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink"
                  xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
                  <ows:Identifier>gs:JRodosWPS</ows:Identifier>
                  <wps:DataInputs>
                    <wps:Input>
                      <ows:Identifier>taskArg</ows:Identifier>
                      <wps:Data>
                        <wps:LiteralData>project="'{project}'"</wps:LiteralData>
                      </wps:Data>
                    </wps:Input>
                    <wps:Input>
                      <ows:Identifier>dataitem</ows:Identifier>
                      <wps:Data>
                        <wps:LiteralData>path="'{path}'"</wps:LiteralData>
                      </wps:Data>
                    </wps:Input>
                    <wps:Input>
                      <ows:Identifier>column</ows:Identifier>
                      <wps:Data>
                        <wps:LiteralData>{column}</wps:LiteralData>
                      </wps:Data>
                    </wps:Input>
                    <wps:Input>
                      <ows:Identifier>vertical</ows:Identifier>
                      <wps:Data>
                        <wps:LiteralData>{vertical}</wps:LiteralData>
                      </wps:Data>
                    </wps:Input>
                  </wps:DataInputs>
                  <wps:ResponseForm>
                    <wps:RawDataOutput mimeType="{format}">
                      <ows:Identifier>result</ows:Identifier>
                    </wps:RawDataOutput>
                  </wps:ResponseForm>
                </wps:Execute>
                """
        data = xml.format(project=self.config.jrodos_project,
                                   path=self.config.jrodos_path,
                                   format=self.config.jrodos_format,
                                   column=unicode(self.column),
                                   vertical=unicode(self.config.jrodos_verticals))

        request = QNetworkRequest(QUrl(self.config.url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'text/xml')  # or? "text/xml; charset=utf-8"
        reply = self.network_manager.post(request, data)
        filename = self.config.output_dir + '/' + unicode(self.column) + '_' + unicode(
            self.config.jrodos_verticals) + '.zip'
        reply.finished.connect(partial(self._data_retrieved, reply, filename))
        # # this part is needed to be sure we do not return immidiatly
        # while not reply.isFinished():
        #     QCoreApplication.processEvents()
