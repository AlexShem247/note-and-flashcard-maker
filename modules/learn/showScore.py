import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis
from PyQt5 import uic
import random
import time
from datetime import datetime
import json

MESSAGES = ["Keep up the good work", "Well done", "Great progress", "Nice answering", "Impressive stuff"]
FINAL_MESSAGES = ["Nearly there", "Almost done", "Only a few more to go"]
random.shuffle(MESSAGES)
random.shuffle(FINAL_MESSAGES)


class Window(qt.QMainWindow):

    def __init__(self, superClass, course, color, closingFunction, noStudied, noRemaining, timeTaken, correctCounter,
                 incorrectCounter, finishCommand):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/learnNotesInfo.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.closingFunction = closingFunction
        self.accuracy = round(100*correctCounter/(correctCounter + incorrectCounter))
        self.scores = []
        self.back = True
        self.finishCommand = finishCommand
        self.updateMenuBar()
        self.show()

        # Get widgets
        self.messageLabel = self.findChild(qt.QLabel, "messageLabel")
        self.noStudiedLabel = self.findChild(qt.QLabel, "noStudiedLabel")
        self.noRemainingLabel = self.findChild(qt.QLabel, "noRemainingLabel")
        self.durationLabel = self.findChild(qt.QLabel, "durationLabel")
        self.estimationLabel = self.findChild(qt.QLabel, "estimationLabel")
        self.progressBar = self.findChild(qt.QProgressBar, "progressBar")
        self.progressLabel = self.findChild(qt.QLabel, "progressLabel")
        self.graphicLayout = self.findChild(qt.QVBoxLayout, "graphicLayout")
        self.continueBtn = self.findChild(qt.QPushButton, "continueBtn")
        self.finishBtn = self.findChild(qt.QPushButton, "finishBtn")

        # Fill labels
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        if noRemaining <= 10:
            self.messageLabel.setText(f"{FINAL_MESSAGES[0]}, {data['nickname']}")
        else:
            self.messageLabel.setText(f"{MESSAGES[0]}, {data['nickname']}")

        self.noStudiedLabel.setText(f"Notes Studied: {noStudied}")
        self.noRemainingLabel.setText(f"Notes Remaining: {noRemaining}")

        m = int(time.strftime("%M", time.gmtime(timeTaken)))
        s = int(time.strftime("%S", time.gmtime(timeTaken)))
        self.durationLabel.setText(f"Session Length: {m}m {s}s")

        # Calculated estimated finishing time
        etfInSeconds = (timeTaken/noStudied) * noRemaining + time.time()
        etf = datetime.fromtimestamp(etfInSeconds).strftime("%H:%M")
        self.estimationLabel.setText(f"Estimated Completion Time: {etf}")

        # Fill progress bar
        percent = 100*noStudied/(noStudied + noRemaining)
        self.progressBar.setValue(percent)
        self.progressLabel.setText(f"{round(percent)}% Completed")

        self.continueBtn.clicked.connect(self.close)
        self.finishBtn.clicked.connect(self.navigateToSummary)

        self.updateAverageScores()
        self.createChart()

    def navigateToSummary(self):
        """ Sends user to summary and finishes learn mode """
        self.finishCommand()
        self.back = False
        self.close()

    def createChart(self):
        """ Create line graph """
        series = QLineSeries(self)  # Create line graph
        for i, v in enumerate(self.scores):
            series.append(i, v)

        chart = QChart()  # Create chart
        chart.addSeries(series)  # Add graph to chart
        chart.setAnimationOptions(QChart.SeriesAnimations)  # Add animation

        # customize axis
        axisX = QCategoryAxis()
        axisY = QCategoryAxis()

        labelFont = QFont("MS Shell Dlg 2")
        labelFont.setPixelSize(12)

        axisX.setLabelsFont(labelFont)
        axisY.setLabelsFont(labelFont)

        axisPen = QPen(Qt.black)
        axisPen.setWidth(2)

        axisX.setLinePen(axisPen)
        axisY.setLinePen(axisPen)

        axixBrush = QBrush(Qt.black)
        axisX.setLabelsBrush(axixBrush)
        axisY.setLabelsBrush(axixBrush)

        axisX.setRange(0, 9)
        axisY.setRange(0, 100)
        axisX.append("Time", 9)
        axisY.setLabelsAngle(-90)
        axisY.append("25%", 25)
        axisY.append("50%", 50)
        axisY.append("75%", 75)
        axisY.append("100%", 100)
        axisY.setTitleText("Average Score")

        axisX.setGridLineVisible(True)
        axisY.setGridLineVisible(True)

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        chart.legend().setVisible(False)  # Set legend to visible

        chartView = QChartView(chart)  # Create chart view object
        chartView.setRenderHint(QPainter.Antialiasing)  # Set rendering
        self.graphicLayout.addWidget(chartView)

    def updateAverageScores(self):
        """ Updates JSON with new score """
        with open("data/" + self.courseName + "/courseInfo.json") as f:
            content = json.load(f)
            textbookPath = content["textbookPath"]
            visitDates = content["dateStudied"]
            self.scores = content["averageScores"]

        # Modify scores
        self.scores.append(self.accuracy)
        while len(self.scores) > 10:
            # Average score between themselves to get an average of 10 scores
            newScores = []
            for i in range(len(self.scores) - 1):
                average = round((self.scores[i] + self.scores[i+1]) / 2)
                newScores.append(average)

            self.scores = newScores.copy()

        # Update json
        with open("data/" + self.courseName + "/courseInfo.json", "w") as f:
            data = {
                "name": self.courseName,
                "color": self.color,
                "textbookPath": textbookPath,
                "dateStudied": visitDates,
                "averageScores": self.scores
            }

            json.dump(data, f, indent=4)


    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()
            self.closingFunction()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        self.courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        self.menuBar = self.findChild(qt.QWidget, "menuBar")

        self.menuBar.setStyleSheet(f"background-color:{self.color}")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        self.courseNameLabel.setText(self.courseName + " - Learn Notes")
        self.courseNameLabel.setStyleSheet(f"color:{fontColor}")
