import pandas as pd
import os
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from PIL import Image
from torchvision.datasets import ImageFolder
from torchvision.transforms import ToTensor

import torch
from skimage import io, transform
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils

# Ignore warnings
import warnings
warnings.filterwarnings("ignore")

plt.ion() 
class LabelAttribution:

    def __init__(self, path_image_google, path_mask_google, path_image_ign, path_mask_ign,
                 path_metadata,
                 colonne_identifiant,
                 path_export_train_test,
                 use_img_google=True,
                 use_img_ign=False
                 ):

        self.path_image_google=path_image_google
        self.path_mask_google=path_mask_google

        self.path_image_ign=path_image_ign
        self.path_mask_ign=path_mask_ign

        self.path_metadata=path_metadata
        self.colonne_identifiant=colonne_identifiant
        self.path_export_train_test=path_export_train_test

        self.use_img_google=use_img_google
        self.use_img_ign=use_img_ign
    
    def run(self):

        annotations_file=pd.read_csv(self.path_metadata)


        #création d'une fonction pour récupérer les noms d'un dossier

        def f(path):
            dirs = os.listdir(path) #on définit le directory d'où on souhaite extraire le nom des fichiers
            return [file.replace('.png','') for file in dirs]
        
        # On récupère tous les noms des images Google et IGN

        images = f(self.path_image_google) + f(self.path_image_ign)

        im_google = f(self.path_image_google)
        im_ign = f(self.path_image_ign)

        im_mask_google = f(self.path_mask_google)
        im_mask_ign = f(self.path_mask_ign)

        #### Conversion en DF
        im = pd.DataFrame (images, columns = [self.colonne_identifiant])

        im_google = pd.DataFrame (im_google, columns = [self.colonne_identifiant])
        im_ign = pd.DataFrame (im_ign, columns = [self.colonne_identifiant])

        im_mask_google = pd.DataFrame (im_mask_google, columns = [self.colonne_identifiant])
        im_mask_ign = pd.DataFrame (im_mask_ign, columns = [self.colonne_identifiant])

        #On label '1' toutes les images comportant un masque et 0 sinon
        im['Label'] = im[self.colonne_identifiant].isin(im_mask_ign[self.colonne_identifiant].append(im_mask_google[self.colonne_identifiant])).astype(int)

        #On label '1' toutes les images Google et '0' sinon
        im['L_Google'] = im[self.colonne_identifiant].isin(im_google[self.colonne_identifiant]).astype(int)

        #On label '1' toutes les images IGN et '0' sinon
        im['L_IGN'] = im[self.colonne_identifiant].isin(im_ign[self.colonne_identifiant]).astype(int)


        if (self.use_img_ign==False)&(self.use_img_google==True):
        #On ne garde que les images Google
               im = im.drop(im[im.L_Google<1].index) #on supprime les images IGN sans équivalent Google


        
        elif (self.use_img_ign==True)&(self.use_img_google==False):
        #On ne garde que les images IGN
                im = im.drop(im[im.L_IGN<1].index) #on supprime les images Google sans équivalent IGN

        #Sinon garde toutes les images

        #On sait que beaucoup d'images Google ont leur équivalent IGN (échelle différente) 
        #On ne garde donc qu'un seul nom (comme sur le fichier metadata)

        im = im.drop_duplicates()

        df = pd.merge(annotations_file, im, how="outer", on=[self.colonne_identifiant]) #cette partie de script ne récupère que les noms déjà présents dans la base

        #On ne garde que l'identifiant et les labels

        df= df[[self.colonne_identifiant, 'Label']]
        df[self.colonne_identifiant] = df[self.colonne_identifiant].astype(str) + '.png' #on rajoute les extensions pour que le dataloader récupère les fichiers

        #On sépare le dataset en un training dataset et un test dataset avec sci-kit learn

        train_df, test_df = train_test_split(df, test_size=0.2, random_state=0)

        train_df.to_csv(self.path_export_train_test+'/'+'train_data.csv', index=False)
        test_df.to_csv(self.path_export_train_test+'/'+'test_data.csv', index=False)


class CustomImageDataset(Dataset):
    def __init__(self, csv_dir, img_dir, transform=None, target_transform=None, resize=None):
        self.img_labels = pd.read_csv(csv_dir)
        self.img_dir = img_dir
        self.transform = transform
        self.target_transform = target_transform
        self.resize=resize

    def __len__(self):
        return len(self.img_labels)

    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.img_labels.iloc[idx, 0])
        #image = read_image(img_path)
        image = Image.open(img_path).convert('RGB') #Yanis
        label = self.img_labels.iloc[idx, 1]

        if self.resize:
             image=image.resize(self.resize)
        if self.transform:
            image = self.transform(image)
            
        if self.target_transform:
            label = self.target_transform(label)
        return image, label

def mean_std(loader):
  images, lebels = next(iter(loader))
  # shape of images = [b,c,w,h]
  mean, std = images.mean([0,2,3]), images.std([0,2,3])
  return mean, std

def batch_mean_and_sd(loader):
    
    cnt = 0
    fst_moment = torch.empty(3)
    snd_moment = torch.empty(3)

    for images, _ in loader:
        b, c, h, w = images.shape
        nb_pixels = b * h * w
        sum_ = torch.sum(images, dim=[0, 2, 3])
        sum_of_square = torch.sum(images ** 2,
                                  dim=[0, 2, 3])
        fst_moment = (cnt * fst_moment + sum_) / (
                      cnt + nb_pixels)
        snd_moment = (cnt * snd_moment + sum_of_square) / (
                            cnt + nb_pixels)
        cnt += nb_pixels

    mean, std = fst_moment, torch.sqrt(
    snd_moment - fst_moment ** 2)        
    return mean,std
# Dataset with flipping tranformations

def vflip(tensor):
    """Flips tensor vertically.
    """
    tensor = tensor.flip(1)
    return tensor


def hflip(tensor):
    """Flips tensor horizontally.
    """
    tensor = tensor.flip(2)
    return tensor
