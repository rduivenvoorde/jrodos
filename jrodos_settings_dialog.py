import os

from PyQt4 import QtGui, uic
from qgissettingmanager import SettingDialog
from jrodos_settings import JRodosSettings

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jrodos_settings_dialog_base.ui'))


class JRodosSettingsDialog(QtGui.QDialog, FORM_CLASS, SettingDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(JRodosSettingsDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.settings = JRodosSettings()
        SettingDialog.__init__(self, self.settings)