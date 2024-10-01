import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from tools.utils import *
import matplotlib.pyplot as plt
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

def add_rolling(df, rainfall, window):
    df[f'{window * 10}분 누적 강수량(mm)'] = rainfall.rolling(window=window).sum()
    return df

def plotMissingValues(df):
    nan_values = df[df.isna().any(axis=1)].fillna(0)
    non_nan_values = df.dropna()

    # NaN이 아닌 값들을 파란 점으로 표시
    plt.scatter(non_nan_values.index, non_nan_values['1분 강수량(mm)'], color='blue', label='Valid Data', alpha=0.2 , s=1)
    # # NaN 값을 빨간 점으로 표시
    plt.scatter(nan_values.index, nan_values['1분 강수량(mm)'], color='red', label='NaN Values', alpha=0.5 , s=2)


if __name__ == '__main__':
    dir = 'datasets/sensor'
    sensors = getAllSensors(dir)

    #강수량
    rainfall = searchSensors(sensors, location='서울', category='강수량계', id='401')
    rainfall = Sensor.load(rainfall.path).value
    rainfall = rainfall[['time', '1분 강수량(mm)']].set_index('time')
    checkMissingValues(rainfall)

    df = t_1S_ema_10T(rainfall)
    df = add_rolling(df, rainfall,3)
    df = add_rolling(df, rainfall, 6)
    df = add_rolling(df, rainfall, 12)

    
    #노면센서
    road = searchSensors(sensors, id='NAMF00000000056')
    road = Sensor.load(road.path).value.set_index('time')

    df['센서'] = t_1S_ema_10T(road)


    # df처리
    df = df[road.index.min():road.index.max()]

    for column in df.columns:
        if column != 'time':
            plt.plot(df.index, df[column], label=column)


    # from src.data.dataset import TimeSeriesDataset
    # dataloader = TimeSeriesDataset(df.to_numpy(), 12)
    # for i in dataloader:
    #     print(i)


    # plt.plot(rainfall['time'], rainfall['1분 강수량(mm)'], alpha=0.5)
    # plt.plot(road['time'], road['value'], alpha=0.5)
    plt.legend(loc='upper right')  # 범례 위치를 명시적으로 설정


    plt.show()