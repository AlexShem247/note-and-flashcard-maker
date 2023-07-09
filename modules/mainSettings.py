import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import os
import json
import shutil


class Window(qt.QWidget):

    def __init__(self, superClass, reloadCourses):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/mainSettings.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.reloadCourses = reloadCourses

        with open("text/currentSettings.json", "r") as f:
            self.data = json.load(f)

        self.show()

        # Get widgets
        self.nameEdit = self.findChild(qt.QLineEdit, "nameEdit")
        self.chTextBtn = self.findChild(qt.QPushButton, "chTextBtn")
        self.chPicBtn = self.findChild(qt.QPushButton, "chPicBtn")
        self.backBtn = self.findChild(qt.QPushButton, "backBtn")
        self.restoreBtn = self.findChild(qt.QPushButton, "restoreBtn")
        self.textPathLabel = self.findChild(qt.QLabel, "textPathLabel")
        self.picPathLabel = self.findChild(qt.QLabel, "picPathLabel")
        self.maxBox = self.findChild(qt.QSpinBox, "maxBox")
        self.nBox = self.findChild(qt.QSpinBox, "nBox")
        self.typoBox = self.findChild(qt.QSpinBox, "typoBox")
        self.deleteBox = self.findChild(qt.QComboBox, "deleteBox")
        self.chEditorBtn = self.findChild(qt.QPushButton, "chEditorBtn")
        self.checkEditor = self.findChild(qt.QCheckBox, "checkEditor")
        self.editorPathLabel = self.findChild(qt.QLabel, "editorPathLabel")

        # Set widget values
        self.nameEdit.setText(self.data["nickname"])
        self.textPathLabel.setText(self.data["textbookPath"])
        self.picPathLabel.setText(self.data["picturePath"])
        self.maxBox.setValue(self.data["maxNotes"])
        self.nBox.setValue(self.data["nNotes"])
        self.typoBox.setValue(self.data["typoLimit"])
        self.editorPathLabel.setText(self.data["editorPath"][0])
        self.checkEditor.setChecked(self.data["editorPath"][1])

        # Bind buttons
        self.deleteBox.currentTextChanged.connect(self.deleteCourse)
        self.backBtn.clicked.connect(self.saveChanges)
        self.chTextBtn.clicked.connect(lambda: self.updatePath(self.textPathLabel, "textbookPath"))
        self.chPicBtn.clicked.connect(lambda: self.updatePath(self.picPathLabel, "picturePath"))
        self.chEditorBtn.clicked.connect(lambda: self.updateFile(self.editorPathLabel, "editorPath"))
        self.restoreBtn.clicked.connect(self.restoreDefault)

        self.labels = {"textbookPath": self.data["textbookPath"], "picturePath": self.data["picturePath"],
                       "editorPath": self.data["editorPath"][0]}

        self.loadCourses()

    def restoreDefault(self):
        """ Inserts default values into widgets """
        with open("text/defaultSettings.json", "r") as f:
            self.data = json.load(f)

        self.labels = {"textbookPath": self.data["textbookPath"], "picturePath": self.data["picturePath"],
                       "editorPath": self.data["editorPath"][0]}

        # Set widget values
        self.nameEdit.setText(self.data["nickname"])
        self.textPathLabel.setText(self.data["textbookPath"])
        self.picPathLabel.setText(self.data["picturePath"])
        self.maxBox.setValue(self.data["maxNotes"])
        self.nBox.setValue(self.data["nNotes"])
        self.typoBox.setValue(self.data["typoLimit"])
        self.editorPathLabel.setText(self.data["editorPath"][0])
        self.checkEditor.setChecked(self.data["editorPath"][1])

    def saveChanges(self):
        """ Updates json file """
        data = {
            "nickname": self.nameEdit.text(),
            "textbookPath": self.labels["textbookPath"],
            "picturePath": self.labels["picturePath"],
            "editorPath": [self.labels["editorPath"], self.checkEditor.isChecked()],
            "maxNotes": self.maxBox.value(),
            "nNotes": self.nBox.value(),
            "typoLimit": self.typoBox.value()
        }

        with open("text/currentSettings.json", "w") as f:
            json.dump(data, f, indent=4)

        self.close()

    def updateFile(self, label, name):
        """ Loads file dialog to look for a file """
        fileName, _ = qt.QFileDialog.getOpenFileName(self, "Select Program", "", "Executables (*.exe)")
        if fileName:
            label.setText(fileName)
            self.labels[name] = fileName

    def updatePath(self, label, name):
        """ Loads file dialog for textbook path """
        fName = str(qt.QFileDialog.getExistingDirectory(self, "Select Folder"))
        if fName:
            label.setText(fName)
            self.labels[name] = fName

    def deleteCourse(self):
        """ Deletes selected course """
        course = self.deleteBox.currentText()

        if course not in ["- Select Course -", ""]:
            reply = qt.QMessageBox.warning(self, "Delete Course", f"Are you sure you want to delete {course}?\n\nThis "
                                           "action cannot be undone. You might want to export your notes first.",
                                           qt.QMessageBox.Yes, qt.QMessageBox.No)
            if reply == qt.QMessageBox.Yes:
                shutil.rmtree(f"data/{course}")

            self.deleteBox.clear()
            self.loadCourses()

    def loadCourses(self):
        """ Adds courses to combo box """
        self.deleteBox.clear()
        self.deleteBox.addItem("- Select Course -")

        for course in os.listdir("data"):
            self.deleteBox.addItem(course)

        self.deleteBox.setCurrentText("- Select Course -")

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.reloadCourses()
        self.superClass.show()
