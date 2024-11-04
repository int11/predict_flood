from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator


class RadioButtonGroup(QWidget):
    def __init__(self, group_name="Graph Type", type=['Line', 'Scatter'], default='Line'):
        super().__init__()

        self.graphType = None  # 선택된 그래프 유형을 저장할 변수

        graphTypeGroup = QGroupBox("Graph Type")
        layout = QHBoxLayout(graphTypeGroup)  # QHBoxLayout 인스턴스 생성

        # 라디오 버튼 생성
        for i in type:
            button = QRadioButton(i)
            if i == default:
                button.setChecked(True)
                self.graphType = i

            # 람다 함수에 현재 버튼의 참조를 명시적으로 전달
            button.toggled.connect(lambda checked, b=button: self.updateGraphType(b) if checked else None)
            layout.addWidget(button)


        mainLayout = QVBoxLayout(self)  # 메인 레이아웃 생성
        mainLayout.setContentsMargins(0, 0, 0, 0)  # 메인 레이아웃의 여백을 제거
        mainLayout.setSpacing(0)  # 메인 레이아웃의 간격을 제거

        mainLayout.addWidget(graphTypeGroup)  # 메인 레이아웃에 graphTypeGroup 추가
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def updateGraphType(self, radioButton):
        self.graphType = radioButton.text()

    def get(self):
        return self.graphType

class checkboxGroup(QWidget):
    def __init__(self, checkbox_names:list[str], except_names=[]):
        super().__init__()
        self.checkboxes = []

        mainLayout = QHBoxLayout(self)  # 메인 레이아웃 생성
        mainLayout.setContentsMargins(0, 0, 0, 0)  # 메인 레이아웃의 여백을 제거
        mainLayout.setSpacing(0)  # 메인 레이아웃의 간격을 제거

        setchecked = False if len(checkbox_names) > 3 else True
        for i in checkbox_names:
            if i in except_names:
                continue
            checkBox = QCheckBox(i, self)
            checkBox.setChecked(setchecked)
            mainLayout.addWidget(checkBox)
            self.checkboxes.append(checkBox)

        mainLayout.addStretch()

    def get(self):
        checked_names = [checkBox.text() for checkBox in self.checkboxes if checkBox.isChecked()]
        return checked_names

class Qinput(QWidget):
    def __init__(self, name, parent=None, FixedWidth=50, default: int=None):
        super().__init__(parent)
        hbox = QHBoxLayout(self)

        width_label = QLabel(name)
        self.width_input = QLineEdit()
        int_validator = QIntValidator() 
        self.width_input.setValidator(int_validator)

        if default:
            self.width_input.setText(str(default))


        self.width_input.setFixedWidth(FixedWidth)
        hbox.addWidget(width_label)
        hbox.addWidget(self.width_input)
        hbox.addStretch()

    def get(self):
        return int(self.width_input.text())