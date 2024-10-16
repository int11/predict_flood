from src.widgets import *
from PyQt5.QtWidgets import *

class TopWidget(QWidget):
    def __init__(self, parent=None):
        super(TopWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)

        self.width_input = Qinput("Width:", default=1500, parent=self)
        self.layout.addWidget(self.width_input)
        self.height_input = Qinput("Height:", default=500, parent=self)
        self.layout.addWidget(self.height_input)
        self.s_input = Qinput("S:", default=3, parent=self)
        self.layout.addWidget(self.s_input)
        self.RadiographType = RadioButtonGroup()
        self.layout.addWidget(self.RadiographType)
        

        self.onLimits = QCheckBox('ON Limits')
        self.onLimits.setChecked(True)
        self.layout.addWidget(self.onLimits)
        self.onShareRange = QCheckBox('ON Share range')
        self.onShareRange.setChecked(True)
        self.layout.addWidget(self.onShareRange)
        
        
        self.layout.addStretch(1)
        self.layout.setContentsMargins(0, 0, 0, 0)