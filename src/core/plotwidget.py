import pyqtgraph as pg
import pyqtgraph as pg
from datetime import datetime
from pyqtgraph import DateAxisItem
from PyQt5.QtCore import QDateTime

class CustomDateAxisItem(DateAxisItem):
    def tickStrings(self, values, scale, spacing):
        # QDateTime 객체를 사용하여 각 값(UNIX 타임스탬프)을 QDateTime으로 변환
        print(values)
        result = [QDateTime.fromSecsSinceEpoch(int(value)).toString('yyyy/MM/dd HH:mm:ss') for value in values]
        result1 = [datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S') for value in values]
        print(result)
        print(result1)
        return result
    

class PlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
    
    def showdf(self, df):
        self.clear()
        for column in df.columns:
            self.plot(df.index, df[column], name=column)

    def show(self):
        super().show()
        pg.exec()

    def plot(self, *args, **kargs):
        # asdf = df.index.to_series().apply(lambda dt: int(QDateTime(dt).toSecsSinceEpoch())).values
        self.plotItem.plot(*args, **kargs)

# plotWidget = src.PlotWidget(axisItems={'bottom': CustomDateAxisItem(orientation='bottom')})
# asdf = df.index.to_series().apply(lambda dt: int(QDateTime(dt).toSecsSinceEpoch())).values
# a = plotWidget.plot(df.index, df['10분 강수량(mm)'], name='10분 강수량(mm)')
# plotWidget.show()