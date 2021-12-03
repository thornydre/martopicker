from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools
import maya.OpenMayaUI as mui
import shiboken2
import sys
import os
import math
from functools import partial
# sys.path.append(os.path.dirname(__file__))
# import Editor

class Supicker(QtWidgets.QDialog):
	def __init__(self, parent = None):
		super(Supicker, self).__init__(parent)
		
		self.setInterface()
		self.connectInterface()
		self.maya_job = cmds.scriptJob(event=["SelectionChanged", self.editor.selectionFromViewport])


	def setInterface(self):
		main_layout = QtWidgets.QVBoxLayout()
		
		self.mode_button = QtWidgets.QPushButton("Edit")
		self.mode_button.setCheckable(True)

		self.editor = Editor(200, 200)

		main_layout.addWidget(self.mode_button)
		main_layout.addWidget(self.editor)

		self.setLayout(main_layout)


	def connectInterface(self):
		self.mode_button.clicked.connect(self.editor.toggleEditMode)


	def closeEvent(self, e):
		cmds.scriptJob(kill=self.maya_job)


class Editor(QtWidgets.QWidget):
	def __init__(self, width, height):
		self.buttons_list = []
		self.edit_mode = False
		self.box_selection = [-1, -1, 0, 0]

		super(Editor, self).__init__()

		self.setMinimumSize(width, height)
		self.resize(width, height) 


	def mousePressEvent(self, e):
		self.box_selection[0] = e.x()
		self.box_selection[1] = e.y()
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			if not self.edit_mode:
				self.updateSelectMode(e)
				self.repaint()


	def mouseReleaseEvent(self, e):
		if self.edit_mode:
			selection = cmds.ls(sl=True)
			self.buttons_list.append(EditorButton(e.x(), e.y(), 10, selection))
			self.updateEditMode()

		if self.box_selection[:1] != [-1, -1]:
			if abs(self.box_selection[2]) > 2 and abs(self.box_selection[3]) > 2:
				self.boxSelect()

			self.box_selection = [-1, -1, 0, 0]
			self.repaint()


	def mouseMoveEvent(self, e):
		if not self.edit_mode:
			if self.box_selection[:1] != [-1, -1]:
				self.box_selection[2] = e.x() - self.box_selection[0]
				self.box_selection[3] = e.y() - self.box_selection[1]
				self.repaint()


	def toggleEditMode(self):
		self.edit_mode = not self.edit_mode


	def paintEvent(self, e):
		qp = QtGui.QPainter()
		qp.begin(self)

		for button in self.buttons_list:
			button.draw(qp)

		if self.box_selection[:1] != [-1, -1]:
			qp.setPen(QtGui.QColor(184, 184, 255, 100))
			qp.setBrush(QtGui.QColor(184, 184, 255, 100))
			qp.drawRect(self.box_selection[0], self.box_selection[1], self.box_selection[2], self.box_selection[3])

		qp.end()


	def updateEditMode(self):
		size = self.size()
		w = size.width()

		self.repaint()


	def updateSelectMode(self, e):
		select = []
		for button in self.buttons_list:
			dist = math.sqrt((e.x() - button.getPosX()) ** 2 + (e.y() - button.getPosY()) ** 2)
			button.deselect()
			if dist < button.getRadius():
				button.select()
				for sel in button.getSelection():
					select.append(sel)

		cmds.select(select)


	def boxSelect(self):
		select = []
		for button in self.buttons_list:
			box_x_min = min((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
			box_x_max = max((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
			box_y_min = min((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))
			box_y_max = max((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))

			button.deselect()
			if button.getPosX() > box_x_min:
				if button.getPosX() < box_x_max:
					if button.getPosY() > box_y_min:
						if button.getPosY() < box_y_max:
							button.select()
							for sel in button.getSelection():
								select.append(sel)

		cmds.select(select)


	def selectionFromViewport(self):
		viewport_selection = cmds.ls(sl=True)

		for button in self.buttons_list:
			valid_sel = True
			for sel in button.getSelection():
				if sel not in viewport_selection:
					valid_sel = False

			if valid_sel:
				button.select()
			else:
				button.deselect()

		self.repaint()


class EditorButton():
	def __init__(self, pos_x, pos_y, radius, selection):
		self.pos_x = pos_x
		self.pos_y = pos_y
		self.radius = radius
		self.selection = selection
		self.selected = False


	def getPosX(self):
		return self.pos_x


	def getPosY(self):
		return self.pos_y


	def getRadius(self):
		return self.radius


	def getSelection(self):
		return self.selection


	def click(self):
		self.selected = not self.selected
		cmds.select(cl=True)
		for sel in self.selection:
			cmds.select(sel, add=True)


	def select(self):
		self.selected = True


	def deselect(self):
		self.selected = False
		# for sel in self.selection:
		# 	cmds.select(sel, deselect=True)


	def draw(self, qp):
		qp.setPen(QtGui.QColor(184, 184, 255))
		if self.selected:
			qp.setBrush(QtGui.QColor(220, 220, 255))
		else:
			qp.setBrush(QtGui.QColor(184, 184, 255))
		qp.drawEllipse(self.getPosX() - self.getRadius()/2, self.getPosY() - self.getRadius()/2, self.getRadius(), self.getRadius())


def getMayaWindow():
	ptr = mui.MQtUtil.mainWindow()
	return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)


def main():
	global ui
	ui = Supicker(getMayaWindow())
	ui.show()


if __name__ == "__main__":
	main()
