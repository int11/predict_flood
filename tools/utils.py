import pandas as pd
import os 
from src import Sensor

def path2df(file_paths, encoding='utf-8'):
    # 파일을 DataFrame으로 불러와 저장할 딕셔너리
    dataframes = {}

    # 각 파일을 불러와 딕셔너리에 저장
    for path in file_paths:
        # 파일 이름을 키로 사용
        key = path.split('/')[-1].split('.')[0]
        dataframes[key] = pd.read_csv(path, encoding=encoding)

    return dataframes


def getAllSensors(dir, only_meta=True):
    leaf_dirs = [dirpath for dirpath, dirnames, _ in os.walk(dir) if not dirnames]
    sensors = [Sensor.load(sensor, only_meta=only_meta) for sensor in leaf_dirs]
    return sensors


def searchSensors(sensors, location=None, category=None, id=None):
    """
    주어진 조건에 맞는 센서를 검색합니다.
    """
    
    matched_sensors = []

    for sensor in sensors:
        if location and location not in sensor.location:
            continue
        if category and category != sensor.category:
            continue
        if id and id != sensor.id:
            continue
        matched_sensors.append(sensor)

    if len(matched_sensors) == 1:
        matched_sensors = matched_sensors[0]
    return matched_sensors
