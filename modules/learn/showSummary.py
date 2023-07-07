import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis, QPieSeries
from PyQt5 import uic
import sqlite3
import json


class Window(qt.QMainWindow):

    def __init__(self, superClass, course, color, factsStudied, defStudied, formStudied, proStudied, diaStudied,
                 tabStudied, noRemaining, timeTaken, correctCounter, incorrectCounter, scorePerTopic):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/learnNotesSummary.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.totalStudied = factsStudied + defStudied + formStudied + proStudied + diaStudied + tabStudied
        self.databasePath = "data/" + course + "/courseData.db"
        self.scores = 0
        self.scorePerTopic = scorePerTopic

        try:
            self.averageTime = round(timeTaken / self.totalStudied)
        except ZeroDivisionError:
            self.averageTime = round(timeTaken)

        try:
            self.accuracy = round(100 * correctCounter / (correctCounter + incorrectCounter))
        except ZeroDivisionError:
            self.accuracy = 0

        self.updateMenuBar()
        self.show()

        # Get widgets
        messageLabel = self.findChild(qt.QLabel, "messageLabel")
        noFactsLabel = self.findChild(qt.QLabel, "noFactsLabel")
        noDefLabel = self.findChild(qt.QLabel, "noDefLabel")
        noProLabel = self.findChild(qt.QLabel, "noProLabel")
        noFormLabel = self.findChild(qt.QLabel, "noFormLabel")
        noDiaLabel = self.findChild(qt.QLabel, "noDiaLabel")
        noTabLabel = self.findChild(qt.QLabel, "noTabLabel")
        totalLabel = self.findChild(qt.QLabel, "totalLabel")
        remainingLabel = self.findChild(qt.QLabel, "remainingLabel")
        coverageLabel = self.findChild(qt.QLabel, "coverageLabel")
        avTimeLabel = self.findChild(qt.QLabel, "avTimeLabel")
        finishBtn = self.findChild(qt.QPushButton, "finishBtn")

        # Fill labels
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        messageLabel.setText(f"Well done {data['nickname']}!")
        noFactsLabel.setText(f"Facts Studied: {factsStudied}")
        noDefLabel.setText(f"Definitions Studied: {defStudied}")

        noProLabel.setText(f"Processes Studied: {proStudied}")
        noFormLabel.setText(f"Formulas Studied: {formStudied}")
        noDiaLabel.setText(f"Diagrams Studied: {diaStudied}")
        noTabLabel.setText(f"Tables Studied: {tabStudied}")

        totalLabel = self.findChild(qt.QLabel, "totalLabel")
        totalLabel.setText(f"Total Notes Studied: {self.totalStudied}")
        remainingLabel.setText(f"Notes Remaining: {noRemaining}")
        graphicLayout = self.findChild(qt.QVBoxLayout, "graphicLayout")
        avTimeLabel.setText(f"Average Time Spent per Note: {self.averageTime}s")

        # Return how notes are in total
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT noteID FROM notes")
        totalNoNumber = len(c.fetchall())
        coverage = round(100 * self.totalStudied / totalNoNumber)
        coverageLabel.setText(f"Total Course Coverage: {coverage}%")

        finishBtn.clicked.connect(self.close)

        self.updateAverageScores()
        self.createPieChart()
        self.createLineGraph()

    def createPieChart(self):
        """ Create pie chart """
        series = QPieSeries()  # Create pie chart
        series.setPieSize(0.5)
        totalTopicPoint = sum(self.scorePerTopic.values())

        for topic in self.scorePerTopic:
            if self.scorePerTopic[topic] > 0:
                score = self.scorePerTopic[topic]
                percent = round(100 * score / totalTopicPoint)
                series.append(f"{topic} - {percent}%", score)  # Insert value into chart

        for pieSlice in series.slices():
            pieSlice.setLabelVisible(True)

        chart = QChart()  # Create chart object
        chart.legend().hide()  # Hide legend
        chart.addSeries(series)  # Add graph to chart
        chart.createDefaultAxes()  # Create axis
        chart.setAnimationOptions(QChart.SeriesAnimations)  # Add animation
        chart.setTitle("Topics Covered")  # Set title
        titleFont = QFont("MS Shell Dlg 2")
        titleFont.setPointSize(12)
        titleFont.setBold(True)
        chart.setTitleFont(titleFont)

        chart.legend().setVisible(False)  # Set legend to visible
        chartView = QChartView(chart)  # Create chart view object
        chartView.setRenderHint(QPainter.Antialiasing)  # Set rendering
        chartView.setMaximumHeight(350)
        self.graphicLayout.addWidget(chartView)

    def createLineGraph(self):
        """ Create line graph """
        series = QLineSeries(self)  # Create line graph
        for i, v in enumerate(self.scores):
            series.append(i, v)

        chart = QChart()  # Create chart
        chart.addSeries(series)  # Add graph to chart
        chart.setAnimationOptions(QChart.SeriesAnimations)  # Add animation
        chart.setTitle("Progress over Time")
        titleFont = QFont("MS Shell Dlg 2")
        titleFont.setPointSize(12)
        titleFont.setBold(True)
        chart.setTitleFont(titleFont)

        # Customise axis
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
        axisBrush = QBrush(Qt.black)
        axisX.setLabelsBrush(axisBrush)
        axisY.setLabelsBrush(axisBrush)
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
        chartView.setMaximumHeight(350)
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
                average = round((self.scores[i] + self.scores[i + 1]) / 2)
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
        self.superClass.show()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        menuBar = self.findChild(qt.QWidget, "menuBar")

        menuBar.setStyleSheet(f"background-color:{self.color}")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        courseNameLabel.setText(self.courseName + " - Learn Mode FINISHED")
        courseNameLabel.setStyleSheet(f"color:{fontColor}")
