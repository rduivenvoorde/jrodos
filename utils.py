from qgis.PyQt.QtCore import QSettings


class Utils:

    SETTINGS_SECTION = "plugins/jrodos/"

    @staticmethod
    def get_settings_value(key, default=''):
        if QSettings().contains(Utils.SETTINGS_SECTION + key):
            key = Utils.SETTINGS_SECTION + key
            val = QSettings().value(key)
            return val
        else:
            return default

    @staticmethod
    def set_settings_value(key, value):
        key = Utils.SETTINGS_SECTION + key
        QSettings().setValue(key, value)
