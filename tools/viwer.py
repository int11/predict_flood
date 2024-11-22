import os
import sys
from PyQt5.QtWidgets import QApplication, QStyleFactory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from src.widgets import *
from src.sensor import Sensor, getAllSensors


class MainWidget(QMainWindow):
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
        self.top = TopWidget()
        self.top.onLimits.stateChanged.connect(self.update_plot_canvas)
        self.top.onShareRange.stateChanged.connect(self.update_plot_canvas)
        self.top.setFixedHeight(60)
        layout.addWidget(self.top)
        
        # down 부분
        down_layout = QHBoxLayout()
        layout.addLayout(down_layout)

        # QSplitter 생성
        splitter = QSplitter(Qt.Horizontal)
        down_layout.addWidget(splitter)

        # explorer
        self.explorerwidget = ExplorerWidget(parent=self, dir=dir)
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
        mapWidget = MapWidget(getAllSensors(dir))
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
            df.name = sensor.path
            dfs.append(df)

        canvas = PlotCanvasWidget(
            dfs,
            width=self.top.width_input.get(),
            height=self.top.height_input.get(), 
            s=self.top.s_input.get(),
            graph_type=self.top.RadiographType.get())
        canvas.emitDeletionRequest.connect(self.removeCanvas)  # 삭제 요청 신호를 처리하는 메서드에 연결
        self.scrollLayout.addWidget(canvas)
        self.update_plot_canvas()
        self.updateScrollWidgetSize()
        return canvas

    def addButtonClicked(self, item):
        self.make_canvas(item)
        
    def plot_one_graph_clicked(self):
        self.make_canvas(self.explorerwidget.check_parentItem)

    def plot_each_clicked(self):
        for i in self.explorerwidget.check_parentItem:
            self.addButtonClicked(i)

    def removeCanvas(self, canvas):
        self.scrollLayout.removeWidget(canvas)

        canvas.deleteLater()
        PlotCanvasWidget.PlotCanvas_list.remove(canvas)
        self.updateScrollWidgetSize()
        
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

    def update_plot_canvas(self):
        PlotCanvasWidget.setLimits(self.top.onLimits.isChecked())
        PlotCanvasWidget.setShareRange(self.top.onShareRange.isChecked())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))  # Windows 10 스타일 적용
    dir = 'datasets/sensor'
    
    main = MainWidget(dir)
    main.show()
    sys.exit(app.exec_())