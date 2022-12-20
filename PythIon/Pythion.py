#!/usr/bin/python
# -*- coding: utf8 -*-
import sys
import numpy as np

import os
from scipy import signal
from scipy import io as spio

#### plotguiuniversal works well for mac and laptops,
##### for larger screens try PlotGUI ####

from plotguiuniversal import *
import matplotlib.pyplot as plt
#from PlotGUI import *
import pyqtgraph as pg
import pandas.io.parsers
import pandas as pd
from abfheader import *
from CUSUMV2 import detect_cusum
# from PoreSizer import *
# from batchinfo import *
import loadmat
from peaktoolkit import *
from filterkit import *
from PythionUtils.loggers import LogSystem
import pyabf
import PyQt5
from PyQt5 import QtCore, QtGui,QtWidgets

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

logger=LogSystem()

class GUIForm(QtWidgets.QMainWindow):


    def __init__(self, width, height, master=None):
        ####Setup GUI and draw elements from UI file#########
        QtWidgets.QMainWindow.__init__(self,master)
        self.ui = Ui_PythIon()
        self.ui.setupUi(self)
        


        ##########Linking buttons to main functions############
        self.ui.loadbutton.clicked.connect(self.getfile)
        self.ui.analyzebutton.clicked.connect(self.analyze)
        self.ui.cutbutton.clicked.connect(self.cut)
        self.ui.baselinebutton.clicked.connect(self.baselinecalc)
        self.ui.clearscatterbutton.clicked.connect(self.clearscatter)
        self.ui.deleteeventbutton.clicked.connect(self.deleteevent)
        self.ui.invertbutton.clicked.connect(self.invertdata)
        self.ui.concatenatebutton.clicked.connect(self.concatenatetext)
        self.ui.nextfilebutton.clicked.connect(self.nextfile)
        self.ui.previousfilebutton.clicked.connect(self.previousfile)
        self.ui.showcatbutton.clicked.connect(self.showcattrace)
        self.ui.savecatbutton.clicked.connect(self.savecattrace)
        self.ui.gobutton.clicked.connect(self.inspectevent)
        self.ui.previousbutton.clicked.connect(self.previousevent)
        self.ui.nextbutton.clicked.connect(self.nextevent)
        self.ui.savefitsbutton.clicked.connect(self.saveeventfits)
        self.ui.fitbutton.clicked.connect(self.CUSUM)
        self.ui.Poresizeraction.triggered.connect(self.sizethepore)
        self.ui.actionBatch_Process.triggered.connect(self.batchinfodialog)        
        self.ui.actionSpike_Analyzer.triggered.connect(self.spikedialog)
        self.ui.actionSpike_Analysis_Test_1.triggered.connect(self.run_spike_test1)
        self.ui.actionFilter_Kit.triggered.connect(self.filterdialog)
        self.ui.actionNormalize_to_G.triggered.connect(self.normalize_to_g)
        ###### Setting up plotting elements and their respective options######
        self.ui.signalplot.setBackground('w')
        self.ui.scatterplot.setBackground('w')
        self.ui.eventplot.setBackground('w')
        self.ui.frachistplot.setBackground('w')
        self.ui.delihistplot.setBackground('w')
        self.ui.dwellhistplot.setBackground('w')
        self.ui.dthistplot.setBackground('w')
#        self.ui.PSDplot.setBackground('w')

        self.p1 = self.ui.signalplot.addPlot()
        self.p1.setLabel('bottom', text='Time', units='s')
        self.p1.setLabel('left', text='Current', units='A')
        self.p1.enableAutoRange(axis = 'x')
        self.p1.setDownsampling(ds=True, auto=True, mode='peak')


        self.w1 = self.ui.scatterplot.addPlot()
        self.p2 = pg.ScatterPlotItem()
        self.p2.sigClicked.connect(self.clicked)
        self.w1.addItem(self.p2)
        self.w1.setLabel('bottom', text='Time', units=u'μs')
        self.w1.setLabel('left', text='Fractional Current Blockage')
        self.w1.setLogMode(x=True,y=False)
        self.w1.showGrid(x=True, y=True)
        self.cb = pg.ColorButton(self.ui.scatterplot, color=(0,0,255,50))
        self.cb.setFixedHeight(30)
        self.cb.setFixedWidth(30)
        self.cb.move(0,210)
        self.cb.show()

        self.w2 = self.ui.frachistplot.addPlot()
        self.w2.setLabel('bottom', text='Fractional Current Blockage')
        self.w2.setLabel('left', text='Counts')

        self.w3 = self.ui.delihistplot.addPlot()
        self.w3.setLabel('bottom', text='ΔI', units ='A')
        self.w3.setLabel('left', text='Counts')

        self.w4 = self.ui.dwellhistplot.addPlot()
        self.w4.setLabel('bottom', text='Log Dwell Time', units = 'μs')
        self.w4.setLabel('left', text='Counts')

        self.w5 = self.ui.dthistplot.addPlot()
        self.w5.setLabel('bottom', text='dt', units = 's')
        self.w5.setLabel('left', text='Counts')

#        self.w6 = self.ui.PSDplot.addPlot()
#        self.w6.setLogMode(x = True, y = True)
#        self.w6.setLabel('bottom', text='Frequency (Hz)')
#        self.w6.setLabel('left', text='PSD (pA^2/Hz)')

        self.p3 = self.ui.eventplot.addPlot()
        self.p3.hideAxis('bottom')
        self.p3.hideAxis('left')

        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.logo=plt.imread(dir_path + os.sep + "pythionlogo.png")
        self.logo=np.rot90(self.logo,-1)
        self.logo = pg.ImageItem(self.logo)
        self.p3.addItem(self.logo)
        self.p3.setAspectLocked(True)


        ####### Initializing various variables used for analysis##############
        self.direc= os.getcwd()
        self.datafilename = []
        self.lr=[]
        self.lastevent=[]
        self.lastClicked=[]
        self.hasbaselinebeenset=0
        self.lastevent=0
        self.deli=[]
        self.frac=[]
        self.dwell=[]
        self.dt=[]
        self.catdata=[]
        self.colors=[]
        self.sdf = pd.DataFrame(columns = ['fn','color','deli','frac',
            'dwell','dt','startpoints','endpoints'])
        self.is_normalized_to_G=False


        

    def Load(self, loadandplot = True):
        self.catdata=[]
        self.batchinfo = pd.DataFrame(columns = list(['cutstart', 'cutend']))
        self.p3.clear()
        self.p3.setLabel('bottom', text='Current', units='A', unitprefix = 'n')
        self.p3.setLabel('left', text='', units = 'Counts')
        self.p3.setAspectLocked(False)

        colors = np.array(self.sdf.color)
        for i in range(len(colors)):
            colors[i] = pg.Color(colors[i])

        self.p2.setBrush(colors, mask=None)

        self.ui.eventinfolabel.clear()
        self.ui.eventcounterlabel.clear()
        self.ui.meandelilabel.clear()
        self.ui.meandwelllabel.clear()
        self.ui.meandtlabel.clear()
        self.totalplotpoints=len(self.p2.data)
        self.ui.eventnumberentry.setText(str(0))



        self.threshold=np.float64(self.ui.thresholdentry.text())*10**-9
        self.ui.filelabel.setText(self.datafilename)
        print(self.datafilename)
        self.LPfiltercutoff = np.float64(self.ui.LPentry.text())*1000
        self.outputsamplerate = np.float64(self.ui.outputsamplerateentry.text())*1000 #use integer multiples of 4166.67 ie 2083.33 or 1041.67


        if str(os.path.splitext(self.datafilename)[1])=='.log':
            self.CHIMERAfile = np.dtype('<u2')
            self.data=np.fromfile(self.datafilename,self.CHIMERAfile)

            self.matfilename=str(os.path.splitext(self.datafilename)[0])
            self.mat = spio.loadmat(self.matfilename)


            samplerate = np.float64(self.mat['ADCSAMPLERATE'])
            TIAgain = np.int32(self.mat['SETUP_TIAgain'])
            preADCgain = np.float64(self.mat['SETUP_preADCgain'])
            currentoffset = np.float64(self.mat['SETUP_pAoffset'])
            ADCvref = np.float64(self.mat['SETUP_ADCVREF'])
            ADCbits = np.int32(self.mat['SETUP_ADCBITS'])
            closedloop_gain = TIAgain*preADCgain;


            if samplerate < 4000e3:
                self.data=self.data[::round(samplerate/self.outputsamplerate)]


            bitmask = (2**16 - 1) - (2**(16-ADCbits) - 1)
            self.data = -ADCvref + (2*ADCvref) * (self.data & bitmask) / 2**16
            self.data = (self.data/closedloop_gain + currentoffset)
            self.data=self.data[0]
        
            ###############################################data has now been loaded
            ###############################################now filtering data

            Wn = round(self.LPfiltercutoff/(samplerate/2),4)
            b,a = signal.bessel(4, Wn, btype='low');

            self.data = signal.filtfilt(b,a,self.data)
            
        ### elements data files ###

        if str(os.path.splitext(self.datafilename)[1])=='.edh':
            self.headerfilename=self.datafilename

            basefname=str(os.path.splitext(self.datafilename)[0])
            i=0
            # max_limit = input("enter maximum number of files to import")
            datafilenames=[]
            while (os.path.exists(basefname+f"_{i:03}.dat")):
                datafilenames.append(basefname+f"_{i:03}.dat")
                i+=1
            i=0
            while (os.path.exists(basefname+f"_CH001_{i:03}.abf")):
                datafilenames.append(basefname+f"_CH001_{i:03}.abf")
                i+=1

            nfiles=len(datafilenames)
            start_num, ok = PyQt5.QtWidgets.QInputDialog.getInt(None,"Starting File",f"Enter starting file number to import (0 - {nfiles-1:03})",value=0,min=0, max=nfiles-1)
            if not ok:
                return
            max_limit, ok = PyQt5.QtWidgets.QInputDialog.getInt(None,"File limit","Enter maximum number of files to import",value=1)
            if not ok:
                return
            self.datafilenames=[]
            i=start_num
            while (os.path.exists(basefname+f"_{i:03}.dat") and i<start_num+max_limit):
                self.datafilenames.append(basefname+f"_{i:03}.dat")
                i+=1
            i=start_num
            while (os.path.exists(basefname+f"_CH001_{i:03}.abf") and i<start_num+max_limit):
                self.datafilenames.append(basefname+f"_CH001_{i:03}.abf")
                i+=1
            if self.datafilenames:
                for fname in self.datafilenames:
                    print("\t"+fname)
                    
            with open(self.headerfilename,"r") as headerfile:
                for line in headerfile:
                    if line.startswith("EDH Version"):
                        if line.split(":")[1].strip()!="2.0":
                            print("EDH version not supported")
                            return
                    else:
                        if line.startswith("Channels"):
                            self.numberOfChannels=int(line.split(":")[1])
                        if line.startswith("Sampling frequency"):
                            samplerate=np.float64(int(line.split(":")[1].strip().split()[0])*1000)
                        if line.startswith("Final Bandwidth"):
                            filtrate=np.float64(samplerate/int(line.split("/")[1].split(" ")[0]))
                        if line.startswith("Active Channels"):
                            self.numberOfChannels=int(line.split(":")[1])
            if self.datafilenames:
                self.data=[]
                self.voltage=[]
                self.matfilename=self.datafilenames[0]
                for datafilename in self.datafilenames:
                    if datafilename[-4:]=='.abf':
                        data=pyabf.ABF(datafilename)
                        data=data.data
                    else:
                        data=np.fromfile(datafilename,dtype="float32")
                        data=data.reshape((self.numberOfChannels+1,-1),order="F")
                    self.data=np.concatenate((self.data,data[0]*1e-9),axis=None)
                    self.voltage=np.concatenate((self.voltage,data[self.numberOfChannels]),axis=None)
                    self.is_normalized_to_G=False
                    print('voltage channel shape ',self.voltage.shape)
                    print('current channel shape ',self.data.shape)
                
            if samplerate < self.outputsamplerate:
                self.outputsamplerate=samplerate
                self.ui.outputsamplerateentry.setText(str((round(samplerate)/1000)))








        if str(os.path.splitext(self.datafilename)[1])=='.opt':
            print(".opt file")
            self.data = np.fromfile(self.datafilename, dtype = np.dtype('>d'))
            print(self.data.shape)
            self.matfilename = str(os.path.splitext(self.datafilename)[0])
            self.voltage=None
            try:
                self.mat = spio.loadmat(self.matfilename + '_inf')
                matstruct = self.mat[os.path.basename(self.matfilename)]
                matstruct.shape
                self.mat = matstruct[0][0]
                samplerate = np.float64(self.mat['samplerate'])
                filtrate = np.float64(self.mat['filterfreq'])
            except TypeError as ee:
########## try to load NFS file #################################         
                print ("skipping ", ee)
                try:
                    matfile = os.path.basename(self.matfilename)
                    self.mat = loadmat.loadmat(self.matfilename)[matfile]
                    samplerate = np.float64(self.mat['samplerate'])
                    filtrate = np.float64(self.mat['filterfreq']*1000)
                    self.potential = np.float64(self.mat['potential'])
                    self.pre_trigger_time_ms = np.float64(self.mat['pretrigger_time'])
                    self.post_trigger_time_ms = np.float64(self.mat['posttrigger_time'])
                    
                    trigger_data = self.mat['triggered_pulse']
                    self.start_voltage = trigger_data[0].initial_value
                    self.final_voltage = trigger_data[0].ramp_target_value
                    self.ramp_duration_ms = trigger_data[0].duration
                    self.eject_voltage = trigger_data[1].initial_value
                    self.eject_duration_ms = np.float64(trigger_data[1].duration)
                except Exception as e:
                    print (e)
                    pass
##################################################################
 
            # if samplerate < self.outputsamplerate:
            #     print("data sampled at lower rate than requested, reverting to original sampling rate")
            #     self.ui.outputsamplerateentry.setText(str((round(samplerate)/1000)))
            #     self.outputsamplerate = samplerate
                
            # elif self.outputsamplerate > 250e3:
            #         print('sample rate can not be >250kHz for axopatch files, displaying with a rate of 250kHz')
            #         self.outputsamplerate  = 250e3


            # if self.LPfiltercutoff >= filtrate:
            #     print('Already LP filtered lower than or at entry, data will not be filtered')
            #     self.LPfiltercutoff  = filtrate
            #     self.ui.LPentry.setText(str((round(self.LPfiltercutoff)/1000)))
                
            # elif self.LPfiltercutoff < 100e3:
            #     Wn = round(self.LPfiltercutoff/(100*10**3/2),4)
            #     b,a = signal.bessel(4, Wn, btype='low');
            #     self.data = signal.filtfilt(b,a,self.data)
            # else:
            #     print('Filter value too high, data not filtered')
        print("checkpoint")
        if str(os.path.splitext(self.datafilename)[1])=='.txt':
            self.data=pandas.io.parsers.read_csv(self.datafilename,skiprows=1)
#            self.data=np.reshape(np.array(self.data),np.size(self.data))*10**9
            self.data=np.reshape(np.array(self.data),np.size(self.data))
            self.matfilename=str(os.path.splitext(self.datafilename)[0])


        if str(os.path.splitext(self.datafilename)[1])=='.npy':
            self.data = np.load(self.datafilename)
            self.matfilename=str(os.path.splitext(self.datafilename)[0])

        if str(os.path.splitext(self.datafilename)[1])=='.abf':
            f = open(self.datafilename, "rb")  # reopen the file
            f.seek(6144, os.SEEK_SET)
            self.data = np.fromfile(f, dtype = np.dtype('<i2'))
            self.matfilename=str(os.path.splitext(self.datafilename)[0])
            self.header = read_header(self.datafilename)
            self.samplerate = 1e6/self.header['protocol']['fADCSequenceInterval']
            self.telegraphmode = int(self.header['listADCInfo'][0]['nTelegraphEnable'])
            if self.telegraphmode == 1:
                self.abflowpass = self.header['listADCInfo'][0]['fTelegraphFilter']
                self.gain = self.header['listADCInfo'][0]['fTelegraphAdditGain']
            else:
                self.gain = 1
                self.abflowpass = self.samplerate
                
            self.data=self.data.astype(float)*(20./(65536*self.gain))*10**-9                
            
            if len(self.header['listADCInfo']) == 2:
                self.v = self.data[1::2]*self.gain/10
                self.data = self. data[::2]
            else:
                self.v = [] 
               
                
            if self.outputsamplerate > self.samplerate:
                    print('output samplerate can not be higher than samplerate, resetting to original rate')
                    self.outputsamplerate  = self.samplerate
                    self.ui.outputsamplerateentry.setText(str((round(self.samplerate)/1000)))
            if self.LPfiltercutoff >= self.abflowpass:
                    print('Already LP filtered lower than or at entry, data will not be filtered')
                    self.LPfiltercutoff  = self.abflowpass
                    self.ui.LPentry.setText(str((round(self.LPfiltercutoff)/1000)))
            else:
                Wn = round(self.LPfiltercutoff/(100*10**3/2),4)
                b,a = signal.bessel(4, Wn, btype='low');
                self.data = signal.filtfilt(b,a,self.data)

                
            tags = self.header['listTag']
            for tag in tags:
                if tag['sComment'][0:21] == "Holding on 'Cmd 0' =>":
                    cmdv = tag['sComment'][22:]
#                    cmdv = [int(s) for s in cmdv.split() if s.isdigit()]
                    cmdt = tag ['lTagTime']/self.outputsamplerate
                    self.p1.addItem(pg.InfiniteLine(cmdt))
#                    cmdtext = pg.TextItem(text = str(cmdv)+' mV')
                    cmdtext = pg.TextItem(text = str(cmdv))
                    self.p1.addItem(cmdtext)
                    cmdtext.setPos(cmdt,np.max(self.data))


        self.t=np.arange(0,len(self.data))
        self.t=self.t/self.outputsamplerate

        if self.hasbaselinebeenset==0:
            self.baseline=np.median(self.data)
            self.var=np.std(self.data)
        self.ui.eventcounterlabel.setText('Baseline='+str(round(self.baseline*10**9,2))+' nA')


        if loadandplot == True:
            self.p1.clear()
            self.p1.setDownsampling(ds = True)
            #skips plotting first and last two points, there was a weird spike issue
            self.p1.plot(self.t[2:][:-2],self.data[2:][:-2],pen='b')
    
            if str(os.path.splitext(self.datafilename)[1]) != '.abf':
                self.p1.addLine(y=self.baseline,pen='g')
                self.p1.addLine(y=self.threshold,pen='r')
    
            self.p1.autoRange()
    
            self.p3.clear()
            aphy, aphx = np.histogram(self.data, bins = 1000)
            aphhist = pg.PlotCurveItem(aphx, aphy, stepMode=True, fillLevel=0, brush='b')
            self.p3.addItem(aphhist)
            self.p3.setXRange(np.min(self.data), np.max(self.data))
            
    
    #        if self.v != []:
    #            self.p1.plot(self.t[2:][:-2],self.v[2:][:-2],pen='r')
            
    #        self.w6.clear()
    #        f, Pxx_den = signal.welch(self.data*10**12, self.outputsamplerate, nperseg = self.outputsamplerate)
    #        self.w6.plot(x = f[1:], y = Pxx_den[1:], pen = 'b')
    #        self.w6.setXRange(0,np.log10(self.outputsamplerate))

    def getfile(self):

        try:
            ######## attempt to open dialog from most recent directory########
            self.datafilename = QtWidgets.QFileDialog.getOpenFileName(self,'Open file',self.direc,("*.log;*.opt;*.npy;*.abf;*.edh"))
            if self.datafilename != ('', ''):
                self.datafilename = self.datafilename[0]
                self.direc=os.path.dirname(self.datafilename)
                self.Load()
        except IOError:
            #### if user cancels during file selection, exit loop#############
            pass

    def run_spike_test1(self):
        self.datafilename="F:/OneDrive - Northeastern University/Wanunu Lab/ViralNPQ/Data/EDR/ViralNPQ/cellexps/Q5_200_spike_on_Ace2_01/Q5_200_spike_on_Ace2.edh"
        self.direc=os.path.dirname(self.datafilename)
        self.Load()
        self.sp={}  
        self.sp["rising"]= True
        self.sp["falling"]= False
        self.sp["heightMin"]= -21*1e-9
        self.sp["heightMax"]= -10*1e-9
        self.sp["widthMin"]=20*1e-6*self.outputsamplerate
        self.sp["widthMax"]=250*1e-6*self.outputsamplerate
        self.sp["relHeight"]=0.5
        self.sp["prominenceMin"]=3.2*1e-9
        self.sp["prominenceMax"]=9*1e-9
        self.sp["distanceMin"]=1*1e-3*self.outputsamplerate
        self.analyze_spikes()
        

    
    def analyze_spikes(self):
        global startpoints,endpoints,mins
        if self.data is None:
            print('no data to analyze')
            return
        self.analyzetype = "spike"
        
        self.w2.clear()
        self.w3.clear()
        self.w4.clear()
        self.w5.clear()
        try:
            if self.sp["rising"]==True:
                peaks,props=signal.find_peaks(self.data,
                    height=(self.sp["heightMin"],self.sp["heightMax"]),
                    width=(self.sp["widthMin"],self.sp["widthMax"]),
                    prominence=(self.sp["prominenceMin"],self.sp["prominenceMax"]),
                    distance=self.sp["distanceMin"],
                    rel_height=self.sp["relHeight"],
                    wlen=self.sp["widthMax"]*5
                    )
            elif self.sp["falling"]==True:
                peaks,props=signal.find_peaks(-self.data,
                    height=(-self.sp["heightMax"],-self.sp["heightMin"]),
                    width=(self.sp["widthMin"],self.sp["widthMax"]),
                    prominence=(self.sp["prominenceMin"],self.sp["prominenceMax"]),
                    distance=self.sp["distanceMin"],
                    rel_height=self.sp["relHeight"]
                    )
            peaks,props=self.readjust_spike_baseline(peaks,props,100)
            print("# peaks found:", peaks.shape[0])
            print(peaks,props)
        except Exception as e:
            print("finding spikes failed...")
            print("error message:",e)
            return

        self.numberofevents=peaks.shape[0]
        self.peakprops=props
        self.deli=props["prominences"]
        self.dwell=props["widths"]*1e6/self.outputsamplerate
        startpoints=self.startpoints=props["left_bases"]
        endpoints=self.endpoints=props["right_bases"]
        self.left_ips=props["left_ips"]
        self.right_ips=props["right_ips"]
        self.frac = self.deli/(np.abs(self.data[peaks])+self.deli)
        self.peaks=peaks
        self.dt = np.array(0)
        self.dt=np.append(self.dt,np.diff(peaks)/self.outputsamplerate)

        self.p1.plot(self.t[peaks], self.data[peaks],pen=None, symbol='o',symbolBrush='g',symbolSize=10)
        self.ui.eventcounterlabel.setText('Events:'+str(self.numberofevents))
        self.ui.meandelilabel.setText('Deli:'+str(round(np.mean(self.deli*10**9),2))+' nA')
        self.ui.meandwelllabel.setText('Dwell:'+str(round(np.median(self.dwell),2))+ u' μs')
        self.ui.meandtlabel.setText('Rate:'+str(round(self.numberofevents/self.t[-1],1))+' events/s')
        self.noise = (10**10)*np.array([np.std(self.data[x:self.endpoints[i]])for i,x in enumerate(self.startpoints)])
        
        try:
            self.p2.data = self.p2.data[np.where(np.array(self.sdf.fn) != self.matfilename)]
        except:
            IndexError
        self.sdf = self.sdf[self.sdf.fn != self.matfilename]

        fn = pd.Series([self.matfilename,] * self.numberofevents)
        color = pd.Series([pg.colorTuple(self.cb.color()),] * self.numberofevents)

        self.sdf = self.sdf.append(pd.DataFrame({'fn':fn,'color':color,'deli':self.deli,
                                    'frac':self.frac,'dwell':self.dwell,
                                    'dt':self.dt,'stdev':self.noise,'startpoints':self.startpoints,
                                    'endpoints':self.endpoints}), ignore_index=True)
        
        self.p2.addPoints(x=np.log10(self.dwell),y=self.frac,
        symbol='o', brush=(self.cb.color()), pen = None, size = 10)


        self.w1.addItem(self.p2)
        self.w1.setLogMode(x=True,y=False)
        # self.p1.autoRange()
        self.w1.autoRange()
        self.ui.scatterplot.update()
        self.w1.setRange(yRange=[0,1])
        colors=self.sdf.color.unique()
        for i,x in enumerate(colors):

            fracy, fracx = np.histogram(self.sdf.frac[self.sdf.color == x], bins=np.linspace(0, 1, int(self.ui.fracbins.text())))
            deliy, delix = np.histogram(self.sdf.deli[self.sdf.color == x], bins=np.linspace(float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9, int(self.ui.delibins.text())))
            dwelly, dwellx = np.histogram(np.log10(self.sdf.dwell[self.sdf.color == x]), bins=np.linspace(float(self.ui.dwellrange0.text()), float(self.ui.dwellrange1.text()), int(self.ui.dwellbins.text())))
            dty, dtx = np.histogram(self.sdf.dt[self.sdf.color == x], bins=np.linspace(float(self.ui.dtrange0.text()), float(self.ui.dtrange1.text()), int(self.ui.dtbins.text())))

        
#            hist = pg.PlotCurveItem(fracy, fracx , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w2.addItem(hist)

            hist = pg.BarGraphItem(height = fracy, x0 = fracx[:-1], x1 = fracx[1:], brush = x)
            self.w2.addItem(hist)

#            hist = pg.PlotCurveItem(delix, deliy , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w3.addItem(hist)

            hist = pg.BarGraphItem(height = deliy, x0 = delix[:-1], x1 = delix[1:], brush = x)
            self.w3.addItem(hist)
#            self.w3.autoRange()
            self.w3.setRange(xRange = [float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9])

#            hist = pg.PlotCurveItem(dwellx, dwelly , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w4.addItem(hist)

            hist = pg.BarGraphItem(height = dwelly, x0 = dwellx[:-1], x1 = dwellx[1:], brush = x)
            self.w4.addItem(hist)

#            hist = pg.PlotCurveItem(dtx, dty , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w5.addItem(hist)

            hist = pg.BarGraphItem(height = dty, x0 = dtx[:-1], x1 = dtx[1:], brush = x)
            self.w5.addItem(hist)

        self.inspectevent(0)
        self.save()



    def readjust_spike_baseline(self,peaks,props,meanlen:int):
        leftmatches= np.argwhere(self.data[peaks]-props["prominences"]== self.data[props["left_bases"]])
        rightmatches=np.argwhere(self.data[peaks]-props["prominences"]==self.data[props["right_bases"]])
        
        
        leftmatches=leftmatches.ravel()
        rightmatches=rightmatches.ravel()
        props["prominences"][leftmatches.ravel()]=self.data[peaks[leftmatches]]  -[np.mean(self.data[props["left_bases"][x]-meanlen:props["left_bases"][x]]) for x in leftmatches]
        props["prominences"][rightmatches.ravel()]=self.data[peaks[rightmatches]]-[np.mean(self.data[props["right_bases"][x]:props["right_bases"][x]+meanlen]) for x in rightmatches]
        return peaks,props




    def spikedialog(self):
        self.spikedialogbox=peakToolkit(self)
        self.spikedialogbox.show()
        self.spikedialogbox.uipeak.peakAnalyzeBtn.clicked.connect(self.accept_spike_analyze)

    def accept_spike_analyze(self):
        self.sp={}  # parameters for peakfinder taken from peak analysis box
        uipeak=self.spikedialogbox.uipeak
        self.sp["rising"]= uipeak.peakTypeRising.isChecked()
        self.sp["falling"]=uipeak.peakTypeFalling.isChecked()
        self.sp["heightMin"]= None if not uipeak.peakLowerBound.isEnabled() else uipeak.peakLowerBound.value()*1e-9
        self.sp["heightMax"]= None if not uipeak.peakUpperBound.isEnabled() else uipeak.peakUpperBound.value()*1e-9
        self.sp["widthMin"]=None if not uipeak.widthMin.isEnabled() else uipeak.widthMin.value()*1e-6*self.outputsamplerate
        self.sp["widthMax"]=None if not uipeak.widthMax.isEnabled() else uipeak.widthMax.value()*1e-6*self.outputsamplerate
        self.sp["relHeight"]=None if not uipeak.relHeight.isEnabled() else uipeak.relHeight.value()
        self.sp["prominenceMin"]=None if not uipeak.prominenceMin.isEnabled() else uipeak.prominenceMin.value()*1e-9
        self.sp["prominenceMax"]=None if not uipeak.prominenceMax.isEnabled() else uipeak.prominenceMax.value()*1e-9
        self.sp["distanceMin"]=None if not uipeak.distanceMin.isEnabled() else uipeak.distanceMin.value()*1e-3*self.outputsamplerate
        print(self.sp)
        print(self.outputsamplerate)
        self.analyze_spikes()



    def filterdialog(self):
        self.filterdialogbox=FilterKit(self.outputsamplerate,self)
        self.filterdialogbox.show()
        self.filterdialogbox.uifilt.filterApplyBtn.clicked.connect(self.apply_filter)
        self.previousData=None

    def apply_filter(self):
        filteredData=self.filterdialogbox.apply_to(self.data)
        if filteredData is not None:
            # self.previousData=self.data
            self.data=filteredData
            self.p1.clear()
            self.p1.plot(self.t,self.data,pen='b')
    def undo_filter(self):
        if self.previousData:
            self.data=self.previousData
            self.p1.clear()
            self.p1.plot(self.t,self.data,pen='b')



    def analyze(self):
        global startpoints,endpoints, mins
        self.analyzetype = 'coarse'
        self.w2.clear()
        self.w3.clear()
        self.w4.clear()
        self.w5.clear()

        self.threshold = np.float64(self.ui.thresholdentry.text())*10**-9

#### find all points below threshold ####

        below = np.where(self.data < self.threshold)[0]

#### locate the points where the current crosses the threshold ####

        startandend = np.diff(below)
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
        if endpoints [-1] == len(self.data)-1:
            startpoints = np.delete(startpoints,-1)
            endpoints = np.delete(endpoints,-1)

#### Track points back up to baseline to find true start and end ####

        numberofevents=len(startpoints)
        highthresh = self.baseline - self.var

        for j in range(numberofevents):
            sp = startpoints[j] #mark initial guess for starting point
            while self.data[sp] < highthresh and sp > 0:
                sp = sp-1 # track back until we return to baseline
            startpoints[j] = sp # mark true startpoint

            ep = endpoints[j] #repeat process for end point
            if ep == len(self.data) -1:  # sure that the current returns to baseline
                endpoints[j] = 0              # before file ends. If not, mark points for
                startpoints[j] = 0              # deletion and break from loop
                ep = 0
                break
            while self.data[ep] < highthresh:
                ep = ep+1
                if ep == len(self.data) -1:  # sure that the current returns to baseline
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
        self.numberofevents = len(startpoints)

        if len(startpoints) > len(endpoints):
            startpoints = np.delete(startpoints, -1)
            self.numberofevents = len(startpoints)


#### Now we want to move the endpoints to be the last minimum for each ####
#### event so we find all minimas for each event, and set endpoint to last ####

        self.deli = np.zeros(self.numberofevents)
        self.dwell = np.zeros(self.numberofevents)

        for i in range(self.numberofevents):
            mins = np.array(signal.argrelmin(self.data[startpoints[i]:endpoints[i]])[0] + startpoints[i])
            mins = mins[self.data[mins] < self.baseline - 4*self.var]
            if len(mins) == 1:
                pass
                self.deli[i] = self.baseline - min(self.data[startpoints[i]:endpoints[i]])
                self.dwell[i] = (endpoints[i]-startpoints[i])*1e6/self.outputsamplerate
                endpoints[i] = mins[0]
            elif len(mins) > 1:
                self.deli[i] = self.baseline - np.mean(self.data[mins[0]:mins[-1]])
                endpoints[i] = mins[-1]
                self.dwell[i] = (endpoints[i]-startpoints[i])*1e6/self.outputsamplerate


        startpoints = startpoints[self.deli!=0]
        endpoints = endpoints[self.deli!=0]
        self.deli = self.deli[self.deli!=0]
        self.dwell = self.dwell[self.dwell!=0]
        self.frac = self.deli/self.baseline
        self.dt = np.array(0)
        self.dt=np.append(self.dt,np.diff(startpoints)/self.outputsamplerate)
        self.numberofevents = len(self.dt)
        self.noise = (10**10)*np.array([np.std(self.data[x:endpoints[i]])for i,x in enumerate(startpoints)])
        

        self.p1.clear()

        #skips plotting first and last two points, there was a weird spike issue
#        self.p1.plot(self.t[::10][2:][:-2],self.data[::10][2:][:-2],pen='b')
        self.p1.plot(self.t[2:][:-2],self.data[2:][:-2],pen='b')
        self.p1.plot(self.t[startpoints], self.data[startpoints],pen=None, symbol='o',symbolBrush='g',symbolSize=10)
        self.p1.plot(self.t[endpoints], self.data[endpoints], pen=None, symbol='o',symbolBrush='r',symbolSize=10)

        self.ui.eventcounterlabel.setText('Events:'+str(self.numberofevents))
        self.ui.meandelilabel.setText('Deli:'+str(round(np.mean(self.deli*10**9),2))+' nA')
        self.ui.meandwelllabel.setText('Dwell:'+str(round(np.median(self.dwell),2))+ u' μs')
        self.ui.meandtlabel.setText('Rate:'+str(round(self.numberofevents/self.t[-1],1))+' events/s')

        try:
            self.p2.data = self.p2.data[np.where(np.array(self.sdf.fn) != self.matfilename)]
        except:
            IndexError
        self.sdf = self.sdf[self.sdf.fn != self.matfilename]

        fn = pd.Series([self.matfilename,] * self.numberofevents)
        color = pd.Series([pg.colorTuple(self.cb.color()),] * self.numberofevents)

        self.sdf = self.sdf.append(pd.DataFrame({'fn':fn,'color':color,'deli':self.deli,
                                    'frac':self.frac,'dwell':self.dwell,
                                    'dt':self.dt,'stdev':self.noise,'startpoints':startpoints,
                                    'endpoints':endpoints}), ignore_index=True)

        self.p2.addPoints(x=np.log10(self.dwell),y=self.frac,
        symbol='o', brush=(self.cb.color()), pen = None, size = 10)


        self.w1.addItem(self.p2)
        self.w1.setLogMode(x=True,y=False)
        self.p1.autoRange()
        self.w1.autoRange()
        self.ui.scatterplot.update()
        self.w1.setRange(yRange=[0,1])

        colors = self.sdf.color.unique()
        for i, x in enumerate(colors):
            fracy, fracx = np.histogram(self.sdf.frac[self.sdf.color == x], bins=np.linspace(0, 1, int(self.ui.fracbins.text())))
            deliy, delix = np.histogram(self.sdf.deli[self.sdf.color == x], bins=np.linspace(float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9, int(self.ui.delibins.text())))
            dwelly, dwellx = np.histogram(np.log10(self.sdf.dwell[self.sdf.color == x]), bins=np.linspace(float(self.ui.dwellrange0.text()), float(self.ui.dwellrange1.text()), int(self.ui.dwellbins.text())))
            dty, dtx = np.histogram(self.sdf.dt[self.sdf.color == x], bins=np.linspace(float(self.ui.dtrange0.text()), float(self.ui.dtrange1.text()), int(self.ui.dtbins.text())))

#            hist = pg.PlotCurveItem(fracy, fracx , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w2.addItem(hist)

            hist = pg.BarGraphItem(height = fracy, x0 = fracx[:-1], x1 = fracx[1:], brush = x)
            self.w2.addItem(hist)

#            hist = pg.PlotCurveItem(delix, deliy , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w3.addItem(hist)

            hist = pg.BarGraphItem(height = deliy, x0 = delix[:-1], x1 = delix[1:], brush = x)
            self.w3.addItem(hist)
#            self.w3.autoRange()
            self.w3.setRange(xRange = [float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9])

#            hist = pg.PlotCurveItem(dwellx, dwelly , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w4.addItem(hist)

            hist = pg.BarGraphItem(height = dwelly, x0 = dwellx[:-1], x1 = dwellx[1:], brush = x)
            self.w4.addItem(hist)

#            hist = pg.PlotCurveItem(dtx, dty , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w5.addItem(hist)

            hist = pg.BarGraphItem(height = dty, x0 = dtx[:-1], x1 = dtx[1:], brush = x)
            self.w5.addItem(hist)

        self.save()
        self.savetarget()

    def save(self):
        if self.analyzetype == "spike":
            import datetime
            timestamp=datetime.datetime.now().isoformat('_','seconds').replace(':','.')
            if hasattr(self,"voltage"):
                self.spikevoltage= self.voltage[self.peaks]
                np.savetxt(self.matfilename+'DB_'+timestamp+'.txt',np.column_stack((self.deli,self.frac,self.dwell,self.dt,self.noise,self.spikevoltage)),delimiter='\t',
                    header= "deli" + '\t' + "frac" + '\t' +"dwell" + '\t'+"dt"+ '\t' + 'stdev' + '\t' + 'voltage')
            else:
                np.savetxt(self.datafilename+'DB_'+timestamp+'.txt',np.column_stack((self.deli,self.frac,self.dwell,self.dt,self.noise,self.peaks)),delimiter='\t',
                    header= "deli" + '\t' + "frac" + '\t' +"dwell" + '\t'+"dt"+ '\t' + 'stdev' + '\t'+'peakpos')
                print("saved")
            return

        np.savetxt(self.matfilename+'DB.txt',np.column_stack((self.deli,self.frac,self.dwell,self.dt,self.noise)),delimiter='\t',
                    header= "deli" + '\t' + "frac" + '\t' +"dwell" + '\t'+"dt"+ '\t' + 'stdev')

    def normalize_to_g(self):

        try:
            if self.voltage is None:
                return
        except:
            return
        if self.is_normalized_to_G:
            self.data=self.current_copy
            self.p1.clear()
            self.p1.setLabel('left',text='Current',units='A')
            self.is_normalized_to_G=False
        else:
            self.current_copy=self.data.copy()
            self.data=self.data/np.abs(self.voltage/1000)
            self.p1.clear()
            self.p1.setLabel('left', text='Signed Conductance', units='S')
            self.is_normalized_to_G=True
        self.p1.plot(self.t[2:][:-2],self.data[2:][:-2],pen='b')

    def inspectevent(self, clicked = []):

        #Reset plot
        self.p3.setLabel('bottom', text='Time', units='s')
        self.p3.setLabel('left', text='Current', units='A')
        self.p3.clear()

        #Correct for user error if non-extistent number is entered
        eventbuffer=np.int(self.ui.eventbufferentry.text())
        firstindex = self.sdf.fn[self.sdf.fn == self.matfilename].index[0]
        if clicked == []:
            eventnumber = np.int(self.ui.eventnumberentry.text())
        else:
            eventnumber = clicked - firstindex
            self.ui.eventnumberentry.setText(str(eventnumber))
        if eventnumber>=self.numberofevents:
            eventnumber=self.numberofevents-1
            self.ui.eventnumberentry.setText(str(eventnumber))

        #plot event trace
        self.p3.plot(self.t[int(startpoints[eventnumber]-eventbuffer):int(endpoints[eventnumber]+eventbuffer)],
                     self.data[int(startpoints[eventnumber]-eventbuffer):int(endpoints[eventnumber]+eventbuffer)], pen='b')

        #plot event fit
        if self.analyzetype!="spike":
            self.p3.plot(self.t[int(startpoints[eventnumber]-eventbuffer):int(endpoints[eventnumber]+eventbuffer)],np.concatenate((
                         np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([self.baseline-self.deli[eventnumber
                         ]]),endpoints[eventnumber]-startpoints[eventnumber]),np.repeat(np.array([self.baseline]),eventbuffer)),0),pen=pg.mkPen(color=(173,27,183),width=3))
        else:
            #plot spike events 

            #vertical line for height
            self.p3.plot([self.t[int(self.peaks[eventnumber])],]*2 , 
                [self.data[self.peaks[eventnumber]]-self.deli[eventnumber] ,self.data[self.peaks[eventnumber]]],
                pen=pg.mkPen(color=(240,0,0),width=3))
            #horizontal line for width
            self.p3.plot([self.t[int(self.left_ips[eventnumber])],self.t[int(self.right_ips[eventnumber])]],
                [self.peakprops["width_heights"][eventnumber],]*2,
                pen=pg.mkPen(color=(0,200,30),width=3))
            #horizontal line for baseline
            self.p3.plot([self.t[int(self.startpoints[eventnumber])],self.t[int(self.endpoints[eventnumber])]],
                [self.data[self.peaks[eventnumber]]-self.deli[eventnumber,]]*2,
                pen=pg.mkPen(color=(190,50,190),width=3))

        self.p3.autoRange()
        #Mark event that is being viewed on scatter plot

        colors = np.array(self.sdf.color)
        for i in range(len(colors)):
            colors[i] = pg.Color(colors[i])
        colors[firstindex + eventnumber] = pg.mkColor('r')

        self.p2.setBrush(colors, mask=None)


        #Mark event start and end points
        if self.analyzetype!="spike":
            self.p3.plot([self.t[int(startpoints[eventnumber])], self.t[int(startpoints[eventnumber])]],[self.data[int(startpoints[eventnumber])], self.data[int(startpoints[eventnumber])]],pen=None, symbol='o',symbolBrush='g',symbolSize=12)
            self.p3.plot([self.t[int(endpoints[eventnumber])], self.t[int(endpoints[eventnumber])]],[self.data[int(endpoints[eventnumber])], self.data[int(endpoints[eventnumber])]],pen=None, symbol='o',symbolBrush='r',symbolSize=12)

        self.ui.eventinfolabel.setText('Dwell Time=' + str(round(self.dwell[eventnumber],2))+ u' μs,   Deli='+str(round(self.deli[eventnumber]*10**9,2)) +' nA')


#        if self.ui.cusumstepentry.text() != 'None':
#
# ########################################################################
#
#            x=self.data[startpoints[eventnumber]-eventbuffer:endpoints[eventnumber]+eventbuffer]
#            mins=signal.argrelmin(x)[0]
#            drift=.0
#            self.fitthreshold = np.float64(self.ui.cusumstepentry.text())
#            eventfit=np.array((0))
#
#            gp, gn = np.zeros(x.size), np.zeros(x.size)
#            ta, tai, taf = np.array([[], [], []], dtype=int)
#            tap, tan = 0, 0
#            # Find changes (online form)
#            for i in range(mins[0], mins[-1]):
#                s = x[i] - x[i-1]
#                gp[i] = gp[i-1] + s - drift  # cumulative sum for + change
#                gn[i] = gn[i-1] - s - drift  # cumulative sum for - change
#                if gp[i] < 0:
#                    gp[i], tap = 0, i
#                if gn[i] < 0:
#                    gn[i], tan = 0, i
#                if gp[i] > self.fitthreshold or gn[i] > self.fitthreshold:  # change detected!
#                    ta = np.append(ta, i)    # alarm index
#                    tai = np.append(tai, tap if gp[i] > self.fitthreshold else tan)  # start
#                    gp[i], gn[i] = 0, 0      # reset alarm
#
#            eventfit=np.repeat(np.array(self.baseline),ta[0])
#            for i in range(1,ta.size):
#                eventfit=np.concatenate((eventfit,np.repeat(np.array(np.mean(x[ta[i-1]:ta[i]])),ta[i]-ta[i-1])))
#            eventfit=np.concatenate((eventfit,np.repeat(np.array(self.baseline),x.size-ta[-1])))
#            self.p3.plot(self.t[startpoints[eventnumber]-eventbuffer:endpoints[eventnumber]+eventbuffer],eventfit
#                ,pen=pg.mkPen(color=(255,255,0),width=3))
#    #        pg.plot(eventfit)
#
#
#            self.p3.plot(self.t[ta+startpoints[eventnumber]-eventbuffer],x[ta],pen=None,symbol='o',symbolBrush='m',symbolSize=8)
#
#
# ########################################################################


    def nextevent(self):
        eventnumber=np.int(self.ui.eventnumberentry.text())

        if eventnumber>=self.numberofevents-1:
            eventnumber=0
        else:
            eventnumber=np.int(self.ui.eventnumberentry.text())+1
        self.ui.eventnumberentry.setText(str(eventnumber))
        self.inspectevent()

    def previousevent(self):

        eventnumber=np.int(self.ui.eventnumberentry.text())

        eventnumber=np.int(self.ui.eventnumberentry.text())-1
        if eventnumber<0:
            eventnumber=self.numberofevents-1
        self.ui.eventnumberentry.setText(str(eventnumber))
        self.inspectevent()

    def cut(self):
        
        ###### first check to see if cutting############

        if self.lr==[]:
            ######## if no cutting window exists, make one##########
            self.lr = pg.LinearRegionItem()
            self.lr.hide()

            ##### detect clears and auto-position window around the clear#####
            clears = np.where(np.abs(self.data) > self.baseline + 10*self.var)[0]
            if clears != []:
                clearstarts = clears[0]
                try:
                    clearends = clearstarts + np.where((self.data[clearstarts:-1] > self.baseline) &
                    (self.data[clearstarts:-1] < self.baseline+self.var))[0][10000]
                except:
                    clearends = -1
                clearstarts = np.where(self.data[0:clearstarts] > self.baseline)
                try:
                    clearstarts = clearstarts[0][-1]
                except:
                    clearstarts = 0

                self.lr.setRegion((self.t[clearstarts],self.t[clearends]))

            self.p1.addItem(self.lr)
            self.lr.show()


        #### if cut region has been set, cut region and replot remaining data####
        else:
            cutregion = self.lr.getRegion()
            self.p1.clear()
            self.data = np.delete(self.data,np.arange(np.int(cutregion[0]*self.outputsamplerate),np.int(cutregion[1]*self.outputsamplerate)))
            try:
                if self.voltage is not None:
                    print(self.voltage.shape)
                    self.voltage=np.delete(self.voltage,np.arange(np.int(cutregion[0]*self.outputsamplerate),np.int(cutregion[1]*self.outputsamplerate)))
                    print('--> ', self.voltage.shape)
            except:
                pass
            self.t=np.arange(0,len(self.data))
            self.t=self.t/self.outputsamplerate

            if self.hasbaselinebeenset==0:
                self.baseline = np.median(self.data)
                self.var=np.std(self.data)
                self.ui.eventcounterlabel.setText('Baseline='+str(round(self.baseline*10**9,2))+' nA')

            self.p1.plot(self.t,self.data,pen='b')
            if str(os.path.splitext(self.datafilename)[1]) != '.abf':
                self.p1.addLine(y=self.baseline,pen='g')
                self.p1.addLine(y=self.threshold,pen='r')
            self.lr=[]
#            self.p1.autoRange()
            self.p3.clear()
#            aphy, aphx = np.histogram(self.data, bins = len(self.data)/1000)
            aphy, aphx = np.histogram(self.data, bins = 1000)

            aphhist = pg.BarGraphItem(height = aphy, x0 = aphx[:-1], x1 = aphx[1:],brush = 'b', pen = None)
            self.p3.addItem(aphhist)
            self.p3.setXRange(np.min(self.data), np.max(self.data))
            
            cf = pd.DataFrame([cutregion], columns = list(['cutstart', 'cutend']))
            self.batchinfo = self.batchinfo.append(cf, ignore_index = True)


    def baselinecalc(self):
        if self.lr==[]:
            self.p1.clear()
            self.lr = pg.LinearRegionItem()
            self.lr.hide()
            self.p1.addItem(self.lr)

#            self.p1.plot(self.t[::100],self.data[::100],pen='b')
            self.p1.plot(self.t,self.data,pen='b')
            self.lr.show()

        else:
            calcregion=self.lr.getRegion()
            self.p1.clear()

            self.baseline=np.median(self.data[np.arange(np.int(calcregion[0]*self.outputsamplerate),np.int(calcregion[1]*self.outputsamplerate))])
            self.var=np.std(self.data[np.arange(np.int(calcregion[0]*self.outputsamplerate),np.int(calcregion[1]*self.outputsamplerate))])
#            self.p1.plot(self.t[::10][2:][:-2],self.data[::10][2:][:-2],pen='b')
            self.p1.plot(self.t,self.data,pen='b')
            self.p1.addLine(y=self.baseline,pen='g')
            self.p1.addLine(y=self.threshold,pen='r')
            self.lr=[]
            self.hasbaselinebeenset=1
            self.ui.eventcounterlabel.setText('Baseline='+str(round(self.baseline*10**9,2))+' nA')
            self.p1.autoRange()


    def clearscatter(self):
        self.p2.setData(x=[],y=[])
        self.lastevent=[]
        self.ui.scatterplot.update()
        self.w2.clear()
        self.w3.clear()
        self.w4.clear()
        self.w5.clear()
        self.sdf = pd.DataFrame(columns = ['fn','color','deli','frac',
            'dwell','dt','startpoints','endpoints'])

    def deleteevent(self):
        global startpoints,endpoints
        eventnumber = np.int(self.ui.eventnumberentry.text())
        firstindex = self.sdf.fn[self.sdf.fn == self.matfilename].index[0]
        if eventnumber > self.numberofevents:
            eventnumber = self.numberofevents-1
            self.ui.eventnumberentry.setText(str(eventnumber))
        self.deli=np.delete(self.deli,eventnumber)
        self.dwell=np.delete(self.dwell,eventnumber)
        self.dt=np.delete(self.dt,eventnumber)
        self.frac=np.delete(self.frac,eventnumber)
        try:
            self.noise=np.delete(self.noise,eventnumber)
        except AttributeError:
            pass
        startpoints=np.delete(startpoints,eventnumber)
        endpoints=np.delete(endpoints,eventnumber)
        self.p2.data=np.delete(self.p2.data,firstindex + eventnumber)

        self.numberofevents = len(self.dt)
        self.ui.eventcounterlabel.setText('Events:'+str(self.numberofevents))

        self.sdf = self.sdf.drop(firstindex + eventnumber).reset_index(drop = True)
        self.inspectevent()

        self.w2.clear()
        self.w3.clear()
        self.w4.clear()
        self.w5.clear()
        colors = self.sdf.color.unique()
        for i, x in enumerate(colors):
            fracy, fracx = np.histogram(self.sdf.frac[self.sdf.color == x], bins=np.linspace(0, 1, int(self.ui.fracbins.text())))
            deliy, delix = np.histogram(self.sdf.deli[self.sdf.color == x], bins=np.linspace(float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9, int(self.ui.delibins.text())))
            dwelly, dwellx = np.histogram(np.log10(self.sdf.dwell[self.sdf.color == x]), bins=np.linspace(float(self.ui.dwellrange0.text()), float(self.ui.dwellrange1.text()), int(self.ui.dwellbins.text())))
            dty, dtx = np.histogram(self.sdf.dt[self.sdf.color == x], bins=np.linspace(float(self.ui.dtrange0.text()), float(self.ui.dtrange1.text()), int(self.ui.dtbins.text())))

#            hist = pg.PlotCurveItem(fracy, fracx , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w2.addItem(hist)

            hist = pg.BarGraphItem(height = fracy, x0 = fracx[:-1], x1 = fracx[1:], brush = x)
            self.w2.addItem(hist)

#            hist = pg.PlotCurveItem(delix, deliy , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w3.addItem(hist)

            hist = pg.BarGraphItem(height = deliy, x0 = delix[:-1], x1 = delix[1:], brush = x)
            self.w3.addItem(hist)
#            self.w3.autoRange()
            self.w3.setRange(xRange = [float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9])

#            hist = pg.PlotCurveItem(dwellx, dwelly , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w4.addItem(hist)

            hist = pg.BarGraphItem(height = dwelly, x0 = dwellx[:-1], x1 = dwellx[1:], brush = x)
            self.w4.addItem(hist)

#            hist = pg.PlotCurveItem(dtx, dty , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w5.addItem(hist)

            hist = pg.BarGraphItem(height = dty, x0 = dtx[:-1], x1 = dtx[1:], brush = x)
            self.w5.addItem(hist)

        if self.analyzetype == 'coarse':
            self.save()
            self.savetarget()
        if self.analyzetype == 'fine':
            np.savetxt(self.matfilename+'llDB.txt',
                       np.column_stack((self.deli,self.frac,self.dwell,self.dt, self.noise)),
                       delimiter='\t',header= "deli" + '\t' + "frac" + '\t' +"dwell" + '\t'+"dt"+ '\t' + 'stdev')

    def invertdata(self):
        self.p1.clear()
        self.data=-self.data

        if self.hasbaselinebeenset==0:
            self.baseline=np.median(self.data)
            self.var=np.std(self.data)

#        self.p1.plot(self.t[::10],self.data[::10],pen='b')
        self.p1.plot(self.t,self.data,pen='b')
        self.p1.addLine(y=self.baseline,pen='g')
        self.p1.addLine(y=self.threshold,pen='r')
        self.p1.autoRange()

    def clicked(self, plot, points):
        for i, p in enumerate(self.p2.points()):
            if p.pos() == points[0].pos():
                clickedindex = i

        if self.sdf.fn[clickedindex] != self.matfilename:
            print('Event is from an earlier file, not clickable')

        else:
            self.inspectevent(clickedindex)



    def concatenatetext(self):
        if self.direc==[]:
            textfilenames = QtGui.QFileDialog.getOpenFileNames(self, 'Open file','*.txt')[0]
            self.direc=os.path.dirname(textfilenames[0])
        else:
            textfilenames =QtGui.QFileDialog.getOpenFileNames(self, 'Open file',self.direc,'*.txt')[0]
            self.direc=os.path.dirname(textfilenames[0])
            
        i=0
        while i<len(textfilenames):
            temptextdata=np.loadtxt(str(textfilenames[i]),delimiter='\t')
            if i==0:
                newtextdata=temptextdata
            else:
                newtextdata=np.concatenate((newtextdata,temptextdata))
            i=i+1

        newfilename = QtGui.QFileDialog.getSaveFileName(self, 'New File name',self.direc,'*.txt')[0]
        np.savetxt(str(newfilename),newtextdata,delimiter='\t',
                   header= "dI" + '\t' + "fr" + '\t' +"dw"+ '\t'+"dt"+ '\t' + 'stdev')

    def nextfile(self):
        if str(os.path.splitext(self.datafilename)[1])=='.log':
            startindex=self.matfilename[-6::]
            filebase=self.matfilename[0:len(self.matfilename)-6]
            nextindex=str(int(startindex)+1)
            while os.path.isfile(filebase+nextindex+'.log')==False:
                nextindex=str(int(nextindex)+1)
                if int(nextindex)>int(startindex)+1000:
                    print('no such file')
                    break
            if os.path.isfile(filebase+nextindex+'.log')==True:
                self.datafilename=(filebase+nextindex+'.log')
                self.Load()

        if str(os.path.splitext(self.datafilename)[1])=='.abf':
            startindex=self.matfilename[-4::]
            filebase=self.matfilename[0:len(self.matfilename)-4]
            nextindex=str(int(startindex)+1).zfill(4)
            while os.path.isfile(filebase+nextindex+'.abf')==False:
                nextindex=str(int(nextindex)+1).zfill(4)
                if int(nextindex)>int(startindex)+1000:
                    print('no such file')
                    break
            if os.path.isfile(filebase+nextindex+'.abf')==True:
                self.datafilename=(filebase+nextindex+'.abf')
                self.Load()



    def previousfile(self):
        if str(os.path.splitext(self.datafilename)[1])=='.log':
            startindex=self.matfilename[-6::]
            filebase=self.matfilename[0:len(self.matfilename)-6]
            nextindex=str(int(startindex)-1)
            while os.path.isfile(filebase+nextindex+'.log')==False:
                nextindex=str(int(nextindex)-1)
                if int(nextindex)<int(startindex)-1000:
                    print('no such file')
                    break
            if os.path.isfile(filebase+nextindex+'.log')==True:
                self.datafilename=(filebase+nextindex+'.log')
                self.Load()

        if str(os.path.splitext(self.datafilename)[1])=='.abf':
            startindex=self.matfilename[-4::]
            filebase=self.matfilename[0:len(self.matfilename)-4]
            nextindex=str(int(startindex)-1).zfill(4)
            while os.path.isfile(filebase+nextindex+'.abf')==False:
                nextindex=str(int(nextindex)-1).zfill(4)
                if int(nextindex)<int(startindex)-1000:
                    print('no such file')
                    break
            if os.path.isfile(filebase+nextindex+'.abf')==True:
                self.datafilename=(filebase+nextindex+'.abf')
                self.Load()

    def savetrace(self):
        self.data.astype('d').tofile(self.matfilename+'_trace.bin')

    def showcattrace(self):
        eventbuffer=np.int(self.ui.eventbufferentry.text())
        numberofevents=len(self.dt)

        self.p1.clear()
        eventtime = [0]
        for i in range(numberofevents):
            if i<numberofevents-1:
                if endpoints[i]+eventbuffer>startpoints[i+1]:
                    print('overlapping event')
                else:
                    eventdata = self.data[startpoints[i]-eventbuffer:endpoints[i]+eventbuffer]
                    fitdata = np.concatenate((np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([
                        self.baseline-self.deli[i]]),endpoints[i]-startpoints[i]),np.repeat(np.array([self.baseline]),eventbuffer)),0)
                    eventtime = np.arange(0,len(eventdata)) + .75*eventbuffer + eventtime[-1]
                    self.p1.plot(eventtime/self.outputsamplerate, eventdata,pen='b')
                    self.p1.plot(eventtime/self.outputsamplerate, fitdata,pen=pg.mkPen(color=(173,27,183),width=2))

        self.p1.autoRange()

    def savecattrace(self):
        eventbuffer=np.int(self.ui.eventbufferentry.text())
        numberofevents=len(self.dt)
        self.catdata=self.data[startpoints[0]-eventbuffer:endpoints[0]+eventbuffer]
        self.catfits=np.concatenate((np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([
            self.baseline-self.deli[0]]),endpoints[0]-startpoints[0]),
            np.repeat(np.array([self.baseline]),eventbuffer)),0)

        for i in range(numberofevents):
            if i<numberofevents-1:
                if endpoints[i]+eventbuffer>startpoints[i+1]:
                    print('overlapping event')
                else:
                    self.catdata=np.concatenate((self.catdata,self.data[startpoints[i]-eventbuffer:endpoints[i]+eventbuffer]),0)
                    self.catfits=np.concatenate((self.catfits,np.concatenate((np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([
                        self.baseline-self.deli[i]]),endpoints[i]-startpoints[i]),np.repeat(np.array([self.baseline]),eventbuffer)),0)),0)

        self.tcat=np.arange(0,len(self.catdata))
        self.tcat=self.tcat/self.outputsamplerate
        self.catdata=self.catdata[::10]
        self.catdata.astype('d').tofile(self.matfilename+'_cattrace.bin')


    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Up:
            self.nextfile()
        if key == QtCore.Qt.Key_Down:
            self.previousfile()
        if key == QtCore.Qt.Key_Right:
            self.nextevent()
        if key == QtCore.Qt.Key_Left:
            self.previousevent()
        if key == QtCore.Qt.Key_Return:
            self.Load()
        if key == QtCore.Qt.Key_Space:
            self.analyze()
        if key == QtCore.Qt.Key_Delete:
            self.deleteevent()

    def saveeventfits(self):
        eventbuffer=np.int(self.ui.eventbufferentry.text())
        numberofevents=len(self.dt)
        self.catdata=self.data[startpoints[0]-eventbuffer:endpoints[0]+eventbuffer]
        self.catfits=np.concatenate((np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([
            self.baseline-self.deli[0]]),endpoints[0]-startpoints[0]),
            np.repeat(np.array([self.baseline]),eventbuffer)),0)

        for i in range(numberofevents):
            if i<numberofevents-1:
                if endpoints[i]+eventbuffer>startpoints[i+1]:
                    print('overlapping event')
                else:
                    self.catdata=np.concatenate((self.catdata,self.data[startpoints[i]-eventbuffer:endpoints[i]+eventbuffer]),0)
                    self.catfits=np.concatenate((self.catfits,np.concatenate((np.repeat(np.array([self.baseline]),eventbuffer),np.repeat(np.array([
                        self.baseline-self.deli[i]]),endpoints[i]-startpoints[i]),np.repeat(np.array([self.baseline]),eventbuffer)),0)),0)

        self.tcat=np.arange(0,len(self.catdata))
        self.tcat=self.tcat/self.outputsamplerate
        self.catfits.astype('d').tofile(self.matfilename+'_cattrace.bin')

    def CUSUM(self):
        self.p1.clear()
        self.p1.setDownsampling(ds = False)
        cusum = detect_cusum(self.data, basesd = self.var, dt = 1/self.outputsamplerate, 
                             threshhold  = np.float64(self.ui.thresholdentry.text()),
                             stepsize = np.float64(self.ui.levelthresholdentry.text()), 
                             minlength = 10)
        np.savetxt(self.matfilename+'_Levels.txt', np.abs(cusum['jumps']*10**12),delimiter='\t')

        self.p1.plot(self.t[2:][:-2],self.data[2:][:-2],pen='b')

        self.w3.clear()
        amp = np.abs(cusum['jumps']*10**12)
        ampy, ampx = np.histogram(amp, bins=np.linspace(float(self.ui.delirange0.text()), float(self.ui.delirange1.text()), int(self.ui.delibins.text())))
        hist = pg.BarGraphItem(height = ampy, x0 = ampx[:-1], x1 = ampx[1:], brush = 'b')
        self.w3.addItem(hist)
#        self.w3.autoRange()
        self.w3.setRange(xRange = [np.min(ampx),np.max(ampx)])

        cusumlines = np.array([]).reshape(0,2)
        for i,level in enumerate(cusum['CurrentLevels']):
            y = 2*[level]
            x = cusum['EventDelay'][i:i+2]
            self.p1.plot(y = y, x = x, pen = 'r')
            cusumlines = np.concatenate((cusumlines,np.array(zip(x,y))))
            try:
                y = cusum['CurrentLevels'][i:i+2]
                x = 2*[cusum['EventDelay'][i+1]]
                self.p1.plot(y = y, x = x, pen = 'r')
                cusumlines = np.concatenate((cusumlines,np.array(zip(x,y))))
            except Exception:
                pass
            
        cusumlines.astype('d').tofile(self.matfilename+'_cusum.bin')
        self.savetrace()
        
        print("Cusum Params" + str(cusum[Threshold],cusum[stepsize]))

#        amp = np.abs(cusum['jumps']*10**12)*10**9
#        ampy, ampx = np.histogram(amp,bins=np.linspace(0, np.max(amp), 100))
#        hist = pg.BarGraphItem(height = ampy, x0 = ampx[:-1], x1 = ampx[1:])
#        levelplot = pg.plot()
#        levelplot.addItem(hist)

    def savetarget(self):
        cutstart = self.batchinfo["cutstart"]
        cutend = self.batchinfo["cutend"]
        self.batchinfo = pd.DataFrame({'cutstart':cutstart,'cutend':cutend})
        self.batchinfo = self.batchinfo.dropna()
        self.batchinfo = self.batchinfo.append(pd.DataFrame({'deli':self.deli,
                    'frac':self.frac,'dwell':self.dwell,'dt':self.dt,'noise':self.noise, 
                    'startpoints':startpoints,'endpoints':endpoints}), ignore_index=True)
        self.batchinfo.to_pickle(self.matfilename+'batchinfo.pkl')

    def batchinfodialog(self):
        self.p1.clear()
        self.bp = batchprocesser()
        self.bp.show()
        
        try:
            self.bp.uibp.mindwellbox.setText(str(self.mindwell))
            self.bp.uibp.minfracbox.setText(str(self.minfrac))
            self.bp.uibp.minleveltbox.setText(str(self.minlevelt*10**6))
            self.bp.uibp.sampratebox.setText(str(self.samplerate))
            self.bp.uibp.LPfilterbox.setText(str(self.LPfiltercutoff/1000))
            self.bp.uibp.cusumstepentry.setText(str(self.cusumstep))
            self.bp.uibp.cusumthreshentry.setText(str(self.cusumthresh))
            self.bp.uibp.maxLevelsBox.setText(str(self.maxstates))
        except:
            ValueError
            
        self.bp.uibp.okbutton.clicked.connect(self.batchprocess)
        
    def batchprocess(self):
        global endpoints, startpoints
        self.analyzetype = 'fine'
        
        invertstatus = self.bp.uibp.invertCheckBox.isChecked()
        self.bp.close()
        self.p1.setDownsampling(ds = False)
        self.mindwell = np.float64(self.bp.uibp.mindwellbox.text())
        self.minfrac = np.float64(self.bp.uibp.minfracbox.text())
        self.minlevelt = np.float64(self.bp.uibp.minleveltbox.text())*10**-6
        self.samplerate = self.bp.uibp.sampratebox.text()
        self.LPfiltercutoff = self.bp.uibp.LPfilterbox.text()
        self.ui.outputsamplerateentry.setText(self.samplerate)
        self.ui.LPentry.setText(self.LPfiltercutoff)
        cusumstep = np.float64(self.bp.uibp.cusumstepentry.text())
        cusumthresh = np.float64(self.bp.uibp.cusumthreshentry.text())
        self.maxstates = np.int(self.bp.uibp.maxLevelsBox.text())
        selfcorrect = self.bp.uibp.selfCorrectCheckBox.isChecked()

        try:
            ######## attempt to open dialog from most recent directory########
            self.filelist = QtGui.QFileDialog.getOpenFileNames(self,'Select Files',self.direc,("*.pkl"))[0]
            self.direc=os.path.dirname(self.filelist[0])
        except TypeError:
            ####### if no recent directory exists open from working directory##
            self.direc==[]
            self.filelist = QtGui.QFileDialog.getOpenFileNames(self, 'Select Files',os.getcwd(),("*.pkl"))[0]
            print(self.filelist)
#            self.direc=os.path.dirname(str(self.filelist[0][0]))
        except IOError:
            #### if user cancels during file selection, exit loop#############
            return

        eventbuffer=np.int(self.ui.eventbufferentry.text())
        eventtime = [0]


        for f in self.filelist: 
            batchinfo = pd.read_pickle(f)
            try:
                self.datafilename = f[:-13] + '.opt'
                self.Load(loadandplot = False)
            except IOError:
                self.datafilename = f[:-13] + '.log'
                self.Load(loadandplot = False)
            if invertstatus:
                self.data=-self.data
                if self.hasbaselinebeenset==0:
                    self.baseline=np.median(self.data)
                    self.var=np.std(self.data)
                    
                
            
            try:
                cs = batchinfo.cutstart[np.isfinite(batchinfo.cutstart)]
                ce = batchinfo.cutend[np.isfinite(batchinfo.cutend)]
                for i, cut in enumerate(cs):
                    self.data = np.delete(self.data,np.arange(np.int(cut*self.outputsamplerate),np.int(ce[i]*self.outputsamplerate)))
            except TypeError:
                pass
             
             
            self.deli = np.array(batchinfo.deli[np.isfinite(batchinfo.deli)])
            self.frac = np.array(batchinfo.frac[np.isfinite(batchinfo.frac)])
            self.dwell = np.array(batchinfo.dwell[np.isfinite(batchinfo.dwell)])
            self.dt = np.array(batchinfo.dt[np.isfinite(batchinfo.dt)])
            startpoints = np.array(batchinfo.startpoints[np.isfinite(batchinfo.startpoints)])
            endpoints = np.array(batchinfo.endpoints[np.isfinite(batchinfo.endpoints)])
            self.noise = (10**10)*np.array([np.std(self.data[int(x):int(endpoints[i])])for i,x in enumerate(startpoints)])


            frac = self.frac
            deli = self.deli
            
 
            with pg.ProgressDialog("Analyzing...", 0, len(self.dwell)) as dlg:               
               for i,dwell in enumerate(self.dwell):
                    toffset = (eventtime[-1] + eventbuffer)/self.outputsamplerate
                    if i < len(self.dt)-1 and dwell > self.mindwell and frac[i] >self.minfrac:
                        if endpoints[i]+eventbuffer>startpoints[i+1]:
                            print('overlapping event')
                            frac[i] = np.NaN
                            deli[i] = np.NaN
                            
                        else:
                            eventdata = self.data[int(startpoints[i]-eventbuffer):int(endpoints[i]+eventbuffer)]
                            eventtime = np.arange(0,len(eventdata)) + eventbuffer + eventtime[-1]
#                            self.p1.plot(eventtime/self.outputsamplerate, eventdata,pen='b')
                            cusum = detect_cusum(eventdata, np.std(eventdata[0:eventbuffer]),
                                1/self.outputsamplerate, threshhold  = cusumthresh,
                                stepsize = cusumstep,
                                minlength = self.minlevelt*self.outputsamplerate,
                                maxstates = self.maxstates)
                            
                            while len(cusum['CurrentLevels']) < 3:
                                cusumthresh = cusumthresh *.9
                                cusumstep = cusumstep * .9
                                cusum = detect_cusum(eventdata, basesd = np.std(eventdata[0:eventbuffer])
                                    , dt = 1/self.outputsamplerate, threshhold  = cusumthresh
                                    , stepsize = cusumstep, minlength = self.minlevelt*self.outputsamplerate, maxstates = self.maxstates)
                                print('Not Sensitive Enough')
    
                                
                            frac[i] = (np.max(cusum['CurrentLevels'])-np.min(cusum['CurrentLevels']))/np.max(cusum['CurrentLevels'])
                            deli[i] = (np.max(cusum['CurrentLevels'])-np.min(cusum['CurrentLevels'])) 
                            
                            if selfcorrect:
                                cusumthresh = cusum['Threshold']
                                cusumstep = cusum['stepsize']
######################  Plotting   #########################                                                    
 #                           for j,level in enumerate(cusum['CurrentLevels']):
 #                               self.p1.plot(y = 2*[level], x = toffset + cusum['EventDelay'][j:j+2], pen = pg.mkPen( 'r', width = 5))
 #                               try:
 #                                   self.p1.plot(y = cusum['CurrentLevels'][j:j+2], x = toffset + 2*[cusum['EventDelay'][j+1]], pen = pg.mkPen( 'r', width = 5))
 #                               except Exception:
 #                                   pass
                    dlg += 1
######################  End Plotting   #########################                                                    


            self.dwell = self.dwell[np.isfinite(deli)]
            self.dt = self.dt[np.isfinite(deli)]
            self.noise = self.noise[np.isfinite(deli)]
            frac = frac[np.isfinite(deli)]
            startpoints = startpoints[np.isfinite(deli)]
            endpoints = endpoints[np.isfinite(deli)]
            deli = deli[np.isfinite(deli)]

            self.deli = deli
            self.frac = frac

            np.savetxt(self.matfilename+'llDB.txt',
                       np.column_stack((deli,frac,self.dwell,self.dt,self.noise)),
                       delimiter='\t',header= "deli" + '\t' + "frac" + '\t' +"dwell" + '\t'+"dt"+ '\t' + 'stdev')
        
        self.p1.autoRange()
        self.cusumthresh = cusumthresh
        self.cusumstep = cusumstep

###########Plotting Histograms#####################        
        self.sdf = self.sdf[self.sdf.fn != self.matfilename]
        self.numberofevents = len(self.dt)

        fn = pd.Series([self.matfilename,] * self.numberofevents)
        color = pd.Series([pg.colorTuple(self.cb.color()),] * self.numberofevents)

        self.sdf = self.sdf.append(pd.DataFrame({'fn':fn,'color':color,'deli':deli,
                                    'frac':frac,'dwell':self.dwell,
                                    'dt':self.dt,'startpoints':startpoints,
                                    'endpoints':endpoints}), ignore_index=True)
    
        self.deli = deli
        self.frac = frac

        self.p2.addPoints(x=np.log10(self.dwell),y=self.frac,
        symbol='o', brush=(self.cb.color()), pen = None, size = 10)


        self.w1.addItem(self.p2)
        self.w1.setLogMode(x=True,y=False)
        self.p1.autoRange()
        self.w1.autoRange()
        self.ui.scatterplot.update()
        self.w1.setRange(yRange=[0,1])

        colors = self.sdf.color.unique()
        for i, x in enumerate(colors):
            fracy, fracx = np.histogram(self.sdf.frac[(self.sdf.color == x) & (np.isnan(self.sdf.frac) == False)], bins=np.linspace(0, 1, int(self.ui.fracbins.text())))
            deliy, delix = np.histogram(self.sdf.deli[(self.sdf.color == x) & (np.isnan(self.sdf.deli) == False)], bins=np.linspace(float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9, int(self.ui.delibins.text())))
            dwelly, dwellx = np.histogram(np.log10(self.sdf.dwell[self.sdf.color == x]), bins=np.linspace(float(self.ui.dwellrange0.text()), float(self.ui.dwellrange1.text()), int(self.ui.dwellbins.text())))
            dty, dtx = np.histogram(self.sdf.dt[self.sdf.color == x], bins=np.linspace(float(self.ui.dtrange0.text()), float(self.ui.dtrange1.text()), int(self.ui.dtbins.text())))

#            hist = pg.PlotCurveItem(fracy, fracx , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w2.addItem(hist)

            hist = pg.BarGraphItem(height = fracy, x0 = fracx[:-1], x1 = fracx[1:], brush = x)
            self.w2.addItem(hist)

#            hist = pg.PlotCurveItem(delix, deliy , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w3.addItem(hist)

            hist = pg.BarGraphItem(height = deliy, x0 = delix[:-1], x1 = delix[1:], brush = x)
            self.w3.addItem(hist)
#            self.w3.autoRange()
            self.w3.setRange(xRange = [float(self.ui.delirange0.text())*10**-9, float(self.ui.delirange1.text())*10**-9])

#            hist = pg.PlotCurveItem(dwellx, dwelly , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w4.addItem(hist)

            hist = pg.BarGraphItem(height = dwelly, x0 = dwellx[:-1], x1 = dwellx[1:], brush = x)
            self.w4.addItem(hist)

#            hist = pg.PlotCurveItem(dtx, dty , stepMode = True, fillLevel=0, brush = x, pen = 'k')
#            self.w5.addItem(hist)

            hist = pg.BarGraphItem(height = dty, x0 = dtx[:-1], x1 = dtx[1:], brush = x)
            self.w5.addItem(hist)
        
        print('\007')
        
        
        

    def sizethepore(self):
        pass
        # self.ps = PoreSizer()
        # self.ps.show()

def start():
    global myapp
    app = QtWidgets.QApplication(sys.argv)
    resolution = app.desktop().screenGeometry()
    width,height = resolution.width(), resolution.height()
    myapp = GUIForm(width=width, height=height)
    myapp.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    start()

