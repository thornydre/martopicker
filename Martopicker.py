from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools
import maya.OpenMayaUI as mui
import shiboken2
import sys
import os
import math
from functools import partial
# sys.path.append(os.path.dirname(__file__))
# import Editor

class Martopicker(QtWidgets.QDialog):
	def __init__(self, parent = None):
		super(Martopicker, self).__init__(parent)
		
		self.setInterface()
		self.connectInterface()
		self.maya_job = cmds.scriptJob(event=["SelectionChanged", self.editor.selectionFromViewport])


	def setInterface(self):
		main_layout = QtWidgets.QVBoxLayout()
		
		buttons_layout = QtWidgets.QHBoxLayout()

		self.mode_button = QtWidgets.QPushButton("Edit")
		self.mode_button.setMaximumWidth(100)
		self.mode_button.setCheckable(True)

		self.edit_buttons_widget = QtWidgets.QWidget()
		edit_buttons_layout = QtWidgets.QHBoxLayout()

		self.add_selector_button = QtWidgets.QPushButton("Add Selector")
		self.add_mult_selector_button = QtWidgets.QPushButton("Add Multiple Selector")

		edit_buttons_layout.addWidget(self.add_selector_button)
		edit_buttons_layout.addWidget(self.add_mult_selector_button)
		self.edit_buttons_widget.setLayout(edit_buttons_layout)
		self.edit_buttons_widget.setVisible(False)

		self.editor = Editor(400, 400)

		buttons_layout.addWidget(self.mode_button)
		buttons_layout.addWidget(self.edit_buttons_widget)
		buttons_layout.addStretch(1)

		main_layout.addLayout(buttons_layout)
		main_layout.addWidget(self.editor)

		self.setLayout(main_layout)


	def connectInterface(self):
		self.mode_button.clicked.connect(self.toggleEditMode)


	def toggleEditMode(self):
		self.editor.toggleEditMode()
		self.edit_buttons_widget.setVisible(self.editor.getEditMode())


	def closeEvent(self, e):
		cmds.scriptJob(kill=self.maya_job)


class Editor(QtWidgets.QWidget):
	def __init__(self, width, height):
		self.buttons_list = []
		self.edit_mode = False
		self.box_selection = [-1, -1, 0, 0]
		self.edited_button = None

		super(Editor, self).__init__()

		self.setAutoFillBackground(True)
		p = self.palette()
		p.setColor(self.backgroundRole(), QtGui.QColor(50, 50, 50))
		self.setPalette(p)
		self.setMinimumSize(width, height)
		self.resize(width, height) 


	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			if self.edit_mode:
				for button in self.buttons_list:
					dist = math.sqrt((e.x() - button.getPosX()) ** 2 + (e.y() - button.getPosY()) ** 2)
					button.deselect()
					if button.isOnButton(e.x(), e.y()):
						self.edited_button = button
			else:
				self.box_selection[0] = e.x()
				self.box_selection[1] = e.y()


	def mouseReleaseEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			if self.edit_mode:
				if self.edited_button:
					self.edited_button = None
				else:
					selection = cmds.ls(sl=True)
					if selection:
						if len(selection) == 1:
							self.buttons_list.append(EditorButton(e.x(), e.y(), 10, 10, selection, "ellipse", ""))
						else:
							self.buttons_list.append(EditorButton(e.x(), e.y(), 20, 10, selection, "rect", ""))
							i = 1
							for sel in selection:
								self.buttons_list.append(EditorButton(e.x(), e.y() + i * 20, 10, 10, [sel], "ellipse", ""))
								i += 1

						self.updateEditMode()
			else:
				self.updateSelectMode(e)
				self.repaint()

		if self.box_selection[:1] != [-1, -1]:
			if abs(self.box_selection[2]) > 2 and abs(self.box_selection[3]) > 2:
				self.boxSelect()

			self.box_selection = [-1, -1, 0, 0]
			self.repaint()


	def mouseMoveEvent(self, e):
		if self.edit_mode:
			if self.edited_button:
				self.edited_button.setPosX(e.x())
				self.edited_button.setPosY(e.y())
				self.repaint()
		else:
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
		self.repaint()


	def updateSelectMode(self, e):
		select = []
		for button in self.buttons_list:
			dist = math.sqrt((e.x() - button.getPosX()) ** 2 + (e.y() - button.getPosY()) ** 2)
			button.deselect()
			if button.isOnButton(e.x(), e.y()):
				button.select()
				for sel in button.getSelection():
					select.append(sel)

		cmds.select(select)


	def boxSelect(self):
		select = []

		box_x_min = min((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
		box_x_max = max((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
		box_y_min = min((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))
		box_y_max = max((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))
		
		for button in self.buttons_list:
			button.deselect()
			if button.getPosX() + button.getRadiusX()/2 > box_x_min:
				if button.getPosX() - button.getRadiusX()/2 < box_x_max:
					if button.getPosY() + button.getRadiusY()/2 > box_y_min:
						if button.getPosY() - button.getRadiusY()/2 < box_y_max:
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


	def getEditMode(self):
		return self.edit_mode


class EditorButton():
	def __init__(self, pos_x, pos_y, radius_x, radius_y, selection, shape, text):
		self.pos_x = pos_x
		self.pos_y = pos_y
		self.radius_x = radius_x
		self.radius_y = radius_y
		self.selection = selection
		self.shape = shape
		self.selected = False
		self.color = QtGui.QColor(120, 120, 255)
		self.selected_color = QtGui.QColor(220, 220, 255)


	def getPosX(self):
		return self.pos_x


	def getPosY(self):
		return self.pos_y


	def setPosX(self, pos_x):
		self.pos_x = pos_x


	def setPosY(self, pos_y):
		self.pos_y = pos_y


	def getRadiusX(self):
		return self.radius_x


	def getRadiusY(self):
		return self.radius_y


	def getSelection(self):
		return self.selection


	def getShape(self):
		return self.shape


	def select(self):
		self.selected = True


	def deselect(self):
		self.selected = False


	def draw(self, qp):
		qp.setPen(QtGui.QColor(10, 10, 10))
		if self.selected:
			qp.setBrush(self.selected_color)
		else:
			qp.setBrush(self.color)

		if self.shape == "ellipse":
			qp.drawEllipse(self.pos_x - self.radius_x/2, self.pos_y - self.radius_y/2, self.radius_x, self.radius_y)
		elif self.shape == "rect":
			qp.drawRect(self.pos_x - self.radius_x/2, self.pos_y - self.radius_y/2, self.radius_x, self.radius_y)

	def isOnButton(self, x, y):
		if x > self.pos_x - self.radius_x/2:
			if x < self.pos_x + self.radius_x/2:
				if y > self.pos_y - self.radius_y/2:
					if y < self.pos_y + self.radius_y/2:
						return True
		return False

def getMayaWindow():
	ptr = mui.MQtUtil.mainWindow()
	return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)


def main():
	global ui
	ui = Martopicker(getMayaWindow())
	ui.show()


if __name__ == "__main__":
	main()
