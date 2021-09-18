import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap, QImage, QKeySequence, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5 import uic
import qimage2ndarray
import sys
from PIL import Image


class Canvas(qt.QLabel):

    def __init__(self, w, h, undo, redo, filename):
        super().__init__()
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.white)
        self.setPixmap(pixmap)
        self.w, self.h = w, h
        self.undoBtn, self.redoBtn = undo, redo
        self.filename = filename
        self.rectSet = False
        self.show()

        self.last_x, self.last_y = None, None
        self.pickColor = False
        self.penEnabled = False
        self.eraserEnabled = False
        self.lines = []
        self.undoLines = []
        self.thickness = 1
        self.color = QColor("#000000")
        
        qt.QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        qt.QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo)
        self.drawLines()
        self.update()
        
    def drawLines(self):
        if not self.rectSet:
            self.rectangle = self.rect()
            self.rectSet = True

        painter = QPainter(self.pixmap())
        painter.setPen(QPen(Qt.white,  1, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.white, Qt.SolidPattern))
        painter.drawRect(0, 0, self.w, self.h)
        
        pixmap = QPixmap(self.filename)
        painter.drawPixmap(self.rectangle, pixmap)
        
        p = painter.pen()
        
        for lineGroup in self.lines:
            p.setWidth(lineGroup["thickness"])
            p.setColor(lineGroup["color"])
            painter.setPen(p)
            for line in lineGroup["points"]:
                painter.drawLine(*line)
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Start drawing
            if self.pickColor:
                image = self.pixmap().toImage()
                b, g, r, a = qimage2ndarray.recarray_view(image)[event.y()+10][event.x()]
                self.color = QColor(r, g, b)
                self.eyeBtn.setChecked(False)
                hex_ = "#%02x%02x%02x" % (r, g, b)
                self.colorLabel.setStyleSheet(f"background-color:{hex_}; border:2px solid #000000")
                self.pickColor = False

            if self.penEnabled:
                self.lines.append({"points": [], "thickness": self.thickness, "color": self.color})
        

    def mouseMoveEvent(self, e):
        if self.last_x is None:  # First event.
            self.last_x = e.x()
            self.last_y = e.y()
            return # Ignore the first time.
        
        if self.penEnabled:
            self.lines[-1]["points"].append((QPoint(self.last_x, self.last_y+10), QPoint(e.x(), e.y()+10)))
            self.undoBtn.setEnabled(True)
            self.undoLines = []
            
        elif self.eraserEnabled:
            for lineGroup in self.lines:
                for line in lineGroup["points"]:
                    x1, x2, y1, y2 = line[0].x(), line[1].x(), line[0].y(), line[1].y()
                    x, y = e.x(), e.y()+10
                    if x1-self.thickness <= x <= x2+self.thickness and \
                        y1-self.thickness <= y <= y2+self.thickness:
                        lineGroup["points"].remove(line)
                
            
        self.drawLines()
            
        self.update()

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e):
        self.last_x = None
        self.last_y = None
        
    def undo(self):
        if self.lines:
            self.undoLines.append(self.lines.pop())
            self.drawLines()
            self.update()
            if not self.lines:
                self.undoBtn.setEnabled(False)
            self.redoBtn.setEnabled(True)
            
    def redo(self):
        if self.undoLines:
            self.lines.append(self.undoLines.pop())
            self.drawLines()
            self.update()
            if not self.undoLines:
                self.redoBtn.setEnabled(False)
            
    def changeThickness(self, v):
        self.thickness = v
        
    def changeColor(self, color):
        self.color = QColor(color)
        
    def eyeDrop(self, eyeBtn, colorLabel):
        self.eyeBtn = eyeBtn
        self.colorLabel = colorLabel
        self.pickColor = True
        
    def setPen(self, val):
        self.penEnabled = val
        
    def setEraser(self, val):
        self.eraserEnabled = val
  
    
class Window(qt.QMainWindow):
    def __init__(self, superClass, filename, paintOptionSelected):
        super().__init__()
        uic.loadUi("gui/paint.ui", self)
        self.superClass = superClass
        self.paintOptionSelected = paintOptionSelected

        self.setFixedSize(720, 640)
        self.show()
        
        self.penSelected = False
        self.eraserSelected = False
        self.imgOption = "close"
        
        # Get widgets
        self.paintBox = self.findChild(qt.QGroupBox, "groupBox")
        self.penBtn = self.findChild(qt.QPushButton, "penBtn")
        self.eraserBtn = self.findChild(qt.QPushButton, "eraserBtn")
        self.eyeBtn = self.findChild(qt.QPushButton, "eyeBtn")
        self.groupBox = self.findChild(qt.QGroupBox, "groupBox")
        self.thickLabel = self.findChild(qt.QLabel, "thickLabel")
        self.thickSlider = self.findChild(qt.QSlider, "thickSlider")
        self.colorBtn = self.findChild(qt.QPushButton, "colorBtn")
        self.colorLabel = self.findChild(qt.QLabel, "colorLabel")
        self.eyeBtn = self.findChild(qt.QPushButton, "eyeBtn")
        self.undoBtn = self.findChild(qt.QPushButton, "undoBtn")
        self.redoBtn = self.findChild(qt.QPushButton, "redoBtn")
        self.saveBtn = self.findChild(qt.QPushButton, "saveBtn")
        self.delBtn = self.findChild(qt.QPushButton, "delBtn")
        
        self.penBtn.setIcon(QIcon("images/pen.png"))
        self.eraserBtn.setIcon(QIcon("images/eraser.png"))
        self.eyeBtn.setIcon(QIcon("images/eye_dropper.png"))
        self.undoBtn.setIcon(QIcon("images/undo.png"))
        self.redoBtn.setIcon(QIcon("images/redo.png"))
        
        # Create box layout
        self.hbox = qt.QHBoxLayout()
        self.groupBox.setLayout(self.hbox)
        
        self.canvas = Canvas(self.paintBox.size().width(), self.paintBox.size().height(),\
                             self.undoBtn, self.redoBtn, filename)
        self.hbox.addWidget(self.canvas)
        
        # Bind widgets
        self.thickSlider.sliderMoved.connect(self.updateThickness)
        self.colorBtn.clicked.connect(self.openColorPicker)
        self.eyeBtn.clicked.connect(self.enableEyeDrop)
        self.penBtn.clicked.connect(self.enabledPen)
        self.eraserBtn.clicked.connect(self.enableEraser)
        self.undoBtn.clicked.connect(self.canvas.undo)
        self.redoBtn.clicked.connect(self.canvas.redo)
        self.saveBtn.clicked.connect(self.saveImage)
        self.delBtn.clicked.connect(self.delImage)

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.imgOption == "close":
            # Close window
            reply = qt.QMessageBox.question(self, "Are you Sure?",
                                            "All unsaved work will be lost", qt.QMessageBox.Yes, qt.QMessageBox.No)
            if reply == qt.QMessageBox.No:
                event.ignore()
            else:
                self.paintOptionSelected(self.imgOption)
                self.superClass.show()

        elif self.imgOption == "delete":
            # Delete image
            reply = qt.QMessageBox.question(self, "Are you Sure?",
                                            "Your work will be lost", qt.QMessageBox.Yes, qt.QMessageBox.No)
            if reply == qt.QMessageBox.No:
                event.ignore()
            else:
                self.paintOptionSelected(self.imgOption)
                self.superClass.show()

        else:
            # Save image
            self.canvas.pixmap().save("images/temp/foo.png")
            self.paintOptionSelected(self.imgOption)
            self.superClass.show()


    def saveImage(self):
        self.imgOption = "save"
        self.close()

    def delImage(self):
        self.imgOption = "delete"
        self.close()
        
    def updateThickness(self):
        v = self.thickSlider.value()
        if v < 1:
            v = 1
        elif v > 20:
            v = 20

        self.thickLabel.setText(f"Line Thickness: {v}px")
        self.canvas.changeThickness(v)
        
    def openColorPicker(self):
        color = qt.QColorDialog.getColor()  # Opens colour picker window
        if color.isValid():
            colorName = color.name()
            self.colorLabel.setStyleSheet(f"background-color:{colorName}; border:2px solid #000000")
            self.canvas.changeColor(colorName)
            
    def enableEyeDrop(self):
        self.eyeBtn.setChecked(True)
        self.canvas.eyeDrop(self.eyeBtn, self.colorLabel)
        
    def enabledPen(self):
        if self.penSelected:
            self.penSelected = False
        else:
            self.penSelected = True
            self.eraserSelected = False
            self.eraserBtn.setChecked(False)
            
        self.canvas.setPen(self.penSelected)
        self.canvas.setEraser(self.eraserSelected)
        
    def enableEraser(self):
        if self.eraserSelected:
            self.eraserSelected = False
        else:
            self.eraserSelected = True
            self.penSelected = False
            self.penBtn.setChecked(False)
            
        self.canvas.setPen(self.penSelected)
        self.canvas.setEraser(self.eraserSelected)
