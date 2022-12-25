import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt

def compute_avg(in_arr, org_arr, rad):
    init_coor = in_arr[0,0:2]
    log_ind = ((in_arr[:,0] - init_coor[0])/10)**2 + ((in_arr[:,1] - init_coor[1])/10)**2 < rad**2
    log_ind2 = ((org_arr[:,0] - init_coor[0])/10)**2 + ((org_arr[:,1] - init_coor[1])/10)**2 < rad**2
    SNR_mean = np.mean(org_arr[log_ind2][:,-1])    
    in_arr = np.delete(in_arr, np.where(log_ind)[0], axis=0)
    return [init_coor, SNR_mean, in_arr]    


def heat_map_plot(pd_frame):
    radius = 0.03 # in meters
    arr1 = pd_frame[['X-coordinate [m]','Y-coordinate [m]', 'SNR [dB]']].to_numpy()
    arr2 = pd_frame[['X-coordinate [m]','Y-coordinate [m]', 'SNR [dB]']].to_numpy()
    coor = []
    snr_val = []
    ln = len(arr1)
    while ln > 0:
        [cr, snr, arr1] = compute_avg(arr1, arr2, radius)  
        coor.append(cr)
        snr_val.append(snr)
        ln = len(arr1)    
    coor = np.asarray(coor)
    snr_val = np.asarray(snr_val)
    font_s = 16
    plt.rcParams.update({'font.size' : font_s})
    plt.figure(figsize=(6*1.5,7*1.5))    
    plt.scatter(coor[:,0], coor[:,1], c=snr_val, cmap='hot_r', s=60, zorder=20)  # , vmin = 10, vmax = 26
    plt.xlim([- 2.5, 10])
    plt.ylim([- 2.5, 14])
    plt.gca().invert_xaxis()
    plt.gca().invert_yaxis()
    plt.grid(True, which='both', linestyle='--', linewidth=0.7)
    plt.xlabel('x - coordinate [m]')
    plt.ylabel('y - coordinate [m]')
    a = plt.colorbar()
    a.set_label('SNR [dB]')
#     path = 'path'
    # filename = 'file_name.pdf'
    title_str = 'From : ' + str(datetime.datetime.fromtimestamp(pd_frame["Location Epoch Time [sec]"].to_numpy()[0]).strftime( "%Y-%m-%d %H:%M:%S")) +  '\n To : ' + str(datetime.datetime.fromtimestamp(pd_frame["Location Epoch Time [sec]"].to_numpy()[-1]).strftime( "%Y-%m-%d %H:%M:%S"))
    plt.title(title_str, fontsize=14)
    # plt.savefig(path + filename, bbox_inches='tight', format='pdf')
    plt.show()

def data_preprocess(t1, t2, t_int, sl_input, loc_input, dst_ind, wall_scen):    
    start_time, end_time = datetime.datetime(t1[0],t1[1],t1[2],t1[3],t1[4],t1[5]).timestamp(), datetime.datetime(t2[0],t2[1],t2[2],t2[3],t2[4],t2[5]).timestamp()
    total_run = int((end_time - start_time)/(t_int*60))
    print('Time interval is : ' + str(t_int) + ' mins')
    print('Total number of processing steps : ' + str(int(total_run)))    
    th = 0.005 # threshold
    sl_t, loc_t = sl_input[['Sidelink Epoch Time [sec]']], loc_input[['Location Epoch Time [sec]']]
    sl_ind = []
    loc_ind = []
    t_start = start_time    
    for i in range(total_run):        
        t_end = t_start + 60*t_int
        print('Processing ' + datetime.datetime.fromtimestamp(t_start).strftime( "%Y-%m-%d %H:%M:%S") + ' - ' + datetime.datetime.fromtimestamp(t_end).strftime( "%Y-%m-%d %H:%M:%S"))                
        sl_t_i = sl_t[(sl_t['Sidelink Epoch Time [sec]'] >= t_start) & (sl_t['Sidelink Epoch Time [sec]'] < t_end)]
        loc_t_i = loc_t[(loc_t['Location Epoch Time [sec]'] >= t_start) & (loc_t['Location Epoch Time [sec]'] < t_end)]  
        sl_t_i = sl_t_i.reset_index().add_suffix('_1')
        loc_t_i = loc_t_i.reset_index().add_suffix('_2')
        m = sl_t_i.merge(loc_t_i, how='cross')
        m = m[(m['Sidelink Epoch Time [sec]_1'] - m['Location Epoch Time [sec]_2']).abs().le(th)]
        res = pd.concat([sl_t_i[~sl_t_i.index_1.isin(m.index_1)], m, loc_t_i[~loc_t_i.index_2.isin(m.index_2)]], ignore_index=True)
        res = res.dropna(subset=['Sidelink Epoch Time [sec]_1','Location Epoch Time [sec]_2'])
        res = res.astype({'index_1': 'int32', 'index_2': 'int32'})        
        sl_ind.extend(res['index_1'].to_numpy())
        loc_ind.extend(res['index_2'].to_numpy())        
        t_start = t_end
        print('Done!')
        print('---------------')
    print('Merging...')
    merged = pd.concat([loc_input.loc[loc_ind].reset_index(drop=True), sl_input.loc[sl_ind].reset_index(drop=True)], axis=1)
    merged['Destination AGV Index'] = np.ones(len(merged))*dst_ind
    merged = merged.astype({'Destination AGV Index': 'int32'})        
    merged['Wall Scenario'] = np.tile(wall_scen, len(merged))    
    merged['Time Difference [sec]'] = np.abs(merged['Sidelink Epoch Time [sec]'] - merged['Location Epoch Time [sec]'])
    cols = merged.columns.tolist()
    print('Done')
    print('---------------')
    print('Processed data captured interval between ' + datetime.datetime.fromtimestamp(merged['Location Epoch Time [sec]'][0]).strftime( "%Y-%m-%d %H:%M:%S") + ' and ' + datetime.datetime.fromtimestamp(merged['Location Epoch Time [sec]'][len(merged)-1]).strftime( "%Y-%m-%d %H:%M:%S"))
    neworder = [0, 3, 19, 1, 2]
    neworder.extend(np.arange(4,19))
    cols = [cols[i] for i in neworder]
    return merged[cols]