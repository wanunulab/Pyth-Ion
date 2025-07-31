from .__version__ import __version__
from .BaseApp import *



def autoFindCutLRs(app:BaseAppMainWindow):
    with app.awaitresponse:
        for k in range(app.perfiledata.data.Nseg):
            seg_range = app.perfiledata.data.srange[k]
            seg_filt = app.perfiledata.data.filt[k]

            std_thersh_for_spike = 10
            ndx_spike = np.where(np.abs(seg_filt) > app.ui_baseline + std_thersh_for_spike * app.ui_baseline_std)[0] 
            ndx_around_baseline = np.nonzero(np.abs(seg_filt-app.ui_baseline) < app.ui_baseline_std)[0]
            extra_relaxation_time_ms = 10
            Nrlx = int(extra_relaxation_time_ms * app.perfiledata.ADC_samplerate_Hz / 1e3)

            k_nab = 0
            endpoint = 0
            for startpoint in ndx_spike:
                if startpoint < endpoint:
                    continue
                k_nab += np.searchsorted(ndx_around_baseline[k_nab:], startpoint, side='right')
                endpoint = ndx_around_baseline[k_nab + Nrlx]
                if k_nab > 0:
                    startpoint = ndx_around_baseline[k_nab-1]
                else:
                    startpoint = 0

                newLR = pg.LinearRegionItem()
                newLR.hide()
                local_region = np.array((startpoint, endpoint))
                global_region = local_region + seg_range[0]
                newLR.setRegion(global_region)
                app.p1.addItem(newLR)
                app.perfiledata.LRs.append(newLR)
                newLR.show()

def addOneManualCutLR(app:BaseAppMainWindow):
    with app.awaitresponse:
        newLR = pg.LinearRegionItem()
        newLR.hide()
        newLR.setRegion((lambda x : (0.7*x[0]+0.3*x[1], 0.3*x[0]+0.7*x[1]))(app.p1.viewRange()[0]))
        app.p1.addItem(newLR)
        app.perfiledata.LRs.append(newLR)
        newLR.show()

def deleteOneCutLR(app:BaseAppMainWindow):
    with app.awaitresponse:
        if len(app.perfiledata.LRs) > 0:
            LR = app.perfiledata.LRs.pop(-1)
            app.p1.removeItem(LR)

def clearLRs(app:BaseAppMainWindow):
    with app.awaitresponse:
        for LR in app.perfiledata.LRs:
            app.p1.removeItem(LR)
        app.perfiledata.LRs.clear()

def measureSelections(app:BaseAppMainWindow):
    with app.awaitresponse:
        if len(app.perfiledata.LRs)>0:
            regions = [np.round(LR.getRegion()).astype(int) for LR in app.perfiledata.LRs]
            sortndx = np.argsort([region[0] for region in regions])
            measure_dtype = np.dtype([('start', int), ('end', int), ('start_ms', float), ('end_ms', float), ('mid_mV', float),
                                        ('median_filt', float), ('mean_filt', float), ('stdev_filt', float),
                                        ('median_raw', float), ('mean_raw', float), ('stdev_raw', float)
                                    ])
            measure_result = np.full(len(sortndx), 0, dtype = measure_dtype)
            for k, ndx in enumerate(sortndx):
                region = regions[ndx]
                reg_start = region[0]
                reg_start_msec = 1e3 * region[0] / app.perfiledata.ADC_samplerate_Hz
                reg_end = region[1]
                reg_end_msec = 1e3 * region[1]  / app.perfiledata.ADC_samplerate_Hz

                reg_mid_msec = (reg_start_msec + reg_end_msec)/2
                reg_mid_voltage_mV = np.nan
                t_V_record = app.perfiledata.t_V_record
                if t_V_record is not None and len(t_V_record)>0:
                    t_record, V_record = t_V_record['msec'], t_V_record['mV']
                    V_ndx = np.searchsorted(t_record, reg_mid_msec)
                    if V_ndx > 0:
                        reg_mid_voltage_mV = V_record[V_ndx-1]

                filt_data = app.perfiledata.data.getConcatDataPoints(region)
                med_filt = np.median(filt_data)
                mean_filt = np.mean(filt_data)
                std_filt = np.std(filt_data)

                raw_data = app.perfiledata.data.getConcatDataPoints(region, rawdata=True)
                med_raw = np.median(raw_data)
                mean_raw = np.mean(raw_data)
                std_raw = np.std(raw_data)

                measure_result[k] = (reg_start, reg_end, reg_start_msec, reg_end_msec, reg_mid_voltage_mV,
                                        med_filt, mean_filt, std_filt,
                                        med_raw, mean_raw, std_raw)
            timestamp = app.getSaveTimeStamp()
            savepath = app.perfiledata.matfilename + '_' + timestamp +  '_measurement.txt'
            np.savetxt(savepath, measure_result, delimiter='\t', 
                    header='\t'.join(measure_result.dtype.names))
            app.printlog(f'Measurement results saved to {savepath:s}')


def autoIVSelection(app:BaseAppMainWindow):
    if len(app.perfiledata.LRs)>0:
        param_dialog = AutoSelectIVDialog(parent=app)
        param_dialog.show()

def commitAutoIVSelection(app:BaseAppMainWindow,params):
    with app.awaitresponse:
        if len(app.perfiledata.LRs)>0:
            app.printlog(f'Auto IV Region Selected with {params!s}')
            t_V = app.perfiledata.t_V_record
            if t_V is not None and len(t_V)>0:
                offset_t_V_t = t_V['msec'] - params['offset_ms']
                new_region_ms = []
                for LR in app.perfiledata.LRs:
                    region_ms = 1e3 * np.array(LR.getRegion())/app.perfiledata.ADC_samplerate_Hz
                    t_V_ndcs=  np.searchsorted(offset_t_V_t, region_ms)
                    for t_V_ndx in range(*t_V_ndcs):
                        t = offset_t_V_t[t_V_ndx]
                        # print(t)
                        V = t_V['mV'][t_V_ndx]
                        if not (t_V_ndx > 0 and V == t_V['mV'][t_V_ndx-1]):
                        # if True:
                            new_region_ms.append(np.array([t+params['start_ms'], t+params['end_ms']]))
                app.clearLRs()
                # new_region_ndx = np.round(np.array(new_region_ms) * app.outputsamplerate).astype(int)
                new_region_ndx = 1e-3 * np.array(new_region_ms) * app.perfiledata.ADC_samplerate_Hz
                for new_region in new_region_ndx:
                # for new_region in new_region_ms:
                    new_LR = pg.LinearRegionItem()
                    new_LR.hide()
                    new_LR.setRegion(new_region)
                    app.p1.addItem(new_LR)
                    app.perfiledata.LRs.append(new_LR)
                    new_LR.show()

