import numpy as np
import matplotlib.pyplot as plt
# get_ipython().run_line_magic('matplotlib', 'notebook')
import math
import time
import sigpy as sp
import sigpy.mri as mr
import sigpy.plot as pl
import scipy.io as sio
from ismrmrdtools import show, transform
# import ReadWrapper
import read_ocmr as read
import h5py
import sys
import os
import torch
# In[2]:


class Recon(sp.app.App):
    def __init__(self, ksp, mask, mps):
        img_shape = mps.shape[1:]

        S = sp.linop.Multiply(img_shape, mps)
        F = sp.linop.FFT(ksp.shape, axes=(-1, -2))
        P = sp.linop.Multiply(ksp.shape, mask)
       # self.W = sp.linop.Wavelet(img_shape)
        A = P * F *S  

        IF = sp.linop.IFFT(img_shape,mps)
        AH = A*IF

    def _output(self):
        return AH
def recon(ksp,mask,mps):
    F = np.fft.fft2(ksp)
    P = np.multiply(F,mask)
    S = np.multiply(F,mps)
    A = np.fft.ifft2(S)
    return A
def make_mask(N, down_rate, center_rows):
    mask = torch.zeros((N, N), dtype=torch.bool)
    mask[::down_rate, :] = True
    mask[mask.shape[0]//2-center_rows//2:mask.shape[0]//2+center_rows//2, :] = True
    return mask
def MRI(im, mask=None):
    """
    returns Fourier samples of im
    """

    y = torch.rfft(im, 2, onesided=False, normalized=True)  # compute a DFT
    y = y.roll(tuple(n//2 for n in y.shape[:2]), dims=(0,1))  # move the center frequency to the center of the image
    if mask is not None:  # apply a sampling mask if one is supplied (used in a later question)
        y[~mask, :] = 0
    return y


def MRI_inv(y):
    """
    returns the inverse DFT of the k-space samples in y, so that MRI_inv(MRI(im)) = im
    """

    y = y.roll(tuple(-(n//2) for n in y.shape[:2]), dims=(0,1))  # move the center frequency back to the upper left corner

    im = torch.irfft(y, 2, onesided=False, normalized=True)  # undo the DFT

    return im
def make_vdrs_mask(N1,N2,nlines,init_lines):
    # Setting Variable Density Random Sampling (VDRS) mask
    mask_vdrs=np.zeros((N1,N2),dtype='bool')
    mask_vdrs[:,int(0.5*(N2-init_lines)):int(0.5*(N2+init_lines))]=True
    nlinesout=int(0.5*(nlines-init_lines))
    rng = np.random.default_rng()
    t1 = rng.choice(int(0.5*(N2-init_lines))-1, size=nlinesout, replace=False)
    t2 = rng.choice(np.arange(int(0.5*(N2+init_lines))+1, N2), size=nlinesout, replace=False)
    mask_vdrs[:,t1]=True; mask_vdrs[:,t2]=True
    return mask_vdrs
# In[ ]:
#fastMRI_path = '/mnt/shared_b/data/fastMRI/singlecoil_train/'
#sys.path.append(fastMRI_path)
#os.chdir(fastMRI_path)
#filename2 = 'file1000001.h5'
#f1 = h5py.File(filename2, 'r')



#file1 = open('/mnt/shared_b/data/fastMRI/singlecoil_train', 'r')
#Lines = file1.readlines()
# Lines = Lines[1:-1]
count=0;
#nFiles=53; # Total files to be read
filenames=[]
N = 320  # image size
#down_rate = 3
#center_rows = 15
#mask =make_mask(N, down_rate, center_rows)
#mask = make_vdrs_mask(x1.shape[0],x2.shape[1],40,30)
#mask = torch.from_numpy(mask)
#mask_GT = mask.numpy()
filename='/mnt/shared_b/data/fastMRI/singlecoil_train/'
#file1 = '/mnt/shared_b/data/OCMR/ocmr_cine/'
# filename = filename[:-1] # Removing newline character
arr = os.listdir(filename)
#filenames.append(arr)
print(arr)

for i in range(15,16):#Lines:
    print(i)
    count=count+1
    filename1 = arr[i]
    f = h5py.File(os.path.join(filename,filename1), 'r') 

    # f = h5py.File(filename2, 'r')
    kData= f['reconstruction_esc'] #actually data after ifft from kspace
    print('Dimension of kData:',kData)#.shape)

          
    # kspace_dim': {'kx ky kz coil phase set slice rep avg'}

    N1=kData.shape[1]
    N2=kData.shape[2]
    Nt=kData.shape[0]
    x_GT=np.zeros((Nt,N1,N2),dtype='complex')
    #error=np.zeros((Nt,N1,N2),dtype='complex')
    x_reconstruct=np.zeros((Nt,N1,N2),dtype='complex')
    #mask = make_vdrs_mask(N1,N2,54,26)
    mask = make_vdrs_mask(N1,N2,27,13)
    mask = torch.from_numpy(mask)

    for phase in range(0,Nt):
        y= kData[phase,:,:] # Fully sampled k-space data for a particular time instance
        print('Testing for phase =',phase, 'with k-space data dimension: ',y.shape)

       # mask_GT=np.ones((N1,N2))
       # init_lines =58
       # mask_middle = mask_GT[int(0.5*(N1-init_lines)):int(0.5*(N1+init_lines)),:]=True
        ksp=y #np.moveaxis(y, -1, 0) # Reaaranging axes: Loading k-space data in sigpy format
        #mps = mr.app.EspiritCalib(ksp).run()
       # mps1 = np.ones_like(mask_GT)
        # lamda = 0
           # max_iter = 5
        recon = torch.from_numpy(ksp)
        recon = torch.abs(recon)
        recon = MRI(recon,mask)
        recon = MRI_inv(recon)
        x_reconstruct[phase,:,:]= recon.numpy()
        x_GT[phase,:,:]= ksp
       # error[phase,:,:] = x_GT[phase,:,:]-x_reconstruct[phase,:,:]


       
                       #print(x_GT[phase,:,:]-x_reconstruct[phase,:,:])

        
    np.savez(os.path.join('..','MRI_descattering','GT_image_8_fold','x_GT'+str(i)+'.npz'),x_GT)

    #np.savez(os.path.join('..','MRI_descattering','ER_image','error'+str(i)+'.npz'),error)
    np.savez(os.path.join('..','MRI_descattering','RC_image_8_fold','RC_image_4_fold'+str(0)+str(i)+'.npz'),x_reconstruct)

    
    
    
    
    
    
    
    
    
    

    
