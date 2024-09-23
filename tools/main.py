from tools.utils import *
import matplotlib.pyplot as plt


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
    df = df.set_index('time')
    df_1S = df.resample('1S').mean()
    df_1S_ema = df_1S.ewm(alpha=0.9, adjust=False).mean()
    df_1S_ema_10T = df_1S_ema.resample('10T').mean()
    return df_1S_ema_10T

# 사용 예시
if __name__ == '__main__':
    dir = 'datasets/sensor'
    sensors = getAllSensors(dir)
    rainfall = searchSensors(sensors, location='서울', category='강수량계', id='401')
    rainfall = Sensor.load(rainfall.path)
    checkMissingValues(rainfall.value)


    road = searchSensors(sensors, id='NAMF00000000056')
    road = Sensor.load(road.path)
    plt.plot(road.value['time'], road.value['value'], alpha=0.2)
    plt.show()
    road.value = t_1S_ema_10T(road.value)


    for sensor in matched_sensors:
        print(sensor)