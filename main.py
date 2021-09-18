import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
import os
import sys
import json
from getpass import getuser
import ctypes
import shutil

sys.path.append("modules")

# Other Windows
import createCourse
import homeScreen
import mainSettings

data = {
            "nickname": getuser().title(),
            "textbookPath": f"C:/Users/{getuser()}/Documents/",
            "picturePath": f"C:/Users/{getuser()}/Pictures/",
            "maxNotes": 50,
            "nNotes": 10,
            "typoLimit": 3
        }

# Create JSON files
if not os.path.isfile("text/defaultSettings.json"):
    with open("text/defaultSettings.json", "w") as f:
        json.dump(data, f, indent=4)

if not os.path.isfile("text/currentSettings.json"):
    with open("text/currentSettings.json", "w") as f:
        json.dump(data, f, indent=4)

# Get courses that have had their name changed
if os.path.isfile("images/temp/courseNameChange.json"):
    with open("images/temp/courseNameChange.json") as f:
        newCourse = json.load(f)
        os.rename(newCourse[0], newCourse[1])
    os.remove("images/temp/courseNameChange.json")

# If data folder does not exist, create it
if not os.path.exists("data"):
    os.makedirs("data")


def show_exception_and_exit(exc_type, exc_value, tb):
    ctypes.windll.user32.MessageBoxW(0, f"{exc_type.__name__}: {exc_value}", "An Unexpected Error has occurred",
                                     0x10)


sys.excepthook = show_exception_and_exit


class Window(qt.QMainWindow):
    w = None

    def __init__(self):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/main.ui", self)

        # Get widgets
        createBtn = self.findChild(qt.QPushButton, "createBtn")
        createBtn.clicked.connect(lambda: self.openWindow(createCourse.Window, loadCourse=self.loadCourses))
        settingsBtn = self.findChild(qt.QPushButton, "settingsBtn")
        settingsBtn.setIcon(QIcon("images/spanner.png"))
        settingsBtn.setIconSize(QSize(50, 50))
        scrollCourses = self.findChild(qt.QScrollArea, "scrollCourses")

        self.widget = qt.QWidget()
        self.courseBox = qt.QVBoxLayout()
        self.widget.setLayout(self.courseBox)

        # Scroll Area Properties
        scrollCourses.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scrollCourses.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollCourses.setWidgetResizable(True)
        scrollCourses.setWidget(self.widget)

        # Bind buttons
        settingsBtn.clicked.connect(self.openSettings)

        self.loadCourses()

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

            # Set button properties
            btn = qt.QPushButton(text=course)
            btn.setStyleSheet(f"background-color : {color}; color : {fontColor}")
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
