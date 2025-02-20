
import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import pandas as pd
import joblib
import xarray as xr
import seaborn as sns
import gc

from n00_config_params import *
from n00bis_config_analysis_functions import *
from n00ter_stats import *

debug = False







#########################
######## PLOT TF ########
#########################



#chan = chan_list_eeg_short[0]
def save_tf_allsujet(chan):

    print(f'#### COMPUTE TF STATS {chan} ####', flush=True)

    #### identify if already computed for all
    os.chdir(os.path.join(path_results, 'TF'))

    if os.path.exists(f'allsujet_{chan}.png'):
        print(f'{chan} ALREADY COMPUTED', flush=True)
        return

    #### load data
    data_allcond = {}
    print('#### LOAD BASELINE ####', flush=True)

    os.chdir(os.path.join(path_precompute, 'TF', 'STRETCH'))

    tf_stretch_baseline_allsujet = np.zeros((len(sujet_list), nfrex, stretch_point_ERP))

    #sujet_i, sujet = 46, sujet_list[46]
    for sujet_i, sujet in enumerate(sujet_list):

        tf_stretch_baseline_allsujet[sujet_i,:,:] = np.load(f'{sujet}_VS_tf_stretch.npy')[np.where(chan_list_eeg_short == chan)[0][0],:,:]

    data_allcond['VS'] = np.median(tf_stretch_baseline_allsujet, axis=0)

    print('#### LOAD COND ####', flush=True)

    tf_stretch_cond_allsujet = np.zeros((len(sujet_list), nfrex, stretch_point_ERP))

    #sujet_i, sujet = 0, sujet_list[47]
    for sujet_i, sujet in enumerate(sujet_list):

        tf_stretch_cond_allsujet[sujet_i,:,:] = np.load(f'{sujet}_CHARGE_tf_stretch.npy')[np.where(chan_list_eeg_short == chan)[0][0],:,:]

    data_allcond['CHARGE'] = np.median(tf_stretch_cond_allsujet, axis=0)
    
    #### load data thresh
    os.chdir(os.path.join(path_precompute, 'TF', 'STRETCH_STATS'))
    
    stats_allcond = np.load(f'{chan}_allsujet_tf_STATS.npy')

    #### scale    
    vlim = np.abs(np.array([data_allcond['VS'].min(), data_allcond['CHARGE'].min(), data_allcond['VS'].max(), data_allcond['CHARGE'].max()])).max()

    #### plot 
    fig, axs = plt.subplots(ncols=len(cond_list))

    plt.suptitle(f'{chan} tf allsujet count:{len(sujet_list)}')

    fig.set_figheight(5)
    fig.set_figwidth(15)

    #### for plotting l_gamma down
    #c, cond = 1, cond_to_plot[1]
    for c, cond in enumerate(cond_list):

        ax = axs[c]
        ax.set_title(cond, fontweight='bold', rotation=0)

        #### generate time vec
        time_vec = np.arange(stretch_point_ERP)

        #### plot
        ax.pcolormesh(time_vec, frex, data_allcond[cond], vmin=-vlim, vmax=vlim, shading='gouraud', cmap=plt.get_cmap('seismic'))
        # ax.pcolormesh(time_vec, frex, data_allcond[cond], shading='gouraud', cmap=plt.get_cmap('seismic'))
        ax.set_yscale('log')

        #### stats
        ax.contour(time_vec, frex, stats_allcond, levels=0, colors='g')

        ax.vlines(stretch_point_ERP/2, ymin=frex[0], ymax=frex[-1], colors='g')
        ax.set_yticks([2,8,10,30,50,100,150], labels=[2,8,10,30,50,100,150])
        ax.set_ylim(frex[0], frex[-1])

    #plt.show()

    #### save
    os.chdir(os.path.join(path_results, 'TF', 'allsujet'))
    fig.savefig(f'{chan}.jpeg', dpi=150)

    fig.clf()
    plt.close('all')
    gc.collect()



   
#chan = chan_list_eeg_short[0]
def save_tf_subjectwise(chan):

    print(f'#### COMPUTE TF STATS {chan} ####', flush=True)

    #### identify if already computed for all
    os.chdir(os.path.join(path_results, 'TF'))

    if os.path.exists(f'allsujet_{chan}.png'):
        print(f'{chan} ALREADY COMPUTED', flush=True)
        return

    #### load data
    print('#### LOAD BASELINE ####', flush=True)

    os.chdir(os.path.join(path_precompute, 'TF', 'STRETCH'))

    tf_stretch_baseline_allsujet = np.zeros((len(sujet_list), nfrex, stretch_point_ERP))

    #sujet_i, sujet = 46, sujet_list[46]
    for sujet_i, sujet in enumerate(sujet_list):

        tf_stretch_baseline_allsujet[sujet_i,:,:] = np.load(f'{sujet}_VS_tf_stretch.npy')[np.where(chan_list_eeg_short == chan)[0][0],:,:]

    print('#### LOAD COND ####', flush=True)

    tf_stretch_cond_allsujet = np.zeros((len(sujet_list), nfrex, stretch_point_ERP))

    #sujet_i, sujet = 0, sujet_list[47]
    for sujet_i, sujet in enumerate(sujet_list):

        tf_stretch_cond_allsujet[sujet_i,:,:] = np.load(f'{sujet}_CHARGE_tf_stretch.npy')[np.where(chan_list_eeg_short == chan)[0][0],:,:]    

    data_allcond = {'VS' : tf_stretch_baseline_allsujet, 'CHARGE' : tf_stretch_cond_allsujet}

    #### plot 
    #sujet_i, sujet = 0, sujet_list[0]
    for sujet_i, sujet in enumerate(sujet_list):

        fig, axs = plt.subplots(ncols=len(cond_list))

        plt.suptitle(f'{sujet} {chan} tf allsujet count:{len(sujet_list)}')

        fig.set_figheight(5)
        fig.set_figwidth(15)

        #### for plotting l_gamma down
        #c, cond = 1, cond_to_plot[1]
        for c, cond in enumerate(cond_list):

            ax = axs[c]
            ax.set_title(cond, fontweight='bold', rotation=0)

            #### generate time vec
            time_vec = np.arange(stretch_point_ERP)

            #### plot
            # ax.pcolormesh(time_vec, frex, data_allcond[cond], vmin=-vlim, vmax=vlim, shading='gouraud', cmap=plt.get_cmap('seismic'))
            ax.pcolormesh(time_vec, frex, data_allcond[cond][sujet_i,:,:], shading='gouraud', cmap=plt.get_cmap('seismic'))
            ax.set_yscale('log')

            ax.vlines(stretch_point_ERP/2, ymin=frex[0], ymax=frex[-1], colors='g')
            ax.set_yticks([2,8,10,30,50,100,150], labels=[2,8,10,30,50,100,150])
            ax.set_ylim(frex[0], frex[-1])

        #plt.show()

        #### save
        os.chdir(os.path.join(path_results, 'TF', 'subjectwise'))
        fig.savefig(f'{sujet}_{chan}.jpeg', dpi=150)

        fig.clf()
        plt.close('all')
        gc.collect()


             

    

#################################
######## TOPOPLOT TF ########
#################################



def save_topoplot_allsujet():

    print(f'#### COMPUTE TOPOPLOT ####', flush=True)

    #### params
    phase_list = ['I', 'T_IE', 'E', 'T_EI']
    phase_shift = 125 
    # 0-125, 125-375, 375-625, 625-875, 875-1000, shift on origial TF
    phase_vec = {'I' : np.arange(250), 'T_IE' : np.arange(250)+250, 'E' : np.arange(250)+500, 'T_EI' : np.arange(250)+750} 

    point_thresh = 0.05

    mask_params = dict(markersize=15, markerfacecolor='y')

    ch_types = ['eeg'] * len(chan_list_eeg_short)
    info = mne.create_info(chan_list_eeg_short.tolist(), ch_types=ch_types, sfreq=srate)
    info.set_montage('standard_1020')

    #### load data
    print('#### LOAD DATA ####', flush=True)

    tf = np.zeros((len(cond_list), len(chan_list_eeg_short), nfrex, stretch_point_ERP))
    tf_stretch_allsujet = np.zeros((len(sujet_list), len(chan_list_eeg_short), nfrex, stretch_point_ERP))

    os.chdir(os.path.join(path_precompute, 'TF', 'STRETCH'))

    for cond_i, cond in enumerate(cond_list):

        print(cond)

        #sujet_i, sujet = 46, sujet_list[46]
        for sujet_i, sujet in enumerate(sujet_list):

            tf_stretch_allsujet[sujet_i,:,:,:] = np.load(f'{sujet}_{cond}_tf_stretch.npy')

        tf[cond_i, :, :, :] = np.median(tf_stretch_allsujet, axis=0)

    tf_diff = tf[1,:,:,:] - tf[0,:,:,:]

    if debug:

        plt.pcolormesh(tf_diff[0,:,:])
        plt.show()
    
    #### load stats
    print('#### LOAD STATS ####', flush=True)

    os.chdir(os.path.join(path_precompute, 'TF', 'STRETCH_STATS'))

    stats_tf = np.zeros((len(chan_list_eeg_short), nfrex, stretch_point_ERP))
    
    for chan_i, chan in enumerate(chan_list_eeg_short):

        stats_tf[chan_i,:] = np.load(f'{chan}_allsujet_tf_STATS.npy')

    #### shift data
    tf_diff_shift = np.concat((tf_diff[:,:,phase_shift:], tf_diff[:,:,:phase_shift]), axis=-1)
    stats_tf_shift = np.concat((stats_tf[:,:,phase_shift:], stats_tf[:,:,:phase_shift]), axis=-1)

    if debug:

        plt.pcolormesh(tf_diff_shift[0,:,:])
        plt.show()

    #### chunk data
    print('CHUNK')
    topoplot_data = np.zeros((len(phase_list), len(freq_band_fc_list), len(chan_list_eeg_short)))
    topoplot_signi = np.zeros((len(phase_list), len(freq_band_fc_list), len(chan_list_eeg_short)), dtype='bool')

    #phase_i, phase = 0, phase_list[0]
    for phase_i, phase in enumerate(phase_list):

        #band_i, band = 0, freq_band_fc_list[0]
        for band_i, band in enumerate(freq_band_fc_list):

            frex_mask = (frex >= freq_band_fc[band][0]) & (frex < freq_band_fc[band][1]) 
            tf_chunk = tf_diff_shift[:,:,phase_vec[phase]][:,frex_mask,:]
            stats_chunk = stats_tf_shift[:,:,phase_vec[phase]][:,frex_mask,:]

            for chan_i, chan in enumerate(chan_list_eeg_short):

                if stats_chunk[chan_i,:,:].sum() >= point_thresh*stats_chunk[chan_i,:,:].size:

                    topoplot_data[phase_i, band_i, chan_i] = np.median(tf_chunk[chan_i,:,:][stats_chunk[chan_i,:,:].astype('bool')])
                    topoplot_signi[phase_i, band_i, chan_i] = True

    #### vlim
    vlim = np.zeros((len(freq_band_fc_list)))
    #band_i, band = 0, freq_band_fc_list[0]
    for band_i, band in enumerate(freq_band_fc_list):

        vlim[band_i] = np.abs(np.array([topoplot_data[:, band_i, :].reshape(-1).min(), topoplot_data[:, band_i, :].reshape(-1).max()])).max()
 
    #### plot
    os.chdir(os.path.join(path_results, 'TF', 'allsujet'))

    #band_i, band = 0, freq_band_fc_list[0]
    for band_i, band in enumerate(freq_band_fc_list):

        fig, axs = plt.subplots(nrows=1, ncols=len(phase_list), figsize=(15,5))

        #phase_i, phase = 0, phase_list[0]
        for phase_i, phase in enumerate(phase_list):

            ax = axs[phase_i]

            mne.viz.plot_topomap(data=topoplot_data[phase_i, band_i, :], axes=ax, show=False, names=chan_list_eeg_short, pos=info,
                            mask=topoplot_data[phase_i, band_i, :], mask_params=mask_params, vlim=(-vlim[band_i], vlim[band_i]), cmap='seismic', extrapolate='local')

            ax.set_title(f'{phase}')

        plt.suptitle(f'{band} lim:{np.round(vlim[band_i],2)}')

        # plt.show()

        fig.savefig(f"topoplot_{band}_allsujet.jpeg")

        plt.close('all')
        
        






########################################
######## EXECUTE AND SAVE ########
########################################


if __name__ == '__main__':

    #chan = chan_list_eeg_short[0]
    for chan in chan_list_eeg_short:
                
        save_tf_allsujet(chan)
        save_tf_subjectwise(chan)

    save_topoplot_allsujet()

        



import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import mixedlm
import seaborn as sns
import matplotlib.pyplot as plt

# Set random seed for reproducibility
np.random.seed(42)

# Simulate data
n_groups = 10
obs_per_group = 20
groups = np.repeat([f'G{i}' for i in range(1, n_groups + 1)], obs_per_group)

# Fixed effects
ages = np.random.randint(20, 60, size=n_groups * obs_per_group)
genders = np.random.choice(['M', 'F'], size=n_groups * obs_per_group)
treatments = np.random.choice(['A', 'B'], size=n_groups * obs_per_group)

# Induce an effect for treatment (e.g., treatment B increases y by 5)
treatment_effect = {'A': 0, 'B': 5}
y_base = 50 + 0.5 * ages  # Base effect of age on y
y_treatment = np.array([treatment_effect[t] for t in treatments])
random_group_effect = np.repeat(np.random.normal(0, 2, n_groups), obs_per_group)  # Random effects
random_noise = np.random.normal(0, 3, n_groups * obs_per_group)  # Residuals

# Dependent variable
y = y_base + y_treatment + random_group_effect + random_noise

# Create DataFrame
df = pd.DataFrame({
    'y': y,
    'age': ages,
    'gender': genders,
    'treatment': treatments,
    'group': groups
})

# Convert categorical variables
df['gender'] = df['gender'].astype('category')
df['treatment'] = df['treatment'].astype('category')

# Display the first few rows of the simulated data
print(df.head())

# Visualize the data
sns.boxplot(x='treatment', y='y', data=df)
plt.title("Effect of Treatment on y")
plt.show()

# --- Mixed Model Analysis ---
# Define the mixed-effects model
model = mixedlm("y ~ age + gender + treatment", df, groups=df["group"])
result = model.fit()

# Display the summary
print(result.summary())

# --- Assumption Checks ---

# 1. Residual Plot
df['fitted'] = result.fittedvalues
df['residuals'] = result.resid

sns.scatterplot(x='fitted', y='residuals', data=df)
plt.axhline(0, color='red', linestyle='--')
plt.title("Residuals vs Fitted Values")
plt.xlabel("Fitted Values")
plt.ylabel("Residuals")
plt.show()

# 2. Normality of Residuals
sns.histplot(df['residuals'], kde=True, bins=20)
plt.title("Histogram of Residuals")
plt.show()

# 3. Random Effect Assumptions
# Extract random effects
random_effects = result.random_effects
random_effects_values = [v[0] for v in random_effects.values()]

sns.histplot(random_effects_values, kde=True, bins=10)
plt.title("Histogram of Random Effects")
plt.xlabel("Random Effect Value")
plt.ylabel("Frequency")
plt.show()

