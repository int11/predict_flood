import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from tools.utils import *
import matplotlib.pyplot as plt
from src.data.dataset import TimeSeriesDataset

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False 

def checkMissingValues(df):
    r_num = df.isna().sum()
    num = len(df)
    per = round(r_num/num,3) * 100
    print(f"전체 데이터 수 : {num}")
    print("결측값 수 :")
    print(r_num) 
    print("결측치 비중 : ")
    print(per)

def t_1S_ema_10T(df):
    df_1S = df.resample('1s').max()
    df_1S_ema = df_1S.ewm(alpha=0.9, adjust=False).mean()
    df_1S_ema_10T = df_1S_ema.resample('10min').max()
    return df_1S_ema_10T

def plotMissingValues(df):
    # NaN 값을 빨간 점으로 표시
    nan_values = df[df.isna().any(axis=1)].fillna(0)
    plt.scatter(nan_values.index, nan_values['1분 강수량(mm)'], color='red', label='NaN Values', alpha=0.5 , s=1)
    
    # NaN이 아닌 값들을 파란 점으로 표시
    non_nan_values = df.dropna()
    plt.plot(non_nan_values.index, non_nan_values['1분 강수량(mm)'], color='blue', label='Valid Data', alpha=0.2)
    
    # NaN 값의 이전 값과 이후 값이 0 또는 NaN인지 확인
    nan_indices = df[df.isna().any(axis=1)].index
    previous_values = df.shift(1).loc[nan_indices]
    next_values = df.shift(-1).loc[nan_indices]
    previous_values_zero_or_nan = (previous_values == 0) | (previous_values.isna())
    next_values_zero_or_nan = (next_values == 0) | (next_values.isna())
    
    # 결과 출력
    for idx, (prev_is_zero_or_nan, next_is_zero_or_nan) in zip(nan_indices, zip(previous_values_zero_or_nan['1분 강수량(mm)'], next_values_zero_or_nan['1분 강수량(mm)'])):
        if prev_is_zero_or_nan and next_is_zero_or_nan:
            pass
        else:
            print(f"NaN at {idx} does not have previous and next value 0 or NaN")
            plt.scatter(idx, nan_values.loc[idx, '1분 강수량(mm)'], color='green', label='NaN with non-zero neighbors', s=20, alpha=0.5)


def concat_road_rainfall(save_path, minute_interval=1, rolling_windows=[10, 30, 60, 120]):
    rainfall_sensors = getAllSensors('datasets/sensor/서울/강수량계')
    road_sensors = getAllSensors('datasets/sensor/서울/노면수위계')

    for road_sensor in road_sensors:
        road = Sensor.load(road_sensor.path).value.set_index('time')
        df = road.resample('1s').max().ewm(alpha=0.9, adjust=False).mean().resample(f'{minute_interval}min').max()

        rainfall_sensor = findNearestSensor(road_sensor, rainfall_sensors)
        rainfall = Sensor.load(rainfall_sensor.path).value
        rainfall = rainfall[['time', '1분 누적강수량(mm)']].set_index('time')
        #  1분 강수량 열 자체가 없는 경우 
        rainfall = rainfall.resample('1min').first()
        
        checkMissingValues(rainfall)

        rainfall = rainfall.interpolate()

        for window in rolling_windows:
            df[str(window)] = rainfall.rolling(window=window).sum()
        
        df = df.resample(f'{minute_interval}min').first()

        road_sensor.value = df.reset_index()
        road_sensor.save(f'{save_path}/{road_sensor.id}_{rainfall_sensor.id}')


if __name__ == '__main__':
    # concat_road_rainfall(minute_interval=10, save_path='datasets/sensor/서울/노면+강수량10분단위')
    # concat_road_rainfall(minute_interval=1, save_path='datasets/sensor/서울/노면+강수량1분단위')

    sensors  = getAllSensors('datasets/sensor/서울/노면+강수량10분단위', only_meta=False)
    for sensor in sensors:
        df = sensor.value

        dataset = TimeSeriesDataset(df, input_window_size=12, output_window_size=6, n=2, threshold=1)
        print(dataset.valid_indices)
        df['조건충족1'] = 0
        df.loc[dataset.valid_indices, '조건충족1'] = 1

        dataset = TimeSeriesDataset(df, input_window_size=12, output_window_size=6, n=1, threshold=1)
        print(dataset.valid_indices)
        df['조건충족2'] = 0
        df.loc[dataset.valid_indices, '조건충족2'] = 1

        sensor.save(f'datasets/sensor/서울/final/{sensor.id}')

        # all_data = np.array([np.concatenate((dataset[i][0], dataset[i][1]), axis=0) for i in range(len(dataset))])
