Example file directory, refer to this [file]('https://github.com/int11/predict_flood/blob/master/src/core/sensor.py')
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

# misc
obsr_unit_id : 기존 관리 아이디
obsr_item_nm : 강우량계 센서 메타정보
msrins_nm : id 


광주데이터 : 노면수위데이터가 퀄리이가 높고
강우량계 6번
7번도 많았다
노면수위계 3번
지하차도 전반적으로없지만 1 2번  



서울데이터 : 하수관로가 퀄리티가 높다
하수관로수위센서 22번의 0007번
하수관로 수위센서에 가장 가까운 401번 데이터 


창원데이터 : 퀄리티가 많이 안좋음. 후순위

전체 10분을 통일
강수량 누적으로 데이터씀
10분중에서의 수위 최대값으로 

이미 한것 :
lstm 스탠다드
transofrmer 인포머모델
cnn layer 스탠다드 대충 vv