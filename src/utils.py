import pandas as pd
import os 
from src.sensor import Sensor
import requests
from io import StringIO
import asyncio
import aiohttp
from datetime import datetime, timedelta


def path2df(file_paths, encoding='utf-8'):
    # 파일을 DataFrame으로 불러와 저장할 딕셔너리
    dataframes = {}

    # 각 파일을 불러와 딕셔너리에 저장
    for path in file_paths:
        # 파일 이름을 키로 사용
        key = path.split('/')[-1].split('.')[0]
        dataframes[key] = pd.read_csv(path, encoding=encoding)

    return dataframes


def recalculate_accumulation(df, window_size):
    """
    주어진 DataFrame의 누적값을 다시 계산합니다.
    """
    if df.isna().any().any():
        raise ValueError("DataFrame contains NaN values")
        
    if not (df[:window_size-1] == 0).all().all():
        raise ValueError("The first window_size values must be 0")

    result = df.copy()
    for i in range(window_size, len(df)):
        result.iloc[i] = df.iloc[i] - df.iloc[i-1] + result.iloc[i-window_size]
    return result


def get_lat_lon(address, api_key=None):
    '''
    구글 API를 이용하여 주소로부터 위도와 경도를 가져옵니다.
    Args:
    ----
    address
        주소
    api_key
        Google Map API 키
    '''
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': address, 'key': api_key}
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        results = response.json().get('results')
    if results:
        location = results[0]['geometry']['location']
        return location['lat'], location['lng']
    return None, None