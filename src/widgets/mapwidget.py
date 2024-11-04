from src.widgets import *
from PyQt5.QtWidgets import *
import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView
import io


class MapWidget(QWidget):
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
            elif sensor.category == '노면수위계2024':
                icon = folium.Icon(color='purple', icon='tint')
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