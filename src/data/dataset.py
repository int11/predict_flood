import torch
from torch.utils.data import Dataset

class TimeSeriesDataset(Dataset):
    def __init__(self, data, window_size):
        """
        data: 시계열 데이터를 포함하는 1차원 또는 2차원 배열
        window_size: 입력으로 사용할 과거 데이터의 길이
        """
        self.data = data
        self.window_size = window_size

    def __len__(self):
        # 마지막 윈도우가 데이터를 벗어나지 않도록 조정
        return len(self.data) - self.window_size

    def __getitem__(self, index):
        # index 위치에서 시작하는 윈도우 크기만큼의 데이터를 반환
        x = self.data[index:index+self.window_size]
        # 예측 대상이 되는 다음 시점의 데이터
        y = self.data[index+self.window_size]
        return torch.tensor(x, dtype=torch.float), torch.tensor(y, dtype=torch.float)
