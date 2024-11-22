import pandas as pd
from src import Sensor
import requests
from io import StringIO
import asyncio
import aiohttp
from datetime import datetime, timedelta


def _download_rainfall(authKey, start="202208080000", end="202208160000", stn="401"):
    """
    기상청 api를 이용하여 강수량 데이터를 다운로드합니다.
    기상청 api는 최대 12시간 단위로 데이터를 다운로드할 수 있습니다.
    
    #  WD1    : 1분 평균 풍향 (degree) : 0-N, 90-E, 180-S, 270-W, 360-무풍 
    #  WS1    : 1분 평균 풍속 (m/s) 
    #  WDS    : 최대 순간 풍향 (degree) 
    #  WSS    : 최대 순간 풍속 (m/s) 
    #  WD10   : 10분 평균 풍향 (degree) 
    #  WS10   : 10분 평균 풍속 (m/s) 
    #  TA     : 1분 평균 기온 (C) 
    #  RE     : 강수감지 (0-무강수, 0이 아니면-강수) 
    #  RN-15m : 15분 누적 강수량 (mm) 
    #  RN-60m : 60분 누적 강수량 (mm) 
    #  RN-12H : 12시간 누적 강수량 (mm) 
    #  RN-DAY : 일 누적 강수량 (mm) 
    #  HM     : 1분 평균 상대습도 (%) 
    #  PA     : 1분 평균 현지기압 (hPa) 
    #  PS     : 1분 평균 해면기압 (hPa) 
    #  TD     : 이슬점온도 (C) 
    #  *) -50 이하면 관측이 없거나, 에러처리된 것을 표시 

    Args
    ----
    start : str
        데이터 다운로드 시작 시간, 'YYYYMMDDHHMM' 형식
    end : str
        데이터 다운로드 종료 시간, 'YYYYMMDDHHMM' 형식
    stn : str
        기상청 지점 번호
    authKey : str
        기상청 api 인증키
    """
    df_list = []

    start = pd.to_datetime(start, format='%Y%m%d%H%M')
    end = pd.to_datetime(end, format='%Y%m%d%H%M')

    # 기상청 api는 12시간씩 끊어서 데이터를 가져올 수 있음.
    date_range = pd.date_range(start=start, end=end, freq='12h')

    if date_range[-1] != end:
        date_range = date_range.append(pd.Index([end]))

    for i in range(len(date_range) - 1):
        tm1 = date_range[i]
        tm2 = date_range[i + 1] - pd.Timedelta(minutes=1)
        tm1 = tm1.strftime('%Y%m%d%H%M')
        tm2 = tm2.strftime('%Y%m%d%H%M')

        url = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min"
        disp = "1"  # 0 : 변수별로 일정한 길이 유지, 포트란에 적합 (default), 1 : 구분자(,)로 구분, 엑셀에 적합
        help = "2"  # 0 : 시작과 종료표시 + 변수명 (default), 1 : 0 + 변수에 대한 설명, 2 : 전혀 표시않음 (값만 표시)
        authKey = authKey

        # URL과 저장 경로 변수를 지정합니다.
        url = f"{url}?tm1={tm1}&tm2={tm2}&stn={stn}&disp={disp}&help={help}&authKey={authKey}"

        response = requests.get(url)
        df = pd.read_csv(StringIO(response.content.decode('utf-8')), header=None)
        df = df.drop(df.columns[18], axis=1)
        df.columns = ['time', 'STN', 'WD1', 'WS1', 'WDS', 'WSS', 'WD10', 'WS10', 'TA', 'RE', 'RN-15m', 'RN-60m', 'RN-12H', 'RN-DAY', 'HM', 'PA', 'PS', 'TD']
        df = df.drop('STN', axis=1)
        # 'time' 열을 datetime 형식으로 변환
        df['time'] = pd.to_datetime(df['time'], format='%Y%m%d%H%M')
        df_list.append(df)

    combined_df = pd.concat(df_list, ignore_index=True)
    columns_to_mask = ['RE', 'RN-15m', 'RN-60m', 'RN-12H', 'RN-DAY']
    combined_df[columns_to_mask] = combined_df[columns_to_mask].mask(combined_df[columns_to_mask] < 0)

    return combined_df


async def _download_sewer(start_date, end_date, api_key):
    '''
    https://data.seoul.go.kr/dataList/OA-2527/S/1/datasetView.do
    Args:
    ----
    start_date:
        시작 날짜 (포맷: %Y%m%d%H)
    end_date:
        종료 날짜 (포맷: %Y%m%d%H)
    api_key:
        서울 열린데이터 광장에서 발급받은 API 키
    '''

    async def fetch_data(session, url):
        i = 1
        while True:
            try:
                async with session.get(url, timeout=10) as response:
                    data = await response.json()
                    if data is None:
                        raise ValueError("No data received")
                    elif data.get('RESULT', {}).get('CODE') == 'ERROR-500':
                        raise ValueError("Server error (500)")
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                print(f"Error at {url}: {e}, retrying {i}")
                i += 1
                await asyncio.sleep(2)  # 재시도 전에 잠시 대기
    
    base_url = "http://openapi.seoul.go.kr:8088"
    api_key = api_key
    data_type = "json"
    service = "DrainpipeMonitoringInfo"
    
    result = []
    start_date = datetime.strptime(start_date, "%Y%m%d%H")
    end_date = datetime.strptime(end_date, "%Y%m%d%H")

    while start_date <= end_date:
        start_date_str = start_date.strftime("%Y%m%d%H")
        next_week_date = start_date + timedelta(days=6, hours=23)
        end_date_str = min(next_week_date, end_date).strftime("%Y%m%d%H")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for sensor_id in range(25):
                sensor_id = str(sensor_id+1).zfill(2)
                url = f"{base_url}/{api_key}/{data_type}/{service}/{0}/{1}/{sensor_id}/{start_date_str}/{end_date_str}"
                tasks.append(fetch_data(session, url))
            responses = await asyncio.gather(*tasks)
            

            for sensor_id in range(25):
                response = responses[sensor_id]
                if 'DrainpipeMonitoringInfo' not in response:
                    print(f"No data for sensor_id: {sensor_id}")
                    continue

                totle_rows = response['DrainpipeMonitoringInfo']['list_total_count']
                sensor_id = str(sensor_id+1).zfill(2)
                print("sensor_id:", sensor_id, "total_rows:", totle_rows)

                tasks = []
                for i in range(0, totle_rows, 1000):
                    url = f"{base_url}/{api_key}/{data_type}/{service}/{i}/{i+999}/{sensor_id}/{start_date_str}/{end_date_str}"
                    tasks.append(fetch_data(session, url))

                more_data = await asyncio.gather(*tasks)
                for item in more_data:
                    if item:
                        result.extend(item['DrainpipeMonitoringInfo']['row'])
        
        start_date = start_date + timedelta(days=7)

    df = pd.DataFrame(result)
    column_names = df.columns
    updated_columns = {col: df[col].to_numpy() for col in column_names}
    df = pd.DataFrame(updated_columns)
    return df

def download_sewer(*args, **kwargs):
    return asyncio.run(_download_sewer(*args, **kwargs))


def concat_road_rainfall(road_sensor : Sensor,
                         rainfall_sensor: Sensor,
                         minute_interval=1, 
                         rolling_windows=[10, 30, 60, 120, 180]):
    '''
    노면수위계 데이터와 누적강수량을 전처리해 합칩니다.

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


    road = road_sensor.value.copy().set_index('time')
    df = road.resample('1s').max().ewm(alpha=0.9, adjust=False).mean().resample(f'{minute_interval}min').max()

    
    rainfall = rainfall_sensor.value.copy()
    rainfall = rainfall[['time', '1분 누적강수량(mm)']].set_index('time')
    #  1분 강수량 열 자체가 없는 경우 
    rainfall = rainfall.resample('1min').first()

    rainfall = rainfall.interpolate()

    for window in rolling_windows:
        df[f'{window}분 누적강수량'] = rainfall.rolling(window=window).sum()

    # df = df.resample(f'{minute_interval}min').first()

    result = Sensor(road_sensor.meta, df.reset_index())
    result.compress()

    return result


def find_missing_intervals(df, hours):
    if isinstance(df, Sensor):
        df = df.value

    roaddf = df.sort_values(by='time').reset_index(drop=True)
    roaddf['time_diff'] = roaddf['time'].diff()
    missing_data_intervals = roaddf[roaddf['time_diff'] > pd.Timedelta(hours=hours)]
    missing_intervals = []
    for idx, row in missing_data_intervals.iterrows():
        start_time = roaddf.loc[idx - 1, 'time']
        end_time = row['time']
        missing_intervals.append((start_time, end_time))
    
    return missing_intervals

