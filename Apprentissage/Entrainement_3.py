import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from Apprentissage.class_network import my_bilstm
from Apprentissage.modele import my_ac2art_modele
import sys
import torch
import os
import csv
import sys
from sklearn.model_selection import train_test_split
from Apprentissage.utils import load_filenames, load_data, load_filenames_deter
from Apprentissage.pytorchtools import EarlyStopping
import time
import random
from os.path import dirname
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import scipy
from os import listdir
#from logger import Logger
import json


root_folder = os.path.dirname(os.getcwd())
fileset_path = os.path.join(root_folder, "Donnees_pretraitees", "fileset")

print(sys.argv)

def train_model(test_on ,n_epochs ,delta_test ,patience ,lr=0.09,to_plot=False,select_arti=False,only_on_corpus=True):
    data_filtered=True
    modele_filtered=True
    train_on =  ["F01","F02","F03","F04","M01","M02","M03","M04","F1","F5","M1",
                 "M3","maps0","faet0",'mjjn0',"falh0","ffes0","fsew0","msak0","MNGU0"]

    if only_on_corpus :
        if test_on in ["F01","F02","F03","F04","M01","M02","M03","M04"]:
            train_on = ["F01","F02","F03","F04","M01","M02","M03","M04"]

        elif test_on in ["F1","F5","M1","M3"]:
            train_on = ["F1","M1","M3"]

        elif test_on in ["maps0","faet0",'mjjn0',"falh0","ffes0","fsew0","msak0"]:
            train_on = ["maps0","faet0",'mjjn0',"falh0","ffes0","fsew0","msak0"]

    train_on.remove(test_on)
    print("train_on :",train_on)
    print("test on:",test_on)

    cuda_avail = torch.cuda.is_available()
    print(" cuda ?", cuda_avail)
    output_dim = 18

    name_file = "test_on_" + test_on+"_idx_"+str(select_arti)+"_onlycorpus_"+str(only_on_corpus)
    print("name file : ",name_file)
#   logger = Logger('./log_' + name_file)

    hidden_dim = 300
    input_dim = 429
    batch_size = 10
    print("batch size",batch_size)

    early_stopping = EarlyStopping(name_file,patience=patience, verbose=True)

    # model = my_bilstm(hidden_dim=hidden_dim,input_dim=input_dim,name_file =name_file, output_dim=output_dim,
   #                   batch_size=batch_size,data_filtered=data_filtered,cuda_avail = cuda_avail,modele_filtered=modele_filtered)
    model = my_ac2art_modele(hidden_dim=hidden_dim, input_dim=input_dim, name_file=name_file, output_dim=output_dim,
                      batch_size=batch_size, data_filtered=data_filtered, cuda_avail=cuda_avail,
                      modele_filtered=modele_filtered)

    model = model.double()

   # try :
    file_weights = os.path.join("saved_models", name_file +".txt")
    if not os.path.exists(file_weights):
        print("premiere fois que ce modèle est crée")
        file_weights = os.path.join("saved_models","modele_preentrainement.txt")

    if not cuda_avail:
        loaded_state = torch.load(file_weights, map_location=torch.device('cpu'))

    else :
        cuda2 = torch.device('cuda:1')
        loaded_state = torch.load( file_weights , map_location= cuda2 )
    model_dict = model.state_dict()
    loaded_state = {k: v for k, v in loaded_state.items() if
                    k in model_dict}  # only layers param that are in our current model
    #print("before ", len(loaded_state), loaded_state.keys())
    loaded_state = {k: v for k, v in loaded_state.items() if
                    loaded_state[k].shape == model_dict[k].shape}  # only if layers have correct shapes
    #print("after", len(loaded_state), loaded_state.keys())
    model_dict.update(loaded_state)
    model.load_state_dict(model_dict)

    if cuda_avail:
        model = model.cuda(device=cuda2)

    def criterion_pearson(my_y,my_y_pred): # (L,K,13)
        y_1 = my_y - torch.mean(my_y,dim=1,keepdim=True)
        y_pred_1 = my_y_pred - torch.mean(my_y_pred,dim=1,keepdim=True)
        nume=  torch.sum(y_1* y_pred_1,dim=1,keepdim=True) # y*y_pred multi terme à terme puis on somme pour avoir (L,1,13)
      #pour chaque trajectoire on somme le produit de la vriae et de la predite
        deno =  torch.sqrt(torch.sum(y_1 ** 2,dim=1,keepdim=True)) * torch.sqrt(torch.sum(y_pred_1 ** 2,dim=1,keepdim=True))# use Pearson correlation
        # deno zero veut dire ema constant à 0 on remplace par des 1
        minim = torch.tensor(0.01,dtype=torch.float64)
        if cuda_avail:
            minim = minim.to(device=cuda2)
            deno = deno.to(device=cuda2)
            nume = nume.to(device=cuda2)
        deno = torch.max(deno,minim)
        my_loss = nume/deno
        my_loss = torch.sum(my_loss) #pearson doit etre le plus grand possible
        #loss = torch.div(loss, torch.tensor(y.shape[2],dtype=torch.float64)) # correlation moyenne par arti
        return -my_loss
    criterion = criterion_pearson

    with open('categ_of_speakers.json', 'r') as fp:
        categ_of_speakers = json.load(fp) #dictionnaire en clé la categorie en valeur un dictionnaire
                                            # #avec les speakers dans la catégorie et les arti concernées par cette categorie

    optimizer = torch.optim.Adam(model.parameters(), lr=lr ) #, betas = beta_param)

    plt.ioff()
    print("number of epochs : ", n_epochs)

    path_files = os.path.join(os.path.dirname(os.getcwd()),"Donnees_pretraitees","fileset")

    files_for_train = load_filenames_deter(train_on, part=["train", "test"])
    print("len files for train",len(files_for_train))
    files_for_valid = load_filenames_deter(train_on, part=["valid"])
    print("lenfiles for valid",len(files_for_valid))

    files_for_test = load_filenames_deter([test_on], part=["train", "valid", "test"])
    print("len files for test",len(files_for_test))

    files_per_categ = dict()
    for categ in categ_of_speakers.keys():
        sp_in_categ = categ_of_speakers[categ]["sp"]
        sp_in_categ = [sp for sp in sp_in_categ if sp in train_on]
        # fichiers qui appartiennent à la categorie car le nom du speaker apparait touojurs dans le nom du fichier
        files_train_this_categ = [[f for f in files_for_train if sp.lower() in f ]for sp in sp_in_categ]
        files_train_this_categ = [item for sublist in files_train_this_categ for item in sublist] # flatten la liste de liste

        files_valid_this_categ = [[f for f in files_for_valid if sp.lower() in f] for sp in sp_in_categ]
        files_valid_this_categ = [item for sublist in files_valid_this_categ for item in sublist]  # flatten la liste de liste

        if len(files_train_this_categ) > 0 : #meaning we have at least one file in this categ
            files_per_categ[categ] = dict()
            N_iter_categ = int(len(files_train_this_categ)/batch_size)+1         # on veut qu'il y a en ait un multiple du batch size , on en double certains
            n_a_ajouter = batch_size*N_iter_categ - len(files_train_this_categ) #si 14 element N_iter_categ vaut 2 et n_a_ajouter vaut 6
            print("files train this categ",len(files_train_this_categ))
            print("Nitercateg",N_iter_categ)
            print("n a ajouter",n_a_ajouter)
            files_train_this_categ = files_train_this_categ + files_train_this_categ[:n_a_ajouter] #nbr de fichier par categorie multiple du batch size
            random.shuffle(files_train_this_categ)
            files_per_categ[categ]["train"] = files_train_this_categ
            print("finalement ",len(files_train_this_categ))
            N_iter_categ = int(len(  files_valid_this_categ) / batch_size) + 1  # on veut qu'il y a en ait un multiple du batch size , on en double certains
            n_a_ajouter = batch_size * N_iter_categ - len(files_valid_this_categ)  # si 14 element N_iter_categ vaut 2 et n_a_ajouter vaut 6
            files_valid_this_categ = files_valid_this_categ + files_valid_this_categ[:n_a_ajouter] # nbr de fichier par categorie multiple du batch size
            random.shuffle(files_valid_this_categ)
            files_per_categ[categ]["valid"] = files_valid_this_categ
            print("files valid this categ", len(files_valid_this_categ))
            print("Nitercateg", N_iter_categ)
            print("n a ajouter", n_a_ajouter)
    categs_to_consider = files_per_categ.keys()
    for epoch in range(n_epochs):
        #random.shuffle(files_for_train)
        random.shuffle(list(categs_to_consider))
        for categ in categs_to_consider:  # de A à F pour le moment
            print("categ ", categ)
            files_this_categ_courant = files_per_categ[categ]["train"] #on na pas encore apprit dessus au cours de cette epoch
            arti_to_consider = categ_of_speakers[categ]["arti"] #liste de 18 0/1 qui indique les arti à considérer
            idx_to_consider = [i for i,n in enumerate(arti_to_consider) if n=="1"]
            print("n train dans categ",len(files_this_categ_courant))


            while len(files_this_categ_courant) > 0:
                x, y = load_data(files_this_categ_courant[:batch_size], filtered=data_filtered,VT=True)
                x, y = model.prepare_batch(x, y)
                y_pred = model(x).double()
                torch.cuda.empty_cache()
                if cuda_avail:
                    # y_pred = y_pred.cuda()
                    y_pred = y_pred.to(device=cuda2)
                y = y.double()
                optimizer.zero_grad()
                loss = criterion(y, y_pred)
                loss.backward()
                optimizer.step()
                files_this_categ_courant = files_this_categ_courant[batch_size:] #we a re going to train on this 10 files

        if epoch%delta_test ==0:  #toutes les delta_test epochs on évalue le modèle sur validation et on sauvegarde le modele si le score est meilleur
            print("evaluation validation")
            loss_vali = 0
            for categ in files_per_categ.keys():  # de A à F pour le moment
                print("categ ,",categ)
                files_this_categ_courant = files_per_categ[categ]["valid"]  # on na pas encore apprit dessus au cours de cette epoch
                arti_to_consider = categ_of_speakers[categ]["arti"]  # liste de 18 0/1 qui indique les arti à considérer
                idx_to_consider = [i for i, n in enumerate(arti_to_consider) if n == "1"]
                while len(files_this_categ_courant) >0 :
                    x, y = load_data(files_this_categ_courant[:batch_size], filtered=data_filtered,VT=True)
                    x, y = model.prepare_batch(x, y)
                    y_pred = model(x).double()
                    torch.cuda.empty_cache()
                    if cuda_avail:
                        y_pred = y_pred.to(device=cuda2)
                    y = y.double()  # (Batchsize, maxL, 18)
                    if select_arti:
                        y = y[:, :, idx_to_consider]
                        y_pred = y_pred[:, :, idx_to_consider]
                    loss_courant = criterion(y, y_pred)
                    loss_vali += loss_courant.item()
                    files_this_categ_courant = files_this_categ_courant[batch_size:]  # on a appris sur ces 10 phrases

            loss_vali = loss_vali
            model.all_validation_loss.append(loss_vali)
            model.all_training_loss.append(loss)

            if epoch>0:
                if loss_vali > model.all_validation_loss[-1]:
                    for param_group in optimizer.param_groups:
                        param_group['lr'] = param_group['lr'] / 2
                        print(param_group["lr"])
                        patience_temp=0

            #model.all_test_loss += [model.all_test_loss[-1]] * (epoch+previous_epoch - len(model.all_test_loss))
            print("\n ---------- epoch" + str(epoch) + " ---------")
            #early_stopping.epoch = previous_epoch+epoch
            early_stopping(loss_vali, model)
            print("train loss ", loss.item())
            print("valid loss ", loss_vali)

         #   logger.scalar_summary('loss_valid', loss_vali,
          #                        model.epoch_ref)
           # logger.scalar_summary('loss_train', loss.item(), model.epoch_ref)

            torch.cuda.empty_cache()

        if early_stopping.early_stop:
            print("Early stopping")
            break

    if n_epochs>0:
        model.load_state_dict(torch.load(os.path.join("saved_models",name_file+'.pt')))
        torch.save(model.state_dict(), os.path.join( "saved_models",name_file+".txt"))

    random.shuffle(files_for_test)
    x, y = load_data(files_for_test)
    print("evaluation on speaker {}".format(test_on))
    std_speaker=  np.load(os.path.join(root_folder, "Traitement", "norm_values","std_ema_"+test_on+".npy"))
    model.evaluate_on_test(criterion=criterion,verbose=True, X_test=x, Y_test=y,
                           to_plot=to_plot, std_ema=max(std_speaker), suffix=test_on)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Train and save a model.')
    parser.add_argument('test_on', metavar='test_on', type=str,
                        help='the speaker we want to test on')

    parser.add_argument('n_epochs', metavar='n_epochs', type=int,
                        help='max number of epochs to train the model')
    parser.add_argument('delta_test', metavar='delta_test', type=int,
                        help='interval between two validation evaluation')
    parser.add_argument('patience', metavar='patience', type=int,
                        help='number of iterations in a row with decreasing validation score before stopping the train ')
    parser.add_argument('lr', metavar='lr', type=str,
                        help='learning rate of Adam optimizer ')
    parser.add_argument('to_plot', metavar='to_plot', type=bool,
                        help='si true plot les resultats sur le test')

    parser.add_argument('select_arti', metavar='select_arti', type=bool,
                        help='ssi dans la retropro on ne considere que les arti bons')

    parser.add_argument('only_on_corpus', metavar='only_on_corpus', type=bool,
                        help='ssi dans la retropro on ne considere que les arti bons')

    args = parser.parse_args()
    test_on =  sys.argv[1]
    n_epochs = int(sys.argv[2])
    delta_test = int(sys.argv[3])
    patience = int(sys.argv[4])
    lr = float(sys.argv[5])
    to_plot = sys.argv[6].lower()=="true"
    select_arti = sys.argv[7].lower()=="true"
    only_on_corpus = sys.argv[8].lower()=="true"

    train_model(test_on = test_on,n_epochs=n_epochs,delta_test=delta_test,patience=patience,
                lr = lr,to_plot=to_plot,select_arti=select_arti,only_on_corpus = only_on_corpus)