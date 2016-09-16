import sys
from PyQt4.QtGui import QComboBox, QApplication, QCompleter, QSortFilterProxyModel, QStandardItemModel, QStandardItem
from PyQt4.QtCore import Qt

# based on:
# http://stackoverflow.com/questions/4827207/how-do-i-filter-the-pyqt-qcombobox-items-based-on-the-text-input

# use an extended widget in qtdesigner
# https://wiki.python.org/moin/PyQt/Using_Python_Custom_Widgets_in_Qt_Designer


class ExtendedCombo(QComboBox):

    def __init__(self, parent=None):
        super(ExtendedCombo, self).__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setEditable(True)

        self.completer = QCompleter(self)
        self.setCompleter(self.completer)
        # always show all completions
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.setPopup(self.view())
        self.completer.activated.connect(self.set_text_on_completer_clicked)

        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.lineEdit().textEdited[unicode].connect(self.pFilterModel.setFilterFixedString)

    def setModel(self, model):
        super(ExtendedCombo, self).setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)

    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super(ExtendedCombo, self).setModelColumn(column)

    def view(self):
        return self.completer.popup()

    def index(self):
        return self.currentIndex()

    def set_text_on_completer_clicked(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    model = QStandardItemModel()

    for i, word in enumerate(['hola', 'adios', 'hello', 'good bye']):
        item = QStandardItem(word)
        model.setItem(i, 0, item)

    combo = ExtendedCombo()
    combo.setModel(model)
    combo.setModelColumn(0)
    combo.show()

    sys.exit(app.exec_())
