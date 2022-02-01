from qgis.PyQt.QtCore import QUrl, QDate, QTime, QDateTime
from qgis.PyQt.QtNetwork import QNetworkRequest
from datetime import datetime
from functools import partial
import json
import re
from .provider_base import ProviderConfig, ProviderBase, ProviderResult
from .utils import Utils

import logging
log = logging.getLogger('JRodos3 Plugin')

"""
To test the WPS:

Create a valid request.xml (see below or in your /tmp/ dir)
Use curl:
  # NOTE the @-sign in the -d option (meaning FILE)
  # NOTE because a binary ZIP is returned, use --output to save to file 
  curl -v -XPOST -H "Content-Type: Content-Type: text/xml" -d @request.xml --output data.zip "http://geoserver.dev.cal-net.nl/geoserver/wps"
"""

class JRodosModelOutputConfig(ProviderConfig):
    def __init__(self):
        ProviderConfig.__init__(self)
        self.url = 'http://localhost:8080/geoserver/wps'
        #self.url = 'http://172.19.115.90:8080/geoserver/wps'
        self.wps_id = 'gs:JRodosGeopkgWPS'  # gs:JRodosWPS = one zipped shapefile, gs:JRodosGeopkgWPS = one GeoPackage
        self.user = 'admin'
        self.password = 'geoserver'
        # taskArg parameter:
        self.jrodos_project = "'wps-test-3'"
        # dataitem parameter:
        self.jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # jrodos_path=  "'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'"  # 1
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Air concentration, time integrated near ground surface=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=I -135'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground contamination dry+wet=;=Cs-137'" # 24
        # jrodos_path = "'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'"
        # this 3 props define the column parameter
        self.jrodos_datetime_start = QDateTime(QDate(2016, 5, 17), QTime(6, 0))
        self.jrodos_model_time = -1  # IN MINUTES !
        self.jrodos_model_step = 3600  # IN SECONDS !
        self.jrodos_columns = 0  # starting at 0, but can also be a range: '0,' '0-23', '0-'
        # vertical parameter:
        self.jrodos_verticals = 0  # z / layers
        # actual output format for WPS
        self.jrodos_format = "application/zip"  # format = "application/zip" "text/xml; subtype=wfs-collection/1.0"
        self.jrodos_datetime_start = QDateTime(QDate(2016, 5, 17), QTime(6, 0))
        self.jrodos_datetime_format = "yyyy-MM-ddTHH:mm:ss.000 00:00"  # '2016-04-25T08:00:00.000+00:00'
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%f")
        self.units = ''

    def __str__(self):
        return u"""WPS settings:\n WPS id: {}\n WPS url: {}\n outputdir: {}\n user: {}\n password: {}\n project: {}\n path: {}\n format: {}\n modeltime(minutes): {} ({} hours)\n step(seconds): {} ({} minutes)\n columns: {}\n verticals: {}\n format: {}\n start : {}\n units : {}
        """.format(self.wps_id, self.url, self.output_dir, self.user, self.password, self.jrodos_project, self.jrodos_path,
                   self.jrodos_format, self.jrodos_model_time, self.jrodos_model_time/60, self.jrodos_model_step, self.jrodos_model_step/60, self.jrodos_columns, self.jrodos_verticals, self.jrodos_datetime_format,
                   self.jrodos_datetime_start.toString(self.jrodos_datetime_format), self.units)

    def __bytes__(self):
        return str(self).encode('utf-8')


    @property
    def output_dir(self):
        return Utils.jrodos_dirname(self.jrodos_project, self.jrodos_path, self.timestamp)


class JRodosModelProvider(ProviderBase):
    """A provider which connects using the WPS interface to a Geoserver-enabled JRodos WPS to retrieve
    model input from projects (timestep, modeltime etc).

    The JRodos WPS is a normal Geoserver with the addition of a jar and a mount to the JRodos output files
    So often running on something like: http://localhost:8080/geoserver/wps

    The JRodos WPS interface needs 4 parameters:
    taskArg: being the 'project name' from JRodos (WITH single quotes around it !!!)
    dataitem: being the 'datapath' from JRodos (WITH single quotes around it !!!, found via rightclick in JRodos)
    column: being the modelstep, so the first model/time step is column 0 etc etc
    vertical: being the vertical layers of a model (IF applicable, in this case always 0)
    threshold: a possible filter for data, use -1 for NO filter. For models 0 is used to filter out zero values.

    The actual request is a WPS XML-request sent as a http-POST

    Using the WPS plugin you can for example test the WPS interface. Note the WPS can have different return format:
    For example GML, a zipped shapefiles or a zipped Geopacakge

    Old WPS implementation uses zipped shapefiles, and saves these in a uniquely named directory in the temp-dir of the
    user, named as: column_vertical.zip (so 0_0.zip, 1_0.zip etc etc)
    Newer WPS implementations return a zipped shapefile with all timestep data in one shapefile, or a geopackage
    with 3 tables: the grid used, the data and a view which relates these to have the time-data.

    Note that the WPS outputs one zipfile being a (model) grid with cells with just two columns: Cell and Value
    So the application is actually responsible for adding a time-column to the data. That is why for the loading of
    the shapefiles we actually need a 'Datetime' AND the number of timesteps AND the length (in minutes) of the
    modelsteps. The application adds this information in a column named 'Datetime'

    There is also a 'jrodos_output_settings.txt' text file saved in the directory, to see/check which parameters are used.

    """
    def __init__(self, config):
        ProviderBase.__init__(self, config)
        # if config.jrodos_columns.isdigit():
        #     # this means a number(!) of columns is given, and we receive them one by one
        #     self.column = 0
        # else:
        #     # this means there is probable a range of columns given, we receive them in one batch
        #     self.column = config.jrodos_columns
        self.column = config.jrodos_columns
        # NOTE 1 !!! 'project' parameter value surrounded by single quotes in this request ??????
        # NOTE 2 !!! 'path' parameter value surrounded by single quotes in this request ??????
        self._xml = """<?xml version="1.0" encoding="UTF-8"?>
 <wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs"
   xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1"
   xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc"
   xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink"
   xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
   <ows:Identifier>{wps_id}</ows:Identifier>
   <wps:DataInputs>
     <wps:Input>
       <ows:Identifier>taskArg</ows:Identifier>
       <wps:Data>
         <wps:LiteralData>{project}</wps:LiteralData>
       </wps:Data>
     </wps:Input>
     <wps:Input>
       <ows:Identifier>dataitem</ows:Identifier>
       <wps:Data>
         <wps:LiteralData>{path}</wps:LiteralData>
       </wps:Data>
     </wps:Input>
     <wps:Input>
       <ows:Identifier>columns</ows:Identifier>
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
     <wps:Input>
       <ows:Identifier>threshold</ows:Identifier>
       <wps:Data>
         <wps:LiteralData>1.0E-15</wps:LiteralData>
       </wps:Data>
     </wps:Input>   
   </wps:DataInputs>
   <wps:ResponseForm>
     <wps:RawDataOutput mimeType="{format}">
       <ows:Identifier>result</ows:Identifier>
     </wps:RawDataOutput>
   </wps:ResponseForm>
 </wps:Execute>"""

        self._xml2 = """<?xml version="1.0" encoding="UTF-8"?>
        <wps:Execute version="1.0.0" service="WPS" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xmlns="http://www.opengis.net/wps/1.0.0" 
          xmlns:wfs="http://www.opengis.net/wfs"
          xmlns:wps="http://www.opengis.net/wps/1.0.0" 
          xmlns:ows="http://www.opengis.net/ows/1.1"
          xmlns:gml="http://www.opengis.net/gml" 
          xmlns:ogc="http://www.opengis.net/ogc"
          xmlns:wcs="http://www.opengis.net/wcs/1.1.1" 
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 
          http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
          <ows:Identifier>{wps_id}</ows:Identifier>
          <wps:DataInputs>
            <wps:Input>
              <ows:Identifier>taskArg</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>{project}</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>dataitem</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>{path}</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>columns</ows:Identifier>
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
            <wps:Input>
              <ows:Identifier>threshold</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>1.0E-15</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>includeSLD</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>1</wps:LiteralData>
              </wps:Data>
            </wps:Input>     
          </wps:DataInputs>
          <wps:ResponseForm>
            <wps:RawDataOutput mimeType="{format}">
              <ows:Identifier>result</ows:Identifier>
            </wps:RawDataOutput>
          </wps:ResponseForm>
        </wps:Execute>"""

        # write settings to file in output dir to be able to do some checking
        wps_settings_file = self.config.output_dir + '/jrodos_output_settings.txt'
        with open(wps_settings_file, 'wb') as f:
            s = self.config
            f.write(bytes(s))
            f.write(b'\n')
            f.write(self.xml().encode('utf-8'))
        # ALSO write the request as xml so you can do:
        # curl -v -XPOST -H "Content-Type: Content-Type: text/xml" -d @request.xml --output data.zip "http://geoserver.dev.cal-net.nl/geoserver/wps"
        request_xml_file = self.config.output_dir + '/request.xml'
        with open(request_xml_file, 'wb') as f:
            f.write(self.xml().encode('utf-8'))

    def xml(self):
        if self.config.wps_id == 'gs:JRodosGeopkgWPS':
            return self._xml2.format(wps_id=self.config.wps_id,
                                    project=self.config.jrodos_project,
                                    path=self.config.jrodos_path,
                                    format=self.config.jrodos_format,
                                    column=self.column,
                                    vertical=self.config.jrodos_verticals)
        else:
            return self._xml.format(wps_id=self.config.wps_id,
                                    project=self.config.jrodos_project,
                                    path=self.config.jrodos_path,
                                    format=self.config.jrodos_format,
                                    column=self.column,
                                    vertical=self.config.jrodos_verticals)

    def _data_retrieved(self, reply, filename):
        log.debug(f'JRodosModelProvider retrieving data, save to: {filename}')
        result = ProviderResult()
        if reply.error():
            log.debug('JRodosModelProvider ERROR: {}'.format(reply.error()))
            result.set_error(reply.error(), reply.request().url().toString(), 'JRodos model output provider (WPS)')
        else:
            content = reply.readAll()
            # log.debug(content)
            # oops WPS emtpy json doc?
            if len(content) < 5:
                result.set_error(-1, reply.url().toString(), 'Project info retrieved is empty: "{}"'.format(content))
                self.ready = True
                self.finished.emit(result)
                reply.deleteLater()  # else timeouts on Windows
                return
            try:
                obj = json.loads(content.data().decode('utf-8'))
                log.debug(f'JRodosModelProvider JSON retrieved ???: {obj}')
            except Exception:
                result.set_error(-1, reply.url().toString(),
                             'JRodosModelOutputProvider json contains '
                             'error: "{}"'.format(content.data()))
                self.ready = True
                self.finished.emit(result)
                reply.deleteLater()  # else timeouts on Windows
                return

            with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed
                f.write(content)

            # NEW:
            # {"type": "FeatureCollection", "features": [
            #     {"type": "Feature",
            #      "properties": {"timeStep": 3600, "durationOfPrognosis": 86400,
            #                     "releaseStart": "2016-04-25T08:00:00.000+0000"},
            #      "id": "RodosLight"}]
            # }

            if 'features' in obj and len(obj['features']) > 0 \
                    and 'properties' in obj['features'][0] \
                    and 'Value' in obj['features'][0]['properties']:
                # TODO remove this one?
                # {u'type': u'FeatureCollection', u'features': [
                #     {u'type': u'Feature',
                #      u'properties': {u'Value': u'{
                #                           timeStep:1800,
                #                           durationOfPrognosis:43200,
                #                           releaseStart:1477146000000}'},
                #      u'id': u'RodosLight'}]}
                values = obj['features'][0]['properties']['Value']
                # preprocess the data to a nice object
                data = {'result': 'OK', 'project': self.config.jrodos_project}
                for prop in values[1:-1].split(','):
                    data[prop.split(':')[0]] = int(prop.split(':')[1])
                result.set_data(data, self.config.url)
            elif 'features' in obj and len(obj['features']) > 0 \
                    and 'properties' in obj['features'][0] \
                    and 'timeStep' in obj['features'][0]['properties']:
                # NEW:
                # {"type": "FeatureCollection", "features": [
                #     {"type": "Feature",
                #      "properties": {"timeStep": 3600,
                #                     "durationOfPrognosis": 86400,
                #                     "releaseStart": "2016-04-25T08:00:00.000+0000"},
                #      "id": "RodosLight"}]}
                data = {'result': 'OK', 'project': obj['features'][0]['properties']}
                for prop in obj['features'][0]['properties']:
                    data[prop] = obj['features'][0]['properties'][prop]
                result.set_data(data, self.config.url)
            else:
                result.set_error(-1, self.config.url, "Wrong json: " + content)
        self.finished.emit(result)
        self.ready = True
        now = QDateTime.currentMSecsSinceEpoch()
        log.debug(f'JRodosModelProvider, finished Retrieving model info in {(now-self.time_total)/1000} seconds')
        reply.deleteLater()  # else timeouts on Windows

    def get_data(self):
        request = QNetworkRequest(QUrl(self.config.url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'text/xml')  # or? "text/xml; charset=utf-8"
        reply = self.network_manager.post(request, bytearray(self.xml(), 'utf-8'))
        filename = self.config.output_dir + '/modelinfo.json'
        reply.finished.connect(partial(self._data_retrieved, reply, filename))



class JRodosModelOutputProvider(JRodosModelProvider):
    """A provider which connects using the WPS interface to a Geoserver-enabled JRodos WPS to retrieve
    model output data OR model input from projects.

    The JRodos WPS is a normal Geoserver with the addition of a jar and a mount to the JRodos output files
    So often running on something like: http://localhost:8080/geoserver/wps

    The JRodos WPS interface needs 4 parameters:
    taskArg: being the 'project name' from JRodos (WITH single quotes around it !!!)
    dataitem: being the 'datapath' from JRodos (WITH single quotes around it !!!, found via rightclick in JRodos)
    column: being the modelstep, so the first model/time step is column 0 etc etc
    vertical: being the vertical layers of a model (IF applicable, in this case always 0)
    threshold: a possible filter for data, use -1 for NO filter. For models 0 is used to filter out zero values.

    The actual request is a WPS XML-request sent as a http-POST

    Using the WPS plugin you can for example test the WPS interface. Note the WPS can have different return format:
    For example GM, zipped shapefiles or geojson.
    Would be nice if in future we could retrieve all columns in one geopackage format :-)

    Current implementation uses zipped shapefiles, and saves these in a uniquely named directory in the temp-dir of the
    user, named as: column_vertical.zip (so 0_0.zip, 1_0.zip etc etc)

    Note that the WPS outputs one zipfile being a (model) grid with cells with just two columns: Cell and Value
    So the application is actually responsible for adding a time-column to the data. That is why for the loading of
    the shapefiles we actually need a 'Datetime' AND the number of timesteps AND the length (in minutes) of the
    modelsteps. The application adds this information in a column named 'Datetime'

    There is also a 'jrodos_output_settings.txt' text file saved in the directory, to see/check which parameters are used.

    """
    def __init__(self, config):
        JRodosModelProvider.__init__(self, config)

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
            log.debug('JRodosModelOutputProvider ERROR: {}'.format(reply.error()))
            result.set_error(reply.error(), reply.request().url().toString(), 'JRodos model output provider (WPS)')
            # OK, we have an error... emit the result + error here and quit the loading loop
            self.ready = True
            self.finished.emit(result)
            reply.deleteLater()  # else timeouts on Windows
            return
        else:
            # log.debug('JRodosModelOutputProvider Content: {}'.format(content))
            with open(filename, 'wb') as f:  # using 'with open', then file is explicitly closed
                first1500bytes = reply.read(1500)
                try:
                    first1500bytes_str = first1500bytes.decode('utf-8')
                    log.debug('first1500bytes_str type: {}'.format(type(first1500bytes_str)))
                    if len(first1500bytes) < 5 or len(first1500bytes_str) < 5:
                        result.set_error(-1, reply.url().toString(), 'JRodosModelOutputProvider Model retrieved has error: "{}"'.format(first1500bytes))
                        self.ready = True
                        self.finished.emit(result)
                        reply.deleteLater()  # else timeouts on Windows
                        return

                    # could be an exception, eg:

                    # <wps:ExecuteResponse xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="en" service="WPS" serviceInstance="http://geoserver.prd.cal-net.nl:80/geoserver/ows?" version="1.0.0">
                    #       <wps:Process wps:processVersion="1.0.0">
                    #       <ows:Identifier>gs:JRodosWPS</ows:Identifier>
                    #       <ows:Title>jrodosWPS</ows:Title>
                    #       <ows:Abstract>JRodos Result Access</ows:Abstract>
                    #       </wps:Process><wps:Status creationTime="2017-04-25T13:36:24.287Z">
                    #       <wps:ProcessFailed>
                    #           <ows:ExceptionReport version="1.1.0">
                    #               <ows:Exception exceptionCode="NoApplicableCode">
                    #                   <ows:ExceptionText>Process failed during execution org.dom4j.DocumentException: Error on line 1 of document  : Content is not allowed in prolog. Nested exception: Content is not allowed in prolog.  Error on line 1 of document  : Content is not allowed in prolog. Nested exception: Content is not allowed in prolog.</ows:ExceptionText>
                    #               </ows:Exception>
                    #           </ows:ExceptionReport>
                    #       </wps:ProcessFailed>
                    #       </wps:Status>
                    # </wps:ExecuteResponse>

                    # <?xml version="1.0" encoding="UTF-8"?>
                    # <wps:ExecuteResponse xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="en" service="WPS" serviceInstance="http://geoserver.dev.cal-net.nl:80/geoserver/ows?" version="1.0.0">
                    #   <wps:Process wps:processVersion="1.0.0">
                    #     <ows:Identifier>gs:JRodosGeopkgWPS</ows:Identifier>
                    #     <ows:Title>jrodosGeopkgWPS</ows:Title>
                    #     <ows:Abstract>JRodos Result Access as a Geopackage file</ows:Abstract>
                    #   </wps:Process>
                    #   <wps:Status creationTime="2019-06-04T06:29:25.602Z">
                    #     <wps:ProcessFailed>
                    #       <ows:ExceptionReport version="1.1.0">
                    #         <ows:Exception exceptionCode="NoApplicableCode">
                    #           <ows:ExceptionText>
                    #              Process failed during execution java.lang.IllegalArgumentException: Column of series should be one of the following types: float[], double[], int[], byte[] Column of series should be one of the following types: float[], double[], int[], byte[]
                    #           </ows:ExceptionText>
                    #         </ows:Exception>
                    #       </ows:ExceptionReport>
                    #     </wps:ProcessFailed>
                    #   </wps:Status>
                    # </wps:ExecuteResponse>
                    exception = re.findall('<wps:ProcessFailed>', first1500bytes_str)
                    if len(exception) > 0:
                        # oops WPS returned an exception
                        result.set_error(-1, reply.url().toString(), first1500bytes_str)
                        self.ready = True
                        self.finished.emit(result)
                        reply.deleteLater()  # else timeouts on Windows
                        return
                except Exception as e:
                    log.debug('JRodosModelOutputProvider: Exception, all OK probably data is NOT an exception xml...')

                f.write(first1500bytes)
                f.write(reply.readAll())

        if str(self.config.jrodos_columns).isdigit() and self.column < self.config.jrodos_columns-1:
            # note self.column will live long enough to be used here?
            self.column += 1
            self.get_data()
        else:
            #logging.debug('All model information received; stop fetching, start loading...')
            result.set_data({'result': 'OK', 'output_dir': self.config.output_dir}, reply.url().toString())
            # we need to wait untill all pages are there before to emit the result; so: INSIDE de loop
            now = QDateTime.currentMSecsSinceEpoch()
            log.debug(f'JRodosModelOutputProvider, finished Retrieving model info in {(now-self.time)/1000} seconds')
            self.ready = True
            self.finished.emit(result)
            reply.deleteLater()  # else timeouts on Windows

    def get_data(self):
        request = QNetworkRequest(QUrl(self.config.url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'text/xml')  # or? "text/xml; charset=utf-8"
        self.reply = self.network_manager.post(request, bytearray(self.xml(), 'utf-8'))
        extension = '.zip'
        if self.config.jrodos_format == 'application/json':
            extension = '.json'
        filename = self.config.output_dir + '/' + str(self.column) + '_' + str(
            self.config.jrodos_verticals) + extension
        self.reply.finished.connect(partial(self._data_retrieved, self.reply, filename))
