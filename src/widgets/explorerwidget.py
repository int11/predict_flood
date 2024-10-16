from src.widgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal, QDir, QDirIterator, QFileInfo
from src import Sensor


class ExplorerWidget(QWidget):
    addButtonClicked = pyqtSignal(QTreeWidgetItem)  # addButton 클릭 시그널
    addAllClicked = pyqtSignal()  # addall 클릭 시그널
    plotOneGraphClicked = pyqtSignal()  # plot_one_graph 클릭 시그널
    plotEachClicked = pyqtSignal()  # plot_each 클릭 시그널
    
    def __init__(self, dir, parent=None):
        super(ExplorerWidget, self).__init__(parent)
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
