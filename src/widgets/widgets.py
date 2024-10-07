import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtGui import QColor
from pyqtgraph import DateAxisItem
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtCore import QDateTime
import numpy as np


class CustomDateAxisItem(DateAxisItem):
    def tickStrings(self, values, scale, spacing):
        # QDateTime 객체를 사용하여 각 값(UNIX 타임스탬프)을 QDateTime으로 변환
        return [QDateTime.fromSecsSinceEpoch(int(value)).toString('yyyy/MM/dd HH:mm:ss') for value in values]


# PlotCanvas 클래스 내에서 CustomDateAxisItem 사용
class PlotCanvas(QWidget):
    PlotCanvas_list = []
    currentLinkedCanvas = None  # 현재 범위가 설정된 PlotCanvas를 추적
    emitDeletionRequest = pyqtSignal(QObject)  # QObject 타입의 신호를 발생시킬 수 있는 pyqtSignal 정의

    def __init__(self, dfs: list[pd.DataFrame], parent=None, width=4000, height=500, s=1, graph_type='Line'):
        PlotCanvas.PlotCanvas_list.append(self)
        super(PlotCanvas, self).__init__(parent)
        self.setFixedSize(width, height)  # 위젯의 고정 크기 설정

        if not isinstance(dfs, list):
            dfs = [dfs]

        vertical_layout = QVBoxLayout(self)

        # 그래프 삭제 버튼 생성
        self.deleteButton = QPushButton('X', self)
        self.deleteButton.setFixedSize(20, 20)
        self.deleteButton.clicked.connect(lambda: self.emitDeletionRequest.emit(self))
        vertical_layout.addWidget(self.deleteButton)

        # CustomDateAxisItem을 사용하여 날짜 축을 생성
        date_axis = CustomDateAxisItem(orientation='bottom')
        self.graphWidget = pg.PlotWidget(axisItems={'bottom': date_axis})
        vertical_layout.addWidget(self.graphWidget)
        self.graphWidget.setBackground('w')  # 배경색을 흰색으로 설정

        # x축과 y축의 글자 색상을 검은색으로 설정
        xAxis = self.graphWidget.getAxis('bottom')
        xAxis.setPen(pg.mkPen(color=(0, 0, 0)))
        yAxis = self.graphWidget.getAxis('left')
        yAxis.setPen(pg.mkPen(color=(0, 0, 0)))

        hue_step = 360 / max(sum(len(df.columns) - 1 for df in dfs), 1)  # 색상 변경 단계 계산
        current_hue = 0  # 시작 색상

        # 범례 추가
        legend = pg.LegendItem(offset=(70, 30))  # 범례 크기 및 위치 조정
        legend.setParentItem(self.graphWidget.graphicsItem())  # 범례를 그래프 위젯에 추가

        for df in dfs:
            df.loc[:, 'time'] = pd.to_datetime(df['time'])
            x = df['time'].apply(lambda dt: int(QDateTime(dt).toSecsSinceEpoch())).values
            y_columns = df.drop('time', axis=1)

            for col in y_columns:
                y = y_columns[col].values
                color = QColor.fromHsv(int(current_hue), 255, 255)  # HSV에서 RGB 색상으로 변환, current_hue를 정수로 변환
                color.setAlphaF(0.5)
                if graph_type == 'Line':
                    plot = self.graphWidget.plot(x, y, pen=pg.mkPen(color=color, width=1),  name=col)
                elif graph_type == 'Scatter':
                    plot = self.graphWidget.plot(x, y, symbol='o', pen=None, symbolBrush=color, symbolSize=s, name=col)
                current_hue = (current_hue + hue_step) % 360  # 다음 색상으로 업데이트
                legend.addItem(plot, f"{df.name} {col}")  # 첫 번째 데이터 세트에 대한 범례


        # 마우스 이벤트 처리를 위한 SignalProxy 설정
        self.proxy = pg.SignalProxy(self.graphWidget.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        self.textItem = pg.TextItem(anchor=(0,1))
        self.graphWidget.addItem(self.textItem)


        # x time 축 제대로 설정
        all_x_values = np.concatenate([df['time'].apply(lambda dt: int(QDateTime(dt).toSecsSinceEpoch())).values for df in dfs])
        padding = 0.02 * (all_x_values.max() - all_x_values.min())
        self.x_range = [all_x_values.min() - padding, all_x_values.max() + padding]
        self.y_range = self.graphWidget.getViewBox().state['viewRange'][1] 
        self.graphWidget.setXRange(self.x_range[0], self.x_range[1], padding=0)


    def setLimits(self, state):
        if state:
            self.graphWidget.setLimits(xMin=self.x_range[0], xMax=self.x_range[1], yMin=self.y_range[0], yMax=self.y_range[1])
        else:
            self.graphWidget.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)

    def setShareRange(self, state):
        if state:
            self.graphWidget.sigRangeChanged.connect(self.onRangeChanged)
        else:
            try:
                self.graphWidget.sigRangeChanged.disconnect(self.onRangeChanged)
            except TypeError:
                pass
            self.graphWidget.setXLink(None)
            self.graphWidget.setYLink(None)

    def mouseMoved(self, evt):
        pos = evt[0]  # 마우스 위치 가져오기
        if self.graphWidget.sceneBoundingRect().contains(pos):
            mousePoint = self.graphWidget.plotItem.vb.mapSceneToView(pos)

            # 에폭 시간을 QDateTime 객체로 변환
            dateTime = QDateTime.fromSecsSinceEpoch(int(mousePoint.x()))
            # QDateTime 객체를 원하는 형식의 문자열로 포맷
            formattedDateTime = dateTime.toString('yyyy/MM/dd HH:mm:ss')

            # 마우스 위치에 따른 x, y 값을 텍스트 아이템에 표시
            self.textItem.setHtml(f"<div style='background-color: white;'>x={formattedDateTime}, y={mousePoint.y():.2f}</div>")
            self.textItem.setPos(mousePoint.x(), mousePoint.y())


    def onRangeChanged(self):
        # 현재 PlotCanvas를 모든 다른 PlotCanvas와 연동
        for canvas in PlotCanvas.PlotCanvas_list:
            if canvas != self:
                canvas.graphWidget.setXLink(self.graphWidget)
                canvas.graphWidget.setYLink(self.graphWidget)

        # 현재 연동된 PlotCanvas를 업데이트
        PlotCanvas.currentLinkedCanvas = self

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