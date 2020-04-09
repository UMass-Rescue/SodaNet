import tensorflow as tf 
from keras.models import load_model
from rectified_adam import RAdam
import numpy as np
import sys
from google_drive_downloader import GoogleDriveDownloader as g
import os
import cv2
from matplotlib.image import imread
import gdown

# Global Variables
DEFAULT_OUTPUT_SHAPE = 160

def fetch_model_file():
    base_path = os.getcwd()
    downloadable_path = os.path.join(base_path, "cokenet", "model")
    model_downloadable_path = os.path.join(downloadable_path, "AlexNet.hdf5")
    model_gdrive_url = 'https://drive.google.com/uc?id=1sAy-xarlnIu0OK6czOMCj3UMHy-0JyvJ'

    if not os.path.exists(downloadable_path):
        os.makedirs(downloadable_path, exist_ok=True)

    if os.path.isfile(model_downloadable_path) is not True:
        gdown.download(model_gdrive_url, model_downloadable_path, quiet=True)
    return

def save_to_file(file_path, dictionary, mode):
    base_path = '/'.join(file_path.split('/')[:-1])
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
    
    with open(file_path, mode) as file:
        [file.write('{0},{1}\n'.format(key, value)) for key, value in dictionary.items()]
    return

class CokeModel:
    def __init__(self, model_path='cokenet/model/AlexNet.hdf5', output_shape=DEFAULT_OUTPUT_SHAPE):
        default_model_path='cokenet/model/AlexNet.hdf5'
        google_drive_file_id = '1sAy-xarlnIu0OK6czOMCj3UMHy-0JyvJ'
        
        self.downloading_from_file = False
        self.output_shape=output_shape
        
        fetch_model_file()
        self.model = tf.keras.models.load_model(model_path, custom_objects={'RAdam': RAdam(lr=0.01)})
        
    def load_image(self, img):
        img = self.resize_image_single(img)
        if len(img.shape) == 4:
            self.img = img
        elif len(img.shape) == 3:
            self.img = img[np.newaxis, :]
        else:
            print ("Image should be an array of 3D image or a single 3D image. ")
            sys.exit(-1)
        
    def get_mapped_list(self, path):
        return [str(file) for r, _, f in os.walk(path) 
                for file in f if any(map(str(file).lower().__contains__, ['.png', '.jpg', '.jpeg']))]
        
    def load_image_from_file(self, input_path):
        self.downloading_from_file = True
        self.files = self.get_mapped_list(input_path)
        self.img = np.zeros((len(self.files), self.output_shape, self.output_shape, 3))
        for idx in range(len(self.files)):
            self.img[idx] = self.resize_image_single(imread(os.path.join(input_path, self.files[idx])))
        return self.img
    
    def resize_image_single_base(self, im_single):
        resized = cv2.resize(im_single, (self.output_shape, self.output_shape), interpolation=cv2.INTER_AREA)
        resized[resized<0] = 0
        if resized.shape == (self.output_shape, self.output_shape, 4):
            resized = resized[:, :, :3]
        return resized
            
    def resize_image_single(self, im):
        if len(im.shape) == 3:
            if im.shape == (self.output_shape, self.output_shape, 3):
                return im
            else:
                return self.resize_image_single_base(im)
        else:
            new_im = np.zeros(im.shape)
            idx = -1
            for im_single in im:
                idx += 1
                if im_single.shape == (self.output_shape, self.output_shape, 3):
                    resized = im_single
                else:
                    resized = self.resize_image_single_base(im_single)
                new_im[idx] = resized
            return new_im
                
            
    def resize_images(self):
        self.new_img = np.zeros_like(self.img).astype(np.float32)
        for i in range(self.img.shape[0]):
            self.new_img[i] = self.resize_image_single(self.img[i])
        del self.img
        return self.new_img
        
    def predict(self):
        return self.model.predict(self.img)
    
    def evaluate(self, output_csv_path='', mode='w'):
        ''' Returns 1 for coke, 0 for not coke...'''
        computed_preds = self.predict()
        if not self.downloading_from_file:
            if self.img.shape[0] == 1:
                return [np.argmax(pred) for pred in computed_preds], self.img[0]
            else:
                return [np.argmax(pred) for pred in computed_preds], self.img
        else:
            results_tray = {}
            for idx in range(len(computed_preds)):
                results_tray[self.files[idx]] = np.argmax(computed_preds[idx])
                if len(output_csv_path) > 0:
                    save_to_file(output_csv_path, results_tray, mode)
            return results_tray
