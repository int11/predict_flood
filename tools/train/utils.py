import os
import sys
import json
import torch
import numpy as np
import logging
from datetime import datetime
from torch.utils.data import Dataset
from src.data import TimeSeriesDataset, concat_road_rainfall, find_missing_intervals



logging.basicConfig(format='%(asctime)s | %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def Setup(args):
    """
        Input:
            args: arguments object from argparse
        Returns:
            config: configuration dictionary
    """
    config = args.__dict__  # configuration dictionary
    # Create output directory
    initial_timestamp = datetime.now()
    output_dir = config['output_dir']
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    output_dir = os.path.join(output_dir, config['data_path'], initial_timestamp.strftime("%Y-%m-%d_%H-%M"))
    config['output_dir'] = output_dir
    config['save_dir'] = os.path.join(output_dir, 'checkpoints')
    config['pred_dir'] = os.path.join(output_dir, 'predictions')
    config['tensorboard_dir'] = os.path.join(output_dir, 'tb_summaries')
    create_dirs([config['save_dir'], config['pred_dir'], config['tensorboard_dir']])

    # Save configuration as a (pretty) json file
    with open(os.path.join(output_dir, 'configuration.json'), 'w') as fp:
        json.dump(config, fp, indent=4, sort_keys=True)

    logger.info("Stored configuration file in '{}' as a configuration.json".format(output_dir))

    return config


def create_dirs(dirs):
    """
    Input:
        dirs: a list of directories to create, in case these directories are not found
    Returns:
        exit_code: 0 if success, -1 if failure
    """
    try:
        for dir_ in dirs:
            if not os.path.exists(dir_):
                os.makedirs(dir_)
        return 0
    except Exception as err:
        print("Creating directories error: {0}".format(err))
        exit(-1)


def Initialization(config):
    if config['seed'] is not None:
        torch.manual_seed(config['seed'])
    device = torch.device('cuda' if (torch.cuda.is_available() and config['gpu'] != '-1') else 'cpu')
    logger.info("Using device: {}".format(device))
    if device == 'cuda':
        logger.info("Device index: {}".format(torch.cuda.current_device()))
    return device


def Sensor_Data_Loader(path, concat_future_rain=False, thresholds=[0, 5, 10, 15, 30]):
    if os.path.exists(path):
        raw_data = np.load(path, allow_pickle=True)
    else:
        raise FileNotFoundError(f"Data file {path} not found.")

    # Data
    data = raw_data[:, :12, 1:]
    if concat_future_rain:
        min10 = raw_data[:, 12:, 2][:, :, np.newaxis]
        data = np.concatenate((data, min10), axis=2) # 미래의 강수량 concat
    data = np.transpose(data, (0, 2, 1)) # 1d conv을 위해 transpose

    # Label 
    label = raw_data[:, 12, 1]
    
    # 라벨링 기준 설정
    label_result = np.zeros_like(label).astype(np.int32)
    for i in range(len(thresholds)):
        min = thresholds[i]
        max = int(thresholds[i + 1]) if i + 1 < len(thresholds) else sys.maxsize
        label_result = np.where((label > min) & (label <= max), i + 1, label_result)

    return data, label_result


def data_split(data, label, val_ratio):
    """
    데이터를 각 클래스별로 나누고 val_ratio 비율만큼 validation set으로 나누어줍니다.
    """
    num_classes = len(np.unique(label))
    val_data = []
    val_label = []
    for i in range(num_classes):
        indices = np.where(label == i)[0]
        np.random.shuffle(indices)
        num_val = int(len(indices) * val_ratio)
        val_data.append(data[indices[:num_val]])
        val_label.append(label[indices[:num_val]])
        data = np.delete(data, indices[:num_val], axis=0)
        label = np.delete(label, indices[:num_val], axis=0)

    val_data = np.concatenate(val_data, axis=0)
    val_label = np.concatenate(val_label, axis=0)

    return data, label, val_data, val_label


def process_sensor_data(road_sensor,
                        rainfall_sensor,
                        minute_interval=10, 
                        rolling_windows=[10, 30, 60, 120, 180], 
                        input_window_size=12, 
                        output_window_size=12, 
                        threshold_feature_axis=2, 
                        threshold=0.04, 
                        concat_output_feature_axis=[2], 
                        label_output_time_axis=[0],
                        label_thresholds=[0, 5, 10, 15, 30]):
    
    '''
    feature 은 [time, 노면수위, rolling_windows[0]누적강수량, rolling_windows[1]누적강수량, ...]
    '''
    result = concat_road_rainfall(road_sensor, rainfall_sensor, minute_interval=minute_interval, rolling_windows=rolling_windows)
    missing_intervals = find_missing_intervals(road_sensor, hours=1)
    dataset = TimeSeriesDataset(result.value, 
                                input_window_size=input_window_size, 
                                output_window_size=output_window_size, 
                                threshold_feature_axis=threshold_feature_axis, 
                                threshold=threshold,
                                ignore_intervals=missing_intervals)

    input = np.array([dataset[i][0] for i in range(len(dataset))])
    output = np.array([dataset[i][1] for i in range(len(dataset))])

    # Data
    if concat_output_feature_axis != None:
        min10 = output[:, :, concat_output_feature_axis]
        input = np.concatenate((input, min10), axis=2) # 미래의 강수량 concat

    data = input[:, :, 1:] # time 열 제외
    data = np.transpose(data, (0, 2, 1)) # 1d conv을 위해 transpose
    
    # Label 
    label = output[:, label_output_time_axis, 1].max(axis=1)
    
    # 라벨링 기준 설정
    label_result = np.zeros_like(label).astype(np.int32)
    for i in range(len(label_thresholds)):
        min = label_thresholds[i]
        max = int(label_thresholds[i + 1]) if i + 1 < len(label_thresholds) else sys.maxsize
        label_result = np.where((label > min) & (label <= max), i + 1, label_result)

    return data, label_result


class dataset_class(Dataset):

    def __init__(self, data, label):
        super(dataset_class, self).__init__()

        self.feature = data
        self.labels = label.astype(np.int32)

    def __getitem__(self, ind):

        x = self.feature[ind]
        x = x.astype(np.float32)

        y = self.labels[ind]  # (num_labels,) array

        data = torch.tensor(x)
        label = torch.tensor(y)

        return data, label, ind

    def __len__(self):
        return len(self.labels)


class Tee:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log_file = open(path, 'w')
        self.file = log_file
        self.stdout = sys.stdout

    def write(self, obj):
        self.file.write(obj)
        self.file.flush()
        self.stdout.write(obj)
        self.stdout.flush()


    def flush(self):
        self.file.flush()
        self.stdout.flush()

    def close(self):
        sys.stdout = sys.__stdout__  # Restore original stdout
        self.file.close()