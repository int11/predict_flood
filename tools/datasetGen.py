import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.utils import *
import matplotlib.pyplot as plt
from src.data.dataset import TimeSeriesDataset
import numpy as np
import pickle
import torch
from src.sensor import Sensor, getAllSensors, findNearestSensor

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False 


def road_append_rainfall(road_sensor : Sensor,
                         rainfall_sensor: Sensor,
                         minute_interval=1, 
                         rolling_windows=[10, 30, 60, 120, 180]):
    '''
    노면수위계 데이터에 누적강수량을 추가하는 함수

    road_sensor는 [time, value] 컬럼을 가지고 있어야 함
    rainfall_sensor는 [time, 1분 누적강수량(mm)] 컬럼을 가지고 있어야 함

    노면수위계는 .resample('1s').max().ewm(alpha=0.9, adjust=False).mean() 으로 결측치 보간
    강수량계는 .resample('1min').first().interpolate() 으로 결측치 보간


    Args
    ----
    save_path :
        저장 경로
    minute_interval :
        노면수위계와 강수량계 데이터를 몇 분 간격으로 저장할지
    rolling_windows :
        사용할 누적강수량
    road_sensor :
        노면수위계 데이터가 저장된 디렉토리
    rainfall_sensors :
        강수량계 데이터가 저장된 디렉토리


    Returns
    -------
    road rainfall 합쳐진 Sensor 객체
    '''

    # Ensure road_sensor has 'time' and 'value' columns
    if not {'time', 'value'}.issubset(road_sensor.value.columns):
        raise ValueError("road_sensor must have 'time' and 'value' columns")
    
    # Ensure each rainfall_sensor has 'time' and '1분 누적강수량(mm)' columns
    if not {'time', '1분 누적강수량(mm)'}.issubset(rainfall_sensor.value.columns):
        raise ValueError("Each rainfall_sensor must have 'time' and '1분 누적강수량(mm)' columns")


    road = road_sensor.value.set_index('time')
    df = road.resample('1s').max().ewm(alpha=0.9, adjust=False).mean().resample(f'{minute_interval}min').max()

    
    rainfall = rainfall_sensor.value
    rainfall = rainfall[['time', '1분 누적강수량(mm)']].set_index('time')
    #  1분 강수량 열 자체가 없는 경우 
    rainfall = rainfall.resample('1min').first()

    rainfall = rainfall.interpolate()

    for window in rolling_windows:
        df[f'{window}분 누적강수량'] = rainfall.rolling(window=window).sum()

    # df = df.resample(f'{minute_interval}min').first()

    road_sensor.value = df.reset_index()

    return road_sensor.copy()


def save_dataset(dataset:torch.utils.data.Dataset, path:str):
    '''
    dataset을 pickle 로 저장하는 함수
    '''
    # 디렉토리가 존재하지 않으면 생성
    sensor_dir = os.path.dirname(path)
    os.makedirs(sensor_dir, exist_ok=True)

    all_data = np.array([np.concatenate((dataset[i][0], dataset[i][1]), axis=0) for i in range(len(dataset))])
    np.save(path, all_data)


def main(minute_interval, rolling_windows, input_window_size, output_window_size, axis, threshold):
    '''
    Args
    ----
    minute_interval :
        노면수위계와 강수량계 데이터를 몇 분 간격으로 저장할지
    rolling_windows :
        사용할 누적강수량
    input_window_size :
        입력 데이터의 시간 간격
    output_window_size :
        출력 데이터의 시간 간격
    axis, threshold :
       input_window_size 기준으로 axis 열 평균이 threshold 이상인 데이터만 사용
        ex) minute_interval 1, input_window_size 12, threshold=1, axis=2, 3번째 열은 30분 누적강수량
            30분 누적강수량 12분 평균이 1 이상인 데이터만 사용
        ex) minute_interval 1, input_window_size 120, threshold=1, axis=1, 1번째 열은 노면수위
            노면수위 120분 평균이 1 이상인 데이터만 사용
        ex) minute_interval 10, input_window_size 12, threshold=1, axis=2, 2번째 열은 10분 누적강수량
            10분 누적강수량 120분 평균이 1 이상인 데이터만 사용
    '''
    road_sensors = getAllSensors('datasets/sensor/서울/노면수위계2024', only_meta=False)
    rainfall_sensors = getAllSensors('datasets/sensor/서울/강수량계', only_meta=False)

    for road_sensor in road_sensors:
        roaddf = road_sensor.value.sort_values(by='time').reset_index(drop=True)
        roaddf['time_diff'] = roaddf['time'].diff()
        missing_data_intervals = roaddf[roaddf['time_diff'] > pd.Timedelta(hours=1)]
        missing_intervals = []
        for idx, row in missing_data_intervals.iterrows():
            start_time = roaddf.loc[idx - 1, 'time']
            end_time = row['time']
            missing_intervals.append((start_time, end_time))
        
        print(road_sensor.id)
        print("데이터가 비어있는 구간 리스트:", missing_intervals)


        rainfall_sensor, min_distance = findNearestSensor(road_sensor, rainfall_sensors)
        
        result = road_append_rainfall(road_sensor, rainfall_sensor, minute_interval=minute_interval, rolling_windows=rolling_windows)

        result.value.rename(columns={'value': '노면수위'}, inplace=True)
        
        dataset = TimeSeriesDataset(result.value, 
                                    input_window_size=input_window_size, 
                                    output_window_size=output_window_size, 
                                    axis=axis, 
                                    threshold=threshold,
                                    ignore_intervals=missing_intervals)
        
        print(f"{result.id} 데이터 갯수:", len(dataset))

        # filter 컬럼 추가
        df = result.value
        df['filter'] = 0
        df.loc[dataset.valid_indices, 'filter'] = 1

        result.save(f"datasets/sensor/서울/한 데이터의 시간 간격 {minute_interval}분, 데이터 간격 {minute_interval}분, '{result.value.columns[axis]}'열 {minute_interval * input_window_size}분 평균 {threshold} 이상/{result.id}_{rainfall_sensor.id}")
        save_dataset(dataset, f'{result.path}/result.npy')


if __name__ == '__main__':
    # 강수량 기준
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=12, axis=2, threshold=1)

    main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=12, axis=2, threshold=0.04)

    # 노면수위 기준
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=6, axis=1, threshold=1)
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=6, axis=1, threshold=0.5)
