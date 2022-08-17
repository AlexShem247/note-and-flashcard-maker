import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QIcon
from PyQt5.QtCore import Qt, QRect
from PIL import Image


class Canvas(qt.QLabel):

    def __init__(self, w, h, filename, snipCompleted):
        super().__init__()
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.white)
        self.setPixmap(pixmap)
        self.w, self.h = w, h
        self.filename = filename
        self.snipCompleted = snipCompleted
        self.rectSet = False
        self.show()

        self.last_x, self.last_y = None, None
        self.startX, self.startY = None, None

        self.drawLines()
        self.update()

    def drawLines(self):
        if not self.rectSet:
            self.rectangle = QRect(0, 0, self.w, self.h)
            self.rectSet = True

        painter = QPainter(self.pixmap())
        painter.setPen(QPen(Qt.white, 1, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.white, Qt.SolidPattern))
        painter.drawRect(0, 0, self.w, self.h)

        pixmap = QPixmap(self.filename)
        painter.drawPixmap(self.rectangle, pixmap)

        if self.startX:
            w = self.endX - self.startX
            h = self.endY - self.startY
            painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
            painter.setBrush(QBrush(Qt.white, Qt.NoBrush))
            painter.drawRect(self.startX, self.startY, w, h)

        painter.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # Start drawing
            self.startX, self.startY = e.x()-10, e.y()

    def mouseMoveEvent(self, e):
        if self.last_x is None:  # First event.
            self.last_x = e.x()
            self.last_y = e.y()
            return  # Ignore the first time.

        self.endX = e.x()
        self.endY = e.y()
        self.drawLines()
        self.update()

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e):
        self.last_x = None
        self.last_y = None
        size = (self.endX - self.startX) * (self.endY - self.startY)
        if size > 2000:
            self.snipCompleted(self.startX, self.startY, self.endX, self.endY)
        else:
            self.last_x, self.last_y = None, None
            self.startX, self.startY = None, None

            self.drawLines()
            self.update()


class Window(qt.QWidget):
    def __init__(self, superClass, filename, uploadQuestFile, _type, duplicate):
        super().__init__()
        self.superClass = superClass
        self.setWindowTitle("Smart Retain")
        self.setWindowIcon(QIcon("images/logo.png"))
        self.setGeometry(50, 50, 1000, 720)
        self.uploadQuestFile = uploadQuestFile
        self.duplicate = duplicate
        self.type = _type
        self.show()

        # Create box layout
        self.groupbox = qt.QGroupBox()
        self.hbox = qt.QHBoxLayout()
        self.groupbox.setLayout(self.hbox)

        # Create canvas
        self.img = Image.open(filename)
        self.canvas = Canvas(self.img.width, self.img.height, filename, self.snipCompleted)
        self.canvas.setAlignment(Qt.AlignCenter)
        self.hbox.addWidget(self.canvas)

        # Scroll Area Properties
        self.scroll = qt.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.groupbox)

        self.layout = qt.QVBoxLayout()
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.superClass.show()

    def snipCompleted(self, x1, y1, x2, y2):
        """ Run when a snip has been taken """
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        path, path2 = "images/temp/foo.png", "images/temp/foo2.png"
        self.img = self.img.crop((x1, y1, x2, y2))
        self.img.save(path)
        if self.duplicate:
            if self.type == "initial":
                self.img.save(path)
                self.img.save(path2)
            else:
                self.img.save(path2)

        self.close()
        self.uploadQuestFile(self.type, fName=path)
