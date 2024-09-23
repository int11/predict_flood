import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from utils import path2df
import pandas as pd
import glob
from src import Sensor
import pickle

def 강수량():
    # "원데이터/강수량/22" 디렉토리에 있는 모든 .csv 파일의 경로를 불러옵니다.
    csv_files = glob.glob("datasets/original/서울데이터/원데이터/강수량/*.csv")

    # 불러온 파일 경로를 출력합니다.
    df = path2df(csv_files, encoding='cp949')
    df = pd.concat(df)

    print(df['지점'].unique())
    meta = {
        'location':'서울특별시 서초구 서초동 1416번지 서초 IC',
        'category':'강수량계',
        'id':str(df['지점'].unique()[0]),
        'WGS84': {'latitude': 37.48462, 'longitude': 127.02601}
    }

    value = df.drop('지점', axis=1)
    value.rename(columns={'일시': 'time'}, inplace=True)
    
    obj = Sensor(meta, value)
    obj.save(path=f'datasets/sensor/서울/강수량계/{obj.meta["id"]}')

def 하수관로():
    csv_files = glob.glob("dataset/original/서울데이터/원데이터/sewer_raw/**/*.csv")
    
    data_by_id: dict[str, Sensor]  = {}

    for i in csv_files:
        print(i)
        df = pd.read_csv(i, encoding='cp949')
        grouped = df.groupby('고유번호')
        for id, group in grouped:

            meta = {
                'location':'서울',
                'category':'하수관로수위계',
                'id':str(id),
            }

            value = group[['측정일자', '측정수위']].copy()
            value.rename(columns={'측정일자': 'time'}, inplace=True)
            obj = Sensor(meta, value)
            if id in data_by_id:
                # 고유번호가 이미 존재하면 데이터 합치기
                data_by_id[id].concat(obj)
            else:
                # 새로운 고유번호면 딕셔너리에 추가
                data_by_id[id] = obj
    
    for i in data_by_id.values():
        i.save()

def 노면수위():
    sensors_location = pd.read_csv('datasets/original/서울데이터/원데이터/tmp/도로수위센서 위치정보/sensor.csv', usecols=[0, 1,3,4], names=['id', 'location', 'latitude', 'longitude'])

    csv_files = glob.glob("datasets/original/서울데이터/원데이터/노면수위/**/*.xlsm")

    df = pd.read_excel(csv_files[-1], sheet_name='log', usecols="A:C", engine='openpyxl')

    grouped = df.groupby('id')
    for id, group in grouped:
        sensor_location = sensors_location[sensors_location['id'] == str(id)]
        meta = {
            'location': sensor_location['location'].iloc[0],
            'category':'노면수위계',
            'id':str(id),
            'WGS84': {'latitude': sensor_location['latitude'].iloc[0], 'longitude': sensor_location['longitude'].iloc[0]}
        }

        value = group[['timestamp', 'raw']].copy()
        value.rename(columns={'timestamp': 'time', 'raw':'value'}, inplace=True)
        obj = Sensor(meta, value)
        obj.save(path=f'datasets/sensor/서울/노면수위계/{id}')


if __name__ == '__main__':
    # 강수량()
    # 하수관로()
    노면수위()