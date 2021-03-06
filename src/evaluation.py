#!/usr/bin/env python
# coding: utf-8

import torch
import os
import utils
from wrapper_datasets import create_dataset
from model_zoo.models_resnet8 import resnet8, resnet8_MCDO
from eval_utils import random_regression_baseline, constant_baseline, \
                       evaluate_regression
from opts import parser


# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def main(FLAGS):
    # Hyperparameters
    batch_size = FLAGS.batch_size # Default 32

    # Loading testing dataset
    test_steer_dataset = create_dataset(FLAGS.test_dir)
    
    test_loader = torch.utils.data.DataLoader(dataset=test_steer_dataset,
                                                batch_size=batch_size,
                                                shuffle=False)
    
    # Cropped image dimensions
    crop_img_width, crop_img_height = FLAGS.crop_img_width, FLAGS.crop_img_height
    # Image mode
    if FLAGS.img_mode=='rgb':
        img_channels = 3
    elif FLAGS.img_mode == 'grayscale':
        img_channels = 1
    else:
        raise IOError("Unidentified image mode: use 'grayscale' or 'rgb'")
    
    # Output dimension
    output_dim = 1
    
    if FLAGS.model_to_test=='resnet8_MCDO':
        model = resnet8_MCDO(img_channels, crop_img_height, crop_img_width, 
                        output_dim).to(device)
        model_ckpt = os.path.join(FLAGS.experiment_rootdir,'resnet8_MCDO.pt')
        model.load_state_dict(torch.load(model_ckpt))
    elif 'resnet8':
        model = resnet8(img_channels, crop_img_height, crop_img_width, 
                             output_dim).to(device)
        model_ckpt = os.path.join(FLAGS.experiment_rootdir,'resnet8.pt')
        model.load_state_dict(torch.load(model_ckpt))
    else:
        raise IOError("Model to test must be 'resnet8' or 'resnet8_MCDO'.")
    

    # Get predictions and ground truth

    _, pred_steerings, real_steerings, epistemic_variance = utils.compute_predictions_and_gt(
            model, test_loader, device, FLAGS)

    # ************************* Steering evaluation ***************************
    
    # Compute random and constant baselines for steerings
    random_steerings = random_regression_baseline(real_steerings)
    constant_steerings = constant_baseline(real_steerings)

    # Create dictionary with filenames
    dict_fname = {'test_regression.json': pred_steerings,
                  'random_regression.json': random_steerings,
                  'constant_regression.json': constant_steerings}
    
    # Create the folder for current experiment settings if not already there
    if FLAGS.is_MCDO: 
        parsed_exp_path = os.path.join(FLAGS.experiment_rootdir, "MCDO_T{}".format(FLAGS.T))
    else: 
        parsed_exp_path = os.path.join(FLAGS.experiment_rootdir, "standard")
    if not os.path.exists(parsed_exp_path):
        os.makedirs(parsed_exp_path)
    
    # Evaluate predictions: EVA, residuals, and highest errors
    for fname, pred in dict_fname.items():
        abs_fname = os.path.join(parsed_exp_path, fname)
        evaluate_regression(pred, real_steerings, abs_fname)

    if epistemic_variance is not None:
        dictionary = {"epistemic_variances": epistemic_variance.tolist()}
        utils.write_to_file(dictionary, os.path.join(parsed_exp_path,
                                                   'epistemic_variances.json'))
        
    # Write predicted and real steerings
    dict_test = {'pred_steerings': pred_steerings.tolist(),
                 'real_steerings': real_steerings.tolist()}
    utils.write_to_file(dict_test,os.path.join(parsed_exp_path,
                                               'predicted_and_real_steerings.json'))


if __name__ == "__main__":
    FLAGS = parser.parse_args()
    main(FLAGS)
