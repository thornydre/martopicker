from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools
import maya.OpenMayaUI as mui
import shiboken2


class Editor(QtWidgets.QWidget):
	def __init__(self, width, height):
		self.buttons_list = []

		super(Editor, self).__init__()

		self.setMinimumSize(width, height)
		self.resize(width, height) 


	def mousePressEvent(self, e):
		self.buttons_list.append((e.x(), e.y()))


	def paintEvent(self, e):
		qp = QtGui.QPainter()
		qp.begin(self)

		qp.setPen(QColor(184, 184, 255))
		qp.setBrush(QColor(184, 184, 255))

		for button in self.buttons_list:
			qp.drawEllipse(button[0], button[1], 10, 10)

		qp.end()


	def update(self, e=None):
		size = self.size()
		w = size.width()

		self.repaint()
