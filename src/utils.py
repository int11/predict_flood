import pandas as pd
import os 
from src import Sensor
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