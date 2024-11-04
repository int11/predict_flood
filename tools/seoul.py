import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.utils import path2df
import pandas as pd
import glob
from src import Sensor
from src.utils import *
import pickle


def 강수량():
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

def 강수량append():
    import glob
    csv_files = glob.glob("datasets/original/서울데이터/원데이터/강수량/**/*.csv")
    sensors = getAllSensors('datasets/sensor/서울/강수량계', only_meta=False)

    for csv_file in csv_files:
        print(csv_file)
        data = pd.read_csv(csv_file, encoding='cp949')
        sensor_id = str(int(data['지점'].unique()[0]))
        data = data.drop(columns=['지점'])

        if '누적강수량(mm)' in data.columns:
            data = data.rename(columns={'일시': 'time', '누적강수량(mm)': '1분 누적강수량(mm)'})
        elif '1분 강수량(mm)' in data.columns:
            data = data.rename(columns={'일시': 'time', '1분 강수량(mm)': '1분 누적강수량(mm)'})

        data['time'] = pd.to_datetime(data['time'])
        
        sensor = searchSensors(sensors, id=sensor_id)
        concat_df = pd.concat([sensor.value, data])
        sensor.value = concat_df.groupby('time').last().reset_index()
        
        sensor.save(sensor.path)


def 하수관로():
    csv_files = glob.glob("datasets/original/서울데이터/원데이터/하수관로/**/*.csv")

    data_by_id: dict[str, Sensor]  = {}

    for i in csv_files:
        print(i)
        try:
            df = pd.read_csv(i, encoding='cp949')
        except:
            df = pd.read_csv(i, encoding='utf-8')

        try:
            grouped = df.groupby('고유번호')
        except:
            grouped = df.groupby('?고유번호')

        for id, group in grouped:

            meta = {
                'location':'서울',
                'category':'하수관로수위계',
                'id':str(id),
            }

            value = group[['측정일자', '측정수위']].copy()
            # rename 측정일자 -> time, 측정수위 -> value
            value.rename(columns={'측정일자': 'time', '측정수위':'value'}, inplace=True)
            obj = Sensor(meta, value)
            if id in data_by_id:
                # 고유번호가 이미 존재하면 데이터 합치기
                data_by_id[id].concat(obj)
            else:
                # 새로운 고유번호면 딕셔너리에 추가
                data_by_id[id] = obj

            data_by_id[id].compress()

    for i in data_by_id.values():
        i.save(f'datasets/sensor/서울/하수관로수위계2/{i.id}')


def 하수관로위치업데이트(api_key=None):
    sewer_dir = 'datasets/sensor/서울/하수관로수위계'

    sewer_meta = pd.read_excel('datasets/original/서울데이터/원데이터/하수관로/하수관로_메타정보.xlsx')
    sensors = getAllSensors(sewer_dir, only_meta=False)

    for index, row in sewer_meta.iterrows():
        matched_sensor = searchSensors(sensors, id=str(row['수위계번호']))

        if matched_sensor:
            address = row['수위계 설치지점']
            matched_sensor.meta['location'] = address
            matched_sensor.meta['box height(m)'] = row['박스높이(m)']
            # 구글 API를 이용하여 위도와 경도를 가져옵니다.

            
            latitude, longitude = get_lat_lon(address, api_key)
            if latitude and longitude:
                matched_sensor.meta['WGS84'] = {'latitude': float(latitude), 'longitude': float(longitude)}
            else:
                print(f"Failed to get coordinates for address: {address}")
            
            matched_sensor.save(f'{sewer_dir}/{matched_sensor.id}')
        else:
            print(f"Sensor not found: {row['수위계번호']}")
    
    
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


def 노면수위계2024():
    df1 = pd.read_csv('roadData/TB_ROADWATERLEVELDATA.txt')
    meta = pd.read_csv('roadData/TB_ROAD_FLOW_INFO.txt')
    df2 = pd.read_csv('roadData/2305to10roadwaterlevelData_1min.csv')


    df1 = df1.drop(columns=['IDX'])
    df1.rename(columns={'DATA_TIME': 'time', 'DEVICE_ID': 'id', 'LEVEL_DATA':'value'}, inplace=True)

    df2 = df2.drop(columns=['work_field_info_id', 'Unnamed: 0'])
    df2.rename(columns={'device_id': 'id'}, inplace=True)

    df = pd.concat([df1, df2])

    grouped = df.groupby('id')
    for i in grouped:
        id, group = i
        group = group.drop(columns=['id'])
        meta_row = meta[meta['ROADGAUGE_CODE'] == id]

        meta_row = meta_row.iloc[0]
        meta_temp = {
            'location': meta_row['ADDRESS'],
            'category': '노면수위계2024',
            'id': str(id),
            'WGS84': {'latitude': meta_row['GPS_LAT'], 'longitude': meta_row['GPS_LON']}
        }
        sensor = Sensor(meta_temp, group)
        sensor.save(f'datasets/sensor/서울/노면수위계2024/{sensor.id}')

        
if __name__ == '__main__':
    # 강수량()
    # 하수관로()
    # 노면수위()