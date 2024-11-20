import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd
from src.sensor import Sensor
from src.utils import path2df


# 파일 경로 리스트
file_paths = [
    'dataset/original/광주데이터/원데이터/강우량계.csv',
    'dataset/original/광주데이터/원데이터/관로수위계.csv',
    'dataset/original/광주데이터/원데이터/노면수위계.csv',
    'dataset/original/광주데이터/원데이터/지하차도.csv'
]

dataframes = path2df(file_paths)


for key, df in dataframes.items():
    print(f"{key}:")
    unique_msrins_nm = df['msrins_nm'].unique()
    
    for i in unique_msrins_nm:
        fdf = df[df['msrins_nm'] == i]

        print(fdf['obsr_unit_id'].unique(), fdf['obsr_item_nm'].unique(), fdf['msrins_nm'].unique())
        

        if key == '관로수위계':
            key = '하수관로수위계'
        elif key == '강우량계':
            key = '강수량계'
        elif key == '지하차도':
            key = '지하차도수위계'
        
        value = fdf[['obsr_value', 'obsr_dt']].copy()
       
        value.rename(columns={'obsr_dt': 'time'}, inplace=True)
        value['time'] = pd.to_datetime(value['time'])

        meta = {
                'location':'광주',
                'category':key, 
                'id':str(fdf['msrins_nm'].unique()[0]), 
                'obsr_unit_id':int(fdf['obsr_unit_id'].unique()[0]), 
                'obsr_item_nm':fdf['obsr_item_nm'].unique()[0]}
        
        obj = Sensor(meta, value)
        obj.save()
