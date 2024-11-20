import os
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
from Training import SupervisedTrainer, train_runner

logger = logging.getLogger('__main__')
parser = argparse.ArgumentParser()
# -------------------------------------------- Input and Output --------------------------------------------------------
parser.add_argument('--data_path', default='Dataset/Sensors/', choices={'Dataset/UEA/', 'Dataset/Segmentation/', 'Dataset/Sensors/'},
                    help='Data path')
parser.add_argument('--output_dir', default='Results',
                    help='Root output directory. Must exist. Time-stamped directories will be created inside.')
parser.add_argument('--Norm', type=bool, default=False, help='Data Normalization')
parser.add_argument('--val_ratio', type=float, default=0.2, help="Proportion of the train-set to be used as validation")
parser.add_argument('--print_interval', type=int, default=10, help='Print batch info every this many batches')
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
parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
parser.add_argument('--batch_size', type=int, default=16, help='Training batch size')
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
    device = Initialization(config)
    All_Results = ['Datasets', 'ConvTran']  # Use to store the accuracy of ConvTran in e.g "Result/Datasets/UEA"

    for problem in os.listdir(config['data_path']):  # for loop on the all datasets in "data_dir" directory
        config['data_dir'] = os.path.join(config['data_path'], problem)
        print('\n', problem)
        # ------------------------------------ Load Data ---------------------------------------------------------------
        logger.info("Loading Data ...")

        data, label = Sensor_Data_Loader(config, concat_future_rain=True)
        train_data, train_label, val_data, val_label = data_split(data, label, val_ratio=0.1)
        
        Data = {'train_data': train_data, 'train_label': train_label, 'val_data': val_data, 'val_label': val_label, 'test_data': val_data, 'test_label': val_label}

        train_dataset = dataset_class(Data['train_data'], Data['train_label'])
        val_dataset = dataset_class(Data['val_data'], Data['val_label'])
        test_dataset = dataset_class(Data['test_data'], Data['test_label'])

        test_loader = DataLoader(dataset=test_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
        train_loader = DataLoader(dataset=train_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
        val_loader = DataLoader(dataset=val_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
        # --------------------------------------------------------------------------------------------------------------
        # -------------------------------------------- Build Model -----------------------------------------------------
        dic_position_results = [config['data_dir'].split('/')[-1]]

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
        save_path = os.path.join(config['save_dir'], problem + 'model_{}.pth'.format('last'))
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

        print("train_label")
        print(pd.DataFrame(train_label).value_counts())
        print("val_label")
        print(pd.DataFrame(val_label).value_counts())

        dic_position_results.append(all_metrics['total_accuracy'])
        problem_df = pd.DataFrame(dic_position_results)
        problem_df.to_csv(os.path.join(config['pred_dir'] + '/' + problem + '.csv'))

        All_Results = np.vstack((All_Results, dic_position_results))

    All_Results_df = pd.DataFrame(All_Results)
    All_Results_df.to_csv(os.path.join(config['output_dir'], 'ConvTran_Results.csv'))
