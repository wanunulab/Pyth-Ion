# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import pickle
import os
import yaml

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import pyqtgraph.exporters


from .__version__ import __version__
from .BaseApp import *
from .ui.loadfile import *
from .ui.exportevents import *
from .ui.exporttraceselection import *

class LoadConfig:
    def __init__(self):
        self.datafilepath = ''
        self.ADC_samplerate_kHz = 250
        self.LPFilter_cutoff_kHz = 100

class LoadFileDialog(QtWidgets.QDialog):
    def __init__(self, parent:BaseAppMainWindow=None):
        self.parent = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_LoadFileDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)
        self.ui.pushButton_Browse.clicked.connect(self.browseFile)
        
        load_config:LoadConfig = parent.load_config
        self.ui.plainTextEdit_DataFilePath.setPlainText(load_config.datafilepath)
        self.ui.lineEdit_ADC_Samplerate.setText(str(load_config.ADC_samplerate_kHz))
        self.ui.lineEdit_LPFilter.setText(str(load_config.LPFilter_cutoff_kHz))
    
    def browseFile(self):
        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '', "(*.opt;*.bin;*.tracedata)")
        if file[0]:
            self.ui.plainTextEdit_DataFilePath.setPlainText(file[0])

    def dialogAccept(self):
        load_config : LoadConfig = self.parent.load_config
        load_config.datafilepath = self.ui.plainTextEdit_DataFilePath.toPlainText()
        load_config.ADC_samplerate_kHz = float(self.ui.lineEdit_ADC_Samplerate.text())
        load_config.LPFilter_cutoff_kHz = float(self.ui.lineEdit_LPFilter.text())
        if os.path.exists(load_config.datafilepath):
            loadFile(self.parent)
        self.close()

    def dialogReject(self):
        self.close()

def loadFile(app:BaseAppMainWindow, loadandplot = True):
    def tryLoadXml(xml_file_path):
        if os.path.isfile(xml_file_path):
            app.printlog(f'Found xml auxiliary file {xml_file_path!s}')
            app.perfiledata.xmltree = ET.parse(xml_file_path)
            app.perfiledata.xmlroot = app.perfiledata.xmltree.getroot()

            voltage_timestamps = app.perfiledata.xmlroot.findall('timestamp/voltage/..')
            t_V_record = np.full(len(voltage_timestamps), -1, dtype=[('msec','int64'),('mV', 'float64')])
            for k,elem in enumerate(voltage_timestamps):
                msec = int(elem.get('msec'))
                mV = float(elem.find('voltage').get('volt'))
                t_V_record[k] = (msec,mV)
            app.perfiledata.t_V_record = t_V_record
            app.printlog(f'read {len(voltage_timestamps):d} voltage records')  

            usernote_timestamps = app.perfiledata.xmlroot.findall('timestamp/usernote/..')
            usernote_record = []
            for k,elem in enumerate(usernote_timestamps):
                msec = int(elem.get('msec'))
                usernote_text = elem.find('usernote').text
                usernote_record.append((msec,usernote_text))
            app.perfiledata.usernote_record = usernote_record
            app.printlog(f'read {len(usernote_record):d} user notes')  
            
    with app.awaitresponse:
        load_config : LoadConfig = app.load_config
        app.perfiledata = FileData()
        app.perfiledata.datafilename = load_config.datafilepath
        app.clearPerFileDisplays()
        app.ui.filelabel.setText(app.perfiledata.datafilename)
        app.printlog(app.perfiledata.datafilename)
        

        datafilebase, datafileext = os.path.splitext(app.perfiledata.datafilename)
        app.perfiledata.matfilename = datafilebase
        datafilename_head, datafilename_tail = os.path.split(app.perfiledata.datafilename)

        app.perfiledata.LPFilter_cutoff_Hz = load_config.LPFilter_cutoff_kHz * 1e3
        app.perfiledata.ADC_samplerate_Hz = load_config.ADC_samplerate_kHz * 1e3 #use integer multiples of 4166.67 ie 2083.33 or 1041.67
        

        if datafileext =='.opt':
            rawdata = np.fromfile(app.perfiledata.datafilename, dtype = np.dtype('>d'))
            app.perfiledata.isFullTrace = True
            app.printlog("opt loaded")

            if np.isfinite(app.perfiledata.LPFilter_cutoff_Hz):
                Wn = round(app.perfiledata.LPFilter_cutoff_Hz/(app.perfiledata.ADC_samplerate_Hz/2),4)
                b,a = signal.bessel(4, Wn, btype='low')
                filtdata = signal.filtfilt(b,a,rawdata)
                app.printlog(f'Data filtered at {app.perfiledata.LPFilter_cutoff_Hz:.0f} Hz')

            else:
                filtdata = rawdata
                app.printlog('Filter value specified as no-filtering, data not filtered')
            app.printlog(f'Read data size: {rawdata.shape!s} samples')

            app.perfiledata.data.setOriginalData(rawdata, filtdata, datafilename_tail)

            xml_file_path = datafilebase + '.xml'
            tryLoadXml(xml_file_path)
                

        elif datafileext =='.bin':
            rawdata = np.fromfile(app.perfiledata.datafilename, dtype = np.dtype('<d'))
            # app.perfiledata.matfilename = str(os.path.splitext(app.perfiledata.datafilename)[0])
            app.printlog("bin loaded")
            if np.isfinite(app.perfiledata.LPFilter_cutoff_Hz):
                Wn = round(app.perfiledata.LPFilter_cutoff_Hz/(app.perfiledata.ADC_samplerate_Hz/2),4)
                b,a = signal.bessel(4, Wn, btype='low')
                filtdata = signal.filtfilt(b,a,rawdata)
                app.printlog(f'Data filtered at {app.perfiledata.LPFilter_cutoff_Hz:.0f} Hz')
            else:
                filtdata = rawdata
                app.printlog('Filter value specified as no-filtering, data not filtered')
            app.printlog(f'Read data size: {rawdata.shape!s}')
            app.perfiledata.data.setOriginalData(rawdata, filtdata, datafilename_tail)

        elif datafileext == '.tracedata':
            with open(app.perfiledata.datafilename,'rb') as dataf:
                tracedata:TraceData = pickle.load(dataf)
            app.perfiledata.data = tracedata
            app.printlog('.tracedata loaded')
            app.printlog(f'trace data created by PythIon version {tracedata.pythion_version:s} of {tracedata.Nseg:d} segments loaded. The original data source was {tracedata.source_file_name:s}')
            source_data_file_base = os.path.splitext(tracedata.source_file_name)[0]
            xml_file_path = os.path.join(datafilename_head, source_data_file_base+'.xml')
            tryLoadXml(xml_file_path)                


        if app.perfiledata.hasbaselinebeenset==0:
            app.ui_baseline=np.median(app.perfiledata.data.filt[0])
            app.ui_baseline_std=np.std(app.perfiledata.data.filt[0])


        if loadandplot == True:
            app.paintCurrentTrace()
            app.p1.autoRange()
            app.p3.clear()
            # FIXME
            aphy, aphx = np.histogram(app.perfiledata.data.filt[0], bins = 1000)
            aphhist = pg.PlotCurveItem(aphx, aphy, stepMode=True, fillLevel=0, brush='b')
            app.p3.addItem(aphhist)
            app.p3.autoRange()
            app.p3.setXRange(np.min(app.perfiledata.data.filt[0]), np.max(app.perfiledata.data.filt[0]))


class ExportEventsDialog(QtWidgets.QDialog):
    def __init__(self, parent:BaseAppMainWindow=None):
        self.parent = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_ExportEventsDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)
        self.event_result_table = parent.perfiledata.analysis_results.result_tables['Event']

        self.totalNpoints = sum([e['local_endpt']-e['local_startpt'] for e in self.event_result_table])


        self.csv_fmt = '+.18e'
        self.bin_fmt = np.dtype('<d')
    
    def updateSizeEstimate(self):
        x = 0
        csv_byte_per_point = len((f'{x:{self.csv_fmt}}\n').encode('utf-8'))
        csv_MiB = int(csv_byte_per_point * self.totalNpoints) >> 20
        self.ui.label_csv_description.setText(f'{csv_MiB:d} MiB per trace')
        
        bin_byte_per_point = self.bin_fmt.itemsize
        bin_MiB = int(bin_byte_per_point * self.totalNpoints) >> 20
        self.ui.label_bin_description.setText(f'{bin_MiB:d} MiB per trace')
        

def exportEvents(app:BaseAppMainWindow):
    pass


class ExportTraceSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        self.parent:BaseAppMainWindow = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_ExportTraceSelectionDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)
        print('ExportTraceSelectionDialog init')
        self.csv_fmt = '+.18e'
        self.bin_fmt = np.dtype('<d')
        self.selection_N_points =  [ ((lambda x: x[1]-x[0])(lr.getRegion())) for lr in self.parent.perfiledata.LRs]
        self.afterDS_points = None
        self.DSRatio = 1
        self.afterDS_samplerate = 0
        self.updateDSRatio()
        self.ui.horizontalSlider_ratio.valueChanged.connect(self.updateDSRatio)
    
    def updateDSRatio(self):
        self.DSRatio = 1 << int(self.ui.horizontalSlider_ratio.value())
        self.ui.label_cur_ratio.setText(f'{self.DSRatio:d}X')
        self.afterDS_samplerate = self.parent.perfiledata.ADC_samplerate_Hz/self.DSRatio
        self.afterDS_points = sum( int(np.ceil(n/self.DSRatio)) for n in self.selection_N_points)
        self.ui.label_cur_samplerate.setText(f'{self.afterDS_samplerate:.4f} Hz')
        self.ui.label_cur_Npoints.setText(f'{self.afterDS_points:d}')
        
        x = 0
        csv_byte_per_point = len((f'{x:{self.csv_fmt}}\n').encode('utf-8'))
        csv_MiB = int(csv_byte_per_point * self.afterDS_points) >> 20
        self.ui.label_csv_description.setText(f'{csv_MiB:d} MiB per trace')
        
        bin_byte_per_point = self.bin_fmt.itemsize
        bin_MiB = int(bin_byte_per_point * self.afterDS_points) >> 20
        self.ui.label_bin_description.setText(f'{bin_MiB:d} MiB per trace')

    def peakDS(self, data):
        DSRatio = self.DSRatio
        pack_size = DSRatio * 2
        n = len(data)
        N_padded = int(np.ceil(n/pack_size)*pack_size)
        N_to_pad = N_padded - n
        data = np.pad(data, pad_width=(0,N_to_pad), constant_values=np.nan)
        data = np.reshape(data, (-1, pack_size))
        mins = np.nanmin(data, axis=1)
        maxs = np.nanmax(data, axis=1)
        return np.ravel(np.transpose([mins, maxs]))

    def meanDS(self, data):
        DSRatio = self.DSRatio
        pack_size = DSRatio
        n = len(data)
        N_padded = int(np.ceil(n/pack_size)*pack_size)
        N_to_pad = N_padded - n
        data = np.pad(data, pad_width=(0,N_to_pad), constant_values=np.nan)
        data = np.reshape(data, (-1, pack_size))
        return np.nanmean(data, axis=1)
    
    def subsamplingDS(self, data):
        DSRatio = self.DSRatio
        pack_size = DSRatio
        return data[::pack_size]

    def dialogAccept(self):
        if_save_raw = self.ui.checkBox_raw.isChecked()
        if_save_filt = self.ui.checkBox_filt.isChecked()
        if_exp_bin = self.ui.checkBox_exp_bin.isChecked()
        if_exp_csv = self.ui.checkBox_exp_csv.isChecked()
        if_exp_png = self.ui.checkBox_exp_png.isChecked()
        if any((if_save_filt,if_save_raw)) and any((if_exp_bin, if_exp_csv, if_exp_png)):
            timestamp = self.parent.getSaveTimeStamp()
            export_dir_path = self.parent.perfiledata.matfilename+ '_export_' + timestamp
            try:
                os.mkdir(export_dir_path)
            except FileExistsError:
                pass
            for k, lr in enumerate(self.parent.perfiledata.LRs):
                sel_region = np.round(lr.getRegion()).astype(int)
                filt_data = self.parent.perfiledata.data.getConcatDataPoints(sel_region, rawdata=False, gap_filler=np.nan)
                raw_data = self.parent.perfiledata.data.getConcatDataPoints(sel_region, rawdata=True, gap_filler=np.nan)
                if self.ui.radioButton_peak.isChecked():
                    DS = self.peakDS
                    DS_string = 'peak'
                elif self.ui.radioButton_mean.isChecked():
                    DS = self.meanDS
                    DS_string = 'mean'
                elif self.ui.radioButton_subsampling.isChecked():
                    DS = self.subsamplingDS
                    DS_string = 'subsampling'
                if if_save_filt: DS_filt_data = DS(filt_data)
                if if_save_raw: DS_raw_data = DS(raw_data)
                
                export_prefix = os.path.join(export_dir_path, f'selection_{k:d}')

                export_info = {
                    'time' : timestamp,
                    'filename': self.parent.perfiledata.datafilename,
                    'source_data_filename' : self.parent.perfiledata.data.source_file_name,
                    'selection_range' : str(sel_region),
                    'export_filtered': if_save_filt,
                    'export_raw': if_save_raw,
                    'downsampling_ratio': self.DSRatio,
                    'downsampling_method': DS_string,
                    'original_samplerate' : float(self.parent.perfiledata.ADC_samplerate_Hz),
                    'downsampled_samplerate(Hz)' : float(self.afterDS_samplerate)
                }

                
                export_info_string = yaml.dump(export_info,sort_keys=False)
                with open(export_prefix+'_info.yaml.txt','w') as expf:
                    expf.write(export_info_string)

                if if_exp_bin:
                    if if_save_filt: DS_filt_data.astype('<d').tofile(export_prefix+'_filt.bin')
                    if if_save_raw: DS_raw_data.astype('<d').tofile(export_prefix+'_raw.bin')
                if if_exp_csv:
                    if if_save_filt: np.savetxt(export_prefix+'_filt.csv', DS_filt_data, fmt='%'+self.csv_fmt)
                    if if_save_raw: np.savetxt(export_prefix+'_raw.csv', DS_raw_data, fmt='%'+self.csv_fmt)
                if if_exp_png:
                    
                    def plot_data(data):
                        fig = plt.figure(figsize=(5,2),dpi=600)
                        ax = fig.add_subplot(111)
                        ax.plot(np.arange(len(data))/self.afterDS_samplerate, 1e12*data,'k-')
                        ax.set_xlabel('t(s)')
                        ax.set_ylabel('I(pA)')
                        fig.tight_layout()
                        return fig
                    if if_save_filt: plot_data(DS_filt_data).savefig(export_prefix+'_filt.png')
                    if if_save_raw: plot_data(DS_raw_data).savefig(export_prefix+'_raw.png')
            self.parent.printlog(f'Data in the selections exported to directory {export_dir_path:s}')
        self.close()

    def dialogReject(self):
        self.close()


def exportSelection(app:BaseAppMainWindow):
    if len(app.perfiledata.LRs)>0:
        export_dialog = ExportTraceSelectionDialog(parent=app)
        export_dialog.exec()

def saveSegInfo(app:BaseAppMainWindow):
    save_dtype = np.dtype([
        ('start', int),
        ('end', int),
        ('start_sec', float),
        ('end_sec', float),
        ('duration_sec',float)
    ])
    Nseg = app.perfiledata.data.Nseg
    srange = app.perfiledata.data.srange
    save_table = np.full(Nseg, -1, dtype=save_dtype)
    for kseg in range(Nseg):
        seg = srange[kseg]
        save_table['start'][kseg] = seg[0]
        save_table['end'][kseg] = seg[1]
        save_table['start_sec'][kseg] = seg[0]/app.perfiledata.ADC_samplerate_Hz
        save_table['end_sec'][kseg] = seg[1]/app.perfiledata.ADC_samplerate_Hz
        save_table['duration_sec'][kseg] = (seg[1]-seg[0])/app.perfiledata.ADC_samplerate_Hz
    header = f"""file: "{app.perfiledata.datafilename:s}"
    source_data_file: "{app.perfiledata.data.source_file_name:s}" 
    """
    header += '\t'.join(save_table.dtype.names)
    timestamp = app.getSaveTimeStamp()
    save_path = app.perfiledata.matfilename + '_' + timestamp + '_segments.txt'
    np.savetxt(save_path, save_table, delimiter='\t', 
        header=header)
    app.printlog(f'Segment information saved to {save_path:s}')


def saveTrace(app:BaseAppMainWindow):
    timestamp = app.getSaveTimeStamp()
    tracedata_savename = app.perfiledata.matfilename+'_'+timestamp+'.tracedata'
    with open(tracedata_savename, 'wb') as outf:
        pickle.dump(app.perfiledata.data, outf)
    
    app.printlog(f'Trace data saved to...\n{tracedata_savename!s}\n')
    savelog(app)
    # TODO
    # save processing information etc.


def savelog(app:BaseAppMainWindow, logfilepath=None):
    timestamp = app.getSaveTimeStamp()
    if logfilepath is None:
        logfilepath = app.perfiledata.matfilename+'_'+timestamp+'_log.txt'
    app.printlog(f'saving PythIon log to {logfilepath!s}')
    app.printlog(f'... PythIon version {__version__!s} ...')
    with open(logfilepath, 'w') as logfile:
        logfile.write(app.perfiledata.logtext)


def saveAnalysis(app:BaseAppMainWindow):
    timestamp = app.getSaveTimeStamp()
    savedir = app.perfiledata.matfilename+'_'+timestamp+'_analysis'
    app.printlog(f'trying to save analysis results to folder {savedir:s}')
    try:
        os.mkdir(savedir)
        save_prefix = os.path.join(savedir, os.path.basename(app.perfiledata.matfilename)+'_'+timestamp)

        table_dir = os.path.join(savedir, 'tables')
        os.mkdir(table_dir)
        for table_key in app.perfiledata.analysis_results.tables.keys():
            table = app.perfiledata.analysis_results.tables[table_key]
            savename_table = os.path.join(table_dir, f'{table_key:s}.txt')
            save_format = [spec[2] for spec in app.perfiledata.analysis_results.result_spec]
            np.savetxt(savename_table, table, fmt=save_format, delimiter='\t', 
                        header='\t'.join(table.dtype.names))
            app.printlog(f'Table "{table_key:s}" saved to {savename_table!s}')
        if app.perfiledata.analysis_results.result_tables.has_key('Event'):
            event_table = app.perfiledata.analysis_results.result_tables['Event']
            legacy_columns=  ['deli','frac','dwell','dt']
            legacy_event_table = event_table[legacy_columns]
            savename_legacy_event_table = os.path.join(table_dir, 'Event_LegacyDB.txt')
            save_format = '%.18e'
            np.savetxt(savename_legacy_event_table, legacy_event_table, fmt=save_format, delimiter='\t',
                        header='\t'.join(legacy_event_table.dtype.names))
            app.printlog(f'Legacy event table saved to {savename_legacy_event_table!s}')


        def exportFig(fig, save_name):
            exporter = pg.exporters.ImageExporter(fig)
            exporter.parameters()['width'] = 4000
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.processEvents()
            exporter.export(save_name)

        fig_save_names = [save_prefix + '_'+nm+'.png' for nm in ('w2','w3','w4','w5')]
        figs_to_save = [app.w2, app.w3, app.w4, app.w5]
        fig_tab_pages = [app.ui.frachisttab, app.ui.delitab, app.ui.dwelltab, app.ui.dttab]
        for fig, save_name, tab_page in zip(figs_to_save, fig_save_names, fig_tab_pages):
            app.ui.tabWidget.setCurrentWidget(tab_page)
            exportFig(fig, save_name)

        app.ui.tabWidget.setCurrentWidget(app.ui.scattertab)
        fig_save_names = [save_prefix + '_'+nm+'.png' for nm in ('w1','w1std','w1skew','w1kurt')]
        figs_to_save = [app.w1, app.w1std, app.w1skew, app.w1kurt]
        fig_tab_pages = [app.ui.blockadetab, app.ui.stdevtab, app.ui.skewnesstab, app.ui.kurtosistab]
        for fig, save_name, tab_page in zip(figs_to_save, fig_save_names, fig_tab_pages):
            app.ui.tabWidget_2.setCurrentWidget(tab_page)
            exportFig(fig, save_name)
        app.ui.tabWidget_2.setCurrentWidget(app.ui.blockadetab)

    except Exception as e:
        app.printlog(str(e))

    savelog(app, logfilepath=os.path.join(savedir, 'log.txt'))
    savelog(app)