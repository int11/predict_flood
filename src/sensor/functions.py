import os
from src.sensor import Sensor


def getAllSensors(dir, only_meta=True):
    leaf_dirs = [dirpath for dirpath, dirnames, _ in os.walk(dir) if not dirnames]
    sensors = [Sensor.load(sensor, only_meta=only_meta) for sensor in leaf_dirs]
    return sensors


def searchSensors(sensors, location:str=None, category:str=None, id:str=None):
    """
    주어진 조건에 맞는 센서를 검색합니다.
    """
    
    matched_sensors = []

    for sensor in sensors:
        if location and location not in sensor.location:
            continue
        if category and category != sensor.category:
            continue
        if id and str(id) != str(sensor.id):
            continue
        matched_sensors.append(sensor)

    if len(matched_sensors) == 0:
        return None
    if len(matched_sensors) == 1:
        matched_sensors = matched_sensors[0]
    return matched_sensors


def findNearestSensor(sensor, sensors):
    # 주어진 센서의 sensor.meta['WGS84']['latitude']와, sensor.meta['WGS84']['longitude']을 이용해 가장 가까운 센서를 찾습니다.
    min_distance = float('inf')
    nearest_sensor = None
    for s in sensors:
        distance = (sensor.meta['WGS84']['latitude'] - s.meta['WGS84']['latitude']) ** 2 + (sensor.meta['WGS84']['longitude'] - s.meta['WGS84']['longitude']) ** 2
        if distance < min_distance:
            min_distance = distance
            nearest_sensor = s
    return nearest_sensor, min_distance