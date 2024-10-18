import torch
from torch.utils.data import Dataset

class TimeSeriesDataset(Dataset):
    def __init__(self, df, input_window_size, output_window_size, axis, threshold, time_stride=1, data_stride=1):
        """
        data: 시계열 데이터를 포함하는 1차원 또는 2차원 배열
        input_window_size: 입력으로 사용할 과거 데이터의 길이
        output_window_size: 출력으로 사용할 미래 데이터의 길이
        n, s: input_window_size 기간 동안의 데이터 중 n열 값의 평균이 threshold 이상인 데이터만 사용
        """
        df = df.copy()
        df['time'] = df['time'].dt.strftime('%Y%m%d%H%M').astype(int)
        self.data = df.to_numpy()
        self.input_window_size = input_window_size
        self.output_window_size = output_window_size
        self.total_window_size = input_window_size + output_window_size

        self.valid_indices = [
            i for i in range(len(self.data) - self.total_window_size + 1)
            if self.data[i:i+self.input_window_size, axis].mean() > threshold
        ]

    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, index):
        valid_index = self.valid_indices[index]
        x = self.data[valid_index:valid_index+self.input_window_size]
        y = self.data[valid_index+self.input_window_size:valid_index+self.total_window_size]
        return torch.tensor(x), torch.tensor(y)