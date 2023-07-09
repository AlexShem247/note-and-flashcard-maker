import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5 import uic
import copy
import re

POWER_SYMBOL = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
                "-": "⁻"}


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, tableValues, tableSubmitted):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/editTable.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.tableValues = copy.deepcopy(tableValues)
        self.originalTableValues = copy.deepcopy(tableValues)
        self.tableSubmitted = tableSubmitted
        self.twoWayTable = False

        # Create fonts
        self.boldFont = QFont("MS Shell Dlg 2")
        self.boldFont.setBold(True)

        # Get widgets
        self.table = self.findChild(qt.QTableWidget, "table")
        self.twoWayCheck = self.findChild(qt.QCheckBox, "twoWayCheck")
        self.noRowBox = self.findChild(qt.QSpinBox, "noRowBox")
        self.noColBox = self.findChild(qt.QSpinBox, "noColBox")
        self.saveBtn = self.findChild(qt.QPushButton, "saveBtn")

        # Bind widgets
        self.twoWayCheck.stateChanged.connect(self.changeTableType)
        self.saveBtn.clicked.connect(self.saveAndQuit)
        self.noRowBox.valueChanged.connect(self.changeNoRows)
        self.noColBox.valueChanged.connect(self.changeNoCols)
        self.table.itemChanged.connect(self.tableChanged)

        # Fill table with values
        self.fillTable()
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(qt.QHeaderView.ResizeToContents)

    def changeTableType(self):
        """ Changes one-way table to two-way and vice versa """
        self.twoWayTable = self.twoWayCheck.isChecked()
        if self.twoWayTable:
            self.createTwoWayTable()
        else:
            self.createOneWayTable()

    def tableChanged(self):
        """ Updates tableValues with values in table """
        for i in range(self.table.rowCount()):
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                if item:
                    text = item.text().strip()
                    # Clean powers
                    powers = re.findall(r"\^\-?\d*", text)
                    for power in powers:
                        newPower = "".join([POWER_SYMBOL[i] for i in power[1:]])
                        text = text.replace(power, newPower)

                    self.tableValues[i][j] = {"text": text, "userFill": item.checkState() == 2}

    def changeNoRows(self):
        """ Change number of rows """
        self.tableChanged()

        # Set minimum and maximum values
        MIN = 1
        if self.noRowBox.value() < MIN:
            self.noRowBox.setValue(MIN)

        # Get change in number of columns
        n = self.noRowBox.value() - self.table.rowCount() + 1

        if n > 0:
            # Increase number of rows
            NO_ROWS = len(self.tableValues)
            for l in range(n):
                self.tableValues.append([{"text": f"Value{NO_ROWS + l}{chr(97 + i)}", "userFill": True} for i in
                                         range(self.table.columnCount())])

                if self.twoWayTable:
                    self.tableValues[-1][0]["userFill"] = False

        elif n < 0:
            # Decrease number of rows
            for _ in range(-n):
                del self.tableValues[-1]

        self.fillTable()

    def changeNoCols(self):
        """ Change number of columns """
        self.tableChanged()

        # Set minimum and maximum values
        MIN, MAX = 2, 26
        if self.noColBox.value() > MAX:
            self.noColBox.setValue(MAX)
        elif self.noColBox.value() < MIN:
            self.noColBox.setValue(MIN)

        # Get change in number of columns
        n = self.noColBox.value() - self.table.columnCount()

        if n > 0:
            # Increase number of columns
            for l, row in enumerate(self.tableValues):
                ROW_LENGTH = len(row)
                for i in range(n):
                    char = chr(97 + ROW_LENGTH + i).lower()
                    if l == 0:
                        # Heading
                        self.tableValues[l].append({"text": f"Column{char.upper()}", "userFill": False})
                    else:
                        self.tableValues[l].append({"text": f"Value{l}{char.lower()}", "userFill": True})
        elif n < 0:
            # Decrease number of columns
            for l, row in enumerate(self.tableValues):
                ROW_LENGTH = len(row) + n
                self.tableValues[l] = self.tableValues[l][:ROW_LENGTH]
        self.fillTable()

    def fillTable(self):
        """ Fills table using current values """
        if not self.tableValues:
            # New tables
            self.tableValues = [[{"text": "ColumnA", "userFill": False}, {"text": "ColumnB", "userFill": False}],
                                [{"text": "Value1a", "userFill": True}, {"text": "Value1b", "userFill": True}],
                                [{"text": "Value2a", "userFill": True}, {"text": "Value2b", "userFill": True}]]

        self.table.setRowCount(len(self.tableValues))
        self.noRowBox.setValue(len(self.tableValues) - 1)
        self.table.setColumnCount(len(self.tableValues[0]))
        self.noColBox.setValue(len(self.tableValues[0]))
        self.table.setVerticalHeaderLabels([""] + [str(i+1) for i in range(len(self.tableValues[1:]))])
        self.table.setHorizontalHeaderLabels([chr(65 + i) for i in range(26)])

        # Work out if table is one-way or two-way
        firstColumn = [row[0]["userFill"] for row in self.tableValues]
        self.twoWayTable = True not in firstColumn
        self.twoWayCheck.setChecked(self.twoWayTable)
        if self.twoWayTable:
            self.createTwoWayTable()
        else:
            self.createOneWayTable()

    def createTwoWayTable(self):
        """ Fills table as two way """
        # Add top headings
        for i, name in enumerate(self.tableValues[0]):
            item = qt.QTableWidgetItem(name["text"])
            item.setFont(self.boldFont)
            self.table.setItem(0, i, item)

        # Add data
        for row, item in enumerate(self.tableValues[1:]):
            for column, element in enumerate(item):
                item = qt.QTableWidgetItem(element["text"])
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

                if element["userFill"]:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)

                self.table.setItem(row + 1, column, item)

        # Add side headings
        for i, name in enumerate([row[0] for row in self.tableValues]):
            item = qt.QTableWidgetItem(name["text"])
            item.setFont(self.boldFont)
            self.table.setItem(i, 0, item)
            self.tableValues[i][0]["userFill"] = False

    def createOneWayTable(self):
        """ Fills table as one way """
        # Add headings
        for i, name in enumerate(self.tableValues[0]):
            item = qt.QTableWidgetItem(name["text"])
            item.setFont(self.boldFont)
            self.table.setItem(0, i, item)

        for i, name in enumerate([row[0] for row in self.tableValues][1:], start=1):
            self.tableValues[i][0]["userFill"] = True

        # Add data
        for row, item in enumerate(self.tableValues[1:]):
            for column, element in enumerate(item):
                item = qt.QTableWidgetItem(element["text"])
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

                if element["userFill"]:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)

                self.table.setItem(row + 1, column, item)

    def saveAndQuit(self):
        """ Save tables values and closes window """
        self.tableChanged()
        fills = [cell["userFill"] for cell in [j for sub in self.tableValues for j in sub]]
        text = [cell["text"] for cell in [j for sub in self.tableValues for j in sub]]
        if True not in fills:
            reply = qt.QMessageBox.critical(self, "Incomplete table", "At least one cell must be ticked",
                                            qt.QMessageBox.Ok)
        elif "" in text:
            reply = qt.QMessageBox.critical(self, "Incomplete table", "All cells must be filled in",
                                            qt.QMessageBox.Ok)

        else:
            self.originalTableValues = copy.deepcopy(self.tableValues)
            self.close()

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.tableChanged()
        if self.originalTableValues != self.tableValues:
            reply = qt.QMessageBox.warning(self, "Table not Saved?", "Do you want to save your new table?",
                                           qt.QMessageBox.Yes, qt.QMessageBox.No)
            if reply == qt.QMessageBox.Yes:
                self.originalTableValues = copy.deepcopy(self.tableValues)

        self.superClass.show()
        self.tableSubmitted(self.originalTableValues)
