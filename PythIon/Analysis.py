# -*- coding: utf-8 -*-
import os
from functools import partial
from tqdm import tqdm
from scipy import signal
import numpy as np
import scipy.stats as spstat
import multiprocessing as mp
from multiprocessing import shared_memory

from .BaseApp import *
from .ui.subeventstatesettings import *
from .ui.analysissettings import *
from .CUSUMV3 import detect_cusum

class Config:
    def __init__(self):
        self.baseline_A = np.nan
        self.baseline_std_A = np.nan
        self.threshold_A = 0.3e-9
        self.enable_subevent_state_detection = True
        self.maxNsta = 16
        self.cusum_stepsize = 10
        self.cusum_threshhold = 30
        self.merge_delta_blockade = 0.02
        self.prefilt_window_us = 100
        self.state_min_duration_us = 150
    def __str__(self):
        if self.enable_subevent_state_detection:
            s = (
            f' ==== Event and Subevent State Detection Configurations ==== \n'
            f'baseline_nA: {self.baseline_A*1e9}\n'
            f'baseline_std_nA: {self.baseline_std_A*1e9}\n'
            f'threshold_nA: {self.threshold_A*1e9}\n'
            f'enable_subevent_state_detection: {self.enable_subevent_state_detection}\n'
            f'maxNsta: {self.maxNsta}\n'
            f'cusum_stepsize: {self.cusum_stepsize}\n'
            f'cusum_threshhold: {self.cusum_threshhold}\n'
            f'merge_delta_blockade: {self.merge_delta_blockade}\n'
            f'prefilt_window_us: {self.prefilt_window_us}\n'
            f'state_min_duration_us: {self.state_min_duration_us}\n'
            f'============================================================'
            )
        else:
            s = (
            f' ==== Event Detection Configurations ==== \n'
            f'baseline_nA: {self.baseline_A*1e9}\n'
            f'baseline_std_nA: {self.baseline_std_A*1e9}\n'
            f'threshold_nA: {self.threshold_A*1e9}\n'
            f'enable_subevent_state_detection: {self.enable_subevent_state_detection}\n'
            f'============================================================'
            )
        return s

class AnalysisResults:
    def __init__(self, analysis_config:Config):
        self.analysis_config = analysis_config
        self.result_spec = [
            ('id', int, r'%d'),
            ('N_child', int, r'%d'),
            ('parent_id', int, r'%d'),
            ('category', '|U16', r'%s'),
            ('index',int, r'%d'),
            ('seg', int, r'%d'), 
            ('local_startpt', int, r'%d'), 
            ('local_endpt', int, r'%d'),
            ('global_startpt',int, r'%d'),
            ('global_endpt',int, r'%d'),
            ('deli',float, r'%.18e'),
            ('frac',float, r'%.18e'),
            ('dwell',float, r'%.18e'),
            ('dt', float, r'%.18e'),
            ('mean', float, r'%.18e'),
            ('stdev', float, r'%.18e'),
            ('skewness', float, r'%.18e'),
            ('kurtosis', float, r'%.18e'),
            ('offset_first_min', int, r'%d'),
            ('stdev_tt', float, r'%.18e'),
            ('skewness_tt', float, r'%.18e'),
            ('kurtosis_tt', float, r'%.18e')
        ]
        self.result_dtype = np.dtype([(spec[0], spec[1]) for spec in self.result_spec])
        self.result_nullvalue = np.array(tuple(np.nan if spec[1] is float else -1 for spec in self.result_spec), dtype=self.result_dtype)
        self.result_nullvalue['N_child'] = 0
        self.result_nullvalue['category'] = 'Null'

        self.tables : dict[str, np.ndarray]= dict()

    def newResultTable(self):
        return np.array([],dtype=self.result_dtype)

class SubEventStateSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent:BaseAppMainWindow):
        self.parent = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_SubeventStateDetectionSettingsDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)

        analysis_config : Config = self.parent.analysis_config
        self.ui.lineEdit_MaxNumOfStates.setText(str(analysis_config.maxNsta))
        self.ui.lineEdit_CUSUMStepSize.setText(str(analysis_config.cusum_stepsize))
        self.ui.lineEdit_CUSUMThresh.setText(str(analysis_config.cusum_threshhold))
        self.ui.lineEdit_MergeBlockadeThresh.setText(str(analysis_config.merge_delta_blockade))
        self.ui.lineEdit_WinOfSmoothing.setText(str(analysis_config.prefilt_window_us))
        self.ui.lineEdit_MinStateDuration.setText(str(analysis_config.state_min_duration_us))


    def dialogAccept(self):
        analysis_config : Config = self.parent.analysis_config
        analysis_config.maxNsta = float(self.ui.lineEdit_MaxNumOfStates.text())
        analysis_config.cusum_stepsize = float(self.ui.lineEdit_CUSUMStepSize.text())
        analysis_config.cusum_threshhold = float(self.ui.lineEdit_CUSUMThresh.text())
        analysis_config.merge_delta_blockade = float(self.ui.lineEdit_MergeBlockadeThresh.text())
        analysis_config.prefilt_window_us = float(self.ui.lineEdit_WinOfSmoothing.text())
        analysis_config.state_min_duration_us = float(self.ui.lineEdit_MinStateDuration.text())
        self.close()

    def dialogReject(self):
        self.close()

class AnalyzeDialog(QtWidgets.QDialog):
    def __init__(self, parent:BaseAppMainWindow):
        self.parent = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_AnalyzeForEventsDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)
        self.ui.radioButton_nA.toggled.connect(self.unitChanged)
        self.ui.radioButton_pctBaseline.toggled.connect(self.unitChanged)
        self.ui.lineEdit_threshold.editingFinished.connect(self.valueChanged)
        analysis_config:Config = self.parent.analysis_config
        analysis_config.baseline_A = self.parent.ui_baseline
        analysis_config.baseline_std_A = self.parent.ui_baseline_std
        self.unitChanged()
    
    def unitChanged(self):
        analysis_config:Config = self.parent.analysis_config
        if self.ui.radioButton_nA.isChecked():
            self.ui.lineEdit_threshold.setText(str(analysis_config.threshold_A*1e9))
        elif self.ui.radioButton_pctBaseline.isChecked():
            self.ui.lineEdit_threshold.setText(str(analysis_config.threshold_A/self.parent.perfiledata.baseline*1e2))
    
    def valueChanged(self):
        analysis_config:Config = self.parent.analysis_config
        if self.ui.radioButton_nA.isChecked():
            analysis_config.threshold_A = float(self.ui.lineEdit_threshold.text())*1e-9
        elif self.ui.radioButton_pctBaseline.isChecked():
            analysis_config.threshold_A = float(self.ui.lineEdit_threshold.text())/1e2 * self.parent.perfiledata.baseline
        self.parent.updateThresholdLine()
    
    def dialogAccept(self):
        analysis_config:Config = self.parent.analysis_config
        analysis_config.enable_subevent_state_detection = self.ui.checkBox_enableSubeventStateDetection.isChecked()
        self.parent.enable_save_analysis = self.ui.checkBox_enableSaveReport.isChecked()
        self.close()
    
    def dialogReject(self):
        self.close()

def merge_oversegmentation(trough_trough_data, cusum_res, merge_delta_I):
    state_starts = cusum_res['starts']
    n_states = cusum_res['nStates']
    getData = lambda k: trough_trough_data[state_starts[k]:state_starts[k+1]]
    mean_I_1 = np.mean(getData(0))
    ndx_starts_to_retain = [0]
    for ksta in range(n_states-1):
        mean_I_0 = mean_I_1
        mean_I_1 = np.mean(getData(ksta+1))
        if abs(mean_I_1 - mean_I_0) > merge_delta_I:
            ndx_starts_to_retain.append(ksta+1)
    ndx_starts_to_retain.append(n_states)
    res = dict()
    res['nStates'] = len(ndx_starts_to_retain)-1
    res['starts'] = np.array([state_starts[k] for k in ndx_starts_to_retain])
    return res

def cusum_worker_(startendpoints, shm_name, data_dtype, data_shape, cusum_std,  cusum_minlen, cusum_maxNsta, cusum_stepsize, cusum_threshhold, prefilt_oneside_window, merge_delta_I):
    startpoint, endpoint = startendpoints
    shm = shared_memory.SharedMemory(name=shm_name)
    trough_trough_data = np.ndarray(data_shape, dtype=data_dtype, buffer=shm.buf)[startpoint:endpoint]
    cusum_res = detect_cusum(trough_trough_data, cusum_std, minlength=cusum_minlen, maxstates=cusum_maxNsta, stepsize=cusum_stepsize, threshhold=cusum_threshhold, moving_oneside_window=prefilt_oneside_window)
    mo_cusum_res = merge_oversegmentation(trough_trough_data, cusum_res, merge_delta_I)
    shm.close()
    return mo_cusum_res


def computeAnalysis(app:BaseAppMainWindow):
    app.printlog('Computing Analysis...')
    analysis_config : Config = app.analysis_config
    analysis_results = AnalysisResults(analysis_config)
    app.printlog(f'Subevent analysis with configuration: \n{analysis_config}\n')
    
    # Set up cusum detection parameters
    state_min_duration_us = analysis_config.state_min_duration_us
    cusum_minlen = int(state_min_duration_us*app.perfiledata.ADC_samplerate_Hz*1e-6)
    prefilt_window_us = analysis_config.prefilt_window_us
    prefilt_oneside_window = int(prefilt_window_us/2*app.perfiledata.ADC_samplerate_Hz*1e-6)
    cusum_maxNsta = analysis_config.maxNsta-1
    cusum_stepsize = analysis_config.cusum_stepsize
    cusum_threshhold = analysis_config.cusum_threshhold
    merge_delta_blockade = analysis_config.merge_delta_blockade
    merge_delta_I = merge_delta_blockade*analysis_config.baseline_A

    # Set up pool of workers for parallel execution
    Ncpu = os.cpu_count()
    if Ncpu>2:
        pool = mp.Pool(processes=Ncpu-2)
    else:
        pool = mp.Pool(processes=1)

    startpoints = []
    endpoints = []
    mins = []

    # app.result_spec = [
    #         ('id', int, r'%d'),
    #         ('N_child', int, r'%d'),
    #         ('parent_id', int, r'%d'),
    #         ('category', '|U16', r'%s'),
    #         ('index',int, r'%d'),
    #         ('seg', int, r'%d'), 
    #         ('local_startpt', int, r'%d'), 
    #         ('local_endpt', int, r'%d'),
    #         ('global_startpt',int, r'%d'),
    #         ('global_endpt',int, r'%d'),
    #         ('deli',float, r'%.18e'),
    #         ('frac',float, r'%.18e'),
    #         ('dwell',float, r'%.18e'),
    #         ('dt', float, r'%.18e'),
    #         ('mean', float, r'%.18e'),
    #         ('stdev', float, r'%.18e'),
    #         ('skewness', float, r'%.18e'),
    #         ('kurtosis', float, r'%.18e'),
    #         ('offset_first_min', int, r'%d'),
    #         ('stdev_tt', float, r'%.18e'),
    #         ('skewness_tt', float, r'%.18e'),
    #         ('kurtosis_tt', float, r'%.18e')
    #     ]
    # result_dtype = np.dtype([(spec[0], spec[1]) for spec in app.result_spec])
    # app.result_dtype = result_dtype
    # result_nullvalue = np.array(tuple(np.nan if spec[1] is float else -1 for spec in app.result_spec), dtype=result_dtype)
    # result_nullvalue['N_child'] = 0
    # result_nullvalue['category'] = 'Null'
    # app.result_nullvalue = result_nullvalue
    result_nullvalue = analysis_results.result_nullvalue
    event_result_table = analysis_results.newResultTable()
    state_result_table = analysis_results.newResultTable()
    result_dtype = analysis_results.result_dtype

    id_counter = 0
    event_index = 0

#### find all points below threshold ####
    for k in tqdm(range(app.perfiledata.data.Nseg),desc='Segment->Event'):
        seg_filt = app.perfiledata.data.filt[k]
        seg_range = app.perfiledata.data.srange[k]

        below = np.where(seg_filt < analysis_config.threshold_A)[0]

#### locate the points where the current crosses the threshold ####

        startandend = np.diff(below)
        if len(startandend) < 1:
            continue
        startpoints = np.insert(startandend, 0, 2)
        endpoints = np.insert(startandend, -1, 2)
        startpoints = np.where(startpoints>1)[0]
        endpoints = np.where(endpoints>1)[0]
        startpoints = below[startpoints]
        endpoints = below[endpoints]

#### Eliminate events that start before file or end after file ####

        if startpoints[0] == 0:
            startpoints = np.delete(startpoints,0)
            endpoints = np.delete(endpoints,0)
        if endpoints [-1] == len(seg_filt)-1:
            startpoints = np.delete(startpoints,-1)
            endpoints = np.delete(endpoints,-1)

#### Track points back up to baseline to find true start and end ####

        numberofevents=len(startpoints)
        # highthresh = app.ui_baseline - app.ui_baseline_std
        highthresh = analysis_config.baseline_A - analysis_config.baseline_std_A

        for j in range(numberofevents):
            sp = startpoints[j] #mark initial guess for starting point
            while seg_filt[sp] < highthresh and sp > 0:
                sp = sp-1 # track back until we return to baseline
            startpoints[j] = sp # mark true startpoint

            ep = endpoints[j] #repeat process for end point
            if ep == len(seg_filt) -1:  # sure that the current returns to baseline
                endpoints[j] = 0              # before file ends. If not, mark points for
                startpoints[j] = 0              # deletion and break from loop
                ep = 0
                break
            while seg_filt[ep] < highthresh:
                ep = ep+1
                if ep == len(seg_filt) -1:  # sure that the current returns to baseline
                    endpoints[j] = 0              # before file ends. If not, mark points for
                    startpoints[j] = 0              # deletion and break from loop
                    ep = 0
                    break
                else:
                    try:
                        if ep > startpoints[j+1]: # if we hit the next startpoint before we
                            startpoints[j+1] = 0    # return to baseline, mark for deletion
                            endpoints[j] = 0                  # and break out of loop
                            ep = 0
                            break
                    except:
                        IndexError
                endpoints[j] = ep

        startpoints = startpoints[startpoints!=0] # delete those events marked for
        endpoints = endpoints[endpoints!=0]       # deletion earlier
        seg_numberofevents = len(startpoints)

        if len(startpoints) > len(endpoints):
            startpoints = np.delete(startpoints, -1)
            seg_numberofevents = len(startpoints)


#### Now we want to move the endpoints to be the last minimum for each ####
#### event so we find all minimas for each event, and set endpoint to last ####

        seg_deli_list = np.zeros(seg_numberofevents)
        seg_dwell_list = np.zeros(seg_numberofevents)

        seg_first_min_offset_list = np.full(seg_numberofevents, -1, dtype=int)
        # -1 initialized
        # -2 only one minimum in the event, which is its end.

        for i in range(seg_numberofevents):
            mins = np.array(signal.argrelmin(seg_filt[startpoints[i]:endpoints[i]])[0] + startpoints[i])
            # mins = mins[seg_filt[mins] < app.baseline - 4*app.baseline_std]
            mins = mins[seg_filt[mins] < (analysis_config.baseline_A + np.mean(seg_filt[startpoints[i]:endpoints[i]]))/2]
            if len(mins) == 1:
                pass
                seg_deli_list[i] = analysis_config.baseline_A - min(seg_filt[startpoints[i]:endpoints[i]])
                seg_dwell_list[i] = (endpoints[i]-startpoints[i])*1e6/app.perfiledata.ADC_samplerate_Hz
                endpoints[i] = mins[0]
                seg_first_min_offset_list[i] = -2
            elif len(mins) > 1:
                seg_deli_list[i] = analysis_config.baseline_A - np.mean(seg_filt[mins[0]:mins[-1]])
                endpoints[i] = mins[-1]
                seg_dwell_list[i] = (endpoints[i]-startpoints[i])*1e6/app.perfiledata.ADC_samplerate_Hz
                seg_first_min_offset_list[i] = mins[0]-startpoints[i]

        valid_events = np.logical_and(seg_deli_list != 0, seg_dwell_list != 0)
        startpoints = startpoints[valid_events]
        endpoints = endpoints[valid_events]
        seg_first_min_offset_list = seg_first_min_offset_list[valid_events]
        seg_deli_list = seg_deli_list[valid_events]
        seg_dwell_list = seg_dwell_list[valid_events]
        seg_frac_list = seg_deli_list/analysis_config.baseline_A
        seg_dt_list = np.array(np.nan)
        seg_dt_list=np.append(seg_dt_list,np.diff(startpoints)/app.perfiledata.ADC_samplerate_Hz)
        seg_numberofevents = len(startpoints)
        seg_noise = np.array([np.std(seg_filt[x:endpoints[i]]) for i,x in enumerate(startpoints)])
        seg_skew = np.array([spstat.skew(seg_filt[x:endpoints[i]]) for i,x in enumerate(startpoints)])
        seg_kurt = np.array([spstat.kurtosis(seg_filt[x:endpoints[i]]) for i,x in enumerate(startpoints)])
        seg_stdev_tt = np.full(seg_numberofevents, np.nan)
        seg_skew_tt = np.full(seg_numberofevents, np.nan)
        seg_kurt_tt = np.full(seg_numberofevents, np.nan)

        for kx, x in enumerate(startpoints):
            first_min_offset = seg_first_min_offset_list[kx]
            if first_min_offset>0:
                trough_trough_data = seg_filt[x+first_min_offset: endpoints[kx]]
                if len(trough_trough_data) == 0:
                    continue
                seg_stdev_tt[kx] = np.std(trough_trough_data)
                seg_skew_tt[kx] = spstat.skew(trough_trough_data)
                seg_kurt_tt[kx] = spstat.kurtosis(trough_trough_data)

        if seg_numberofevents>0:
            seg_result_table = np.full(seg_numberofevents, result_nullvalue, dtype=result_dtype)
            seg_result_table['id'] = np.arange(seg_numberofevents) + id_counter
            seg_result_table['category'] = 'Event'
            seg_result_table['index'] = np.arange(seg_numberofevents) + event_index
            seg_result_table['seg'] = k
            seg_result_table['local_startpt'] = startpoints
            seg_result_table['local_endpt'] = endpoints
            seg_result_table['global_startpt'] = startpoints + seg_range[0]
            seg_result_table['global_endpt'] = endpoints + seg_range[0]
            seg_result_table['deli'] = seg_deli_list
            seg_result_table['frac'] = seg_frac_list
            seg_result_table['dwell'] = seg_dwell_list
            seg_result_table['dt'] = seg_dt_list
            seg_result_table['mean'] = np.array([np.mean(seg_filt[x:endpoints[i]]) for i,x in enumerate(startpoints)])
            seg_result_table['stdev'] = seg_noise
            seg_result_table['skewness'] = seg_skew
            seg_result_table['kurtosis'] = seg_kurt
            seg_result_table['offset_first_min'] = seg_first_min_offset_list
            seg_result_table['stdev_tt'] = seg_stdev_tt
            seg_result_table['skewness_tt'] = seg_skew_tt
            seg_result_table['kurtosis_tt'] = seg_kurt_tt
            event_result_table = np.append(event_result_table, seg_result_table)


        if analysis_config.enable_subevent_state_detection:
            # Set up shared memory for parallel cusum detection
            shm = shared_memory.SharedMemory(create=True, size=seg_filt.nbytes)
            shared_seg_filt = np.ndarray(seg_filt.shape, dtype=seg_filt.dtype, buffer=shm.buf)
            shared_seg_filt[:] = seg_filt
            shm_name = shm.name

            # Set up cusum detection parallel worker
            cusum_worker = partial(
                cusum_worker_, 
                shm_name=shm_name, 
                data_dtype=seg_filt.dtype, 
                data_shape=seg_filt.shape, 
                cusum_std=analysis_config.baseline_std_A, 
                cusum_minlen=cusum_minlen, 
                cusum_maxNsta=cusum_maxNsta, 
                cusum_stepsize=cusum_stepsize, 
                cusum_threshhold=cusum_threshhold, 
                prefilt_oneside_window=prefilt_oneside_window, 
                merge_delta_I=merge_delta_I
            )

            # Parallel cusum detection
            startendpoints_list = []
            event_kx_list = []
            for kx in range(seg_numberofevents):
                first_min_offset = seg_first_min_offset_list[kx]
                if first_min_offset>0:
                    startpoint = startpoints[kx] + first_min_offset
                    endpoint = endpoints[kx]
                    if endpoint-startpoint < cusum_minlen:
                        continue
                    startendpoints_list.append((startpoint, endpoint))
                    event_kx_list.append(kx)
            mo_cusum_res_iter = pool.imap(cusum_worker, startendpoints_list)
            mo_cusum_res_list = list(tqdm(mo_cusum_res_iter, total=len(startendpoints_list), desc='Event->State', leave=False))
            mo_cusum_res_list = [(event_kx_list[k], mo_cusum_res) for k, mo_cusum_res in enumerate(mo_cusum_res_list)]
            shm.close()
            shm.unlink()


            # Fallback seraial cusum detection

            # mo_cusum_res_list = []
            # for kx, x in enumerate(tqdm(startpoints,leave=False, desc='Event->State')):
            #     first_min_offset = seg_first_min_offset_list[kx]
            #     if first_min_offset>0:
            #         trough_trough_data = seg_filt[x+first_min_offset: endpoints[kx]]
            #         if len(trough_trough_data) == 0:
            #             continue
            #         # cusum_res = detect_cusum(trough_trough_data, seg_stdev_tt[kx], 1, minlength=cusum_minlen, maxstates=cusum_maxNsta, stepsize=5, threshhold=10)
            #         cusum_res = detect_cusum(trough_trough_data, analysis_config.baseline_A_std, minlength=cusum_minlen,
            #                                     maxstates=cusum_maxNsta, stepsize=cusum_stepsize, threshhold=cusum_threshhold, moving_oneside_window=prefilt_oneside_window)
            #         mo_cusum_res = merge_oversegmentation(trough_trough_data, cusum_res, merge_delta_I)
            #         mo_cusum_res_list.append((kx,mo_cusum_res))


            # TODO Construct a reverse lookup table for event to segment

            for res_item in mo_cusum_res_list:
                kx, mo_cusum_res = res_item
                startpoint = startpoints[kx]
                endpoint = endpoints[kx]
                first_min_offset = seg_first_min_offset_list[kx]
                trough_trough_data = seg_filt[startpoint+first_min_offset:endpoint]
                cusum_Nsta = mo_cusum_res['nStates']
                parent_event_result = event_result_table[event_index+kx]
                parent_event_result['N_child'] = cusum_Nsta
                if cusum_Nsta>1 :
                    event_state_result_table = np.full(cusum_Nsta, result_nullvalue, dtype=result_dtype)
                    for ksta in range(cusum_Nsta):
                        state_start = mo_cusum_res['starts'][ksta]
                        state_end = mo_cusum_res['starts'][ksta+1]
                        state_data = trough_trough_data[state_start:state_end]
                        state_result = event_state_result_table[ksta]
                        state_result['id'] = result_nullvalue['id']
                        state_result['parent_id'] = parent_event_result['id']
                        state_result['category']='CUSUMState'
                        state_result['index']=ksta
                        state_result['seg'] = k
                        state_result['local_startpt'] = state_start + first_min_offset + startpoint
                        state_result['local_endpt'] = state_end + first_min_offset + startpoint
                        state_result['global_startpt'] = state_result['local_startpt'] + seg_range[0]
                        state_result['global_endpt'] = state_result['local_endpt'] + seg_range[0]
                        state_result['mean'] = np.mean(state_data)
                        state_result['deli'] = analysis_config.baseline_A - state_result['mean']
                        state_result['frac'] = state_result['deli'] / analysis_config.baseline_A
                        state_result['dwell'] = len(state_data)/app.perfiledata.ADC_samplerate_Hz*1e6
                        state_result['stdev'] = np.std(state_data)
                        state_result['skewness'] = spstat.skew(state_data)
                        state_result['kurtosis'] = spstat.kurtosis(state_data)
                    state_result_table = np.append(state_result_table, event_state_result_table)

        # Update event index and id counter for next segment
        event_index += seg_numberofevents
        id_counter += seg_numberofevents

    # Close pool of workers
    pool.close()
    pool.join()

    if analysis_config.enable_subevent_state_detection:
        # touch up the ids
        state_result_table['id'] = np.arange(len(state_result_table)) + id_counter
        id_counter += len(state_result_table)
        analysis_results.tables['CUSUMState'] = state_result_table
        
    # populate the results
    analysis_results.tables['Event'] = event_result_table

    app.perfiledata.analysis_results = analysis_results
    app.printlog(f'Analyzed with baseline: {analysis_config.baseline_A*1e9:.4f} nA, '
                 f'std: {analysis_config.baseline_std_A*1e9:.5f} nA, '
                 f'threshold: {analysis_config.threshold_A*1e9:.4f} nA.\n'
                 f'Total events found: {len(analysis_results.tables["Event"]):d}.')