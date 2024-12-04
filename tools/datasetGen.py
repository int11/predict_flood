import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.utils import *
import matplotlib.pyplot as plt
from src.data import *
import numpy as np
import torch
from src.sensor import getAllSensors, findNearestSensor

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False 


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
        rainfall_sensor, min_distance = findNearestSensor(road_sensor, rainfall_sensors)
        print(road_sensor.id, rainfall_sensor.id, min_distance)

        result = concat_road_rainfall(road_sensor, rainfall_sensor, minute_interval=minute_interval, rolling_windows=rolling_windows)
        missing_intervals = find_missing_intervals(road_sensor, hours=1)

        print("데이터가 비어있는 구간 리스트:", missing_intervals)

        dataset = TimeSeriesDataset(result.value, 
                                    input_window_size=input_window_size, 
                                    output_window_size=output_window_size, 
                                    threshold_feature_axis=axis, 
                                    threshold=threshold,
                                    ignore_intervals=missing_intervals)
        
        print(f"데이터 갯수:", len(dataset))

        # filter 컬럼 추가
        df = result.value
        df['filter'] = 0
        df.loc[dataset.valid_indices, 'filter'] = 1

        result.save(f"datasets/sensor/서울/window간 간격 {minute_interval}분, 다음 데이터간 간격 {minute_interval}분, '{result.value.columns[axis]}'열 {minute_interval * input_window_size}분 평균 {threshold} 이상/{result.id}_{rainfall_sensor.id}")
        save_dataset(dataset, f'{result.path}/result.npy')


if __name__ == '__main__':
    # 강수량 기준
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=12, axis=2, threshold=1)

    main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=12, axis=2, threshold=0.04)

    # 노면수위 기준
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=6, axis=1, threshold=1)
    # main(minute_interval=10, rolling_windows=[10, 30, 60, 120, 180], input_window_size=12, output_window_size=6, axis=1, threshold=0.5)