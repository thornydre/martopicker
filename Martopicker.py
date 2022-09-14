from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools
import maya.OpenMayaUI as mui
import shiboken2
import sys
import os
import math
import pickle
import maya.cmds as cmds
from functools import partial
# sys.path.append(os.path.dirname(__file__))
# import Editor

class Martopicker(QtWidgets.QDialog):
	def __init__(self, parent = None):
		super(Martopicker, self).__init__(parent)

		# self.installEventFilter(self)

		self.setInterface()
		self.connectInterface()
		self.maya_job = cmds.scriptJob(event=["SelectionChanged", self.editor.selectionFromViewport])


	def setInterface(self):
		main_layout = QtWidgets.QVBoxLayout()
		
		buttons_widget = QtWidgets.QWidget()
		buttons_widget.setMinimumHeight(30)
		buttons_widget.setMaximumHeight(30)
		buttons_widget.setContentsMargins(0, 0, 0, 0)
		buttons_layout = QtWidgets.QHBoxLayout()
		buttons_layout.setContentsMargins(0, 0, 0, 0)

		self.mode_button = QtWidgets.QPushButton("Edit")
		self.mode_button.setMaximumWidth(100)
		self.mode_button.setCheckable(True)

		self.edit_buttons_widget = QtWidgets.QWidget()
		edit_buttons_layout = QtWidgets.QHBoxLayout()
		edit_buttons_layout.setContentsMargins(0, 0, 0, 0)

		self.color_button = QtWidgets.QPushButton("Color")
		self.size_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.name_textfield = QtWidgets.QLineEdit()
		self.add_scripted_button = QtWidgets.QPushButton("Add Scripted Button")

		edit_buttons_layout.addWidget(self.color_button)
		edit_buttons_layout.addWidget(self.size_slider)
		edit_buttons_layout.addWidget(self.name_textfield)
		edit_buttons_layout.addWidget(self.add_scripted_button)
		self.edit_buttons_widget.setLayout(edit_buttons_layout)
		self.edit_buttons_widget.setVisible(False)

		self.editor = Editor(self, 600, 400)

		buttons_layout.addWidget(self.mode_button)
		buttons_layout.addWidget(self.edit_buttons_widget)
		buttons_layout.addStretch(1)

		buttons_widget.setLayout(buttons_layout)

		main_layout.addWidget(buttons_widget)
		main_layout.addWidget(self.editor)

		self.setLayout(main_layout)


	def connectInterface(self):
		self.mode_button.clicked.connect(self.toggleEditModeCommand)
		self.color_button.clicked.connect(self.chooseColorCommand)
		self.name_textfield.textEdited.connect(self.buttonNameChangedCommand)


	def toggleEditModeCommand(self):
		self.editor.toggleEditMode()
		self.edit_buttons_widget.setVisible(self.editor.getEditMode())


	def chooseColorCommand(self):
		# color = QtWidgets.QColorDialog.getColor(options=QtWidgets.QColorDialog.DontUseNativeDialog)
		color = QtWidgets.QColorDialog.getColor()

		print(color)


	def buttonNameChangedCommand(self):
		name = self.name_textfield.text()

		self.editor.setButtonName(name)


	def closeEvent(self, e):
		cmds.scriptJob(kill=self.maya_job)


	def keyPressEvent(self, e):
		self.editor.keyPressEvent(e)


class Editor(QtWidgets.QWidget):
	def __init__(self, parent, width, height):
		self.parent = parent
		self.buttons_list = []
		self.selected_list = []
		self.edit_mode = False
		self.box_selection = [-1, -1, 0, 0]
		self.edited_list = []

		self.moving_buttons = False

		super(Editor, self).__init__()

		self.installEventFilter(self)

		self.setAutoFillBackground(True)
		p = self.palette()
		p.setColor(self.backgroundRole(), QtGui.QColor(50, 50, 50))
		self.setPalette(p)
		self.setMinimumSize(width, height)
		self.resize(width, height) 


	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.setFocus()

			start_box = True
			if self.edit_mode:
				self.edited_list = []
				reset_selection = True

				if self.selected_list:
					for button in self.buttons_list:
						if button.isOnButton(e.x(), e.y()):
							if button.getSelected():
								reset_selection = False

				for button in self.buttons_list:
					button.setEditOffset((button.getPosX() - e.x(), button.getPosY() - e.y()))

					if reset_selection:
						self.deselectButton(button)
					else:
						if button.getSelected():
							self.edited_list.append(button)

					if button.isOnButton(e.x(), e.y()):
						self.selectButton(button)
						start_box = False

						if reset_selection:
							if button.getSelected():
								self.edited_list.append(button)

			if start_box:
				self.box_selection[0] = e.x()
				self.box_selection[1] = e.y()


	def mouseReleaseEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			if self.edit_mode:
				if self.edited_list:
					self.edited_list = []
				else:
					if abs(self.box_selection[2]) < 2 and abs(self.box_selection[3]) < 2:
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

							self.repaint()

			self.updateSelectMode(e)

		if self.box_selection[:1] != [-1, -1]:
			if not self.edited_list:
				if (self.box_selection[2] ** 2 + self.box_selection[3] ** 2) ** 0.5 > 2:
					self.boxSelect()


	def mouseMoveEvent(self, e):
		repaint = False

		if self.edit_mode:
			self.moving_buttons = True
			for button in self.edited_list:
				button.setPosX(e.x() + button.getEditOffset()[0])
				button.setPosY(e.y() + button.getEditOffset()[1])
				repaint = True

		if self.box_selection[:1] != [-1, -1]:
			if not self.edited_list:
				self.box_selection[2] = e.x() - self.box_selection[0]
				self.box_selection[3] = e.y() - self.box_selection[1]
				repaint = True

		if repaint:
			self.repaint()


	def keyPressEvent(self, e):
		if e.key() == QtCore.Qt.Key_Delete:
			if self.edit_mode:
				for button in self.selected_list:
					self.buttons_list.remove(button)
				self.selected_list = []
			else:
				cmds.delete(cmds.ls(sl=True))
				for button in self.selected_list:
					self.buttons_list.remove(button)
				self.selected_list = []

			self.repaint()

		elif e.key() == QtCore.Qt.Key_S:
			if e.modifiers() == QtCore.Qt.ControlModifier:
				save_path = QtWidgets.QFileDialog.getSaveFileName(caption="Save picker", filter="*.pik")[0]

				self.savePicker(save_path)

		elif e.key() == QtCore.Qt.Key_O:
			if e.modifiers() == QtCore.Qt.ControlModifier:
				file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Load picker", filter="*.pik")[0]

				self.loadPicker(file_path)


	def toggleEditMode(self):
		self.edit_mode = not self.edit_mode
		self.repaint()


	def paintEvent(self, e):
		qp = QtGui.QPainter()
		qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
		qp.begin(self)

		for button in self.buttons_list:
			button.draw(qp, self.edit_mode)

		if self.box_selection[:1] != [-1, -1]:
			qp.setPen(QtGui.QColor(184, 184, 255, 50))
			qp.setBrush(QtGui.QColor(184, 184, 255, 50))
			qp.drawRect(self.box_selection[0], self.box_selection[1], self.box_selection[2], self.box_selection[3])

		qp.end()


	def updateSelectMode(self, e):
		select = []

		if self.moving_buttons:
			self.moving_buttons = False
		else:
			for button in self.buttons_list:
				dist = math.sqrt((e.x() - button.getPosX()) ** 2 + (e.y() - button.getPosY()) ** 2)
				self.deselectButton(button)
				if button.isOnButton(e.x(), e.y()):
					self.selectButton(button)
					for sel in button.getSelection():
						select.append(sel)

		if not self.edit_mode:
			cmds.select(select)

		self.repaint()


	def boxSelect(self):
		select = []

		box_x_min = min((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
		box_x_max = max((self.box_selection[0], self.box_selection[0] + self.box_selection[2]))
		box_y_min = min((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))
		box_y_max = max((self.box_selection[1], self.box_selection[1] + self.box_selection[3]))
		
		for button in self.buttons_list:
			self.deselectButton(button)
			if button.getPosX() + button.getRadiusX()/2 > box_x_min:
				if button.getPosX() - button.getRadiusX()/2 < box_x_max:
					if button.getPosY() + button.getRadiusY()/2 > box_y_min:
						if button.getPosY() - button.getRadiusY()/2 < box_y_max:
							self.selectButton(button)
							for sel in button.getSelection():
								select.append(sel)

		if not self.edit_mode:
			cmds.select(select)

		if len(self.selected_list) == 1:
			self.parent.name_textfield.setEnabled(True)
		else:
			self.parent.name_textfield.setEnabled(False)

		self.box_selection = [-1, -1, 0, 0]

		self.repaint()


	def selectionFromViewport(self):
		if not self.edit_mode:
			viewport_selection = cmds.ls(sl=True)

			for button in self.buttons_list:
				valid_sel = True
				for sel in button.getSelection():
					if sel not in viewport_selection:
						valid_sel = False

				if valid_sel:
					self.selectButton(button)
				else:
					self.deselectButton(button)

			self.repaint()


	def getEditMode(self):
		return self.edit_mode


	def setButtonName(self, name):
		self.selected_list[0].setText(name)
		self.repaint()


	def selectButton(self, button):
		button.select()
		if button not in self.selected_list:
			self.selected_list.append(button)


	def deselectButton(self, button):
		button.deselect()
		if button in self.selected_list:
			self.selected_list.remove(button)


	def savePicker(self, path):
		if path:
			if os.path.splitext(path)[1] == ".pik":
				with open(path, "wb") as file:
					pickle.dump(self.buttons_list, file)


	def loadPicker(self, path):
		if path:
			if os.path.splitext(path)[1] == ".pik":
				with open(path, "rb") as file:
					self.buttons_list = pickle.load(file)
					self.repaint()


class EditorButton():
	def __init__(self, pos_x, pos_y, radius_x, radius_y, selection, shape, text):
		self.pos_x = pos_x
		self.pos_y = pos_y
		self.radius_x = radius_x
		self.radius_y = radius_y
		self.edit_offset = (0, 0)
		self.selection = selection
		self.shape = shape
		self.text = text
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


	def setEditOffset(self, edit_offset):
		self.edit_offset = edit_offset


	def getEditOffset(self):
		return self.edit_offset


	def getSelection(self):
		return self.selection


	def getShape(self):
		return self.shape


	def getText(self):
		return self.text


	def setText(self, text):
		self.text = text


	def select(self):
		self.selected = True


	def deselect(self):
		self.selected = False


	def getSelected(self):
		return self.selected


	def draw(self, qp, edit_mode):
		qp.setBrush(self.color)
		qp.setPen(QtGui.QColor(10, 10, 10))

		if self.selected:
			qp.setBrush(self.selected_color)
			if edit_mode:
				qp.setBrush(self.color)
				qp.setPen(self.selected_color)

		if self.shape == "ellipse":
			if self.text:
				qp.drawRoundedRect()
				qp.drawText(self.pos_x - self.radius_x/2, self.pos_y - self.radius_y/2, self.text)
			else:
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
