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
	def __init__(self, parent=None):
		super(Martopicker, self).__init__(parent)

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
		self.bg_image_button = QtWidgets.QPushButton("Change Background")

		edit_buttons_layout.addWidget(self.color_button)
		edit_buttons_layout.addWidget(self.size_slider)
		edit_buttons_layout.addWidget(self.name_textfield)
		edit_buttons_layout.addWidget(self.add_scripted_button)
		edit_buttons_layout.addWidget(self.bg_image_button)
		self.edit_buttons_widget.setLayout(edit_buttons_layout)
		self.edit_buttons_widget.setVisible(False)

		self.editor = Editor(600, 400, self)

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
		self.size_slider.valueChanged.connect(self.sizeSliderCommand)
		self.name_textfield.textEdited.connect(self.buttonNameChangedCommand)
		self.add_scripted_button.clicked.connect(self.textEditorCommand)
		self.bg_image_button.clicked.connect(self.changeBackgroundCommand)


	def toggleEditModeCommand(self):
		self.editor.toggleEditMode()
		self.edit_buttons_widget.setVisible(self.editor.getEditMode())


	def chooseColorCommand(self):
		color = QtGui.QColor(128, 128, 128)

		selected_list = self.editor.getSelectedList()

		if selected_list:
			color = selected_list[-1].getColor()

		color_dialog = ColorPickerWindow(color, self)
		color_dialog.move(self.pos().x() - color_dialog.width() * 2.5, self.pos().y())
		color_dialog.exec()

		color_info = color_dialog.getData()

		if color_info:
			self.editor.setButtonColor(color_info["color"])


	def sizeSliderCommand(self):
		size = self.size_slider.value() / 5

		self.editor.setButtonSizeOffset(size)


	def buttonNameChangedCommand(self):
		name = self.name_textfield.text()

		self.editor.setButtonName(name)


	def textEditorCommand(self):
		text_editor = TextEditor(self)
		text_editor.exec()

		button_info = text_editor.getData()

		if button_info:
			self.editor.addEditorButton((50, 50), (20, 20), [], "rect", QtGui.QColor(255, 249, 23), "", button_info["script"])
			self.editor.repaint()


	def changeBackgroundCommand(self):
		image_path = QtWidgets.QFileDialog.getOpenFileName(caption="Load background image", filter="Images (*.png *.xpm *.jpg)")[0]

		self.editor.setBackgroundImage(image_path)


	def closeEvent(self, e):
		cmds.scriptJob(kill=self.maya_job)


	def keyPressEvent(self, e):
		self.editor.keyPressEvent(e)


class Editor(QtWidgets.QWidget):
	def __init__(self, width, height, parent=None):
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

		self.bg_image = ""


	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.setFocus()
			not_selected = True

			start_box = True
			if self.edit_mode:
				self.edited_list = []
				reset_selection = True

				if self.selected_list:
					for button in self.buttons_list:
						if button.isOnButton(e.x(), e.y()):
							if button.getSelected():
								reset_selection = False

				for button in reversed(self.buttons_list):
					button.setEditOffset((button.getPosX() - e.x(), button.getPosY() - e.y()))

					if not_selected:
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
								not_selected = False

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
								color = self.generateButtonColor(selection[0])
								self.addEditorButton((e.x(), e.y()), (10, 10), selection, "ellipse", color, "", "")
							else:
								self.addEditorButton((e.x(), e.y()), (20, 10), selection, "rect", QtGui.QColor(255, 249, 23), "", "")
								i = 1
								for sel in selection:
									color = self.generateButtonColor(sel)
									self.addEditorButton((e.x(), e.y() + i * 20), (10, 10), [sel], "ellipse", color, "", "")
									i += 1

							self.repaint()

			self.updateSelectMode(e)

		if self.box_selection[:1] != [-1, -1]:
			if not self.edited_list:
				if (self.box_selection[2] ** 2 + self.box_selection[3] ** 2) ** 0.5 > 2:
					self.boxSelect()

		self.box_selection = [-1, -1, 0, 0]
		self.repaint()

		if len(self.selected_list) == 1:
			self.parent.name_textfield.setEnabled(True)
			self.parent.name_textfield.setText(self.selected_list[0].getText())
			self.parent.size_slider.setValue(self.selected_list[0].getSize() * 5)
		else:
			self.parent.name_textfield.setText("")
			self.parent.name_textfield.setEnabled(False)


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

			self.parent.name_textfield.setText("")
			self.parent.name_textfield.setEnabled(False)

			self.repaint()

		elif e.key() == QtCore.Qt.Key_Left:
			if self.edit_mode:
				self.verticalAlignMin()

		elif e.key() == QtCore.Qt.Key_Right:
			if self.edit_mode:
				self.verticalAlignMax()

		elif e.key() == QtCore.Qt.Key_Up:
			if self.edit_mode:
				self.horizontalAlignMin()

		elif e.key() == QtCore.Qt.Key_Down:
			if self.edit_mode:
				self.horizontalAlignMax()

		elif e.key() == QtCore.Qt.Key_A:
			if self.edit_mode:
				self.align()

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
		qp.begin(self)
		qp.setRenderHint(QtGui.QPainter.Antialiasing, True)

		if self.bg_image:
			qp.drawPixmap(self.bg_scaled_pixmap.rect(), self.bg_scaled_pixmap)

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
				self.deselectButton(button)
				if button.isOnButton(e.x(), e.y()):
					self.selectButton(button)
					for sel in button.getSelection():
						if cmds.objExists(sel):
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
								if cmds.objExists(sel):
									select.append(sel)

		if not self.edit_mode:
			cmds.select(select)


	def selectionFromViewport(self):
		if not self.edit_mode:
			viewport_selection = cmds.ls(sl=True)

			for button in self.buttons_list:
				valid_sel = True
				if button.getSelection():
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


	def getSelectedList(self):
		return self.selected_list

	def setButtonColor(self, color):
		for button in self.selected_list:
			button.setColor(color)
		self.repaint()


	def setButtonSizeOffset(self, size):
		for button in self.selected_list:
			button.setSize(size)
		self.repaint()


	def setButtonName(self, name):
		self.selected_list[0].setText(name)
		self.repaint()


	def selectButton(self, button):
		if not self.edit_mode and button.getScript():
			button.executeScript()
		else:
			button.select()
			if button not in self.selected_list:
				self.selected_list.append(button)


	def deselectButton(self, button):
		button.deselect()
		if button in self.selected_list:
			self.selected_list.remove(button)


	def setBackgroundImage(self, image_path):
		self.bg_image = image_path
		bg_pixmap = QtGui.QPixmap(self.bg_image)
		self.bg_scaled_pixmap = bg_pixmap.scaledToWidth(600)
		self.setMinimumSize(self.bg_scaled_pixmap.width(), self.bg_scaled_pixmap.height())
		self.resize(self.bg_scaled_pixmap.width(), self.bg_scaled_pixmap.height())


	def savePicker(self, path):
		if path:
			if os.path.splitext(path)[1] == ".pik":
				data = {"buttons": self.buttons_list, "background": self.bg_image}
				with open(path, "wb") as file:
					pickle.dump(data, file)


	def loadPicker(self, path):
		if path:
			if os.path.splitext(path)[1] == ".pik":
				with open(path, "rb") as file:
					data = pickle.load(file)
					self.buttons_list = data["buttons"]
					self.setBackgroundImage(data["background"])
					self.repaint()


	def generateButtonColor(self, selection):
		name_based = False
		position_based = True
		color_based = False

		if name_based:
			if "_lf_" in selection:
				return QtGui.QColor(120, 120, 255)
			elif "_rt_" in selection:
				return QtGui.QColor(255, 120, 120)

		elif position_based:
			if cmds.xform(selection, q=True, t=True, ws=True)[0] > 0:
				return QtGui.QColor(120, 120, 255)
			elif cmds.xform(selection, q=True, t=True, ws=True)[0] < 0:
				return QtGui.QColor(255, 120, 120)

		return QtGui.QColor(255, 249, 23)


	def addEditorButton(self, pos, size, elem, shape, color, text, script):
		self.buttons_list.append(EditorButton(pos[0], pos[1], size[0], size[1], elem, shape, color, text, script))


	def verticalAlignMin(self):
		min_button = self.selected_list[0]

		for button in self.selected_list:
			if button.getPosX() < min_button.getPosX():
				min_button = button

		for button in self.selected_list:
			button.setPosX(min_button.getPosX())

		self.repaint()


	def verticalAlignMax(self):
		min_button = self.selected_list[0]

		for button in self.selected_list:
			if button.getPosX() > min_button.getPosX():
				min_button = button

		for button in self.selected_list:
			button.setPosX(min_button.getPosX())

		self.repaint()


	def horizontalAlignMin(self):
		min_button = self.selected_list[0]

		for button in self.selected_list:
			if button.getPosY() < min_button.getPosY():
				min_button = button

		for button in self.selected_list:
			button.setPosY(min_button.getPosY())

		self.repaint()


	def horizontalAlignMax(self):
		min_button = self.selected_list[0]

		for button in self.selected_list:
			if button.getPosY() > min_button.getPosY():
				min_button = button

		for button in self.selected_list:
			button.setPosY(min_button.getPosY())

		self.repaint()


	def align(self):
		start_button = self.selected_list[-1]
		end_button = self.selected_list[-2]

		vec = [end_button.getPosX() - start_button.getPosX(), end_button.getPosY() - start_button.getPosY()]

		intervals = len(self.selected_list) - 1

		inter_vec = [vec[0] / intervals, vec[1] / intervals]

		for i, button in enumerate(self.selected_list[:-2]):
			buton.setPosX(start_button.getPosX() + inter_vec * (i + 1))
			buton.setPosY(start_button.getPosY() + inter_vec * (i + 1))


class EditorButton():
	def __init__(self, pos_x, pos_y, radius_x, radius_y, selection, shape, color, text, script):
		self.pos_x = pos_x
		self.pos_y = pos_y
		self.default_radius_x = radius_x
		self.radius_x = radius_x
		self.default_radius_y = radius_y
		self.radius_y = radius_y
		self.size_offset = 0
		self.edit_offset = (0, 0)
		self.selection = selection
		self.shape = shape
		self.color = color
		self.selected_color = QtGui.QColor.fromHsv(self.color.hue(), max(self.color.saturation() - 100, 0), min(self.color.value() + 100, 255))
		self.text = text
		self.script = script

		self.selected = False


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


	def getColor(self):
		return self.color


	def setColor(self, color):
		self.color = color
		self.selected_color = QtGui.QColor.fromHsv(self.color.hue(), max(self.color.saturation() - 120, 0), min(self.color.value() + 120, 255))


	def getText(self):
		return self.text


	def setText(self, text):
		self.text = text

		if self.text:
			qp = QtGui.QPainter()
			font = qp.font()
			fm = QtGui.QFontMetrics(font)
			rect = fm.boundingRect(self.text)

			self.radius_x = rect.width() + 5 + self.size_offset
			self.radius_y = rect.height() + 2 + self.size_offset

		else:
			self.radius_x = self.default_radius_x + self.size_offset
			self.radius_y = self.default_radius_y + self.size_offset


	def getScript(self):
		return self.script


	def getSize(self):
		return self.size_offset


	def setSize(self, size):
		self.size_offset = size

		if self.text:
			qp = QtGui.QPainter()
			font = qp.font()
			fm = QtGui.QFontMetrics(font)
			rect = fm.boundingRect(self.text)

			self.radius_x = rect.width() + 5 + self.size_offset
			self.radius_y = rect.height() + 2 + self.size_offset

		else:
			self.radius_x = self.default_radius_x + self.size_offset
			self.radius_y = self.default_radius_y + self.size_offset


	def select(self):
		self.selected = True


	def deselect(self):
		self.selected = False


	def executeScript(self):
		exec(self.script)


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

		size_x = self.radius_x
		size_y = self.radius_y

		if self.shape == "ellipse":
			if self.text:
				qp.drawRoundedRect(self.pos_x - size_x/2, self.pos_y - size_y/2, size_x, size_y, 5, 5)
				qp.drawText(self.pos_x - size_x/2, self.pos_y - size_y/2, size_x, size_y, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter, self.text)
			else:
				qp.drawEllipse(self.pos_x - size_x/2, self.pos_y - size_y/2, size_x, size_y)
		elif self.shape == "rect":
			qp.drawRect(self.pos_x - size_x/2, self.pos_y - size_y/2, size_x, size_y)

			if self.text:
				qp.drawText(self.pos_x - size_x/2, self.pos_y - size_y/2, size_x, size_y, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter, self.text)


	def isOnButton(self, x, y):
		if x > self.pos_x - self.radius_x/2:
			if x < self.pos_x + self.radius_x/2:
				if y > self.pos_y - self.radius_y/2:
					if y < self.pos_y + self.radius_y/2:
						return True
		return False


class TextEditor(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super(TextEditor, self).__init__(parent)

		self.validate = True
		self.script = ""

		self.setInterface()
		self.connectInterface()


	def setInterface(self):
		main_layout = QtWidgets.QVBoxLayout()

		self.text_editor = QtWidgets.QPlainTextEdit()

		buttons_layout = QtWidgets.QHBoxLayout()
		buttons_layout.setContentsMargins(0, 0, 0, 0)

		self.submit_button = QtWidgets.QPushButton("Create Button")
		self.cancel_button = QtWidgets.QPushButton("Cancel")

		buttons_layout.addWidget(self.submit_button)
		buttons_layout.addWidget(self.cancel_button)

		main_layout.addWidget(self.text_editor)
		main_layout.addLayout(buttons_layout)

		self.setLayout(main_layout)


	def connectInterface(self):
		self.submit_button.clicked.connect(self.createButtonCommand)
		self.cancel_button.clicked.connect(self.cancelCommand)


	def createButtonCommand(self):
		self.script = self.text_editor.toPlainText()

		if self.script:
			self.close()


	def cancelCommand(self):
		self.validate = False
		self.close()


	def getData(self):
		if self.validate:
			if self.script:
				result = {}
				result["script"] = self.script
				return result
		return None


class ColorPickerWindow(QtWidgets.QDialog):
	def __init__(self, color, parent=None):
		super(ColorPickerWindow, self).__init__(parent)

		self.color = color
		self.validate = True
		
		self.setInterface()
		self.connectInterface()


	def setInterface(self):
		vertical_layout = QtWidgets.QVBoxLayout()
		horizontal_layout = QtWidgets.QHBoxLayout()

		self.color_wheel_widget = ColorWheel(parent=self, radius=100, color=self.color)
		self.color_value_widget = ColorValue(parent=self, width=16, height=200, color=self.color)
		self.color_display_widget = ColorDisplay(color=self.color)
		
		horizontal_layout.addWidget(self.color_wheel_widget)
		horizontal_layout.addWidget(self.color_value_widget)

		buttons_layout = QtWidgets.QHBoxLayout()
		buttons_layout.setContentsMargins(0, 0, 0, 0)

		self.submit_button = QtWidgets.QPushButton("OK")
		self.cancel_button = QtWidgets.QPushButton("Cancel")

		buttons_layout.addWidget(self.submit_button)
		buttons_layout.addWidget(self.cancel_button)

		vertical_layout.addLayout(horizontal_layout)
		vertical_layout.addWidget(self.color_display_widget)
		vertical_layout.addLayout(buttons_layout)

		self.setLayout(vertical_layout)


	def connectInterface(self):
		self.color_wheel_widget.color_changed_signal.connect(self.colorChangedCommand)
		self.color_value_widget.value_changed_signal.connect(self.valueChangedCommand)
		self.submit_button.clicked.connect(self.submitCommand)
		self.cancel_button.clicked.connect(self.cancelCommand)


	def getColor(self):
		return self.color_wheel_widget.getColor()


	@QtCore.Slot()
	def valueChangedCommand(self):
		self.color_wheel_widget.setValue(self.color_value_widget.getValue())
		self.colorChangedCommand()


	@QtCore.Slot()
	def colorChangedCommand(self):
		self.color_display_widget.setColor(self.color_wheel_widget.getColor())


	def submitCommand(self):
		self.close()


	def cancelCommand(self):
		self.validate = False
		self.close()


	def getData(self):
		if self.validate:
			result = {}
			result["color"] = self.color_wheel_widget.getColor()
			return result
		return None


class ColorWheel(QtWidgets.QWidget):
	color_changed_signal = QtCore.Signal()

	def __init__(self, radius, color, parent=None):
		super(ColorWheel, self).__init__(parent)

		self.parent = parent

		self.radius = radius
		self.hue = color.hueF()
		self.saturation = color.saturationF()
		self.value = color.valueF()
		self.pressed = False
		self.cursor_pos = [0, 0]
		self.positionCursor()
		self.cursor_radius = 6

		self.setMinimumWidth(self.radius * 2)
		self.setMinimumHeight(self.radius * 2)

		self.qp = QtGui.QPainter()


	def paintEvent(self, e):
		self.qp.begin(self)
		self.qp.setRenderHint(QtGui.QPainter.Antialiasing, True)

		center = QtCore.QPointF(self.radius, self.radius)
		self.hsv_grad = QtGui.QConicalGradient(center, self.radius)
		for deg in range(360):
			col = QtGui.QColor.fromHsvF(deg / 360, 1, self.value)
			self.hsv_grad.setColorAt(deg / 360, col)

		self.val_grad = QtGui.QRadialGradient(center, self.radius)
		self.val_grad.setColorAt(0.0, QtGui.QColor.fromHsvF(0.0, 0.0, self.value, 1.0))
		self.val_grad.setColorAt(1.0, QtCore.Qt.transparent)

		self.qp.setPen(QtCore.Qt.transparent)
		self.qp.setBrush(self.hsv_grad)
		self.qp.drawEllipse(0, 0, self.radius * 2, self.radius * 2)
		self.qp.setBrush(self.val_grad)
		self.qp.drawEllipse(0, 0, self.radius * 2, self.radius * 2)

		self.qp.setPen(QtGui.QColor(0, 0, 0))
		self.qp.setBrush(QtGui.QColor(255, 255, 255))
		self.qp.drawEllipse(self.cursor_pos[0] - self.cursor_radius/2, self.cursor_pos[1] - self.cursor_radius/2, self.cursor_radius, self.cursor_radius)

		self.qp.end()


	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.setFocus()

			self.updateCursorPos(e.x(), e.y())

			self.pressed = True

			self.repaint()


	def mouseMoveEvent(self, e):
		if self.pressed:
			self.updateCursorPos(e.x(), e.y())

			self.repaint()


	def mouseReleaseEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.pressed = False

			self.repaint()


	def updateCursorPos(self, new_x, new_y):
		self.cursor_pos = [new_x, new_y]

		dist = ((self.radius - self.cursor_pos[0]) ** 2 + (self.radius - self.cursor_pos[1]) ** 2) ** 0.5
		x = self.cursor_pos[0] - self.radius
		y = self.cursor_pos[1] - self.radius
		if dist > self.radius:
			ratio = self.radius / dist
			self.cursor_pos[0] = self.radius + x * ratio
			self.cursor_pos[1] = self.radius + y * ratio

		mod = math.sqrt(x * x + y * y) * math.sqrt(1)
		angle = math.acos(y / mod) / math.pi
		
		if x < 0:
			self.hue = (1 - angle) / 2
		else:
			self.hue = angle / 2 + 0.5

		self.saturation = min(dist / self.radius, 1.0)

		self.color_changed_signal.emit()


	def setHue(self, hue):
		self.hue = hue
		self.repaint()


	def setSaturation(self, saturation):
		self.saturation = saturation
		self.repaint()


	def setValue(self, value):
		self.value = value
		self.repaint()


	def getColor(self):
		return QtGui.QColor.fromHsvF(self.hue, self.saturation, self.value)


	def positionCursor(self):
		x_coord = math.sin(self.hue * math.pi * 2) * self.radius * self.saturation * -1
		y_coord = math.cos(self.hue * math.pi * 2) * self.radius * self.saturation * -1

		self.cursor_pos[0] = self.radius + x_coord
		self.cursor_pos[1] = self.radius + y_coord


class ColorValue(QtWidgets.QWidget):
	value_changed_signal = QtCore.Signal()

	def __init__(self, height, width, color, parent=None):
		super(ColorValue, self).__init__(parent)

		self.parent = parent

		self.height = height
		self.width = width
		self.value = color.valueF()
		self.pressed = False
		self.cursor_pos = [self.width / 2, 0]
		self.positionCursor()
		self.cursor_radius = 6

		self.setMinimumWidth(self.width)
		self.setMinimumHeight(self.height)

		self.qp = QtGui.QPainter()


	def paintEvent(self, e):
		self.qp.begin(self)
		self.qp.setRenderHint(QtGui.QPainter.Antialiasing, True)

		self.val_grad = QtGui.QLinearGradient(0.0, 0.0, 0.0, self.height)
		self.val_grad.setColorAt(1.0, QtGui.QColor(0, 0, 0))
		self.val_grad.setColorAt(0.0, QtGui.QColor(255, 255, 255))

		self.qp.setPen(QtCore.Qt.transparent)
		self.qp.setBrush(self.val_grad)
		slider_rect = QtCore.QRectF(0, 0, self.width, self.height)
		self.qp.drawRoundedRect(slider_rect, 5, 5)

		self.qp.setPen(QtGui.QColor(0, 0, 0))
		self.qp.setBrush(QtGui.QColor(255, 255, 255))
		self.qp.drawEllipse(self.cursor_pos[0] - self.cursor_radius/2, self.cursor_pos[1] - self.cursor_radius/2, self.cursor_radius, self.cursor_radius)

		self.qp.end()


	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.setFocus()

			self.updateCursorPos(e.x(), e.y())

			self.pressed = True

			self.repaint()


	def mouseMoveEvent(self, e):
		if self.pressed:
			self.updateCursorPos(e.x(), e.y())

			self.repaint()


	def mouseReleaseEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.pressed = False

			self.repaint()


	def updateCursorPos(self, new_x, new_y):
		self.cursor_pos = [self.width / 2, new_y]

		self.cursor_pos[1] = max(0, self.cursor_pos[1])
		self.cursor_pos[1] = min(self.height, self.cursor_pos[1])

		self.value = 1 - self.cursor_pos[1] / self.height

		self.value_changed_signal.emit()


	def setValue(self, value):
		self.value = value


	def getValue(self):
		return self.value


	def positionCursor(self):
		self.cursor_pos[1] = self.height * (1 - self.value)


class ColorDisplay(QtWidgets.QWidget):
	def __init__(self, color, parent=None):
		super(ColorDisplay, self).__init__(parent)

		self.color = color

		# self.height = 20
		# self.width = 100

		# self.setMinimumWidth(self.width)
		self.setMinimumHeight(20)

		self.qp = QtGui.QPainter()


	def paintEvent(self, e):
		self.qp.begin(self)
		self.qp.setRenderHint(QtGui.QPainter.Antialiasing, True)

		self.qp.setPen(QtCore.Qt.transparent)
		self.qp.setBrush(self.color)
		display_rect = QtCore.QRectF(0, 0, self.width(), self.height())
		self.qp.drawRoundedRect(display_rect, 5, 5)

		self.qp.end()


	def setColor(self, color):
		self.color = color
		self.repaint()


def getMayaWindow():
	ptr = mui.MQtUtil.mainWindow()
	return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)


def main():
	global ui
	ui = Martopicker(getMayaWindow())
	ui.show()


if __name__ == "__main__":
	main()
