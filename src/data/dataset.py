import torch
from torch.utils.data import Dataset
import pandas as pd

class TimeSeriesDataset(Dataset):
    def __init__(self,
                 df, 
                 input_window_size, 
                 output_window_size, 
                 threshold_feature_axis, threshold, 
                 ignore_intervals: list[tuple[pd.Timestamp, pd.Timestamp]]=None):
        """
        Args:
        -----
        df: DataFrame
        input_window_size: 입력으로 사용할 데이터의 길이
        output_window_size: 출력으로 사용할 데이터의 길이
        axis : threshold를 적용할 열
        threshold : feature 중 지정된 axis의 input_window_size 기간 동안 평균이 threshold 이상인 데이터만 사용
        ignore_intervals: 강제로 무시할 구간 리스트
        """

        temp_df = df.copy()
        temp_df['time'] = temp_df['time'].dt.strftime('%Y%m%d%H%M').apply(int)
        self.data = temp_df.to_numpy()

        self.input_window_size = input_window_size
        self.output_window_size = output_window_size
        self.total_window_size = input_window_size + output_window_size
        self.ignore_intervals = ignore_intervals if ignore_intervals is not None else []

        self.valid_indices = [
            i for i in range(len(self.data) - self.total_window_size + 1)
            if self.data[i:i+self.input_window_size, threshold_feature_axis].mean() > threshold
            and not self.is_in_ignore_intervals(
                df.iloc[i]['time'],
                df.iloc[i + self.total_window_size - 1]['time']
            )
        ]

    def is_in_ignore_intervals(self, start_time, end_time):
        for interval_start, interval_end in self.ignore_intervals:
            if start_time < interval_end and end_time > interval_start:
                return True
        return False
    
    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, index):
        valid_index = self.valid_indices[index]
        x = self.data[valid_index:valid_index+self.input_window_size]
        y = self.data[valid_index+self.input_window_size:valid_index+self.total_window_size]

        return torch.tensor(x), torch.tensor(y)