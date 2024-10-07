import os
import pandas as pd
import pickle

class Sensor:
    """
    ex)
    meta = {
        'location':'서울특별시 서초구 서초동 1416번지 서초 IC',
        'category':'강수량계',
        'id':401,
        'WGS84': {'latitude': 37.48462, 'longitude': 127.02601},
        'columns': ['time', '기온(°C)', '1분 강수량(mm)', '강수유무(유무)', '풍향(deg)', '풍속(m/s)', '현지기압(hPa)', '해면기압(hPa)', '습도(%)', '일사(MJ/m^2)', '일조(Sec)']
    }
    """
    def __init__(self, meta: dict[str, str], value: pd.DataFrame=None, path=None):
        self.meta = meta
        if value is not None and value.empty == False:
            value['time'] = pd.to_datetime(value['time'])

        self.value = value
        self.path = None

    def save(self, path=None, groupby=False):
        if path is None:
            if self.path is None:
                raise ValueError('path is None')
            path = self.path

        if self._value is None:
            raise ValueError('value is None')

        os.makedirs(path, exist_ok=True)
        
        with open(os.path.join(path, 'meta.pkl'), 'wb') as meta_file:
            pickle.dump(self.meta, meta_file)

        self.compress()

        if not groupby:
            # value를 저장합니다.
            with open(os.path.join(path, 'value.pkl'), 'wb') as value_file:
                pickle.dump(self._value, value_file)
        else:
            # value의 time 열을 분석해 달 별로 나눠서 저장합니다.
            for (year, month), group in self._value.groupby([self._value['time'].dt.year, self._value['time'].dt.month]):
                filename = f'{year}_{month}.pkl'
                with open(os.path.join(path, filename), 'wb') as file:
                    pickle.dump(group, file)
                    
        self.path = path

    def compress(self):
        column_names = self._value.columns
        # 각 열을 to_numpy()를 사용하여 numpy 배열로 변환하고, 이를 새로운 DataFrame으로 재구성합니다.
        updated_columns = {col: self._value[col].to_numpy() for col in column_names}
        self._value = pd.DataFrame(updated_columns)

    @staticmethod
    def load(path, only_meta=False, groupby=False):
        with open(os.path.join(path, 'meta.pkl'), 'rb') as meta_file:
            meta = pickle.load(meta_file)
        
        if only_meta:
            value = None
        elif groupby:
            value = pd.DataFrame()
            for file in os.listdir(path):
                if file.endswith('.pkl') and file != 'meta.pkl':
                    with open(os.path.join(path, file), 'rb') as value_file:
                        df = pickle.load(value_file)
                        value = pd.concat([value, df])
        else:
            with open(os.path.join(path, 'value.pkl'), 'rb') as value_file:
                value = pickle.load(value_file)
        
        result = Sensor(meta, value)
        result.path = path
        return result

    def __lt__(self, other):
        # 먼저 'category'를 기준으로 비교합니다.
        if self.category < other.category:
            return True
        elif self.category > other.category:
            return False
        else:
            # 'category'가 같을 경우 'location'을 기준으로 비교합니다.
            if self.location < other.location:
                return True
            elif self.location > other.location:
                return False
            else:
                # 'location'이 같을 경우 'id'를 기준으로 비교합니다.
                return self.id < other.id

    def concat(self, other):
        self._value = pd.concat([self._value, other.value])
        self.compress()

    @property
    def name(self):
        return '_'.join([self.location, self.category, str(self.id)])

    @property
    def id(self):
        return self.meta['id']

    @property
    def location(self):
        return self.meta['location']

    @property
    def category(self):
        return self.meta['category']

    @property
    def columns(self):
        return self.meta['columns']
    
    def __repr__(self):
        return f"Sensor(location={self.location}, category={self.category}, id={self.id})"

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, new_value):
        if new_value is not None:
            self.meta['columns'] = list(new_value.columns)
        self._value = new_value