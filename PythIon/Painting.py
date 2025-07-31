# -*- coding: utf-8 -*-

from .BaseApp import *
# import cProfile

def paintCurrentTrace(app:BaseAppMainWindow):
    print('Painting Current Trace')
    app.p1.clear()
    # FIXME
    #skips plotting first and last two points, there was a weird spike issue
    # app.p1.plot(app.t[2:][:-2],app.data.filt[2:][:-2],pen='b')
    # app.p1RawTraceHandle = app.p1.plot(app.t,app.data.raw,pen='gray', antialiasing=False)
    dscl = app.current_display_scale_factor
    app.perfiledata.p1RawTraceHandles = []
    app.perfiledata.p1FiltTraceHandles = []
    for k in range(app.perfiledata.data.Nseg):
        x = app.perfiledata.data.getSegCoord(k)
        handle = pg.PlotDataItem(x, (app.perfiledata.data.raw[k] * dscl),pen='gray', antialiasing=False)
        app.p1.addItem(handle)
        handle.setDownsampling(ds=app.DSratio, auto=False, method='peak')
        #FIXME As opposed to the documentation, setting cliptoview to true decreased the 
        # performance drastically on x-axis dragging.
        # app.p1RawTraceHandle.setClipToView(True)
        # app.p1RawTraceHandle.setSkipFiniteCheck(True)
        handle.setDynamicRangeLimit(10.0)
        app.perfiledata.p1RawTraceHandles.append(handle)

        handle2 = pg.PlotDataItem(x, (app.perfiledata.data.filt[k]* dscl),pen='blue', antialiasing=False)
        app.p1.addItem(handle2)
        handle2.setDownsampling(ds=app.DSratio, auto=False, method='peak')
        handle2.setDynamicRangeLimit(10.0)
        app.perfiledata.p1FiltTraceHandles.append(handle2)

        region_handle = pg.LinearRegionItem(values=app.perfiledata.data.srange[k], 
                                            brush=pg.mkBrush(0,255,0,127), pen=pg.mkPen(color='orange', width=3), span=(0,0.1), movable=False)
        app.p1.addItem(region_handle)

    app.p1.getAxis('bottom').setScale(1/app.perfiledata.ADC_samplerate_Hz)

    app.p1.addLine(y=app.ui_baseline*dscl,pen='g')
    app.p1.addLine(y=(app.ui_baseline+app.ui_baseline_std)*dscl, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
    app.p1.addLine(y=(app.ui_baseline-app.ui_baseline_std)*dscl,pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
    app.updateThresholdLine()
    
    # if app.perfiledata.isFullTrace:
    if True:
        if app.perfiledata.t_V_record is not None and len(app.perfiledata.t_V_record)>0:
            t_V_record = app.perfiledata.t_V_record
            t_V_curve = np.full((2*len(t_V_record),2), np.nan)
            t_V_curve[::2,1] = t_V_record['mV']
            t_V_curve[1::2,1] = t_V_record['mV']
            t_V_curve[0:-1:2,0] = t_V_record['msec'] * app.perfiledata.ADC_samplerate_Hz *1e-3
            t_V_curve[1:-1:2,0] = t_V_record['msec'][1:] * app.perfiledata.ADC_samplerate_Hz *1e-3
            t_V_curve[-1,0] = app.perfiledata.data.original_length
            pV = pg.PlotDataItem(t_V_curve[:,0], t_V_curve[:,1]*1e-12*dscl, pen='magenta')
            app.p1.addItem(pV)
            

    app.p1.showGrid(x=True, y=True)
    app.updateRawFiltVisibility()


def plotAnalysis(app:BaseAppMainWindow):
    app.printlog(f'Plotting analysis')
    for p in app.p2s:
        for entry in app.scatter_entries:
            p[entry].clear()
            p[entry].update()

    app.ui.scatterplot.update()

    app.w2.clear()
    app.w3.clear()
    app.w4.clear()
    app.w5.clear()
    paintCurrentTrace(app)

    event_result_table = app.perfiledata.analysis_results.tables['Event']
    
    print('started annotating main trace plot')
    dscl = app.current_display_scale_factor

    x0 = []
    x1 = []
    y0 = []
    y1 = []
    for event in event_result_table:
        k = event['seg']
        seg_filt = app.perfiledata.data.filt[k]
        x0.append(event['global_startpt'])
        x1.append(event['global_endpt'])
        y0.append(seg_filt[event['local_startpt']] * dscl)
        y1.append(seg_filt[event['local_endpt']] * dscl)
    
    app.p1.plot(x0, y0, pen=None, symbol='o',symbolBrush='g',symbolSize=10)
    app.p1.plot(x1, y1, pen=None, symbol='o',symbolBrush='r',symbolSize=10)
    

    print('finished annotating main trace plot')

    print('started plotting scatterplots')
    # event_number_of_states = np.array([len(state_result_table[state_result_table['parent_id']==event['id']]) for event in event_result_table])
    event_number_of_states = event_result_table['N_child']
    event_sizes = np.where(event_number_of_states>1, 1, 3)
    app.perfiledata.event_sizes = event_sizes
    event_colors = [ app.inspect_event_fit_color_multistate if Nsta>1 else app.inspect_event_fit_color_singlestate for Nsta in event_number_of_states]
    app.perfiledata.event_colors = event_colors
    scatter_pts_x = np.log10(event_result_table['dwell'])
    app.p2['events'].addPoints(x=scatter_pts_x,y=event_result_table['frac'],
    symbol='o', brush=event_colors, pen = None, size = event_sizes)
    # def getValid(column):
    #     pts_valid = column > 0
    #     column_masked = np.full_like(column, np.nan)
    #     column_masked[pts_valid] = column[pts_valid]
    #     return column_masked
    def getValid(column):
        return column
    app.p2std['events'].addPoints(x=scatter_pts_x,y=getValid(event_result_table['stdev_tt']),
    symbol='o', brush=event_colors, pen = None, size = event_sizes)
    app.p2skew['events'].addPoints(x=scatter_pts_x,y=getValid(event_result_table['skewness_tt']),
    symbol='o', brush=event_colors, pen = None, size = event_sizes)
    app.p2kurt['events'].addPoints(x=scatter_pts_x,y=getValid(event_result_table['kurtosis_tt']),
    symbol='o', brush=event_colors, pen = None, size = event_sizes)

    if app.perfiledata.analysis_results.analysis_config.enable_subevent_state_detection:
        print('start plotting state scatterplots')
        state_result_table = app.perfiledata.analysis_results.tables['CUSUMState']
        state_scatter_x = np.log10(state_result_table['dwell'])
        state_scatter_color = [ app.state_colors[ind_state] for ind_state in state_result_table['index'] ]
        app.p2['cusum_states'].addPoints(x=state_scatter_x, y=state_result_table['frac'], symbol='t', brush=state_scatter_color, pen=None, size=5)
        app.p2std['cusum_states'].addPoints(x=state_scatter_x, y=state_result_table['stdev'], symbol='t', brush=state_scatter_color, pen=None, size=5)
        app.p2skew['cusum_states'].addPoints(x=state_scatter_x, y=state_result_table['skewness'], symbol='t', brush=state_scatter_color, pen=None, size=5)
        app.p2kurt['cusum_states'].addPoints(x=state_scatter_x, y=state_result_table['kurtosis'], symbol='t', brush=state_scatter_color, pen=None, size=5)
    
    # app.w1.addItem(app.p2)
    app.w1.setLogMode(x=True,y=False)
    app.w1.autoRange()
    app.ui.scatterplot.update()
    app.w1.setRange(yRange=[0,1])
    print('finished plotting scatterplots')

    print('started plotting histograms')

    color = app.inspect_event_fit_color_singlestate    
    fracy, fracx = np.histogram(event_result_table['frac'], bins=np.linspace(0, 1, int(app.ui.fracbins.text())))
    deliy, delix = np.histogram(event_result_table['deli'], bins=np.linspace(float(app.ui.delirange0.text())*10**-9, float(app.ui.delirange1.text())*10**-9, int(app.ui.delibins.text())))
    dwelly, dwellx = np.histogram(np.log10(event_result_table['dwell']), bins=np.linspace(float(app.ui.dwellrange0.text()), float(app.ui.dwellrange1.text()), int(app.ui.dwellbins.text())))
    dty, dtx = np.histogram(event_result_table['dt'], bins=np.linspace(float(app.ui.dtrange0.text()), float(app.ui.dtrange1.text()), int(app.ui.dtbins.text())))

    hist = pg.BarGraphItem(height = fracy, x0 = fracx[:-1], x1 = fracx[1:], brush = color)
    app.w2.addItem(hist)
    hist = pg.BarGraphItem(height = deliy, x0 = delix[:-1], x1 = delix[1:], brush = color)
    app.w3.addItem(hist)
    app.w3.setRange(xRange = [float(app.ui.delirange0.text())*10**-9, float(app.ui.delirange1.text())*10**-9])
    hist = pg.BarGraphItem(height = dwelly, x0 = dwellx[:-1], x1 = dwellx[1:], brush = color)
    app.w4.addItem(hist)
    hist = pg.BarGraphItem(height = dty, x0 = dtx[:-1], x1 = dtx[1:], brush = color)
    app.w5.addItem(hist)
    print('finished plotting histograms')
    app.setSubeventStateVisibility(app.ui.checkBoxShowSubeventStates.isChecked())


def inspectEvent(app:BaseAppMainWindow, clickedentry=None, clicked = None):
    # cProfile.runctx('inspectEvent_(app, clickedentry, clicked)', globals(), locals())
    inspectEvent_(app, clickedentry, clicked)

def inspectEvent_(app:BaseAppMainWindow, clickedentry=None, clicked = None):
    if clickedentry is None:
        clickedentry = 'events'
    if clickedentry == 'annotations':
        return
    
    analysis_results = app.perfiledata.analysis_results
    event_result_table = analysis_results.tables['Event']
    

    #Reset plot
    app.p3.setLabel('bottom', text='Time', units='s')
    app.p3.setLabel('left', text='Current', units='A')
    app.p3.clear()
    for p in app.p2s:
        p['annotations'].clear()

    #Correct for user error if non-extistent number is entered
    eventbuffer=int(app.ui.eventbufferentry.text())
    
    # Get row number of event
    if clicked is None:
        event_row_number = int(app.ui.eventnumberentry.text())
    else:
        if clickedentry == 'events':
            event_row_number = clicked
        elif clickedentry == 'cusum_states':
            if not app.perfiledata.analysis_results.analysis_config.enable_subevent_state_detection:
                return
            state_result_table = analysis_results.tables['CUSUMState']
            state_parent_id = state_result_table[clicked]['parent_id']
            # print(event_id, state['id'])
            event_row_number = np.nonzero(event_result_table['id']==state_parent_id)[0][0]

    if event_row_number>=len(analysis_results.tables['Event']):
        event_row_number=len(analysis_results.tables['Event'])-1
    app.ui.eventnumberentry.setText(str(event_row_number))

    event_color = app.perfiledata.event_colors[event_row_number]

    
    #plot event trace
    event_res = event_result_table[event_row_number]
    k_seg = event_res['seg']
    # print(k_seg)
    seg_range = app.perfiledata.data.srange[k_seg]
    event_seg_filt = app.perfiledata.data.filt[k_seg]
    flank_local_start = event_res['local_startpt'] - eventbuffer
    flank_local_start = max(0, flank_local_start)
    flank_global_start = flank_local_start + seg_range[0]
    flank_local_end =event_res['local_endpt'] + eventbuffer
    flank_local_end = min(len(event_seg_filt), flank_local_end)
    flank_global_end = flank_local_end + seg_range[0]

    app.p3.plot(app.perfiledata.getT(range(flank_global_start, flank_global_end)),
                    event_seg_filt[flank_local_start:flank_local_end], pen='b')

    #plot event fit
    x = (
        flank_global_start, 
        event_res['global_startpt'], 
        event_res['global_startpt'],
        event_res['global_endpt'],
        event_res['global_endpt'],
        flank_global_end
    )

    y = (
        app.ui_baseline,
        app.ui_baseline,
        app.ui_baseline-event_result_table['deli'][event_row_number],
        app.ui_baseline-event_result_table['deli'][event_row_number],
        app.ui_baseline,
        app.ui_baseline
    )
    app.p3.plot(app.perfiledata.getT(x),y,pen=pg.mkPen(color=event_color,width=2))
    app.p3.autoRange()

    #Mark event start and end points
    app.p3.plot([app.perfiledata.getT(event_res['global_startpt'])], [event_seg_filt[event_res['local_startpt']]],
                    symbol='o',symbolBrush='g',symbolSize=12
                )
    app.p3.plot([app.perfiledata.getT(event_res['global_startpt'] + event_res['offset_first_min'])], [event_seg_filt[event_res['local_startpt'] + event_res['offset_first_min']]],
                    symbol='d',symbolBrush='g',symbolSize=12
                )
    app.p3.plot([app.perfiledata.getT(event_res['global_endpt'])], [event_seg_filt[event_res['local_endpt']]],
                    symbol='o',symbolBrush='r',symbolSize=12
                )
    
    # Annotate event parameters
    app.ui.eventinfolabel.setText('Dwell Time=' + str(round(event_result_table[event_row_number]['dwell'],2))+ u' μs,   Deli='+str(round(event_result_table[event_row_number]['deli']*1e9,2)) +' nA')
    
    # Annotate event plot
    log_event_dwell = [np.log10(event_result_table['dwell'][event_row_number])]
    event_frac = [event_result_table['frac'][event_row_number]]
    event_stdev = [event_result_table['stdev_tt'][event_row_number]]
    event_skew = [event_result_table['skewness_tt'][event_row_number]]
    event_kurt = [event_result_table['kurtosis_tt'][event_row_number]]

    app.p2['annotations'].addPoints(x=log_event_dwell, y=event_frac, symbol='o', brush=None, pen=pg.mkPen('y', width=2), size=12)
    app.p2['annotations'].addPoints(x=log_event_dwell, y=event_frac, symbol='o', brush=None, pen=pg.mkPen('k', width=2), size=8)
    app.p2['annotations'].addPoints(x=log_event_dwell, y=event_frac, symbol='o', brush=event_color, size=6)
    app.p2std['annotations'].addPoints(x=log_event_dwell, y=event_stdev, symbol='o', brush=None, pen=pg.mkPen('y', width=2), size=12)
    app.p2std['annotations'].addPoints(x=log_event_dwell, y=event_stdev, symbol='o', brush=None, pen=pg.mkPen('k', width=2), size=8)
    app.p2std['annotations'].addPoints(x=log_event_dwell, y=event_stdev, symbol='o', brush=event_color, size=6)
    app.p2skew['annotations'].addPoints(x=log_event_dwell, y=event_skew, symbol='o', brush=None, pen=pg.mkPen('y', width=2), size=12)
    app.p2skew['annotations'].addPoints(x=log_event_dwell, y=event_skew, symbol='o', brush=None, pen=pg.mkPen('k', width=2), size=8)
    app.p2skew['annotations'].addPoints(x=log_event_dwell, y=event_skew, symbol='o', brush=event_color, size=6)
    app.p2kurt['annotations'].addPoints(x=log_event_dwell, y=event_kurt, symbol='o', brush=None, pen=pg.mkPen('y', width=2), size=12)
    app.p2kurt['annotations'].addPoints(x=log_event_dwell, y=event_kurt, symbol='o', brush=None, pen=pg.mkPen('k', width=2), size=8)
    app.p2kurt['annotations'].addPoints(x=log_event_dwell, y=event_kurt, symbol='o', brush=event_color, size=6)

    if app.perfiledata.analysis_results.analysis_config.enable_subevent_state_detection:

        # Plot subevent state fits
        state_result_table = analysis_results.tables['CUSUMState']
        state_row_numbers = np.nonzero(state_result_table['parent_id'] == event_result_table['id'][event_row_number])[0]
        state_colors = [ app.state_colors[state['index']] for state in state_result_table[state_row_numbers]]
        for state_row_number in state_row_numbers:
            state = state_result_table[state_row_number]
            app.p3.plot([app.perfiledata.getT(state['global_startpt'])], [event_seg_filt[state['local_startpt']]], 
                            symbol='t', symbolBrush='m', symbolSize=10)
            app.p3.plot([app.perfiledata.getT(state['global_endpt'])], [event_seg_filt[state['local_endpt']]], 
                            symbol='t', symbolBrush='m', symbolSize=10)
            x = (app.perfiledata.getT(state['global_startpt']), app.perfiledata.getT(state['global_endpt']))
            y = (state['mean'], state['mean'])
            app.p3.plot(x, y, pen=pg.mkPen(color=app.state_colors[state['index']], width=4))

        # Annotate subevent state plot
        state_frac_list = state_result_table['frac'][state_row_numbers]
        state_stdev_list = state_result_table['stdev'][state_row_numbers]
        state_skew_list = state_result_table['skewness'][state_row_numbers]
        state_kurt_list = state_result_table['kurtosis'][state_row_numbers]
        log_state_dwell_list = np.log10(state_result_table['dwell'][state_row_numbers])
        app.p2['annotations'].addPoints(x=log_state_dwell_list, y=state_frac_list, symbol='t', brush=None, pen=pg.mkPen('y', width=2), size=12)
        app.p2['annotations'].addPoints(x=log_state_dwell_list, y=state_frac_list, symbol='t', brush=None, pen=pg.mkPen('k', width=2), size=8)
        app.p2['annotations'].addPoints(x=log_state_dwell_list, y=state_frac_list, symbol='t', brush=state_colors, size=6)
        app.p2std['annotations'].addPoints(x=log_state_dwell_list, y=state_stdev_list, symbol='t', brush=None, pen=pg.mkPen('y', width=2), size=12)
        app.p2std['annotations'].addPoints(x=log_state_dwell_list, y=state_stdev_list, symbol='t', brush=None, pen=pg.mkPen('k', width=2), size=8)
        app.p2std['annotations'].addPoints(x=log_state_dwell_list, y=state_stdev_list, symbol='t', brush=state_colors, size=6)
        app.p2skew['annotations'].addPoints(x=log_state_dwell_list, y=state_skew_list, symbol='t', brush=None, pen=pg.mkPen('y', width=2), size=12)
        app.p2skew['annotations'].addPoints(x=log_state_dwell_list, y=state_skew_list, symbol='t', brush=None, pen=pg.mkPen('k', width=2), size=8)
        app.p2skew['annotations'].addPoints(x=log_state_dwell_list, y=state_skew_list, symbol='t', brush=state_colors, size=6)
        app.p2kurt['annotations'].addPoints(x=log_state_dwell_list, y=state_kurt_list, symbol='t', brush=None, pen=pg.mkPen('y', width=2), size=12)
        app.p2kurt['annotations'].addPoints(x=log_state_dwell_list, y=state_kurt_list, symbol='t', brush=None, pen=pg.mkPen('k', width=2), size=8)
        app.p2kurt['annotations'].addPoints(x=log_state_dwell_list, y=state_kurt_list, symbol='t', brush=state_colors, size=6)


def scatterClicked(app:BaseAppMainWindow, plot, points):    
    for entry in app.scatter_entries:
        for p in app.p2s:
            if plot is p[entry]:
                clickedentry = entry
                break
    clickedindex = points[0].index()
    inspectEvent(app, clickedentry, clickedindex)

def inspectRange(app:BaseAppMainWindow, grange:tuple[int]):
    range_data = app.perfiledata.data.getConcatDataPoints(grange, rawdata=False, gap_filler=np.nan)
    app.p3.clear()
    app.p3.setLabel('bottom', text='Time', units='s')
    app.p3.setLabel('left', text='Current', units='A')
    app.p3.plot(app.perfiledata.getT(range(grange[0], grange[1])), range_data, pen='b')
    app.p3.autoRange()

def inspectSelection(app:BaseAppMainWindow):
    """
    Inspect the selected linear region.
    """
    if len(app.perfiledata.LRs) > 0:
        selected_region = app.perfiledata.LRs[-1]
        region = selected_region.getRegion()
        app.printlog(f'Inspecting selected region: {region}')
        start, end = int(region[0]), int(region[1])
        grange = (start, end)
        inspectRange(app, grange)
        
        