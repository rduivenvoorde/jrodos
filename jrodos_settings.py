from .qgissettingmanager import SettingManager, Scope
from .qgissettingmanager.types.bool import Bool
from .qgissettingmanager.types.string import String
from .qgissettingmanager.types.integer import Integer

# Working with: https://github.com/3nids/qgissettingmanager
# learning from: https://github.com/3nids/wincan2qgep
# https://github.com/3nids/quickfinder

# KNMI services:

class JRodosSettings(SettingManager):

    def __init__(self):

        plugin_name = 'jrodos'  # NOTE: will be root node in QSettings: always lowercase!

        SettingManager.__init__(self, plugin_name)


        # JRodos Models WPS service url
        # jrodos_enabled
        self.add_setting(Bool('jrodos_enabled', Scope.Global, True))
        # jrodos_wps_url
        self.add_setting(String('jrodos_wps_url', Scope.Global, 'http://jrodos.prd.cal-net.nl/geoserver/wps'))
        # jrodos_rest_url
        self.add_setting(String('jrodos_rest_url', Scope.Global, 'http://jrodos.prd.cal-net.nl/rest/jrodos'))


        # CalNet Measurements WFS service url
        # measurements_enabled
        self.add_setting(Bool('measurements_enabled', Scope.Global, True))
        # measurements_wfs_url
        self.add_setting(String('measurements_wfs_url', Scope.Global,
                                'http://geoserver.prd.cal-net.nl/geoserver/radiation.measurements/ows?'))
        self.add_setting(Integer('measurements_wfs_page_size', Scope.Global, 25000))
        # measurements_wms_url
        self.add_setting(String('measurements_wms_url', Scope.Global,
                                'http://geoserver.dev.cal-net.nl/geoserver/rivm/wms?'))
        # measurements_soap_utils_url
        self.add_setting(String('measurements_soap_utils_url', Scope.Global,
                                'http://geoserver.prd.cal-net.nl/calnet-measurements-ws/utilService'))
        # calweb_project_service_url
        self.add_setting(String('calweb_project_service_url', Scope.Global,
                                'http://microservices.prd.cal-net.nl:8300/calweb/projects'))

        # Rainradar WMS-T service
        # rainradar_enabled
        self.add_setting(Bool('rainradar_enabled', Scope.Global, True))
        # rainradar_wmst_name
        self.add_setting(String('rainradar_wmst_name', Scope.Global,
                                'KNMI'))
        # rainradar_wmst_url
        self.add_setting(String('rainradar_wmst_url', Scope.Global,
                                'http://geoservices.knmi.nl/cgi-bin/RADNL_OPER_R___25PCPRR_L3.cgi'))
        # rainradar_wmst_layers
        self.add_setting(String('rainradar_wmst_layers', Scope.Global,
                                'RADNL_OPER_R___25PCPRR_L3_KNMI'))
        # rainradar_wmst_styles
        self.add_setting(String('rainradar_wmst_styles', Scope.Global,
                                ''))
        # rainradar_wmst_imgformat
        self.add_setting(String('rainradar_wmst_imgformat', Scope.Global,
                                'image/png'))
        # rainradar_wmst_crs
        self.add_setting(String('rainradar_wmst_crs', Scope.Global,
                                'EPSG:28992'))

