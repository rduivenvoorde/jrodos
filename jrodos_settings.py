from qgissettingmanager import *

# Working with: https://github.com/3nids/qgissettingmanager
# learning from: https://github.com/3nids/wincan2qgep
# https://github.com/3nids/quickfinder

# KNMI services:

class JRodosSettings(SettingManager):

    def __init__(self):

        plugin_name = 'JRodos'

        SettingManager.__init__(self, plugin_name)

        # JRodos Models WPS service url
        self.add_setting(String('jrodos_wps_url', Scope.Global, 'http://localhost:8080/geoserver/wps'))


        # CalNet Measurements WFS service url
        self.add_setting(String('measurements_wfs_url', Scope.Global,
                                'http://geoserver.dev.cal-net.nl/geoserver/radiation.measurements/ows?'))
        self.add_setting(Integer('measurements_wfs_page_size', Scope.Global, 10000))
