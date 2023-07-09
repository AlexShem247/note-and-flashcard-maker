import platform

import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
import os
import sys
import json
from getpass import getuser
import ctypes
import traceback

import modules.createCourse as createCourse
import modules.homeScreen as homeScreen
import modules.mainSettings as mainSettings

data = {
    "nickname": getuser().title(),
    "textbookPath": f"C:/Users/{getuser()}/Documents/",
    "picturePath": f"C:/Users/{getuser()}/Pictures/",
    "editorPath": ["", False],
    "maxNotes": 50,
    "nNotes": 10,
    "typoLimit": 1
}

# Determine whether user's computer has MS Paint
if platform.system() == "Windows":
    data["editorPath"] = ["mspaint", False]

# Create JSON files
if not os.path.isfile("text/defaultSettings.json"):
    with open("text/defaultSettings.json", "w") as f:
        json.dump(data, f, indent=4)

if not os.path.isfile("text/currentSettings.json"):
    with open("text/currentSettings.json", "w") as f:
        json.dump(data, f, indent=4)

# Create temp folder
if not os.path.exists("images/temp"):
    os.makedirs("images/temp")

# Get courses that have had their name changed
if os.path.isfile("images/temp/courseNameChange.json"):
    with open("images/temp/courseNameChange.json") as f:
        newCourse = json.load(f)
        os.rename(newCourse[0], newCourse[1])
    os.remove("images/temp/courseNameChange.json")

def show_exception_and_exit(exc_type, exc_value, tb):
    ctypes.windll.user32.MessageBoxW(0, f"{exc_type.__name__}: {exc_value}", "An Unexpected Error has occurred", 0x10)


#sys.excepthook = show_exception_and_exit # TODO Add this before pushing
sys.excepthook = lambda exc_type, exc_value, tb: (traceback.print_exception(exc_type, exc_value, tb), sys.exit(-1))


class Window(qt.QMainWindow):
    w = None

    def __init__(self):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/main.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))

        # Get widgets
        self.createBtn = self.findChild(qt.QPushButton, "createBtn")
        self.createBtn.clicked.connect(lambda: self.openWindow(createCourse.Window, loadCourse=self.loadCourses))

        self.logo = self.findChild(qt.QLabel, "logo")
        pixmap = QPixmap("images/full logo transparent.png")
        self.logo.setPixmap(pixmap)
        self.logo.resize(pixmap.width(), pixmap.height())

        self.settingsBtn = self.findChild(qt.QPushButton, "settingsBtn")
        self.settingsBtn.setIcon(QIcon("images/spanner.png"))
        self.settingsBtn.setIconSize(QSize(50, 50))
        self.infoBtn = self.findChild(qt.QPushButton, "infoBtn")
        self.infoBtn.setIcon(QIcon("images/info.png"))
        self.infoBtn.setIconSize(QSize(50, 50))
        self.scrollCourses = self.findChild(qt.QScrollArea, "scrollCourses")

        self.widget = qt.QWidget()
        self.courseBox = qt.QVBoxLayout()
        self.widget.setLayout(self.courseBox)

        # Scroll Area Properties
        self.scrollCourses.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollCourses.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollCourses.setWidgetResizable(True)
        self.scrollCourses.setWidget(self.widget)

        # Bind buttons
        self.settingsBtn.clicked.connect(self.openSettings)
        self.infoBtn.clicked.connect(self.openInfo)

        self.loadCourses()

    def openInfo(self):
        """ Opens information window """
        msg = qt.QMessageBox()
        msg.setWindowTitle("About Smart Retain")
        msg.setText("Smart Retain is a Note Maker and Revision Software written by Alexander Shemaly "
                    "2021-2023.\n\nClick one of the courses in the scroll box or press 'Create Course' to begin "
                    "learning.")
        msg.setIcon(qt.QMessageBox.Information)
        msg.addButton("Ok", qt.QMessageBox.YesRole)
        x = msg.exec_()

    def openWindow(self, windowClass, sendBtnText=False, loadCourse=None):
        """ Open a child window """
        if sendBtnText:
            self.w = windowClass(self, self.sender().text())
        elif loadCourse:
            self.w = windowClass(self, loadCourse)
        else:
            self.w = windowClass(self)

        self.w.show()
        self.hide()

    def loadCourses(self):
        """ Checks files for saved courses and displays them """
        for i in reversed(range(self.courseBox.count())):
            self.courseBox.itemAt(i).widget().setParent(None)

        for course in os.listdir("data"):
            # Get colour
            with open("data/" + course + "/courseInfo.json") as f:
                content = json.load(f)
                color = content["color"]

            # Return font colour
            fontColor = color.lstrip("#")
            lv = len(fontColor)
            r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
            if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
                fontColor = "#000000"
            else:
                fontColor = "#FFFFFF"

            # Work out highlighted colour version
            rgb = [r, g, b]
            for i, value in enumerate(rgb):
                rgb[i] = value - 50
                if rgb[i] < 0:
                    rgb[i] = 0
            highlightColor = "#%02x%02x%02x" % tuple(rgb)

            # Set button properties
            btn = qt.QPushButton(text=course)
            btn.setStyleSheet(f"""QPushButton {{
            background-color : {color};
            color : {fontColor};
            border-radius: 10px;
            padding: 3px 3px 3px 3px;
            }}
            QPushButton:hover {{
            background-color:{highlightColor};
            }}""")
            btn.setFont(QFont("MS Shell Dlg 2", 18))
            btn.clicked.connect(lambda: self.openWindow(homeScreen.Window, sendBtnText=True))

            self.courseBox.addWidget(btn)

    def openSettings(self):
        """ Opens settings window """
        self.w = mainSettings.Window(self, self.loadCourses)
        self.w.show()
        self.hide()


if __name__ == "__main__":
    app = qt.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
