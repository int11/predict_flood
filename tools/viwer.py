import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import io

from PyQt5.QtWidgets import *
from src.widgets import *
from src import Sensor
from PyQt5.QtCore import QDir, QDirIterator, QFileInfo
from PyQt5.QtWebEngineWidgets import QWebEngineView
from tools.utils import *
import folium

class topWidget(QWidget):
    def __init__(self, parent=None):
        super(topWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)

        self.width_input = Qinput("Width:", default=4000, parent=self)
        self.height_input = Qinput("Height:", default=500, parent=self)
        self.s_input = Qinput("S:", default=3, parent=self)
        self.RadiographType = RadioButtonGroup()
        self.layout.addWidget(self.width_input)
        self.layout.addWidget(self.height_input)
        self.layout.addWidget(self.s_input)
        self.layout.addWidget(self.RadiographType)
        self.layout.addStretch(1)

        self.layout.setContentsMargins(0, 0, 0, 0)

class explorerWidget(QWidget):
    addButtonClicked = pyqtSignal(QTreeWidgetItem)  # addButton 클릭 시그널
    addAllClicked = pyqtSignal()  # addall 클릭 시그널
    plotOneGraphClicked = pyqtSignal()  # plot_one_graph 클릭 시그널
    plotEachClicked = pyqtSignal()  # plot_each 클릭 시그널
    
    def __init__(self, dir, parent=None):
        super(explorerWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.treeWidget = QTreeWidget(self)
        self.layout.addWidget(self.treeWidget)
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setHeaderLabels(['File System', 'Actions'])
        self.treeWidget.setColumnWidth(0, 230)
        self.treeWidget.setColumnWidth(1, 1000)

        # 루트 항목 추가
        rootItem = QTreeWidgetItem(self.treeWidget, [dir])
        self.treeWidget.addTopLevelItem(rootItem)
        # 루트 디렉토리에 대한 항목과 버튼 추가
        self.addItemsAndButtons(rootItem, dir)
        self.check_parentItem = []
        self.treeWidget.itemChanged.connect(self.handleItemChanged)

        # addall, plot_one_graph, plot_each 버튼 생성
        hbox = QHBoxLayout()
        self.layout.addLayout(hbox)

        addall = QPushButton('+', self)
        addall.setStyleSheet("background-color: red;")
        addall.setFixedSize(20, 20)
        addall.clicked.connect(self.emitAddAllClicked)
        hbox.addWidget(addall)

        plot_one_graph = QPushButton('checked plot draw one graph', self)
        plot_one_graph.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plot_one_graph.clicked.connect(self.emitPlotOneGraphClicked)

        plot_each = QPushButton('checked plot draw each', self)
        plot_each.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plot_each.clicked.connect(self.emitPlotEachClicked)
        
        hbox.addWidget(plot_one_graph)
        hbox.addWidget(plot_each)

    def handleItemChanged(self, item, column):
        # 체크 상태 변경을 처리하는 메서드
        if column == 0:  # 첫 번째 열의 체크 상태가 변경된 경우
            if item.checkState(0) == Qt.Checked:
                # 항목이 체크된 경우, 리스트에 추가합니다.
                if item not in self.check_parentItem:
                    self.check_parentItem.append(item)
            else:
                # 항목의 체크가 해제된 경우, 리스트에서 삭제합니다.
                if item in self.check_parentItem:
                    self.check_parentItem.remove(item)

    def addItemsAndButtons(self, parentItem, path):
        dirIterator = QDirIterator(path, QDir.Dirs | QDir.NoDotAndDotDot, QDirIterator.NoIteratorFlags)
        hasSubdirectory = False
        while dirIterator.hasNext():
            hasSubdirectory = True
            dirPath = dirIterator.next()
            dirInfo = QFileInfo(dirPath)
            if dirInfo.isDir():
                childItem = QTreeWidgetItem(parentItem, [dirInfo.fileName()])
                self.addItemsAndButtons(childItem, dirPath)

        if not hasSubdirectory:
            # 마지막 디렉토리인 경우
            sensor = Sensor.load(path, only_meta=True)
            checkboxgroup = checkboxGroup(sensor.meta['columns'], except_names=['time'])

            parentItem.setData(0, Qt.UserRole, sensor)
            parentItem.setData(1, Qt.UserRole, checkboxgroup)
            
            parentItem.setCheckState(0, Qt.Unchecked)

            addButton = QPushButton('+')
            addButton.setFixedSize(20, 20)
            addButton.clicked.connect(lambda: self.emitAddButtonClicked(parentItem))


            containerWidget = QWidget()
            layout = QHBoxLayout(containerWidget)
            layout.addWidget(addButton)
            layout.addWidget(checkboxgroup)
            layout.setContentsMargins(0, 0, 0, 0)


            self.treeWidget.setItemWidget(parentItem, 1, containerWidget)

    def emitAddAllClicked(self):
        self.addAllClicked.emit()

    def emitPlotOneGraphClicked(self):
        self.plotOneGraphClicked.emit()

    def emitPlotEachClicked(self):
        self.plotEachClicked.emit()

    def emitAddButtonClicked(self, parentItem):
        self.addButtonClicked.emit(parentItem)


class Map(QWidget):
    def __init__(self, sensors):
        super().__init__()
        mainLayout = QVBoxLayout(self)

        self.browser = QWebEngineView()
        mainLayout.addWidget(self.browser)

        # Folium으로 지도 생성
        m = folium.Map(location=[37.566535, 126.977969], zoom_start=12)
        
        
        for sensor in sensors:
            if 'WGS84' not in sensor.meta:
                continue

            latitude, longitude = sensor.meta['WGS84']['latitude'], sensor.meta['WGS84']['longitude']
            popup_html = f"<div style='min-width:100px;'>{sensor.category} {sensor.id}</div>"
            # 센서 카테고리에 따른 마커 색상 지정
            if sensor.category == '노면수위계':
                icon = folium.Icon(color='blue', icon='tint')
            elif sensor.category == '강수량계':
                icon = folium.Icon(color='red', icon='cloud')
            elif sensor.category == '하수관로수위계':
                icon = folium.Icon(color='green', icon='tint')
            else:
                icon = folium.Icon()

            folium.Marker(
                [latitude, longitude], 
                popup=folium.Popup(popup_html),
                icon=icon
            ).add_to(m)

        # 지도를 HTML 문자열로 변환
        data = io.BytesIO()
        m.save(data, close_file=False)

        self.browser.setHtml(data.getvalue().decode())

class MainWindow(QMainWindow):
    def __init__(self, dir):
        super().__init__()
        self.setWindowTitle('DataFrame Viewer')
        self.setGeometry(100, 100, 2000, 1200)

        # 탭 위젯 생성
        tabWidget = QTabWidget()
        self.setCentralWidget(tabWidget)

        # Main 탭
        mainWidget = QWidget()
        tabWidget.addTab(mainWidget, "Main")
        layout = QVBoxLayout(mainWidget)
        
        # top 부분
        self.top = topWidget()
        self.top.setFixedHeight(60)
        layout.addWidget(self.top)
        
        # down 부분
        down_layout = QHBoxLayout()
        layout.addLayout(down_layout)

        # QSplitter 생성
        splitter = QSplitter(Qt.Horizontal)
        down_layout.addWidget(splitter)

        # explorer
        self.explorerwidget = explorerWidget(parent=self, dir=dir)
        self.explorerwidget.addButtonClicked.connect(self.addButtonClicked)
        self.explorerwidget.plotOneGraphClicked.connect(self.plot_one_graph_clicked)
        self.explorerwidget.plotEachClicked.connect(self.plot_each_clicked)
        splitter.addWidget(self.explorerwidget)

        # graph 스크롤 영역
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(0, 0, 0, 0)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidget(self.scrollWidget)
        splitter.addWidget(self.scrollArea)
        splitter.setSizes([1,5000])


        # Map 탭
        mapWidget = Map(getAllSensors(dir))
        tabWidget.addTab(mapWidget, "Map")

    def make_canvas(self, items:list[QTreeWidgetItem]):
        if type(items) is not list:
            items = [items]

        dfs = []
        for item in items:
            sensor = item.data(0, Qt.UserRole)
            if sensor.value is None:
                #reload sensor with value
                sensor = Sensor.load(sensor.path)
                item.setData(0, Qt.UserRole, sensor)
            
            checked = item.data(1, Qt.UserRole).get()
            checked.append('time')
            df = sensor.value[checked]
            df.name = sensor.name
            dfs.append(df)

        canvas = PlotCanvas(
            dfs,
            width=self.top.width_input.get(),
            height=self.top.height_input.get(), 
            s=self.top.s_input.get(),
            graph_type=self.top.RadiographType.get())
        return canvas

    def addButtonClicked(self, item):
        canvas = self.make_canvas(item)
        canvas.emitDeletionRequest.connect(self.removeCanvas)  # 삭제 요청 신호를 처리하는 메서드에 연결
        self.scrollLayout.addWidget(canvas)
        self.updateScrollWidgetSize()

    def removeCanvas(self, canvas):
        self.scrollLayout.removeWidget(canvas)

        canvas.deleteLater()
        PlotCanvas.PlotCanvas_list.remove(canvas)
        self.updateScrollWidgetSize()
        
    def plot_one_graph_clicked(self):
        canvas = self.make_canvas(self.explorerwidget.check_parentItem)
        self.scrollLayout.addWidget(canvas)
        self.updateScrollWidgetSize()

    def plot_each_clicked(self):
        for i in self.explorerwidget.check_parentItem:
            self.addButtonClicked(i)

    def updateScrollWidgetSize(self):
        total_height = 0
        max_width = 0
        for i in range(self.scrollLayout.count()):
            widget = self.scrollLayout.itemAt(i).widget()
            if widget is not None:
                total_height += widget.height()
                max_width = max(max_width, widget.width())
        
        self.scrollWidget.setFixedHeight(total_height)
        self.scrollWidget.setFixedWidth(max_width)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))  # Windows 10 스타일 적용
    dir = 'datasets/sensor'
    
    main = MainWindow(dir)
    main.show()
    sys.exit(app.exec_())