#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Created august 2019
    by Maud Parrot
    Script to perform several experiments on the model by cross validation.
    The user can chose which parameter he wants to do an experiment for (filter, alpha, batch normalization).
    The user can also chose the training base for the experiment, it can be one ore several corpus.
    For an experiment, the script evaluate the model for each value of the parameter.
    To evaluate the model, it uses a cross validation scheme :
    it leaves one speaker out of training set and test on this speaker. And this for all speakers of the training set.
    The results are then averaged over all the speakers results.
"""


import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)


from Preprocessing.tools_preprocessing import get_speakers_per_corpus
from Training.train import train_model
import numpy as np
import argparse
import csv
from datetime import date




n_epochs = 2
loss_train = "both_90"
patience = 5
select_arti = True
batch_norma = False
filter_type = "fix"
to_plot = False
lr = 0.001
delta_test = 1
corpus = ["Haskins"]
train_a_bit_on_test = False
output_dim = 18 #18 trajectories
speakers = get_speakers_per_corpus("Haskins")
config = "indep"


def cross_val(corpus_to_train_on):
    """
    performs the cross validation on corpus_to_train_on for 3 types of filter in order to evaluate the impact of the filter
    the parameters (other than typefilter) are defined above and can be modified
    the results of the experiment are printed (future work : add results in csv expliciting the experiment)
    """

    speakers = []
    for co in str(corpus_to_train_on[1:-1]).split(","):
        speakers = speakers + get_speakers_per_corpus(co)


    count = 0
    rmse_all, pearson_all = np.zeros((len(speakers), output_dim)), np.zeros((len(speakers), output_dim))
    for speaker in speakers:
        rmse, pearson = train_model(test_on=speaker, n_epochs=n_epochs, loss_train=loss_train, patience=patience,
                                    select_arti=select_arti, corpus_to_train_on=corpus_to_train_on,
                                    batch_norma=batch_norma, filter_type=filter_type, to_plot=to_plot,
                                    lr=lr, delta_test=delta_test, config=config)
        rmse_all[count, :] = rmse
        pearson_all[count, :] = pearson
        count += 1
    results_rmse = np.mean(rmse_all, axis=0)
    results_pearson = np.mean(pearson_all, axis=0)
    std_rmse = np.std(rmse_all, axis=0)
    std_pearson = np.std(pearson_all, axis=0)
    print("for filter type {} results are".format(filter_type))
    print("RMSE mean ", results_rmse)
    print("RMSE std ", std_rmse)
    print("PEARSON ", results_pearson)
    print(" PEARSON STD", std_pearson)
    today = date.today().strftime("%d/%m/%Y")
    with open('experiment_results_general.csv', 'a') as f:
        writer = csv.writer(f)
        row_rmse_mean = [today, "rmse_mean"] + results_rmse.tolist()
        row_rmse_std = [today, "rmse_std"] + std_rmse.tolist()
        row_pearson_mean = [today, "pearson_mean"] + results_pearson.tolist()
        row_pearson_std = [today, "pearson_std"] + std_pearson.tolist()
        for row in [row_rmse_mean, row_rmse_std, row_pearson_mean, row_pearson_std]:
            writer.writerow(row)


def cross_val_filter(corpus_to_train_on):
    """
    performs the cross validation on Haskins corpus for 3 types of filter in order to evaluate the impact of the filter
    the parameters (other than typefilter) are defined above and can be modified
    the results of the experiment are printed (future work : add results in csv expliciting the experiment)
    """

    speakers = []
    for co in str(corpus_to_train_on[1:-1]).split(","):
        speakers = speakers + get_speakers_per_corpus(co)

    for filter_type in ["fix","unfix","out"]:
        count = 0
        rmse_all, pearson_all = np.zeros((len(speakers), output_dim)), np.zeros((len(speakers), output_dim))
        for speaker in speakers :
            rmse, pearson = train_model(test_on=speaker, n_epochs=n_epochs, loss_train=loss_train,patience=patience,
                                        select_arti=select_arti, corpus_to_train_on=corpus_to_train_on,
                                        batch_norma=batch_norma, filter_type=filter_type, to_plot=to_plot,
                                        lr=lr, delta_test=delta_test, config=config)
            rmse_all[count, :] = rmse
            pearson_all[count, :] = pearson
            count += 1

        results_rmse = np.mean(rmse_all, axis=0)
        results_pearson = np.mean(pearson_all, axis=0)
        std_rmse = np.std(rmse_all, axis=0)
        std_pearson = np.std(pearson_all, axis=0)
        print("for filter type {} results are".format(filter_type))
        print("RMSE mean ", results_rmse)
        print("RMSE std ", std_rmse)
        print("PEARSON ", results_pearson)
        print(" PEARSON STD", std_pearson)
        today = date.today().strftime("%d/%m/%Y")
        with open('experiment_results_filter.csv', 'a') as f:
            writer = csv.writer(f)
            row_rmse_mean = [today, filter_type, "rmse_mean"] + results_rmse.tolist()
            row_rmse_std = [today, filter_type,"rmse_std"] + std_rmse.tolist()
            row_pearson_mean = [today, filter_type, "pearson_mean"] + results_pearson.tolist()
            row_pearson_std = [today, filter_type, "pearson_std"] + std_pearson.tolist()
            for row in [row_rmse_mean, row_rmse_std, row_pearson_mean, row_pearson_std]:
                writer.writerow(row)


def cross_val_bath_norma(corpus_to_train_on):
    """
    performs the cross validation on corpus_to_train_on corpus with and without batch normalization
    the parameters (other than bath_norma) are defined above and can be modified
    the results of the experiment are printed
    (future work : maybe batch norma after dense layers and not after lstm )
    """
    speakers = []
    for co in str(corpus_to_train_on[1:-1]).split(","):
        speakers = speakers + get_speakers_per_corpus(co)
    corpus_to_train_on = str(corpus)
    for batch_norma in ["True", "False"]:
        count = 0
        rmse_all, pearson_all = np.zeros((len(speakers), output_dim)), np.zeros((len(speakers), output_dim))
        for speaker in speakers :
            rmse, pearson = train_model(test_on=speaker, n_epochs=n_epochs, loss_train=loss_train, patience=patience,
                                        select_arti=select_arti, corpus_to_train_on=corpus_to_train_on,
                                        batch_norma=batch_norma, filter_type=filter_type, to_plot=to_plot,
                                        lr=lr, delta_test=delta_test, config=config)
            rmse_all[count,:] = rmse
            pearson_all[count,:]= pearson
            count += 1
        results_rmse = np.mean(rmse_all, axis=0)
        results_pearson = np.mean(pearson_all, axis=0)
        std_rmse = np.std(rmse_all, axis=0)
        std_pearson = np.std(pearson_all, axis=0)
        print("for filter type {} results are".format(filter_type))
        print("RMSE mean ", results_rmse)
        print("RMSE std ", std_rmse)
        print("PEARSON ", results_pearson)
        print(" PEARSON STD", std_pearson)
        today = date.today().strftime("%d/%m/%Y")
        with open('experiment_results_batchnorma.csv', 'a') as f:
            writer = csv.writer(f)
            row_rmse_mean = [today, batch_norma, "rmse_mean"] + results_rmse.tolist()
            row_rmse_std = [today, batch_norma, "rmse_std"] + std_rmse.tolist()
            row_pearson_mean = [today, batch_norma, "pearson_mean"] + results_pearson.tolist()
            row_pearson_std = [today, batch_norma, "pearson_mean"] + std_pearson.tolist()
            for row in [row_rmse_mean, row_rmse_std, row_pearson_mean, row_pearson_std]:
                writer.writerow(row)


def cross_val_for_alpha(corpus_to_train_on):
    """
        performs the cross validation on corpus_to_train_on corpus for different values of alpha in the combined loss
        experiment to determine the optimal alpha
        the parameters (other than alpha) are defined above and can be modified
        the results of the experiment are printed
        """
    for alpha in [0, 20, 40, 60, 80, 100]:
        count = 0
        loss_train = "both_" + str(alpha)
        rmse_all, pearson_all = np.zeros((len(speakers), output_dim)), np.zeros((len(speakers), output_dim))
        for speaker in speakers:
            rmse, pearson = train_model(test_on=speaker, n_epochs=n_epochs, loss_train=loss_train, patience=patience,
                                        select_arti=select_arti, corpus_to_train_on=corpus_to_train_on,
                                        batch_norma=batch_norma, filter_type=filter_type, to_plot=to_plot,
                                        lr=lr, delta_test=delta_test, config=config)
            rmse_all[count, :] = rmse
            pearson_all[count, :] = pearson
            count += 1

        results_rmse = np.mean(rmse_all, axis=0)
        results_pearson = np.mean(pearson_all, axis=0)
        std_rmse = np.std(rmse_all, axis=0)
        std_pearson = np.std(pearson_all, axis=0)
        print("for filter type {} results are".format(filter_type))
        print("RMSE mean ", results_rmse)
        print("RMSE std ", std_rmse)
        print("PEARSON ", results_pearson)
        print(" PEARSON STD", std_pearson)
        today = date.today().strftime("%d/%m/%Y")
        with open('experiment_results_alpha.csv', 'a') as f:
            writer = csv.writer(f)
            row_rmse_mean = [today, alpha, "rmse_mean"] + results_rmse.tolist()
            row_rmse_std = [today, alpha, "rmse_std"] + std_rmse.tolist()
            row_pearson_mean = [today, alpha, "pearson_mean"] + results_pearson.tolist()
            row_pearson_std = [today, alpha, "pearson_std"] + std_pearson.tolist()
            for row in [row_rmse_mean, row_rmse_std, row_pearson_mean, row_pearson_std]:
                writer.writerow(row)

if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Experiment on the asked corpus by cross validation')
    parser.add_argument('corpus_exp', type=str,
                        help='list of corpus on which perform the experiment')

    parser.add_argument('experiment', type=str,
                        help='type of experiment (filter alpha or bn)')

    args = parser.parse_args()

    if args.experiment == "general" :
        cross_val(args.corpus_exp)

    elif args.experiment == "filter":
        cross_val_filter(args.corpus_exp)

    elif args.experiment == "alpha":
        cross_val_for_alpha(args.corpus_exp)

    elif args.experiment == "bn":
        cross_val_bath_norma(args.corpus_exp)

