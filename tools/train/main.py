import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
import argparse
import logging
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
# Import Project Modules -----------------------------------------------------------------------------------------------
from utils import *
from src.models.convtran.model import model_factory, count_parameters
from src.models.convtran.optimizers import get_optimizer
from src.models.convtran.loss import get_loss_module
from src.models.convtran.utils import load_model
from src.models.convtran.analysis import str_confusion_matrix
from Training import SupervisedTrainer, train_runner
from src.sensor import Sensor, getAllSensors, findNearestSensor
from src.data import *

logger = logging.getLogger('__main__')
parser = argparse.ArgumentParser()


# -------------------------------------------- Input and Output --------------------------------------------------------
parser.add_argument('--data_path', default='datasets/sensor/서울/노면수위계2024',
                    help='Road data path')
parser.add_argument('--sensor_ids', nargs='+', type=str, default=["EUMW00223060013", 
                                                                  "EUMW00223050014", 
                                                                  "EUMW00223050025", 
                                                                  "EUMW00223120045", 
                                                                  "EUMW00223050004", 
                                                                  "EUMW00223050015", 
                                                                  "EUMW00223060036", 
                                                                  "EUMW00223060030",], help='List of sensor IDs to use for training')
parser.add_argument('--rainfall_path', default='datasets/sensor/서울/강수량계',
                    help='Rainfall data path')
parser.add_argument('--output_dir', default='Results',
                    help='Root output directory. Must exist. Time-stamped directories will be created inside.')
parser.add_argument('--Norm', type=bool, default=False, help='Data Normalization')
parser.add_argument('--val_ratio', type=float, default=0.2, help="Proportion of the train-set to be used as validation")
parser.add_argument('--print_interval', type=int, default=10, help='Print batch info every this many batches')
# -------------------------------------------- Data Preprocessing -------------------------------------------------------
parser.add_argument('--minute_interval', type=int, default=10, help='Interval of the data in minutes')
parser.add_argument('--rolling_windows', nargs='+', type=int, default=[10, 30, 60, 120, 180], help='List of rolling windows for rainfall')
parser.add_argument('--input_window_size', type=int, default=12, help='Input window size')
parser.add_argument('--output_window_size', type=int, default=12, help='Output window size')
parser.add_argument('--threshold_feature_axis', type=int, default=2, 
                    help="feature 중 지정된 axis의 input_window_size 기간 동안 평균이 threshold 이상인 데이터만 사용"
                    "example feature columns [time, road, rainfall.rolling(window=rolling_windows[0]), rainfall.rolling(window=rolling_windows[1]), ...]")
parser.add_argument('--threshold', type=float, default=0.04, help='Threshold for axis')
parser.add_argument('--concat_output_feature_axis', nargs='+', type=int, default=[2,3,4,5,6], help='Receive output axis to concatenate.') 
parser.add_argument('--label_output_time_axis', nargs='+', type=int, default=[[0], [1], [2], [3], [4], [5], [0,1], [0,1,2], [0,1,2,3], [0,1,2,3,4], [0,1,2,3,4,5]], 
                    help='Time axis to use when creating label data, ex) [0]: 0~10, [1]: 10~20, [2]: 20~30, [0,1]: 0~20, [1,2]: 10~30')
parser.add_argument('--label_thresholds', nargs='+', type=float, default=[0, 12, 35, 60], help='라벨링 구간')
# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------- Model Parameter and Hyperparameter ---------------------------------------------
parser.add_argument('--Net_Type', default=['C-T'], choices={'T', 'C-T'}, help="Network Architecture. Convolution (C)"
                                                                              "Transformers (T)")
# Transformers Parameters ------------------------------
parser.add_argument('--emb_size', type=int, default=16, help='Internal dimension of transformer embeddings')
parser.add_argument('--dim_ff', type=int, default=256, help='Dimension of dense feedforward part of transformer layer')
parser.add_argument('--num_heads', type=int, default=8, help='Number of multi-headed attention heads')
parser.add_argument('--Fix_pos_encode', choices={'tAPE', 'Learn', 'None'}, default='tAPE',
                    help='Fix Position Embedding')
parser.add_argument('--Rel_pos_encode', choices={'eRPE', 'Vector', 'None'}, default='eRPE',
                    help='Relative Position Embedding')
# Training Parameters/ Hyper-Parameters ----------------
parser.add_argument('--epochs', type=int, default=500, help='Number of training epochs')
parser.add_argument('--batch_size', type=int, default=2048, help='Training batch size')
parser.add_argument('--lr', type=float, default=1e-3, help='learning rate')
parser.add_argument('--dropout', type=float, default=0.01, help='Droupout regularization ratio')
parser.add_argument('--val_interval', type=int, default=2, help='Evaluate on validation every XX epochs. Must be >= 1')
parser.add_argument('--key_metric', choices={'loss', 'accuracy', 'precision'}, default='accuracy',
                    help='Metric used for defining best epoch')
# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------ System --------------------------------------------------------
parser.add_argument('--gpu', type=int, default='0', help='GPU index, -1 for CPU')
parser.add_argument('--console', action='store_true', help="Optimize printout for console output; otherwise for file")
parser.add_argument('--seed', default=1234, type=int, help='Seed used for splitting sets')
args = parser.parse_args()

if __name__ == '__main__':
    config = Setup(args)  # configuration dictionary
    sys.stdout = Tee(os.path.join(config['output_dir'], 'log.txt')) # logging to file
    device = Initialization(config)
    
    rainfall_sensors = getAllSensors(args.rainfall_path, only_meta=True)

    # label_output_time_axes multiple input handling
    label_output_time_axes = config['label_output_time_axis']
    if isinstance(label_output_time_axes, list) and all(isinstance(i, int) for i in label_output_time_axes):
        label_output_time_axes = [label_output_time_axes]
    elif isinstance(label_output_time_axes, int):
        label_output_time_axes = [[label_output_time_axes]]
    # concat_output_feature_axis multiple input handling
    if isinstance(config['concat_output_feature_axis'], int):
        config['concat_output_feature_axis'] = [config['concat_output_feature_axis']]

    result_df = pd.DataFrame(index=args.sensor_ids, columns=[str(i) for i in label_output_time_axes])

    for label_output_time_axis in config['label_output_time_axis']:
        for sensor_id in args.sensor_ids:  # for loop on the all datasets in "data_dir" directory
            config['data_dir'] = sensor_id
            print('\n', sensor_id, '\n')
            # ------------------------------------ Load Data ---------------------------------------------------------------
            logger.info("Loading Data ...")

            road_sensor = Sensor.load(f'{args.data_path}/{sensor_id}', only_meta=False)
            rainfall_sensor, min_distance = findNearestSensor(road_sensor, rainfall_sensors)
            rainfall_sensor = Sensor.load(rainfall_sensor.path, only_meta=False)

            data, label = process_sensor_data(road_sensor, 
                                            rainfall_sensor, 
                                            minute_interval=args.minute_interval, 
                                            rolling_windows=args.rolling_windows,
                                            input_window_size=args.input_window_size, 
                                            output_window_size=args.output_window_size, 
                                            threshold_feature_axis=args.threshold_feature_axis, 
                                            threshold=args.threshold,
                                            concat_output_feature_axis=args.concat_output_feature_axis, 
                                            label_output_time_axis=label_output_time_axis,
                                            label_thresholds=args.label_thresholds)
            
            train_data, train_label, val_data, val_label = data_split(data, label, val_ratio=0.1)
            
            Data = {'train_data': train_data, 'train_label': train_label, 'val_data': val_data, 'val_label': val_label, 'test_data': val_data, 'test_label': val_label}

            train_dataset = dataset_class(Data['train_data'], Data['train_label'])
            val_dataset = dataset_class(Data['val_data'], Data['val_label'])
            test_dataset = dataset_class(Data['test_data'], Data['test_label'])

            train_loader = DataLoader(dataset=train_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
            val_loader = DataLoader(dataset=val_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
            test_loader = DataLoader(dataset=test_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
            # --------------------------------------------------------------------------------------------------------------
            # -------------------------------------------- Build Model -----------------------------------------------------
            logger.info("Creating model ...")
            config['Data_shape'] = Data['train_data'].shape
            config['num_labels'] = int(max(Data['train_label']))+1
            model = model_factory(config)
            logger.info("Model:\n{}".format(model))
            logger.info("Total number of parameters: {}".format(count_parameters(model)))
            # -------------------------------------------- Model Initialization ------------------------------------
            optim_class = get_optimizer("RAdam")
            config['optimizer'] = optim_class(model.parameters(), lr=config['lr'], weight_decay=0)
            config['loss_module'] = get_loss_module()
            save_path = os.path.join(config['save_dir'], f"{sensor_id}_model_last.pth")
            tensorboard_writer = SummaryWriter('summary')
            model.to(device)
            # ---------------------------------------------- Training The Model ------------------------------------
            logger.info('Starting training...')
            trainer = SupervisedTrainer(model, train_loader, device, config['loss_module'], config['optimizer'], l2_reg=0,
                                        print_interval=config['print_interval'], console=config['console'], print_conf_mat=False)
            val_evaluator = SupervisedTrainer(model, val_loader, device, config['loss_module'],
                                            print_interval=config['print_interval'], console=config['console'],
                                            print_conf_mat=False)

            train_runner(config, model, trainer, val_evaluator, save_path)
            best_model, optimizer, start_epoch = load_model(model, save_path, config['optimizer'])
            best_model.to(device)

            best_test_evaluator = SupervisedTrainer(best_model, test_loader, device, config['loss_module'],
                                                    print_interval=config['print_interval'], console=config['console'],
                                                    print_conf_mat=True)
            best_aggr_metrics_test, all_metrics = best_test_evaluator.evaluate(keep_all=True)
            print_str = 'Best Model Test Summary: '
            for k, v in best_aggr_metrics_test.items():
                print_str += '{}: {} | '.format(k, v)
            print(print_str)

            value_counts = pd.DataFrame(train_label).value_counts().to_dict()
            print("train label value counts" + str(value_counts))

            result_df.at[sensor_id, str(label_output_time_axis)] = \
                str_confusion_matrix(all_metrics['ConfMatrix'], best_test_evaluator.analyzer.existing_class_names) + "\n\n" + \
                best_test_evaluator.analyzer.generate_classification_report() + "\n" + \
                "loss : " + str(best_aggr_metrics_test['loss']) + "\n" + \
                "accuracy : " + str(all_metrics['total_accuracy']) + "\n" + \
                "train_label value_counts : " + str(value_counts)
            result_df.to_csv(os.path.join(config['output_dir'], 'ConvTran_Results.csv'))
    sys.stdout.close()