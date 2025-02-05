

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import mne
import pandas as pd
import sys
import stat
import subprocess
import scipy.stats
import xarray as xr
import physio
import paramiko
import getpass
import cv2
import statsmodels
#install netcdf4

import neurokit2 as nk

from n00_config_params import *


debug = False




########################################
######## SURFACE LAPLACIAN ########
########################################


#raw, leg_order, m, smoothing = raw, 4, 50, 1e-5
def surface_laplacian(raw, leg_order, m, smoothing):
    """
    This function attempts to compute the surface laplacian transform to an mne Epochs object. The 
    algorithm follows the formulations of Perrin et al. (1989) and it consists for the most part in a 
    nearly-literal translation of Mike X Cohen's 'Analyzing neural time series data' corresponding MATLAB 
    code (2014).
    
    INPUTS are:
        - raw: raw mne object with  data(chan,sig)
        - leg_order: maximum order of the Legendre polynomial
        - m: smothness parameter for G and H
        - smoothing: smothness parameter for the diagonal of G
        - montage: montage to reconstruct the transformed Epochs object (same as in raw data import)
        
    OUTPUTS are:
        - raw_lap: surface laplacian transform of the original raw object
        
    References:
        - Perrin, F., Pernier, J., Bertrand, O. & Echallier, J.F. (1989). Spherical splines for scalp 
          potential and current density mapping. Electroencephalography and clinical Neurophysiology, 72, 
          184-187.
        - Cohen, M.X. (2014). Surface Laplacian In Analyzing neural time series data: theory and practice 
          (pp. 275-290). London, England: The MIT Press.
    """
    # import libraries
    import numpy as np
    from scipy import special
    import math
    import mne
    
    # get electrodes positions
    locs = raw._get_channel_positions()

    x = locs[:,0]
    y = locs[:,1]
    z = locs[:,2]

    # arrange data
    data = raw.get_data() # data
    orig_data_size = np.squeeze(data.shape)

    numelectrodes = len(x)
    
    # normalize cartesian coordenates to sphere unit
    def cart2sph(x, y, z):
        hxy = np.hypot(x, y)
        r = np.hypot(hxy, z)
        el = np.arctan2(z, hxy)
        az = np.arctan2(y, x)
        return az, el, r

    junk1, junk2, spherical_radii = cart2sph(x,y,z)
    maxrad = np.max(spherical_radii)
    x = x/maxrad
    y = y/maxrad
    z = z/maxrad
    
    # compute cousine distance between all pairs of electrodes
    cosdist = np.zeros((numelectrodes, numelectrodes))
    for i in range(numelectrodes):
        for j in range(i+1,numelectrodes):
            cosdist[i,j] = 1 - (((x[i] - x[j])**2 + (y[i] - y[j])**2 + (z[i] - z[j])**2)/2)

    cosdist = cosdist + cosdist.T + np.identity(numelectrodes)

    # get legendre polynomials
    legpoly = np.zeros((leg_order, numelectrodes, numelectrodes))
    for ni in range(leg_order):
        for i in range(numelectrodes):
            for j in range(i+1, numelectrodes):
                #temp = special.lpn(8,cosdist[0,1])[0][8]
                legpoly[ni,i,j] = special.lpn(ni+1,cosdist[i,j])[0][ni+1]

    legpoly = legpoly + np.transpose(legpoly,(0,2,1))

    for i in range(leg_order):
        legpoly[i,:,:] = legpoly[i,:,:] + np.identity(numelectrodes)

    # compute G and H matrixes
    twoN1 = np.multiply(2, range(1, leg_order+1))+1
    gdenom = np.power(np.multiply(range(1, leg_order+1), range(2, leg_order+2)), m, dtype=float)
    hdenom = np.power(np.multiply(range(1, leg_order+1), range(2, leg_order+2)), m-1, dtype=float)

    G = np.zeros((numelectrodes, numelectrodes))
    H = np.zeros((numelectrodes, numelectrodes))

    for i in range(numelectrodes):
        for j in range(i, numelectrodes):

            g = 0
            h = 0

            for ni in range(leg_order):
                g = g + (twoN1[ni] * legpoly[ni,i,j]) / gdenom[ni]
                h = h - (twoN1[ni] * legpoly[ni,i,j]) / hdenom[ni]

            G[i,j] = g / (4*np.pi)
            H[i,j] = -h / (4*np.pi)

    G = G + G.T
    H = H + H.T

    G = G - np.identity(numelectrodes) * G[1,1] / 2
    H = H - np.identity(numelectrodes) * H[1,1] / 2

    # compute C matrix
    Gs = G + np.identity(numelectrodes) * smoothing
    GsinvS = np.sum(np.linalg.inv(Gs), 0)
    dataGs = np.dot(data.T, np.linalg.inv(Gs))
    C = dataGs - np.dot(np.atleast_2d(np.sum(dataGs, 1)/np.sum(GsinvS)).T, np.atleast_2d(GsinvS))

    # apply transform
    original = np.reshape(data, orig_data_size)
    surf_lap = np.reshape(np.transpose(np.dot(C,np.transpose(H))), orig_data_size)

    info = raw.info
    raw_lap =  mne.io.RawArray(surf_lap,info)
    
    return raw_lap





########################################
######## GENERATE FOLDERS ########
########################################


#os.getcwd()
def create_folder(folder_name, construct_token):
    if os.path.exists(folder_name) == False:
        os.mkdir(folder_name)
        print('create : ' + folder_name)
        construct_token += 1
    return construct_token

def generate_folder_structure(sujet):

    construct_token = 0

    os.chdir(path_general)
    
    construct_token = create_folder('Analyses', construct_token)
    construct_token = create_folder('Data', construct_token)
    construct_token = create_folder('Mmap', construct_token)

    #### Analyses
    os.chdir(os.path.join(path_general, 'Analyses'))
    construct_token = create_folder('preprocessing', construct_token)
    construct_token = create_folder('precompute', construct_token)
    construct_token = create_folder('results', construct_token)
    construct_token = create_folder('protocole', construct_token)
    
        #### preprocessing
    os.chdir(os.path.join(path_general, 'Analyses', 'preprocessing'))

        #### precompute
    os.chdir(os.path.join(path_general, 'Analyses', 'precompute'))
    construct_token = create_folder(sujet, construct_token)
    construct_token = create_folder('allsujet', construct_token)

        #### results
    os.chdir(os.path.join(path_general, 'Analyses', 'results'))
    construct_token = create_folder(sujet, construct_token)

    return construct_token




    


################################################
######## DATA MANAGEMENT CLUSTER ########
################################################


def sync_folders__push_to_mnt(clusterexecution=True):

    #### need to be exectuted outside of cluster to work
    folder_to_push_to = {path_data : os.path.join(path_mntdata, 'Data'), path_precompute : os.path.join(path_mntdata, 'Analyses', 'precompute'), 
                         path_prep : os.path.join(path_mntdata, 'Analyses', 'preprocessing'), path_main_workdir : os.path.join(path_mntdata, 'Scripts'),
                         path_slurm : os.path.join(path_mntdata, 'Scripts_slurm'), 
                         os.path.join(path_results, 'RESPI', 'respfeatures') : os.path.join(path_mntdata, 'Analyses', 'results', 'RESPI', 'respfeatures')}

    if clusterexecution:
            
        #### We push from A to B
        for folder_local, folder_remote in folder_to_push_to.items():

            subprocess.run([f"rsync -avz --delete -v {folder_local}/ {folder_remote}/"], shell=True)

    else:

        hostname_local = '10.69.168.93'
        port = 22
        username = 'jules.granget'

        # Create an SSH client
        ssh_client = paramiko.SSHClient()
        
        # Automatically add the server's SSH key (if not already known)
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prompt for the SSH password
        password = getpass.getpass(prompt="Enter your SSH password: ")
        
        try:
            # Connect to the remote machine
            print(f"Connecting to {hostname_local}...")
            ssh_client.connect(hostname_local, port=port, username=username, password=password)
            print("Connection established.")

            #### test
            if debug:

                #### A to B
                sync_from_remote_to_local = f"rsync -avz --delete -v {os.path.join(path_general, 'test')}/ {os.path.join(path_mntdata, 'test')}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)

                #### B to A
                sync_from_remote_to_local = f"rsync -avz --delete -v {os.path.join(path_mntdata, 'test')}/ {os.path.join(path_general, 'test')}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)

            #### We push from A to B
            for folder_local, folder_remote in folder_to_push_to.items():

                sync_from_remote_to_local = f"rsync -avz --delete -v {folder_local}/ {folder_remote}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)

        except:
            print(f"An error occurred")



def sync_folders__push_to_crnldata(clusterexecution=True):

    #### dont push scripts from mnt to crnldata
    folder_to_push_to = {path_data : os.path.join(path_mntdata, 'Data'), path_precompute : os.path.join(path_mntdata, 'Analyses', 'precompute'), 
                         path_prep : os.path.join(path_mntdata, 'Analyses', 'preprocessing'), path_slurm : os.path.join(path_mntdata, 'Scripts_slurm')}

    if clusterexecution:
            
        #### We push from A to B
        for folder_local, folder_remote in folder_to_push_to.items():

            subprocess.run([f"rsync -avz --delete -v {folder_remote}/ {folder_local}/"], shell=True)

    else:

        hostname_local = '10.69.168.93'
        port = 22
        username = 'jules.granget'

        # Create an SSH client
        ssh_client = paramiko.SSHClient()
        
        # Automatically add the server's SSH key (if not already known)
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prompt for the SSH password
        password = getpass.getpass(prompt="Enter your SSH password: ")
        
        try:
            # Connect to the remote machine
            print(f"Connecting to {hostname_local}...")
            ssh_client.connect(hostname_local, port=port, username=username, password=password)
            print("Connection established.")

            #### test
            if debug:

                #### A to B
                sync_from_remote_to_local = f"rsync -avz --delete -v {os.path.join(path_general, 'test')}/ {os.path.join(path_mntdata, 'test')}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)

                #### B to A
                sync_from_remote_to_local = f"rsync -avz --delete -v {os.path.join(path_mntdata, 'test')}/ {os.path.join(path_general, 'test')}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)

            #### We push from A to B
            for folder_local, folder_remote in folder_to_push_to.items():

                sync_from_remote_to_local = f"rsync -avz --delete -v {folder_remote}/ {folder_local}/"
                stdin, stdout, stderr = ssh_client.exec_command(sync_from_remote_to_local)
                output = stdout.read().decode()
                print(output)
        
        except:
            print(f"An error occurred")






################################
######## SLURM EXECUTE ########
################################


#name_script, name_function, params = 'n06_precompute_TF_STATS', 'precompute_tf_STATS_allsujet', [chan]
def execute_function_in_slurm_bash(name_script, name_function, params, n_core=15, mem='15G'):

    script_path = os.getcwd()
    
    python = sys.executable

    #### params to print in script
    params_str = ""
    for i, params_i in enumerate(params):
        if isinstance(params_i, str):
            str_i = f"'{params_i}'"
        else:
            str_i = str(params_i)

        if i == 0 :
            params_str = params_str + str_i
        else:
            params_str = params_str + ' , ' + str_i

    #### params to print in script name
    params_str_name = ''
    for i, params_i in enumerate(params):

        str_i = str(params_i)

        if i == 0 :
            params_str_name = params_str_name + str_i
        else:
            params_str_name = params_str_name + '_' + str_i

    #### remove all txt that block name save
    for txt_remove_i in ["'", "[", "]", "{", "}", ":", " ", ","]:
        if txt_remove_i == " " or txt_remove_i == ",":
            params_str_name = params_str_name.replace(txt_remove_i, '_')
        else:
            params_str_name = params_str_name.replace(txt_remove_i, '')
    
    #### script text
    lines = [f'#! {python}']
    lines += ['import sys']
    lines += [f"sys.path.append('{os.path.join(path_mntdata, 'Scripts')}')"]
    lines += [f'from {name_script} import {name_function}']
    lines += [f'{name_function}({params_str})']
        
    #### write script and execute
    os.chdir(path_slurm)
    slurm_script_name =  f"run__{name_function}__{params_str_name}.py" #add params
        
    with open(slurm_script_name, 'w') as f:
        f.writelines('\n'.join(lines))
        os.fchmod(f.fileno(), mode = stat.S_IRWXU)
        f.close()
    
    #### script text
    lines = ['#!/bin/bash']
    lines += [f'#SBATCH --job-name={name_function}']
    lines += [f'#SBATCH --output=%slurm_{name_function}_{params_str_name}.log']
    lines += [f'#SBATCH --cpus-per-task={n_core}']
    lines += [f'#SBATCH --mem={mem}']
    lines += [f"srun {python} {os.path.join(path_mntdata, 'Scripts_slurm', slurm_script_name)}"]
        
    #### write script and execute
    slurm_bash_script_name =  f"bash__{name_function}__{params_str_name}.sh" #add params
        
    with open(slurm_bash_script_name, 'w') as f:
        f.writelines('\n'.join(lines))
        os.fchmod(f.fileno(), mode = stat.S_IRWXU)
        f.close()

    ###synchro
    sync_folders__push_to_mnt()

    #### execute bash
    print(f'#### slurm submission : from {name_script} execute {name_function}({params})')
    os.chdir(os.path.join(path_mntdata, 'Scripts_slurm'))
    subprocess.run([f'sbatch {slurm_bash_script_name}'], shell=True) 

    # wait subprocess to lauch before removing
    #time.sleep(4)
    #os.remove(slurm_script_name)
    #os.remove(slurm_bash_script_name)

    #### get back to original path
    os.chdir(script_path)












################################
######## WAVELETS ########
################################


def get_wavelets():

    #### compute wavelets
    wavelets = np.zeros((nfrex, len(wavetime)), dtype=complex)

    # create Morlet wavelet family
    for fi in range(nfrex):
        
        s = cycles[fi] / (2*np.pi*frex[fi])
        gw = np.exp(-wavetime**2/ (2*s**2)) 
        sw = np.exp(1j*(2*np.pi*frex[fi]*wavetime))
        mw =  gw * sw

        wavelets[fi,:] = mw

    if debug:

        plt.plot(np.sum(np.abs(wavelets),axis=1))
        plt.show()

        plt.pcolormesh(np.real(wavelets))
        plt.show()

        plt.plot(np.real(wavelets)[0,:])
        plt.show()

    return wavelets



#freq = freq_band_fc[band]
def get_wavelets_fc(freq):

    #### select wavelet parameters
    wavelets_mask = (frex >= freq[0]) & (frex <= freq[-1])
    frex_list = frex[wavelets_mask]
    ncycle_list = cycles[wavelets_mask]
    nfrex_freq = wavelets_mask.sum()

    if freq[0] < 45:
        wavetime = np.arange(-2,2,1/srate)

    if freq[0] > 45:
        wavetime = np.arange(-.5,.5,1/srate)

    #### compute wavelets
    wavelets = np.zeros((nfrex_freq,len(wavetime)) ,dtype=complex)

    # create Morlet wavelet family
    for fi in range(nfrex_freq):
        
        s = ncycle_list[fi] / (2*np.pi*frex_list[fi])
        gw = np.exp(-wavetime**2/ (2*s**2)) 
        sw = np.exp(1j*(2*np.pi*frex_list[fi]*wavetime))
        mw =  gw * sw

        wavelets[fi,:] = mw

    if debug:

        plt.plot(np.sum(np.abs(wavelets),axis=1))
        plt.show()

        plt.pcolormesh(np.real(wavelets))
        plt.show()

        plt.plot(np.real(wavelets)[0,:])
        plt.show()

    return wavelets





############################
######## LOAD DATA ########
############################




def load_data_sujet(sujet, cond):

    path_source = os.getcwd()
    
    os.chdir(path_prep)

    raw = mne.io.read_raw_fif(f'{sujet}_{cond}.fif', preload=True, verbose='critical')

    data = raw.get_data()

    #### go back to path source
    os.chdir(path_source)

    #### free memory
    del raw

    return data



def get_srate(sujet):

    path_source = os.getcwd()
    
    os.chdir(os.path.join(path_prep, sujet, 'sections'))

    raw = mne.io.read_raw_fif(sujet + '_FR_CV_1_lf.fif', preload=True, verbose='critical')
    
    srate = int(raw.info['sfreq'])

    #### go back to path source
    os.chdir(path_source)

    #### free memory
    del raw

    return srate


def get_pos_file(sujet, band_prep):

    path_source = os.getcwd()
    
    os.chdir(os.path.join(path_prep, sujet, 'sections'))

    raw = mne.io.read_raw_fif(f'{sujet}_o_FR_CV_1_{band_prep}.fif', preload=True, verbose='critical')
    
    info = raw.info

    #### go back to path source
    os.chdir(path_source)

    #### free memory
    del raw

    return info



########################################
######## LOAD RESPI FEATURES ########
########################################

def load_respfeatures(sujet):

    path_source = os.getcwd()
    
    os.chdir(os.path.join(path_results, 'RESPI', 'respfeatures'))
    respfeatures_listdir = os.listdir()

    #### get respi features
    respfeatures_allcond = {}

    for cond in cond_list:

        load_i = []
        for session_i, session_name in enumerate(respfeatures_listdir):
            if session_name.find(cond) != -1 and session_name.find(sujet) != -1:
                load_i.append(session_i)
            else:
                continue

        load_list = [respfeatures_listdir[i] for i in load_i]

        respfeatures_allcond[cond] = pd.read_excel(load_list[0])

    #### go back to path source
    os.chdir(path_source)

    return respfeatures_allcond



def get_all_respi_ratio(sujet):
    
    respfeatures_allcond = load_respfeatures(sujet)
    
    respi_ratio_allcond = {}

    for cond in cond_list:

        if len(respfeatures_allcond[cond]) == 1:

            mean_cycle_duration = np.mean(respfeatures_allcond[cond][0][['insp_duration', 'exp_duration']].values, axis=0)
            mean_inspi_ratio = mean_cycle_duration[0]/mean_cycle_duration.sum()

            respi_ratio_allcond[cond] = [ mean_inspi_ratio ]

        elif len(respfeatures_allcond[cond]) > 1:

            data_to_short = []
            data_to_short_count = 1

            for session_i in range(len(respfeatures_allcond[cond])):   
                
                if session_i == 0 :

                    mean_cycle_duration = np.mean(respfeatures_allcond[cond][session_i][['insp_duration', 'exp_duration']].values, axis=0)
                    mean_inspi_ratio = mean_cycle_duration[0]/mean_cycle_duration.sum()
                    data_to_short = [ mean_inspi_ratio ]

                elif session_i > 0 :

                    mean_cycle_duration = np.mean(respfeatures_allcond[cond][session_i][['insp_duration', 'exp_duration']].values, axis=0)
                    mean_inspi_ratio = mean_cycle_duration[0]/mean_cycle_duration.sum()

                    data_replace = [(data_to_short[0] + mean_inspi_ratio)]
                    data_to_short_count += 1

                    data_to_short = data_replace.copy()
            
            # to put in list
            respi_ratio_allcond[cond] = data_to_short[0] / data_to_short_count

    return respi_ratio_allcond








################################
######## STRETCH ########
################################
    


#resp_features, nb_point_by_cycle = respfeatures[cond], stretch_point_ERP
def stretch_data(resp_features, nb_point_by_cycle, data, srate):

    #### params
    cycle_times = resp_features[['inspi_time', 'expi_time', 'next_inspi_time']].values
    mean_cycle_duration = np.mean(resp_features[['inspi_duration', 'expi_duration']].values, axis=0)
    mean_inspi_ratio = mean_cycle_duration[0]/mean_cycle_duration.sum()
    times = np.arange(0,data.shape[0])/srate

    #### stretch
    if stretch_TF_auto:

        cycles = physio.deform_traces_to_cycle_template(data.reshape(-1,1), times, cycle_times, points_per_cycle=nb_point_by_cycle, 
                segment_ratios=mean_inspi_ratio, output_mode='stacked')
    else:
        
        cycles = physio.deform_traces_to_cycle_template(data.reshape(-1,1), times, cycle_times, points_per_cycle=nb_point_by_cycle, 
                segment_ratios=ratio_stretch_TF, output_mode='stacked')

    #### reshape
    if np.iscomplex(data[0]):
        data_stretch = np.zeros(( cycles.shape[0], nb_point_by_cycle ), dtype='complex')
    else:
        data_stretch = np.zeros(( cycles.shape[0], nb_point_by_cycle ))

    for cycle_i in range(cycles.shape[0]):

        data_stretch[cycle_i, :] = cycles[cycle_i,:].reshape(-1)

    #### inspect
    if debug == True:

        plt.plot(data_stretch.mean(axis=0))
        plt.show()

    return data_stretch, mean_inspi_ratio

    




#resp_features, nb_point_by_cycle, data, srate = respfeatures, stretch_point_ERP, tf_load, srate
def stretch_data_tf(resp_features, nb_point_by_cycle, data, srate):

    #### params
    cycle_times = resp_features[['inspi_time', 'expi_time', 'next_inspi_time']].values
    mean_cycle_duration = np.mean(resp_features[['inspi_duration', 'expi_duration']].values, axis=0)
    mean_inspi_ratio = mean_cycle_duration[0]/mean_cycle_duration.sum()
    times = np.arange(0,data.shape[1])/srate

    #### stretch
    if stretch_TF_auto:

        cycles = physio.deform_traces_to_cycle_template(data.T, times, cycle_times, points_per_cycle=nb_point_by_cycle, 
                segment_ratios=mean_inspi_ratio, output_mode='stacked')
    else:
        
        cycles = physio.deform_traces_to_cycle_template(data.T, times, cycle_times, points_per_cycle=nb_point_by_cycle, 
                segment_ratios=ratio_stretch_TF, output_mode='stacked')

    #### reshape
    if np.iscomplex(data[0,0]):
        data_stretch = np.zeros(( cycles.shape[0], data.shape[0], nb_point_by_cycle ), dtype='complex')
    else:
        data_stretch = np.zeros(( cycles.shape[0], data.shape[0], nb_point_by_cycle ))

    for cycle_i in range(cycles.shape[0]):

        data_stretch[cycle_i, :, :] = cycles[cycle_i,:,:].T

    #### inspect
    if debug == True:

        plt.pcolormesh(np.mean(data_stretch, axis=0))
        plt.show()

    return data_stretch, mean_inspi_ratio









########################################
######## CHANGE NAME CSV TRC ########
########################################

#chan_list = prms['chan_list_ieeg']
def modify_name(chan_list):
    
    chan_list_modified = []
    chan_list_keep = []

    for nchan in chan_list:

        #### what we remove
        if nchan.find("+") != -1:
            continue

        if np.sum([str.isalpha(str_i) for str_i in nchan]) >= 2 and nchan.find('p') == -1:
            continue

        if nchan.find('ECG') != -1:
            continue

        if nchan.find('.') != -1:
            continue

        if nchan.find('*') != -1:
            continue

        #### what we do to chan we keep
        else:

            nchan_mod = nchan.replace(' ', '')
            nchan_mod = nchan_mod.replace("'", 'p')

            if nchan_mod.find('p') != -1:
                split = nchan_mod.split('p')
                letter_chan = split[0]

                if len(split[1]) == 1:
                    num_chan = '0' + split[1] 
                else:
                    num_chan = split[1]

                chan_list_modified.append(letter_chan + 'p' + num_chan)
                chan_list_keep.append(nchan)
                continue

            if nchan_mod.find('p') == -1:
                letter_chan = nchan_mod[0]

                split = nchan_mod[1:]

                if len(split) == 1:
                    num_chan = '0' + split
                else:
                    num_chan = split

                chan_list_modified.append(letter_chan + num_chan)
                chan_list_keep.append(nchan)
                continue


    return chan_list_modified, chan_list_keep












########################################
######## MI ANALYSIS FUNCTIONS ########
########################################


#x = data_mat[sujet_i,pair_i,:]
def shuffle_sig(x):

    cut = np.random.randint(low=0, high=len(x), size=1)[0]
    x_cut1 = x[:cut]
    x_cut2 = x[cut:]
    x_shift = np.concatenate((x_cut2, x_cut1), axis=0)

    return x_shift
    

def shuffle_CycleFreq(x):

    cut = int(np.random.randint(low=0, high=len(x), size=1))
    x_cut1 = x[:cut]
    x_cut2 = x[cut:]*-1
    x_shift = np.concatenate((x_cut2, x_cut1), axis=0)

    return x_shift
    

def shuffle_Cxy(x):
   half_size = x.shape[0]//2
   ind = np.random.randint(low=0, high=half_size)
   x_shift = x.copy()
   
   x_shift[ind:ind+half_size] *= -1
   if np.random.rand() >=0.5:
       x_shift *= -1

   return x_shift


def Kullback_Leibler_Distance(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return np.sum(np.where(a != 0, a * np.log(a / b), 0))

def Shannon_Entropy(a):
    a = np.asarray(a, dtype=float)
    return - np.sum(np.where(a != 0, a * np.log(a), 0))

def Modulation_Index(distrib, show=False, verbose=False):
    distrib = np.asarray(distrib, dtype = float)
    
    if verbose:
        if np.sum(distrib) != 1:
            print(f'(!)  The sum of all bins is not 1 (sum = {round(np.sum(distrib), 2)})  (!)')
        
    N = distrib.size
    uniform_distrib = np.ones(N) * (1/N)
    mi = Kullback_Leibler_Distance(distrib, uniform_distrib) / np.log(N)
    
    if show:
        bin_width_deg = 360 / N
        
        doubled_distrib = np.concatenate([distrib,distrib] )
        x = np.arange(0, doubled_distrib.size*bin_width_deg, bin_width_deg)
        fig, ax = plt.subplots(figsize = (8,4))
        
        doubled_uniform_distrib = np.concatenate([uniform_distrib,uniform_distrib] )
        ax.scatter(x, doubled_uniform_distrib, s=2, color='r')
        
        ax.bar(x=x, height=doubled_distrib, width = bin_width_deg/1.1, align = 'edge')
        ax.set_title(f'Modulation Index = {round(mi, 4)}')
        ax.set_xlabel(f'Phase (Deg)')
        ax.set_ylabel(f'Amplitude (Normalized)')
        ax.set_xticks([0,360,720])

    return mi

def Shannon_MI(a):
    a = np.asarray(a, dtype = float)
    N = a.size
    kl_divergence_shannon = np.log(N) - Shannon_Entropy(a)
    return kl_divergence_shannon / np.log(N)



def get_MVL(x):
    _phase = np.arange(0, x.shape[0])*2*np.pi/x.shape[0]
    complex_vec = x*np.exp(1j*_phase) # ici sous la forme du module * angle, r * phi

    MVL = np.abs(np.mean(complex_vec))
    
    if debug:
        fig = plt.figure()
        ax = fig.add_subplot(projection='polar')
        ax.scatter(complex_vec.real, complex_vec.imag)
        ax.scatter(np.mean(complex_vec.real), np.mean(complex_vec.imag), linewidth=3, color='r')
        plt.show()

    return MVL




def get_MI_2sig(x, y):

    #### Freedman and Diaconis rule
    nbins_x = int(np.ceil((x.max() - x.min()) / (2 * scipy.stats.iqr(x)*(x.size**(-1/3)))))
    nbins_y = int(np.ceil((y.max() - y.min()) / (2 * scipy.stats.iqr(y)*(y.size**(-1/3)))))

    #### compute proba
    hist_x = np.histogram(x,bins = nbins_x)[0]
    hist_x = hist_x/np.sum(hist_x)
    hist_y = np.histogram(y,bins = nbins_y)[0]
    hist_y = hist_y/np.sum(hist_y)

    hist_2d = np.histogram2d(x, y, bins=[nbins_x, nbins_y])[0]
    hist_2d = hist_2d / np.sum(hist_2d)

    #### compute MI
    E_x = 0
    E_y = 0
    E_x_y = 0

    for p in hist_x:
        if p!=0 :
            E_x += -p*np.log2(p)

    for p in hist_y:
        if p!=0 :
            E_y += -p*np.log2(p)

    for p0 in hist_2d:
        for p in p0 :
            if p!=0 :
                E_x_y += -p*np.log2(p)

    MI = E_x+E_y-E_x_y

    return MI









########################################
######## SCRIPT ADVANCEMENT ########
########################################


def print_advancement(i, i_final, steps=[25, 50, 75]):

    steps_i = {}
    for step in steps:

        step_i = 0
        while (step_i/i_final*100) < step:
            step_i += 1

        steps_i[step] = step_i

    for step, step_i in steps_i.items():

        if i == step_i:
            print(f'{step}%', flush=True)






################################
######## NORMALIZATION ########
################################


def zscore(x):

    x_zscore = (x - x.mean()) / x.std()

    return x_zscore




def zscore_mat(x):

    _zscore_mat = (x - x.mean(axis=1).reshape(-1,1)) / x.std(axis=1).reshape(-1,1)

    return _zscore_mat



def rscore(x):

    mad = np.median( np.abs(x-np.median(x)) ) # median_absolute_deviation

    rzscore_x = (x-np.median(x)) * 0.6745 / mad

    return rzscore_x
    



def rscore_mat(x):

    mad = np.median(np.abs(x-np.median(x, axis=1).reshape(-1,1)), axis=1) # median_absolute_deviation

    _rscore_mat = (x-np.median(x, axis=1).reshape(-1,1)) * 0.6745 / mad.reshape(-1,1)

    return _rscore_mat






#tf_conv = tf_median_cycle[nchan, :, :]
def norm_tf(sujet, tf_conv, norm_method):

    path_source = os.getcwd()

    chan_list_sel = chan_list_eeg_short

    if norm_method not in ['rscore', 'zscore']:

        #### load baseline
        os.chdir(os.path.join(path_precompute, sujet, 'baselines'))

        baselines = xr.open_dataarray(f'{sujet}_baselines.nc')

    if norm_method == 'dB':

        for n_chan_i, n_chan in enumerate(chan_list_sel):

            tf_conv[n_chan_i,:,:] = 10*np.log10(tf_conv[n_chan_i,:,:] / baselines.loc[n_chan, :, 'median'].values.reshape(-1,1))

    if norm_method == 'zscore_baseline':

        for n_chan_i, n_chan in enumerate(chan_list_sel):

            tf_conv[n_chan_i,:,:] = (tf_conv[n_chan_i,:,:] - baselines.loc[n_chan,:,'mean'].values.reshape(-1,1)) / baselines.loc[n_chan,:,'std'].values.reshape(-1,1)
                
    if norm_method == 'rscore_baseline':

        for n_chan_i, n_chan in enumerate(chan_list_sel):

            tf_conv[n_chan_i,:,:] = (tf_conv[n_chan_i,:,:] - baselines.loc[n_chan,:,'median'].values.reshape(-1,1)) * 0.6745 / baselines.loc[n_chan,:,'mad'].values.reshape(-1,1)

    if norm_method == 'zscore':

        for n_chan_i, n_chan in enumerate(chan_list_sel):

            tf_conv[n_chan_i,:,:] = zscore_mat(tf_conv[n_chan_i,:,:])
                
    if norm_method == 'rscore':

        for n_chan_i, n_chan in enumerate(chan_list_sel):

            tf_conv[n_chan_i,:,:] = rscore_mat(tf_conv[n_chan_i,:,:])


    #### verify baseline
    if debug:

        nchan = 0
        nchan_name = chan_list_sel[nchan]

        fig, axs = plt.subplots(ncols=2)
        axs[0].set_title('mean std')
        axs[0].plot(baselines.loc[nchan_name,:,'mean'], label='mean')
        axs[0].plot(baselines.loc[nchan_name,:,'std'], label='std')
        axs[0].legend()
        axs[0].set_yscale('log')
        axs[1].set_title('median mad')
        axs[1].plot(baselines.loc[nchan_name,:,'median'], label='median')
        axs[1].plot(baselines.loc[nchan_name,:,'mad'], label='mad')
        axs[1].legend()
        axs[1].set_yscale('log')
        plt.show()

        tf_test = tf_conv[nchan,:,:int(tf_conv.shape[-1]/10)].copy()

        fig, axs = plt.subplots(nrows=6)
        fig.set_figheight(10)
        fig.set_figwidth(15)

        percentile_sel = 0

        vmin = np.percentile(tf_test.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_test.reshape(-1),100-percentile_sel)
        im = axs[0].pcolormesh(tf_test, vmin=vmin, vmax=vmax)
        axs[0].set_title('raw')
        fig.colorbar(im, ax=axs[0])

        tf_baseline = 10*np.log10(tf_test / baselines.loc[chan_list_eeg[nchan], :, 'median'].values.reshape(-1,1))
        vmin = np.percentile(tf_baseline.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_baseline.reshape(-1),100-percentile_sel)
        im = axs[1].pcolormesh(tf_baseline, vmin=vmin, vmax=vmax)
        axs[1].set_title('db')
        fig.colorbar(im, ax=axs[1])

        tf_baseline = (tf_test - baselines.loc[chan_list_eeg[nchan],:,'mean'].values.reshape(-1,1)) / baselines.loc[chan_list_eeg[nchan],:,'std'].values.reshape(-1,1)
        vmin = np.percentile(tf_baseline.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_baseline.reshape(-1),100-percentile_sel)
        im = axs[2].pcolormesh(tf_baseline, vmin=vmin, vmax=vmax)
        axs[2].set_title('zscore')
        fig.colorbar(im, ax=axs[2])

        tf_baseline = (tf_test - baselines.loc[chan_list_eeg[nchan],:,'median'].values.reshape(-1,1)) / baselines.loc[chan_list_eeg[nchan],:,'mad'].values.reshape(-1,1)
        vmin = np.percentile(tf_baseline.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_baseline.reshape(-1),100-percentile_sel)
        im = axs[3].pcolormesh(tf_baseline, vmin=vmin, vmax=vmax)
        axs[3].set_title('rscore')
        fig.colorbar(im, ax=axs[3])

        tf_baseline = zscore_mat(tf_test)
        vmin = np.percentile(tf_baseline.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_baseline.reshape(-1),100-percentile_sel)
        im = axs[4].pcolormesh(tf_baseline, vmin=vmin, vmax=vmax)
        axs[4].set_title('zscore_mat')
        fig.colorbar(im, ax=axs[4])

        tf_baseline = rscore_mat(tf_test)
        vmin = np.percentile(tf_baseline.reshape(-1),percentile_sel)
        vmax = np.percentile(tf_baseline.reshape(-1),100-percentile_sel)
        im = axs[5].pcolormesh(tf_baseline, vmin=vmin, vmax=vmax)
        axs[5].set_title('rscore_mat')
        fig.colorbar(im, ax=axs[5])

        plt.show()

    os.chdir(path_source)

    return tf_conv






########################################
######## HRV ANALYSIS HOMEMADE ########
########################################



#### params
def get_params_hrv_homemade(srate_resample_hrv):
    
    nwind_hrv = int( 128*srate_resample_hrv )
    nfft_hrv = nwind_hrv
    noverlap_hrv = np.round(nwind_hrv/90)
    win_hrv = scipy.signal.windows.hann(nwind_hrv)
    f_RRI = (.1, .5)

    return nwind_hrv, nfft_hrv, noverlap_hrv, win_hrv, f_RRI




#### RRI, IFR
#ecg_i, ecg_cR, srate, srate_resample = ecg_i, ecg_cR, srate, srate_resample_hrv
def get_RRI_IFR(ecg_cR, srate_resample) :

    cR_sec = ecg_cR # cR in sec

    # RRI computation
    RRI = np.diff(cR_sec)
    RRI = np.insert(RRI, 0, np.median(RRI))
    IFR = (1/RRI)

    # interpolate
    f = scipy.interpolate.interp1d(cR_sec, RRI, kind='quadratic', fill_value="extrapolate")
    cR_sec_resample = np.arange(cR_sec[0], cR_sec[-1], 1/srate_resample)
    RRI_resample = f(cR_sec_resample)

    #plt.plot(cR_sec, RRI, label='old')
    #plt.plot(cR_sec_resample, RRI_resample, label='new')
    #plt.legend()
    #plt.show()

    return RRI, RRI_resample, IFR



def get_fig_RRI_IFR(ecg_i, ecg_cR, RRI, IFR, srate, srate_resample):

    cR_sec = ecg_cR # cR in sec
    times = np.arange(0,len(ecg_i))/srate # in sec

    f = scipy.interpolate.interp1d(cR_sec, RRI, kind='quadratic', fill_value="extrapolate")
    cR_sec_resample = np.arange(cR_sec[0], cR_sec[-1], 1/srate_resample)
    RRI_resample = f(cR_sec_resample)

    fig, ax = plt.subplots()
    ax = plt.subplot(411)
    plt.plot(times, ecg_i)
    plt.title('ECG')
    plt.ylabel('a.u.')
    plt.xlabel('s')
    plt.vlines(cR_sec, ymin=min(ecg_i), ymax=max(ecg_i), colors='k')
    plt.subplot(412, sharex=ax)
    plt.plot(cR_sec, RRI)
    plt.title('RRI')
    plt.ylabel('s')
    plt.subplot(413, sharex=ax)
    plt.plot(cR_sec_resample, RRI_resample)
    plt.title('RRI_resampled')
    plt.ylabel('Hz')
    plt.subplot(414, sharex=ax)
    plt.plot(cR_sec, IFR)
    plt.title('IFR')
    plt.ylabel('Hz')
    #plt.show()

    # in this plot one RRI point correspond to the difference value between the precedent RR
    # the first point of RRI is the median for plotting consideration

    return fig




def get_fig_PSD_LF_HF(Pxx, hzPxx, VLF, LF, HF):

    # PLOT
    fig = plt.figure()
    plt.plot(hzPxx,Pxx)
    plt.ylim(0, np.max(Pxx[hzPxx>0.01]))
    plt.xlim([0,.6])
    plt.vlines([VLF, LF, HF], ymin=min(Pxx), ymax=max(Pxx), colors='r')
    #plt.show()
    
    return fig

        
def get_fig_poincarre(RRI):

    RRI_1 = RRI[1:]
    RRI_1 = np.append(RRI_1, RRI[-1]) 

    fig = plt.figure()
    plt.scatter(RRI, RRI_1)
    plt.xlabel('RR (ms)')
    plt.ylabel('RR+1 (ms)')
    plt.title('Poincarré ')
    plt.xlim(.600,1.)
    plt.ylim(.600,1.)

    return fig
    
#### DeltaHR

#RRI, srate_resample, f_RRI, condition = result_struct[keys_result[0]][1], srate_resample, f_RRI, cond 
def get_dHR(RRI_resample, srate_resample, f_RRI):
    
    times = np.arange(0,len(RRI_resample))/srate_resample

        # stairs method
    #RRI_stairs = np.array([])
    #len_cR = len(cR) 
    #for RR in range(len(cR)) :
    #    if RR == 0 :
    #        RRI_i = cR[RR+1]/srate - cR[RR]/srate
    #        RRI_stairs = np.append(RRI_stairs, [RRI_i*1e3 for i in range(int(cR[RR+1]))])
    #    elif RR != 0 and RR != len_cR-1 :
    #        RRI_i = cR[RR+1]/srate - cR[RR]/srate
    #        RRI_stairs = np.append(RRI_stairs, [RRI_i*1e3 for i in range(int(cR[RR+1] - cR[RR]))])
    #    elif RR == len_cR-1 :
    #        RRI_stairs = np.append(RRI_stairs, [RRI_i*1e3 for i in range(int(len(ecg) - cR[RR]))])

    def find_extrema():

        #### define function for HRV

        return

    peaks, troughs = find_extrema(RRI_resample, srate_resample, f_RRI)
    peaks_RRI, troughs_RRI = RRI_resample[peaks], RRI_resample[troughs]
    peaks_troughs = np.stack((peaks_RRI, troughs_RRI), axis=1)

    fig_verif = plt.figure()
    plt.plot(times, RRI_resample)
    plt.vlines(peaks/srate_resample, ymin=min(RRI_resample), ymax=max(RRI_resample), colors='b')
    plt.vlines(troughs/srate_resample, ymin=min(RRI_resample), ymax=max(RRI_resample), colors='r')
    #plt.show()

    dHR = np.diff(peaks_troughs/srate_resample, axis=1)*1e3

    fig_dHR = plt.figure()
    ax = plt.subplot(211)
    plt.plot(times, RRI_resample*1e3)
    plt.title('RRI')
    plt.ylabel('ms')
    plt.subplot(212, sharex=ax)
    plt.plot(troughs/srate_resample, dHR)
    plt.hlines(np.median(dHR), xmin=min(times), xmax=max(times), colors='m', label='median = {:.3f}'.format(np.median(dHR)))
    plt.legend()
    plt.title('dHR')
    plt.ylabel('ms')
    plt.vlines(peaks/srate_resample, ymin=0, ymax=0.01, colors='b')
    plt.vlines(troughs/srate_resample, ymin=0, ymax=0.01, colors='r')
    plt.tight_layout()
    #plt.show()

    return fig_verif, fig_dHR

#ecg_allcond[cond][odor_i], ecg_cR_allcond[cond][odor_i], prms_hrv
def ecg_analysis_homemade(ecg_i, srate, srate_resample_hrv, fig_token=False):

    #### load params
    nwind_hrv, nfft_hrv, noverlap_hrv, win_hrv, f_RRI = get_params_hrv_homemade(srate_resample_hrv)

    #### load cR
    ecg_cR = scipy.signal.find_peaks(ecg_i, distance=srate*0.5)[0]
    ecg_cR = ecg_cR/srate

    #### verif
    if debug:
        times = np.arange(ecg_i.shape[0])/srate
        plt.plot(times, ecg_i)
        plt.vlines(ecg_cR, ymin=np.min(ecg_i) ,ymax=np.max(ecg_i), colors='r')
        plt.show()


    #### initiate metrics names
    res_list = ['HRV_MeanNN', 'HRV_SDNN', 'HRV_RMSSD', 'HRV_pNN50', 'HRV_LF', 'HRV_HF', 'HRV_LFHF', 'HRV_SD1', 'HRV_SD2', 'HRV_S', 'HRV_rCOV', 'HRV_MAD', 'HRV_MEDIAN']

    #### RRI
    RRI, RRI_resample, IFR = get_RRI_IFR(ecg_i, ecg_cR, srate, srate_resample_hrv)

    HRV_MeanNN = np.mean(RRI)
    
    #### PSD
    VLF, LF, HF = .04, .15, .4
    AUC_LF, AUC_HF, LF_HF_ratio, hzPxx, Pxx = get_PSD_LF_HF(RRI_resample, srate_resample_hrv, nwind_hrv, nfft_hrv, noverlap_hrv, win_hrv, VLF, LF, HF)

    #### descriptors
    MeanNN, SDNN, RMSSD, NN50, pNN50, COV, mad, median = get_stats_descriptors(RRI)

    #### poincarré
    SD1, SD2, Tot_HRV = get_poincarre(RRI)

    #### df
    res_tmp = [HRV_MeanNN*1e3, SDNN*1e3, RMSSD, pNN50*100, AUC_LF/10, AUC_HF/10, LF_HF_ratio, SD1*1e3, SD2*1e3, Tot_HRV*1e6, COV, mad*1e3, median*1e3]
    data_df = {}
    for i, dv in enumerate(res_list):
        data_df[dv] = [res_tmp[i]]

    hrv_metrics_homemade = pd.DataFrame(data=data_df)

    #### for figures

    #### dHR
    if fig_token:
        fig_verif, fig_dHR = get_dHR(RRI_resample, srate_resample_hrv, f_RRI)

    #### fig
    if fig_token:
        fig_RRI = get_fig_RRI_IFR(ecg_i, ecg_cR, RRI, IFR, srate, srate_resample_hrv)
        fig_PSD = get_fig_PSD_LF_HF(Pxx, hzPxx, VLF, LF, HF) 
        fig_poincarre = get_fig_poincarre(RRI)

        fig_list = [fig_RRI, fig_PSD, fig_poincarre, fig_verif, fig_dHR]

        plt.close('all')

        return hrv_metrics_homemade, fig_list

    else:

        return hrv_metrics_homemade



def get_hrv_metrics_win(RRI):

    #### initiate metrics names
    res_list = ['HRV_MeanNN', 'HRV_SDNN', 'HRV_RMSSD', 'HRV_pNN50', 'HRV_SD1', 'HRV_SD2', 'HRV_S', 'HRV_COV', 'HRV_MAD', 'HRV_MEDIAN']

    HRV_MeanNN = np.mean(RRI)
    
    #### descriptors
    MeanNN, SDNN, RMSSD, NN50, pNN50, COV, mad, median = get_stats_descriptors(RRI)

    #### poincarré
    SD1, SD2, Tot_HRV = get_poincarre(RRI)

    #### df
    res_tmp = [HRV_MeanNN*1e3, SDNN*1e3, RMSSD, pNN50*100, SD1*1e3, SD2*1e3, Tot_HRV*1e6, COV, mad*1e3, median*1e3]
    data_df = {}
    for i, dv in enumerate(res_list):
        data_df[dv] = [res_tmp[i]]

    hrv_metrics_homemade = pd.DataFrame(data=data_df)

    return hrv_metrics_homemade



########################################
######## HRV METRICS HOMEMADE ######## 
########################################



def get_PSD_LF_HF(RRI_resample, prms_hrv, VLF, LF, HF):

    srate_resample, nwind, nfft, noverlap, win = prms_hrv['srate_resample_hrv'], prms_hrv['nwind_hrv'], prms_hrv['nfft_hrv'], prms_hrv['noverlap_hrv'], prms_hrv['win_hrv']

    # DETREND
    RRI_detrend = RRI_resample-np.median(RRI_resample)

    # FFT WELCH
    hzPxx, Pxx = scipy.signal.welch(RRI_detrend, fs=srate_resample, window=win, nperseg=nwind, noverlap=noverlap, nfft=nfft)

    AUC_LF = np.trapz(Pxx[(hzPxx>VLF) & (hzPxx<LF)])
    AUC_HF = np.trapz(Pxx[(hzPxx>LF) & (hzPxx<HF)])
    LF_HF_ratio = AUC_LF/AUC_HF

    return AUC_LF, AUC_HF, LF_HF_ratio, hzPxx, Pxx



def get_stats_descriptors(RRI) :

    MeanNN = np.mean(RRI)

    SDNN = np.std(RRI)

    RMSSD = np.sqrt(np.mean((np.diff(RRI)*1e3)**2))

    NN50 = []
    for RR in range(len(RRI)) :
        if RR == len(RRI)-1 :
            continue
        else :
            NN = abs(RRI[RR+1] - RRI[RR])
            NN50.append(NN)

    NN50 = np.array(NN50)*1e3
    pNN50 = np.sum(NN50>50)/len(NN50)

    mad = np.median( np.abs(RRI-np.median(RRI)) )
    COV = mad / np.median(RRI)

    median = np.median(RRI)

    return MeanNN, SDNN, RMSSD, NN50, pNN50, COV, mad, median


def get_poincarre(RRI):
    RRI_1 = RRI[1:]
    RRI_1 = np.append(RRI_1, RRI[-1]) 

    SD1_val = []
    SD2_val = []
    for RR in range(len(RRI)) :
        if RR == len(RRI)-1 :
            continue
        else :
            SD1_val_tmp = (RRI[RR+1] - RRI[RR])/np.sqrt(2)
            SD2_val_tmp = (RRI[RR+1] + RRI[RR])/np.sqrt(2)
            SD1_val.append(SD1_val_tmp)
            SD2_val.append(SD2_val_tmp)

    SD1 = np.std(SD1_val)
    SD2 = np.std(SD2_val)
    Tot_HRV = SD1*SD2*np.pi

    return SD1, SD2, Tot_HRV



def get_hrv_metrics_homemade(cR_time, prms_hrv, analysis_time='5min'):

    #### get RRI
    cR_sec = cR_time/prms_hrv['srate'] # cR in sec

    if analysis_time == '3min':

        cR_sec_mask = (cR_sec >= 60) & (cR_sec <= 240)
        cR_sec = cR_sec[cR_sec_mask] - 60

    RRI = np.diff(cR_sec)
    RRI = np.insert(RRI, 0, np.median(RRI))

    if debug:
        plt.plot(cR_sec, RRI)
        plt.show()
    
    #### descriptors
    MeanNN, SDNN, RMSSD, NN50, pNN50, COV, mad, median = get_stats_descriptors(RRI)

    #### poincarré
    SD1, SD2, Tot_HRV = get_poincarre(RRI)

    #### PSD
    f = scipy.interpolate.interp1d(cR_sec, RRI, kind='quadratic', fill_value="extrapolate")
    cR_sec_resample = np.arange(cR_sec[0], cR_sec[-1], 1/prms_hrv['srate_resample_hrv'])
    RRI_resample = f(cR_sec_resample)

    if debug:
        plt.plot(cR_sec, RRI, label='raw')
        plt.plot(cR_sec_resample, RRI_resample, label='resampled')
        plt.legend()
        plt.show()

    VLF, LF, HF = .04, .15, .4
    AUC_LF, AUC_HF, LF_HF_ratio, hzPxx, Pxx = get_PSD_LF_HF(RRI_resample, prms_hrv, VLF, LF, HF)

    #### df
    res_tmp = {'HRV_MeanNN' : MeanNN*1e3, 'HRV_SDNN' : SDNN*1e3, 'HRV_RMSSD' : RMSSD, 'HRV_pNN50' : pNN50*100, 'HRV_LF' : AUC_LF/10, 'HRV_HF' : AUC_HF/10, 
               'HRV_LFHF' : LF_HF_ratio, 'HRV_SD1' : SD1*1e3, 'HRV_SD2' : SD2*1e3, 'HRV_S' : Tot_HRV*1e6, 'HRV_COV' : COV, 'HRV_MAD' : mad, 'HRV_MEDIAN' : median}
    
    data_df = {}
    for i, dv in enumerate(prms_hrv['metric_list']):
        data_df[dv] = res_tmp[dv]

    hrv_metrics_homemade = pd.DataFrame([data_df])

    return hrv_metrics_homemade






################################
######## NEUROKIT ######## 
################################

#ecg_i = xr_chunk[sujet_i, cond_i, trial_i, :].data
def nk_analysis(ecg_i, srate):

    ecg_cR = scipy.signal.find_peaks(ecg_i, distance=srate*0.5)[0]
    peaks_dict = {'ECG_R_Peaks' : ecg_cR}
    ecg_peaks = pd.DataFrame(peaks_dict)

    hrv_metrics = nk.hrv(ecg_peaks, sampling_rate=srate, show=False)

    hrv_metrics_name = ['HRV_MeanNN', 'HRV_SDNN', 'HRV_RMSSD', 'HRV_pNN50', 'HRV_LF', 'HRV_HF', 'HRV_LFHF', 'HRV_SD1', 'HRV_SD2', 'HRV_S']

    col_to_drop = []
    col_hrv = list(hrv_metrics.columns.values) 
    for metric_name in col_hrv :
        if (metric_name in hrv_metrics_name) == False :
            col_to_drop.append(metric_name)

    hrv_metrics_short = hrv_metrics.copy()
    hrv_metrics_short = hrv_metrics_short.drop(col_to_drop, axis=1)

    return hrv_metrics_short




########################################
######## PERMUTATION STATS ######## 
########################################

# # data_baseline, data_cond, n_surr = data_baseline, data_cond, n_surr_fc
# def get_permutation_wilcoxon_2groups_debug(data_baseline, data_cond, n_surr):

#     if debug:
#         plt.hist(data_baseline, bins=50, alpha=0.5, label='baseline')
#         plt.hist(data_cond, bins=50, alpha=0.5, label='cond')
#         plt.legend()
#         plt.show()

#     n_trials_baselines = data_baseline.shape[0]

#     data_shuffle = np.concatenate((data_baseline, data_cond), axis=0)
#     n_trial_tot = data_shuffle.shape[0]

#     stat_obs, p_value = scipy.stats.wilcoxon(data_baseline, data_cond)

#     stats_permuted = np.zeros((n_surr))

#     #surr_i = 0
#     for surr_i in range(n_surr):

#         #### shuffle
#         random_sel = np.random.choice(n_trial_tot, size=n_trial_tot, replace=False)
#         data_shuffle_baseline = data_shuffle[random_sel[:n_trials_baselines]]
#         data_shuffle_cond = data_shuffle[random_sel[n_trials_baselines:]]

#         if debug:

#             plt.hist(data_shuffle_baseline, bins=50, label='baseline', alpha=0.5)
#             plt.hist(data_shuffle_cond, bins=50, label='cond', alpha=0.5)
#             plt.legend()
#             plt.show()

#         #### extract max min
#         stats_permuted[surr_i], _ = scipy.stats.wilcoxon(data_shuffle_baseline, data_shuffle_cond)
        
#     min, max = np.percentile(stats_permuted, 2.5), np.percentile(stats_permuted, 97.5) 

#     if debug:
#         plt.hist(stats_permuted, bins=50, alpha=0.5, color='k')
#         plt.vlines([stat_obs], ymin=0, ymax=70, color='c')
#         plt.vlines([min, max], ymin=0, ymax=70, color='r')
#         plt.legend()
#         plt.show()

#     if stat_obs < min or stat_obs > max:
#         stats_res = True
#     else:
#         stats_res = False

#     return stats_res


# data_baseline, data_cond, n_surr = data_baseline, data_cond, n_surr_fc
def get_permutation_wilcoxon_2groups(data_baseline, data_cond, n_surr, mode_grouped='mean', mode_generate_surr='minmax'):

    if debug:
        plt.hist(data_baseline, bins=50, alpha=0.5, label='baseline')
        plt.hist(data_cond, bins=50, alpha=0.5, label='cond')
        plt.legend()
        plt.show()

    n_trials_baselines = data_baseline.shape[0]

    data_shuffle = np.concatenate((data_baseline, data_cond), axis=0)
    n_trial_tot = data_shuffle.shape[0]

    if mode_grouped == 'mean':
        obs_distrib = data_baseline.mean() - data_cond.mean()
    elif mode_grouped == 'median':
        obs_distrib = np.median(data_baseline) - np.median(data_cond)

    surr_distrib = np.zeros((n_surr, 2))

    #surr_i = 0
    for surr_i in range(n_surr):

        #### shuffle
        random_sel = np.random.choice(n_trial_tot, size=n_trial_tot, replace=False)
        data_shuffle_baseline = data_shuffle[random_sel[:n_trials_baselines]]
        data_shuffle_cond = data_shuffle[random_sel[n_trials_baselines:]]

        if mode_grouped == 'mean':
            diff_shuffle = data_shuffle_cond.mean() - data_shuffle_baseline.mean()
        elif mode_grouped == 'median':
            diff_shuffle = np.median(data_shuffle_cond) - np.median(data_shuffle_baseline)

        #### generate distrib
        if mode_generate_surr == 'minmax':
            surr_distrib[surr_i, 0], surr_distrib[surr_i, 1] = diff_shuffle.min(), diff_shuffle.max()
        elif mode_generate_surr == 'percentile':
            surr_distrib[surr_i, 0], surr_distrib[surr_i, 1] = np.percentile(diff_shuffle, 1), np.percentile(diff_shuffle, 99)    

    if debug:
        count, _, _ = plt.hist(surr_distrib[:,0], bins=50, color='k', alpha=0.5)
        count, _, _ = plt.hist(surr_distrib[:,1], bins=50, color='k', alpha=0.5)
        plt.vlines([obs_distrib], ymin=0, ymax=count.max(), label='obs', colors='g')

        plt.vlines([np.percentile(surr_distrib[:,0], 1)], ymin=0, ymax=count.max(), label='perc_1_99', colors='r', linestyles='--')
        plt.vlines([np.percentile(surr_distrib[:,1], 99)], ymin=0, ymax=count.max(), colors='r', linestyles='--')
        plt.vlines([np.percentile(surr_distrib[:,0], 2.5)], ymin=0, ymax=count.max(), label='perc_025_975', colors='r', linestyles='-.')
        plt.vlines([np.percentile(surr_distrib[:,1], 97.5)], ymin=0, ymax=count.max(), colors='r', linestyles='-.')
        plt.legend()
        plt.show()

    #### thresh
    # surr_dw, surr_up = np.percentile(surr_distrib[:,0], 2.5, axis=0), np.percentile(surr_distrib[:,1], 97.5, axis=0)
    surr_dw, surr_up = np.percentile(surr_distrib[:,0], 1, axis=0), np.percentile(surr_distrib[:,1], 99, axis=0)

    if obs_distrib < surr_dw or obs_distrib > surr_up:
        stats_res = True
    else:
        stats_res = False

    return stats_res





# # data_baseline, data_cond, n_surr = data_baseline, data_cond, n_surr_fc
# def get_permutation_cluster_1d_DEBUG(data_baseline, data_cond, n_surr):

#     n_trials_baselines = data_baseline.shape[0]
#     len_sig = data_baseline.shape[-1]

#     data_shuffle = np.concatenate((data_baseline, data_cond), axis=0)
#     n_trial_tot = data_shuffle.shape[0]

#     data_baseline_median = np.median(data_baseline, axis=0)
#     data_cond_median = np.median(data_cond, axis=0)

#     surr_distrib = np.zeros((n_surr, len_sig))

#     #surr_i = 0
#     for surr_i in range(n_surr):

#         #### shuffle
#         random_sel = np.random.choice(n_trial_tot, size=n_trial_tot, replace=False)
#         data_shuffle_baseline = data_shuffle[random_sel[:n_trials_baselines]]
#         data_shuffle_cond = data_shuffle[random_sel[n_trials_baselines:]]

#         if debug:
#             plt.plot(np.mean(data_shuffle_baseline, axis=0), label='baseline')
#             plt.plot(np.mean(data_shuffle_cond, axis=0), label='cond')
#             plt.legend()
#             plt.show()

#             plt.hist(np.median(data_shuffle_baseline, axis=0), bins=50, label='baseline', alpha=0.5)
#             plt.hist(np.median(data_shuffle_cond, axis=0), bins=50, label='cond', alpha=0.5)
#             plt.legend()
#             plt.show()

#         # surr_distrib[surr_i, :], _ = scipy.stats.wilcoxon(data_shuffle_cond, data_shuffle_baseline)
#         # surr_distrib[surr_i, :], _ = scipy.stats.ttest_rel(data_shuffle_cond, data_shuffle_baseline, axis=0)
#         surr_distrib[surr_i, :] = zscore(np.median(data_shuffle_cond, axis=0) - np.median(data_shuffle_baseline, axis=0))

#     # obs_distrib, _ = scipy.stats.wilcoxon(data_baseline, data_cond)
#     # obs_distrib, _ = scipy.stats.ttest_rel(data_baseline, data_cond, axis=0)
#     obs_distrib = zscore(data_cond_median - data_baseline_median)

#     if debug:
#         i = 0
#         count, _, _ = plt.hist(surr_distrib[:,i], bins=50, label='surr')
#         plt.vlines([obs_distrib[i]], ymin=0, ymax=count.max(), label='obs', colors='c')
#         plt.vlines([np.percentile(surr_distrib[:,i], 2.5)], ymin=0, ymax=count.max(), label='surr_dw', colors='r')
#         plt.vlines([np.percentile(surr_distrib[:,i], 97.5)], ymin=0, ymax=count.max(), label='surr_up', colors='r')
#         plt.legend()
#         plt.show()

#         plt.plot(obs_distrib, label='obs')
#         plt.plot(np.percentile(surr_distrib, 2.5, axis=0), color='r', linestyle='--', alpha=0.5)
#         plt.plot(np.percentile(surr_distrib, 97.5, axis=0), color='r', linestyle='--', alpha=0.5)
#         plt.legend()
#         plt.show()

#     surr_dw, surr_up = np.percentile(surr_distrib, 2.5, axis=0), np.percentile(surr_distrib, 97.5, axis=0)

#     #### thresh data
#     mask = (obs_distrib < surr_dw) | (obs_distrib > surr_up) | (obs_distrib < surr_dw) | (obs_distrib > surr_up)

#     if debug:

#         plt.scatter(range(mask.size), mask)
#         plt.show()

#     if mask.sum() != 0:
    
#         #### thresh cluster
#         mask_thresh = mask.astype('uint8')
#         nb_blobs, im_with_separated_blobs, stats, _ = cv2.connectedComponentsWithStats(mask_thresh)
#         #### nb_blobs, im_with_separated_blobs, stats = nb clusters, clusters image with labeled clusters, info on clusters
#         sizes = stats[1:, -1]
#         nb_blobs -= 1
#         min_size = np.percentile(sizes,tf_stats_percentile_cluster_size_thresh)  

#         if debug:

#             count, _, _ = plt.hist(sizes, bins=100)
#             plt.vlines(np.percentile(sizes,tf_stats_percentile_cluster_size_thresh), ymin=0, ymax=count.max(), colors='r')
#             plt.show()

#         mask_thresh = np.zeros_like(im_with_separated_blobs)
#         for blob in range(nb_blobs):
#             if sizes[blob] >= min_size:
#                 mask_thresh[im_with_separated_blobs == blob + 1] = 1

#         mask_thresh = mask_thresh.reshape(-1)

#         if debug:

#             time = np.arange(data_baseline.shape[-1])
#             sem_baseline = data_baseline.std(axis=0)/np.sqrt(data_baseline.shape[0])
#             sem_cond = data_cond.std(axis=0)/np.sqrt(data_cond.shape[0])

#             plt.plot(time, data_baseline_median, label='baseline', color='c')
#             plt.fill_between(time, data_baseline_median-sem_baseline, data_baseline_median+sem_baseline, color='c', alpha=0.5)
#             plt.plot(time, data_cond_median, label='cond', color='g')
#             plt.fill_between(time, data_cond_median-sem_cond, data_cond_median+sem_cond, color='g', alpha=0.5)
#             plt.hlines(min, xmin=0, xmax=data_shuffle.shape[-1], color='r', label='min')
#             plt.hlines(max, xmin=0, xmax=data_shuffle.shape[-1], color='r', label='max')
#             plt.fill_between(time, data_baseline_median.min(), data_cond_median.max(), where=mask, color='r', alpha=0.5)
#             plt.title('mask not threshed')
#             plt.legend()
#             plt.show()

#             plt.plot(time, data_baseline_median, label='baseline', color='c')
#             plt.fill_between(time, data_baseline_median-sem_baseline, data_baseline_median+sem_baseline, color='c', alpha=0.5)
#             plt.plot(time, data_cond_median, label='cond', color='g')
#             plt.fill_between(time, data_cond_median-sem_cond, data_cond_median+sem_cond, color='g', alpha=0.5)
#             plt.hlines(min, xmin=0, xmax=data_shuffle.shape[-1], color='r', label='min')
#             plt.hlines(max, xmin=0, xmax=data_shuffle.shape[-1], color='r', label='max')
#             plt.fill_between(time, data_baseline_median.min(), data_cond_median.max(), where=mask_thresh, color='r', alpha=0.5)
#             plt.title('mask threshed')
#             plt.legend()
#             plt.show()

#     else:

#         mask_thresh = mask

#     return mask_thresh



# data_baseline, data_cond, n_surr = data_baseline, data_cond, n_surr_fc
def get_permutation_cluster_1d(data_baseline, data_cond, n_surr, mode_grouped='mean', mode_generate_surr='minmax', mode_select_thresh='mean', size_thresh_alpha=0.05):

    n_trials_baselines = data_baseline.shape[0]
    len_sig = data_baseline.shape[-1]

    data_shuffle = np.concatenate((data_baseline, data_cond), axis=0)
    n_trial_tot = data_shuffle.shape[0]

    if mode_grouped == 'mean':
        data_baseline_grouped = np.mean(data_baseline, axis=0)
        data_cond_grouped = np.mean(data_cond, axis=0)
    elif mode_grouped == 'median':
        data_baseline_grouped = np.median(data_baseline, axis=0)
        data_cond_grouped = np.median(data_cond, axis=0)

    if debug:
        time = np.arange(len_sig)
        sem_baseline = data_baseline.std(axis=0)/np.sqrt(data_baseline.shape[0])
        sem_cond = data_cond.std(axis=0)/np.sqrt(data_cond.shape[0])

        plt.plot(time, data_baseline_grouped, label='baseline', color='c')
        plt.fill_between(time, data_baseline_grouped-sem_baseline, data_baseline_grouped+sem_baseline, color='c', alpha=0.5)
        plt.plot(time, data_cond_grouped, label='cond', color='g')
        plt.fill_between(time, data_cond_grouped-sem_cond, data_cond_grouped+sem_cond, color='g', alpha=0.5)
        plt.legend()
        plt.show()

    obs_distrib = data_cond_grouped - data_baseline_grouped

    surr_distrib = np.zeros((n_surr, 2))

    #surr_i = 0
    for surr_i in range(n_surr):

        #### shuffle
        random_sel = np.random.choice(n_trial_tot, size=n_trial_tot, replace=False)
        data_shuffle_baseline = data_shuffle[random_sel[:n_trials_baselines]]
        data_shuffle_cond = data_shuffle[random_sel[n_trials_baselines:]]

        if mode_grouped == 'mean':
            diff_shuffle = np.mean(data_shuffle_cond, axis=0) - np.mean(data_shuffle_baseline, axis=0)
        elif mode_grouped == 'median':
            diff_shuffle = np.median(data_shuffle_cond, axis=0) - np.median(data_shuffle_baseline, axis=0)

        if debug:
            plt.plot(np.mean(data_shuffle_baseline, axis=0), label='baseline')
            plt.plot(np.mean(data_shuffle_cond, axis=0), label='cond')
            plt.legend()
            plt.show()

            plt.hist(np.median(data_shuffle_baseline, axis=0), bins=50, label='baseline', alpha=0.5)
            plt.hist(np.median(data_shuffle_cond, axis=0), bins=50, label='cond', alpha=0.5)
            plt.legend()
            plt.show()

        #### generate distrib
        if mode_generate_surr == 'minmax':
            surr_distrib[surr_i, 0], surr_distrib[surr_i, 1] = diff_shuffle.min(), diff_shuffle.max()
        elif mode_generate_surr == 'percentile':
            surr_distrib[surr_i, 0], surr_distrib[surr_i, 1] = np.percentile(diff_shuffle, 1), np.percentile(diff_shuffle, 99)    

    if debug:
        count, _, _ = plt.hist(surr_distrib[:,0], bins=50, color='k', alpha=0.5)
        count, _, _ = plt.hist(surr_distrib[:,1], bins=50, color='k', alpha=0.5)
        count, _, _ = plt.hist(obs_distrib, bins=50, label='obs', color='g')
        plt.vlines([np.median(surr_distrib[:,0])], ymin=0, ymax=count.max(), label='median', colors='r')
        plt.vlines([np.median(surr_distrib[:,1])], ymin=0, ymax=count.max(), colors='r')
        plt.vlines([np.mean(surr_distrib[:,0])], ymin=0, ymax=count.max(), label='meab', colors='b')
        plt.vlines([np.mean(surr_distrib[:,1])], ymin=0, ymax=count.max(), colors='b')
        plt.vlines([np.percentile(surr_distrib[:,0], 1)], ymin=0, ymax=count.max(), label='perc_1_99', colors='r', linestyles='--')
        plt.vlines([np.percentile(surr_distrib[:,1], 99)], ymin=0, ymax=count.max(), colors='r', linestyles='--')
        plt.vlines([np.percentile(surr_distrib[:,0], 2.5)], ymin=0, ymax=count.max(), label='perc_025_975', colors='r', linestyles='-.')
        plt.vlines([np.percentile(surr_distrib[:,1], 97.5)], ymin=0, ymax=count.max(), colors='r', linestyles='-.')
        plt.legend()
        plt.show()

        plt.plot(obs_distrib)
        plt.hlines([np.median(surr_distrib[:,0])], xmin=0, xmax=len_sig, label='median', colors='r')
        plt.hlines([np.median(surr_distrib[:,1])], xmin=0, xmax=len_sig, colors='r')
        plt.hlines([np.mean(surr_distrib[:,0])], xmin=0, xmax=len_sig, label='mean', colors='b')
        plt.hlines([np.mean(surr_distrib[:,1])], xmin=0, xmax=len_sig, colors='b')
        plt.hlines([np.percentile(surr_distrib[:,0], 1)], xmin=0, xmax=len_sig, label='perc_1_99', colors='r', linestyles='--')
        plt.hlines([np.percentile(surr_distrib[:,1], 99)], xmin=0, xmax=len_sig, colors='r', linestyles='--')
        plt.hlines([np.percentile(surr_distrib[:,0], 2.5)], xmin=0, xmax=len_sig, label='perc_025_975', colors='r', linestyles='-.')
        plt.hlines([np.percentile(surr_distrib[:,1], 97.5)], xmin=0, xmax=len_sig, colors='r', linestyles='-.')
        plt.legend()
        plt.show()

    if mode_select_thresh == 'percentile':
        # surr_dw, surr_up = np.percentile(surr_distrib[:,0], 2.5, axis=0), np.percentile(surr_distrib[:,1], 97.5, axis=0)
        surr_dw, surr_up = np.percentile(surr_distrib[:,0], 1, axis=0), np.percentile(surr_distrib[:,1], 99, axis=0)
    elif mode_select_thresh == 'mean':
        surr_dw, surr_up = np.mean(surr_distrib[:,0], axis=0), np.median(surr_distrib[:,1], axis=0)
    elif mode_select_thresh == 'median':
        surr_dw, surr_up = np.median(surr_distrib[:,0], axis=0), np.median(surr_distrib[:,1], axis=0)

    #### thresh data
    mask = (obs_distrib < surr_dw) | (obs_distrib > surr_up)

    if debug:

        plt.scatter(range(mask.size), mask)
        plt.show()

    if mask.sum() != 0:
    
        #### thresh cluster
        mask_thresh = mask.astype('uint8')
        nb_blobs, im_with_separated_blobs, stats, _ = cv2.connectedComponentsWithStats(mask_thresh)
        #### nb_blobs, im_with_separated_blobs, stats = nb clusters, clusters image with labeled clusters, info on clusters
        sizes = stats[1:, -1]
        nb_blobs -= 1
        # min_size = np.percentile(sizes,size_thresh)  
        min_size = len_sig*size_thresh_alpha  

        if debug:

            count, _, _ = plt.hist(sizes, bins=50, cumulative=True)
            plt.vlines(min_size, ymin=0, ymax=count.max(), colors='r')
            plt.show()

        mask_thresh = np.zeros_like(im_with_separated_blobs)
        for blob in range(nb_blobs):
            if sizes[blob] >= min_size:
                mask_thresh[im_with_separated_blobs == blob + 1] = 1

        mask_thresh = mask_thresh.reshape(-1)

        if debug:

            time = np.arange(data_baseline.shape[-1])
            sem_baseline = data_baseline.std(axis=0)/np.sqrt(data_baseline.shape[0])
            sem_cond = data_cond.std(axis=0)/np.sqrt(data_cond.shape[0])

            plt.plot(time, data_baseline_grouped, label='baseline', color='c')
            plt.fill_between(time, data_baseline_grouped-sem_baseline, data_baseline_grouped+sem_baseline, color='c', alpha=0.5)
            plt.plot(time, data_cond_grouped, label='cond', color='g')
            plt.fill_between(time, data_cond_grouped-sem_cond, data_cond_grouped+sem_cond, color='g', alpha=0.5)
            plt.fill_between(time, data_baseline_grouped.min(), data_cond_grouped.max(), where=mask, color='r', alpha=0.5)
            plt.title('mask not threshed')
            plt.legend()
            plt.show()

            plt.plot(time, data_baseline_grouped, label='baseline', color='c')
            plt.fill_between(time, data_baseline_grouped-sem_baseline, data_baseline_grouped+sem_baseline, color='c', alpha=0.5)
            plt.plot(time, data_cond_grouped, label='cond', color='g')
            plt.fill_between(time, data_cond_grouped-sem_cond, data_cond_grouped+sem_cond, color='g', alpha=0.5)
            plt.fill_between(time, data_baseline_grouped.min(), data_cond_grouped.max(), where=mask_thresh, color='r', alpha=0.5)
            plt.title('mask threshed')
            plt.legend()
            plt.show()

    else:

        mask_thresh = mask

    return mask_thresh




# data_baseline, data_cond, n_surr = tf_stretch_baseline_allsujet, tf_stretch_cond_allsujet, 100
def get_permutation_cluster_2d(data_baseline, data_cond, n_surr):

    """
    For data shape (trial,frequences,time)

    """

    #### define ncycle
    n_trial_baselines = data_baseline.shape[0]
    n_trial_cond = data_cond.shape[0]
    n_trial_selection = np.array([n_trial_baselines, n_trial_cond]).min()

    pixel_based_distrib = np.zeros((data_baseline.shape[1], 2))
    data_shuffle = np.zeros((n_trial_selection, data_baseline.shape[1], data_baseline.shape[-1]))

    #### space allocation
    _pixel_based_distrib = np.zeros((nfrex, n_surr, 2), dtype=np.float32)

    #surrogates_i = 0
    for surrogates_i in range(n_surr):

        print_advancement(surrogates_i, n_surr, steps=[25, 50, 75])

        #### random selection
        draw_indicator = np.random.randint(low=0, high=2, size=n_trial_selection)
        sel_baseline = np.random.choice(n_trial_baselines, size=(draw_indicator == 0).sum(), replace=False)
        sel_cond = np.random.choice(n_trial_cond, size=(draw_indicator == 1).sum(), replace=False)

        #### extract max min
        data_shuffle[:len(sel_baseline),:,:] = data_baseline[sel_baseline, :, :]
        data_shuffle[len(sel_baseline):,:,:] = data_cond[sel_cond, :, :]

        _min, _max = np.median(data_shuffle, axis=0).min(axis=1), np.median(data_shuffle, axis=0).max(axis=1)
        
        _pixel_based_distrib[:, surrogates_i, 0] = _min
        _pixel_based_distrib[:, surrogates_i, 1] = _max

    pixel_based_distrib[:,0], pixel_based_distrib[:,1] = np.median(_pixel_based_distrib[:,:,0], axis=1), np.median(_pixel_based_distrib[:,:,1], axis=1)
    # min, max = np.percentile(pixel_based_distrib_i[:,:,0], tf_percentile_sel_stats_dw, axis=1), np.percentile(pixel_based_distrib_i[:,:,1], tf_percentile_sel_stats_up, axis=1) 

    if debug:

        data_plot = np.median(data_cond, axis=0)

        time = np.arange(data_plot.shape[-1])

        plt.pcolormesh(time, frex, data_plot, shading='gouraud', cmap='seismic')
        plt.yscale('log')
        plt.show()

        #wavelet_i = 0
        for wavelet_i in range(20):
            count, _, _ = plt.hist(data_plot[wavelet_i, :], bins=500)
            plt.vlines([pixel_based_distrib[wavelet_i], pixel_based_distrib[wavelet_i]], ymin=0, ymax=count.max(), color='r')
            plt.show()

    #### thresh data
    data_thresh_dict = {}

    for type in ['baseline', 'cond']:

        if type == 'baseline':
            data_median = np.median(data_baseline, axis=0)
        elif type == 'cond':
            data_median = np.median(data_cond, axis=0)
        
        data_thresh = np.zeros(data_cond[0,:,:].shape)

        #wavelet_i = 0
        for wavelet_i in range(data_baseline.shape[1]):

            mask = np.logical_or(data_median[wavelet_i, :] < pixel_based_distrib[wavelet_i, 0], data_median[wavelet_i, :] > pixel_based_distrib[wavelet_i, 1])
            data_thresh[wavelet_i, :] = mask*1

        if debug:

            plt.pcolormesh(data_thresh)
            plt.show()

        #### thresh cluster
        data_thresh = data_thresh.astype('uint8')
        nb_blobs, im_with_separated_blobs, stats, _ = cv2.connectedComponentsWithStats(data_thresh)
        #### nb_blobs, im_with_separated_blobs, stats = nb clusters, clusters image with labeled clusters, info on clusters
        sizes = stats[1:, -1]
        nb_blobs -= 1
        min_size = np.percentile(sizes,tf_stats_percentile_cluster_size_thresh)  

        if debug:

            count, _, _ = plt.hist(sizes, bins=100)
            plt.vlines(np.percentile(sizes,95), ymin=0, ymax=count.max(), colors='r')
            plt.show()

        data_thresh = np.zeros_like(im_with_separated_blobs)
        for blob in range(nb_blobs):
            if sizes[blob] >= min_size:
                data_thresh[im_with_separated_blobs == blob + 1] = 1

        if debug:
        
            time = np.arange(data_median.shape[-1])

            plt.pcolormesh(time, frex, data_median, shading='gouraud', cmap='seismic')
            plt.contour(time, frex, data_thresh, levels=0, colors='g')
            plt.yscale('log')
            plt.show()

        data_thresh_dict[type] = data_thresh

    return data_thresh_dict['baseline'], data_thresh_dict['cond']



########################
######## FILTER ########
########################

#sig = data
def iirfilt(sig, srate, lowcut=None, highcut=None, order=4, ftype='butter', verbose=False, show=False, axis=0):

    if len(sig.shape) == 1:

        axis = 0

    if lowcut is None and not highcut is None:
        btype = 'lowpass'
        cut = highcut

    if not lowcut is None and highcut is None:
        btype = 'highpass'
        cut = lowcut

    if not lowcut is None and not highcut is None:
        btype = 'bandpass'

    if btype in ('bandpass', 'bandstop'):
        band = [lowcut, highcut]
        assert len(band) == 2
        Wn = [e / srate * 2 for e in band]
    else:
        Wn = float(cut) / srate * 2

    filter_mode = 'sos'
    sos = scipy.signal.iirfilter(order, Wn, analog=False, btype=btype, ftype=ftype, output=filter_mode)

    filtered_sig = scipy.signal.sosfiltfilt(sos, sig, axis=axis)

    return filtered_sig





########################################
######## CLUSTER WORKING ######## 
########################################

#name = 'test.png'
def export_fig(name, fig):

    path_pre = os.getcwd()

    os.chdir(path_general)

    fig.savefig(name)

    os.chdir(path_pre)




