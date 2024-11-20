# predict_flood

[(주)무한정보기술](https://muhanit.kr/), [안정호 교수](https://ace.kangnam.ac.kr/menu/5f5be509b40da4c114dbdd6f33bbe907.do) 분들 과 함께 서울시 침수 예측 선행 연구 

# Dataset

Example file directory, refer to this [file](https://github.com/int11/predict_flood/blob/master/src/sensor/sensor.py#L5)
```
datasets
    {your file dir}
        {Sensor name}
            meta.pkl : meta data file
            value.pkl : pandas.dataframe file
            
```

Example code
```
Sensor.load(datasets/{your file dir}/{Sensor name})
```

