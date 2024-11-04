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
        'WGS84': {'latitude': 37.48462, 'longitude': 127.02601}
    }
    """
    def __init__(self, meta: dict[str, str], value: pd.DataFrame=None, path=None):
        self.meta = meta
        if value is not None and value.empty == False:
            value['time'] = pd.to_datetime(value['time'])

        self.value = value
        self.path = None

    def save(self, path=None):
        if path is None:
            if self.path is None:
                raise ValueError('path is None')
            path = self.path

        if self.value is None:
            raise ValueError('value is None')

        os.makedirs(path, exist_ok=True)
        
        with open(os.path.join(path, 'meta.pkl'), 'wb') as meta_file:
            meta = self.meta.copy()
            meta['columns'] = list(self.value.columns)
            pickle.dump(meta, meta_file)

        self.compress()

        self.value = self.value.reset_index(drop=True)
        self.value = self.value.sort_values(by='time')
        
        # value를 저장합니다.
        with open(os.path.join(path, 'value.pkl'), 'wb') as value_file:
            pickle.dump(self.value, value_file)

                    
        self.path = path

    def compress(self):
        column_names = self.value.columns
        # 각 열을 to_numpy()를 사용하여 numpy 배열로 변환하고, 이를 새로운 DataFrame으로 재구성합니다.
        updated_columns = {col: self.value[col].to_numpy() for col in column_names}
        self.value = pd.DataFrame(updated_columns)

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

    def concat(self, other, keep=None):
        '''
        Args
        ----
        df : pd.DataFrame
            추가할 데이터프레임
        keep : str
            'first' or 'last' 중 하나를 입력받습니다.
            'first'인 경우, 같은 시간 데이터가 있을 때 기존 데이터프레임을 유지합니다
            'last'인 경우, 같은 시간 데이터가 있을 때 덮어씁니다
        '''
        if isinstance(other, Sensor):
            other = other.value

        self.value = pd.concat([self.value, other])
        if keep is not None:
            self.value = self.value.drop_duplicates(subset=['time'], keep=keep)
        
        self.value = self.value.sort_values(by='time')

        self.compress()

    @property
    def name(self):
        return '_'.join([self.location, self.category, str(self.id)])

    @property
    def id(self):
        return self.meta['id']

    @id.setter
    def id(self, value):
        self.meta['id'] = str(value)

    @property
    def location(self):
        return self.meta['location']

    @location.setter
    def location(self, value):
        self.meta['location'] = value

    @property
    def category(self):
        return self.meta['category']

    @category.setter
    def category(self, value):
        self.meta['category'] = value

    @property
    def latitude(self):
        return self.meta['WGS84']['latitude']
    
    @latitude.setter
    def latitude(self, value):
        self.meta['WGS84']['latitude'] = float(value)

    @property
    def longitude(self):
        return self.meta['WGS84']['longitude']
    
    @longitude.setter
    def longitude(self, value):
        self.meta['WGS84']['longitude'] = float(value)

    def __repr__(self):
        return f"Sensor(location={self.location}, category={self.category}, id={self.id})"
    
    def copy(self):
        new_meta = self.meta.copy()
        new_value = self.value.copy() if self.value is not None else None
        return Sensor(new_meta, new_value, self.path)
    

    
