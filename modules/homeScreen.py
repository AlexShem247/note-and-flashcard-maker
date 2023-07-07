import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QTextCharFormat, QPalette, QColor, QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
from random import randrange
import json
import sqlite3
from datetime import datetime, date
import matplotlib.pyplot as plt
import pandas as pd
from math import pi


import modules.create.createNotesNoPDF as createNotesNoPDF
import modules.create.createNotes as createNotes
import modules.view.viewNotes as viewNotes
import modules.learn.learnFilter as learnFilter
import modules.export.exportNotes as exportNotes
import modules.courseOptions as courseOptions


def getTodaysQuote():
    """ Returns quote of the day of the year """
    with open("text/quotes.json") as f:
        dayOfTheYear = datetime.now().timetuple().tm_yday
        content = json.load(f)[dayOfTheYear - 1]
    return content[0] + "\n\n - " + content[1]


class ImageLabel(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent=parent)
        self.p = QPixmap()

    def setPixmap(self, p):
        self.p = p
        self.update()

    def paintEvent(self, event):
        if not self.p.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, Qt.KeepAspectRatio)
            painter.drawPixmap(self.rect(), self.p)


def rotate(l, n):
    return l[n:] + l[:n]


class Window(qt.QMainWindow):
    color = None
    textbookPath = None
    visitDates = []
    w = None

    def __init__(self, superClass, course):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/homeScreen.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.databasePath = "data/" + course + "/courseData.db"
        self.show()

        message = self.updateJSON()
        quote = getTodaysQuote()

        # Define variables
        self.topicList = []
        self.topicListIndex = None
        self.imageList = []

        # Get widgets
        introLabel = self.findChild(qt.QLabel, "introLabel")
        pastLabel = self.findChild(qt.QLabel, "pastLabel")
        quoteEdit = self.findChild(qt.QPlainTextEdit, "quoteEdit")
        calendarWidget = self.findChild(qt.QCalendarWidget, "calendarWidget")
        strongLabel = self.findChild(qt.QLabel, "strongLabel")
        weakLabel = self.findChild(qt.QLabel, "weakLabel")
        scoreLabel = self.findChild(qt.QLabel, "scoreLabel")
        chartLayout = self.findChild(qt.QHBoxLayout, "chartLayout")
        createNotesBtn = self.findChild(qt.QPushButton, "createNotesBtn")
        viewNotesBtn = self.findChild(qt.QPushButton, "viewNotesBtn")
        learnNotesBtn = self.findChild(qt.QPushButton, "learnNotesBtn")
        previousBtn = self.findChild(qt.QToolButton, "previousBtn")
        forwardBtn = self.findChild(qt.QToolButton, "forwardBtn")
        exportBtn = self.findChild(qt.QPushButton, "exportBtn")

        # Change label text
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        introLabel.setText("Welcome back, " + data["nickname"])
        pastLabel.setText(message)
        quoteEdit.insertPlainText(quote)
        quoteEdit.verticalScrollBar().setSliderPosition(0)

        # Bind buttons
        createNotesBtn.clicked.connect(self.navigateToCreate)
        viewNotesBtn.clicked.connect(self.navigateToView)
        learnNotesBtn.clicked.connect(self.navigateToLearn)
        previousBtn.clicked.connect(lambda: self.changeGraph(-1))
        forwardBtn.clicked.connect(lambda: self.changeGraph(1))
        exportBtn.clicked.connect(self.navigateToExport)

        # Change menu bar
        self.updateMenuBar()

        # Show progress graphic
        self.showProgress()

        # Update calendar
        self.highlightDays()

        # Show best/worst topics
        self.updateScoreLabels()

    def updateCourseOptions(self):
        """ Navigates to options menu """
        self.w = courseOptions.Window(self, self.courseName, self.color)
        self.w.show()
        self.hide()

    def updateScoreLabels(self):
        """ Updates score labels with data from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        notesExist = c.fetchall()

        if notesExist:
            c.execute("SELECT topicName, correctCount*userScore, userScore "
                      "FROM notes n "
                      "JOIN subtopics s "
                      "ON n.subtopicID = s.subtopicID "
                      "JOIN topics t ON "
                      "s.topicID = t.topicID "
                      "WHERE practiceCount > 0 "
                      "ORDER BY t.topicID")
            noteData = c.fetchall()

            if noteData:
                topics = list(set([note[0] for note in noteData]))
                scores = {}
                total = []

                # Modify data
                for topic in topics:
                    scores[topic] = []

                for note in noteData:
                    scores[note[0]].append(note[1])
                    total.append(note[2])

                # Get average score
                for score in scores:
                    average = sum(scores[score]) / len(scores[score])
                    scores[score] = average

                topicRanked = list({k: v for k, v in sorted(scores.items(), key=lambda item: item[1])}.keys())
                worstTopic = topicRanked[0]
                bestTopic = topicRanked[-1]
                averageScore = round(100*sum(total) / len(total), 1)

                # Change labels
                self.strongLabel.setText(bestTopic)
                self.weakLabel.setText(worstTopic)
                self.scoreLabel.setText(f"{averageScore} %")

                # Show graph
                c.execute("SELECT topicName FROM topics ORDER BY topicID")
                self.topicList = [topic[0] for topic in c.fetchall()]
                self.topicListIndex = 0
                self.showRadarChart(scores)


        conn.close()

    def showRadarChart(self, scores):
        """ Show radar chart of topic performance """
        # Organise scores
        scoreNames = list({k: v for k, v in sorted(scores.items(), key=lambda item: item[1])}.keys())
        m = [scoreNames.pop()]
        scoreNames = scoreNames[::2] + m + scoreNames[1::2][::-1]
        scoreNames = rotate(scoreNames, randrange(len(scoreNames)))
        newScore = {}
        for name in scoreNames:
            newScore[name] = scores[name]
        scores = newScore.copy()

        # Set data
        topics = {"group": ["A"]}

        for topic in scores:
            score = scores[topic]
            if score > 5:
                score = 5

            # Adjust topic name to fit
            MAX_LENGTH = 12
            words = topic.split()
            lines = [words[0]]

            for word in words[1:]:
                # Replace 'and' with '&'
                if word.lower() == "and":
                    word = "&"

                if len(lines[-1]) + len(word) <= MAX_LENGTH:
                    lines[-1] = lines[-1] + " " + word
                else:
                    lines.append(word)

            topicName = "\n".join(lines)
            topics[topicName] = score

        df = pd.DataFrame(topics)

        # Number of variable
        categories = list(df)[1:]
        N = len(categories)

        # Plot the first line of the data frame
        values = df.loc[0].drop("group").values.flatten().tolist()
        values += values[:1]

        # The angle of each axis in the plot
        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]

        # Initialise the spider plot
        ax = plt.subplot(111, polar=True)
        plt.xticks(angles[:-1], categories, color="grey", size=18)
        ax.tick_params(axis="both", which="major", pad=25)
        plt.tight_layout()

        # Draw y labels
        ax.set_rlabel_position(0)
        plt.yticks([1, 2, 3, 4, 5], ["1", "2", "3", "4", "5"], color="grey", size=12)
        plt.ylim(0, 5)

        # Fill graph
        ax.plot(angles, values, linewidth=1, linestyle="solid")
        ax.fill(angles, values, "b", alpha=0.1)

        plt.savefig("images/temp/0.png")

        for i in reversed(range(self.chartLayout.count())):
            self.chartLayout.itemAt(i).widget().setParent(None)

        label = ImageLabel(self)
        label.setPixmap(QPixmap(f"images/temp/0.png"))
        pixmap = QPixmap(f"images/temp/0.png")  # Create image array
        pixmap = pixmap.scaled(QSize(1350, 900), transformMode=Qt.SmoothTransformation)
        self.imageList = [pixmap]

        self.chartLayout.addWidget(label)
        self.forwardBtn.setEnabled(True)

        # Create images
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        for i, topic in enumerate(self.topicList, start=1):
            plt.rcdefaults()
            fig, ax = plt.subplots()

            # Get Data
            c.execute("SELECT s.subtopicName, correctCount*userScore "
                      "FROM notes n "
                      "JOIN subtopics s "
                      "ON n.subtopicID = s.subtopicID "
                      "JOIN topics t "
                      "ON s.topicID = t.topicID "
                      f"WHERE t.topicName = '{topic}'")

            noteData = c.fetchall()
            topics = list(set([note[0] for note in noteData]))
            scores = {}

            # Modify data
            for topicName in topics:
                scores[topicName] = []

            for note in noteData:
                scores[note[0]].append(note[1])

            # Get average score
            for score in scores:
                average = sum(scores[score]) / len(scores[score])
                if average > 5:
                    average = 5
                scores[score] = average

            subtopics = list(scores.keys())
            subtopicScores = list(scores.values())

            ax.barh(subtopics, subtopicScores, align="center")
            ax.set_yticks(subtopics)
            ax.set_yticklabels(subtopics, fontsize=12)
            ax.invert_yaxis()
            ax.set_xlabel("Average Score", fontsize=12)
            ax.set_title(topic, fontsize=24)
            plt.xlim(0, 5)
            plt.savefig(f"images/temp/{i}.png", bbox_inches="tight")
            plt.close("all")

            pixmap = QPixmap(f"images/temp/{i}.png")  # Create image array
            pixmap = pixmap.scaled(QSize(1350, 900), transformMode=Qt.SmoothTransformation)
            self.imageList.append(pixmap)

        conn.close()

    def changeGraph(self, i):
        """ Changes graph """
        self.topicListIndex += i

        for i in reversed(range(self.chartLayout.count())):
            self.chartLayout.itemAt(i).widget().setParent(None)

        label = ImageLabel(self)
        label.setPixmap(QPixmap(self.imageList[self.topicListIndex]))
        self.chartLayout.addWidget(label)

        self.previousBtn.setEnabled(self.topicListIndex > 0)
        self.forwardBtn.setEnabled(self.topicListIndex < len(self.topicList))


    def closeEvent(self, event):
        """ Run when window gets closed """
        self.superClass.show()

    def updateJSON(self):
        """ Add today's date to JSON file """
        with open("data/" + self.courseName + "/courseInfo.json") as f:
            content = json.load(f)
            self.color = content["color"]
            self.textbookPath = content["textbookPath"]
            self.visitDates = content["dateStudied"]

            if self.visitDates:
                prevDate = date(*tuple(self.visitDates[-1]))
                today = datetime.today()
                curDate = date(today.year, today.month, today.day)
                delta = str((curDate - prevDate).days)

                if delta == "0":
                    message = "You have already logged in today"
                elif delta == "1":
                    message = "It has been " + delta + " day since you lasted logged in"
                else:
                    message = "It has been " + delta + " days since you lasted logged in"

            else:
                message = "Today is your first day learning " + self.courseName

        with open("data/" + self.courseName + "/courseInfo.json") as f:
            scores = content["averageScores"]

        # Update json
        with open("data/" + self.courseName + "/courseInfo.json", "w") as f:
            today = datetime.today()
            today = [today.year, today.month, today.day]
            if today not in self.visitDates:
                self.visitDates.append(today)

            data = {
                "name": self.courseName,
                "color": self.color,
                "textbookPath": self.textbookPath,
                "dateStudied": self.visitDates,
                "averageScores": scores,
            }

            json.dump(data, f, indent=4)

        return message

    def highlightDays(self):
        """ Highlights the days that the user has logged in """
        # Select colours
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(212, 212, 212))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

        # Create highlight object
        highlightFormat = QTextCharFormat()
        highlightFormat.setBackground(palette.brush(QPalette.Highlight))
        highlightFormat.setForeground(palette.color(QPalette.HighlightedText))

        # Highlight days
        for day in self.visitDates:
            self.calendarWidget.setDateTextFormat(date(*day), highlightFormat)

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        menuBar = self.findChild(qt.QWidget, "menuBar")
        settingsBtn = self.findChild(qt.QPushButton, "settingsBtn")

        # Add icons
        settingsBtn.setIcon(QIcon("images/options.png"))
        settingsBtn.clicked.connect(self.updateCourseOptions)

        menuBar.setStyleSheet(f"background-color:{self.color};border-style: outset;border-width: 2px;border-radius: "
                              f"10px;border-color: #303545;")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        courseNameLabel.setText(self.courseName + " - Home Menu")
        courseNameLabel.setStyleSheet(f"color:{fontColor};border-width:0px")

    def showProgress(self):
        """ Adds charts to the progress groupbox """
        text = "Create More Notes to View Progress"

        # Checks whether note table has been created
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        noteTableExists = c.fetchall()

        # Checks whether any notes have been created
        if noteTableExists:
            c.execute("SELECT * FROM notes")
            notes = c.fetchall()
            if notes:
                text = "Learn More Notes to View Progress"

        conn.close()

        # Add label explaining how to get progress charts to show
        hBox = qt.QHBoxLayout()
        label = qt.QLabel(text)
        label.setFont(QFont("Arial", 16))
        label.setAlignment(Qt.AlignCenter)
        self.chartLayout.addWidget(label)

    def navigateToCreate(self):
        """ Sends user to Create Notes window """
        if self.textbookPath[2]:
            self.w = createNotes.Window(self, self.courseName, self.color, self.textbookPath)
        else:
            self.w = createNotesNoPDF.Window(self, self.courseName, self.color, self.textbookPath)
        self.w.show()
        self.hide()

    def navigateToView(self):
        """ Sends user to View Notes window """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        notes = c.fetchall()
        conn.commit()
        conn.close()

        if notes:
            self.w = viewNotes.Window(self, self.courseName, self.color, self.textbookPath)
            self.w.show()
            self.hide()
        else:
            error = qt.QMessageBox.critical(self, "Cannot View Notes", "Please Create Some Notes First",
                                            qt.QMessageBox.Ok)

    def navigateToLearn(self):
        """ Send user to Learn Notes window """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        notes = c.fetchall()
        conn.commit()
        conn.close()

        if notes:
            self.w = learnFilter.Window(self, self.courseName, self.color, self.textbookPath)
            self.w.show()
            self.hide()
        else:
            error = qt.QMessageBox.critical(self, "Cannot Learn Notes", "Please Create Some Notes First",
                                            qt.QMessageBox.Ok)

    def navigateToExport(self):
        """ Send user to Export Notes Window """
        self.w = exportNotes.Window(self, self.courseName, self.color)
        self.w.show()
        self.hide()
