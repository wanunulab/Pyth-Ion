# -*- coding: utf8 -*-

import os
import numpy as np
from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
import colorcet as cc
import time as builtintime
from abc import ABC, abstractmethod

from .DataTypes import *
from .__version__ import __version__

from .ui.maingui import *
from .ui.ivselection import Ui_AutoIVSelectDialog


class LogExponentAxisItem(pg.AxisItem):
    def __init__(self, orientation, **kwargs):
        super().__init__(orientation=orientation, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        strings = []
        for val in values:
            if val <= 0:
                strings.append('')
            else:
                # exponent = np.log10(val)
                exponent = val
                # Check if exponent is an integer
                if np.isclose(exponent, int(exponent)):
                    exponent = int(exponent)
                    strings.append(str(exponent))
                else:
                    # exponent = np.round(exponent, 2)
                    strings.append('')                
        return strings
        

class BaseAppMainWindow(QtWidgets.QMainWindow):
    class AwaitResponse:
        def __init__(self,widget) -> None:
            self._widget = widget

        def __enter__(self):
            self._widget.setDisabled(True)
            self._widget.repaint()
        
        def __exit__(self,*argv):
            self._widget.setDisabled(False)

    def __init__(self, width, height, master=None):
        ####Setup GUI and draw elements from UI file#########
        QtWidgets.QMainWindow.__init__(self,master)
        self.ui = Ui_PythIon()
        self.ui.setupUi(self)
        
        self.awaitresponse = self.AwaitResponse(self.ui.centralwidget)
        self.ui.action_version.setText(f'{__version__}')


        ###### Setting up plotting elements and their respective options######
        self.ui.signalplot.setBackground('w')
        self.ui.scatterplot.setBackground('w')
        self.ui.eventplot.setBackground('w')
        self.ui.frachistplot.setBackground('w')
        self.ui.delihistplot.setBackground('w')
        self.ui.dwellhistplot.setBackground('w')
        self.ui.dthistplot.setBackground('w')
#        self.ui.PSDplot.setBackground('w')
        for p in (self.ui.stdevplot, self.ui.skewnessplot, self.ui.kurtosisplot):
            p.setBackground('w')

        def setAxisFont(ax:pg.AxisItem):
            font = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
            fontsize_px = font.pixelSize()
            ax.setStyle(tickFont=font, tickTextOffset = fontsize_px)

        self.p1 : pg.PlotItem = self.ui.signalplot.addPlot()
        self.p1.setLabel('bottom', text='Time', units='s')
        self.p1.setLabel('left', text='Current (for voltage:pA->mV) ', units='A')
        self.p1.enableAutoRange(axis = 'x')
        #FIXME Curiously, when I change the x-axis data (self.t) to np.int32 dtype, the performance goes down.
        # Okay, so solely multiplying y-axis data (self.data.filt/raw) by 1e13 without casting to np.int32 
        # also increases performance. This means the performance issue was not on the dtype, but on eps?
        # self.p1.getAxis('bottom').setScale(1e-6)
        self.current_display_scale_factor = 1e13
        self.p1.getAxis('left').setScale(1/self.current_display_scale_factor)
        setAxisFont(self.p1.getAxis('left'))
        setAxisFont(self.p1.getAxis('bottom'))
        

        self.scatter_entries = ('events', 'cusum_states', 'annotations')
        self.state_colors = cc.b_glasbey_bw_minc_20
        self.inspect_event_fit_color_singlestate = (173,27,183,100)
        self.inspect_event_fit_color_multistate = (90, 110, 85, 100)

        self.w1 = self.ui.scatterplot.addPlot()
        axis = LogExponentAxisItem(orientation='bottom')
        self.w1.setAxisItems({'bottom':axis})
        self.p2 = dict()
        for entry in self.scatter_entries:
            p = pg.ScatterPlotItem()
            self.w1.addItem(p)
            self.p2[entry] = p
        self.w1.setLabel('bottom', text='Log Dwell Time', units=u'Log10(μs)')
        self.w1.setLabel('left', text='Fractional Current Blockage')
        self.w1.setLogMode(x=True,y=False)
        self.w1.showGrid(x=True, y=True)
        self.w1.getAxis('bottom').enableAutoSIPrefix(False)
        setAxisFont(self.w1.getAxis('bottom'))
        setAxisFont(self.w1.getAxis('left'))

        self.w1std = self.ui.stdevplot.addPlot()
        axis = LogExponentAxisItem(orientation='bottom')
        self.w1std.setAxisItems({'bottom':axis})
        self.p2std = dict()
        for entry in self.scatter_entries:
            p = pg.ScatterPlotItem()
            self.w1std.addItem(p)
            self.p2std[entry] = p
        self.w1std.setLabel('bottom', text='Log Dwell Time', units=u'Log10(μs)')
        self.w1std.setLabel('left', text='Standard deviation', units='A')
        self.w1std.setLogMode(x=True,y=False)
        self.w1std.showGrid(x=True, y=True)
        self.w1std.getAxis('bottom').enableAutoSIPrefix(False)
        setAxisFont(self.w1std.getAxis('bottom'))
        setAxisFont(self.w1std.getAxis('left'))

        self.w1skew = self.ui.skewnessplot.addPlot()
        axis = LogExponentAxisItem(orientation='bottom')
        self.w1skew.setAxisItems({'bottom':axis})
        self.p2skew = dict()
        for entry in self.scatter_entries:
            p = pg.ScatterPlotItem()
            self.w1skew.addItem(p)
            self.p2skew[entry] = p
        self.w1skew.setLabel('bottom', text='Log Dwell Time', units=u'Log10(μs)')
        self.w1skew.setLabel('left', text='Skewness')
        self.w1skew.setLogMode(x=True,y=False)
        self.w1skew.showGrid(x=True, y=True)
        self.w1skew.getAxis('bottom').enableAutoSIPrefix(False)
        setAxisFont(self.w1skew.getAxis('bottom'))
        setAxisFont(self.w1skew.getAxis('left'))

        self.w1kurt = self.ui.kurtosisplot.addPlot()
        axis = LogExponentAxisItem(orientation='bottom')
        self.w1kurt.setAxisItems({'bottom':axis})
        self.p2kurt = dict()
        for entry in self.scatter_entries:
            p = pg.ScatterPlotItem()
            self.w1kurt.addItem(p)
            self.p2kurt[entry] = p
        self.w1kurt.setLabel('bottom', text='Log Dwell Time', units=u'Log10(μs)')
        self.w1kurt.setLabel('left', text='Kurtosis')
        self.w1kurt.setLogMode(x=True,y=False)
        self.w1kurt.showGrid(x=True, y=True)
        self.w1kurt.getAxis('bottom').enableAutoSIPrefix(False)
        setAxisFont(self.w1kurt.getAxis('bottom'))
        setAxisFont(self.w1kurt.getAxis('left'))

        self.p2s = (self.p2, self.p2std, self.p2skew, self.p2kurt)

        self.w2 = self.ui.frachistplot.addPlot()
        self.w2.setLabel('bottom', text='Fractional Current Blockage')
        self.w2.setLabel('left', text='Counts')
        setAxisFont(self.w2.getAxis('bottom'))
        setAxisFont(self.w2.getAxis('left'))

        self.w3 = self.ui.delihistplot.addPlot()
        self.w3.setLabel('bottom', text='ΔI', units ='A')
        self.w3.setLabel('left', text='Counts')
        setAxisFont(self.w3.getAxis('bottom'))
        setAxisFont(self.w3.getAxis('left'))

        self.w4 = self.ui.dwellhistplot.addPlot()
        self.w4.setLabel('bottom', text='Log Dwell Time', units = 'μs')
        self.w4.setLabel('left', text='Counts')
        setAxisFont(self.w4.getAxis('bottom'))
        setAxisFont(self.w4.getAxis('left'))

        self.w5 = self.ui.dthistplot.addPlot()
        self.w5.setLabel('bottom', text='dt', units = 's')
        self.w5.setLabel('left', text='Counts')
        setAxisFont(self.w5.getAxis('bottom'))
        setAxisFont(self.w5.getAxis('left'))

        self.p3 = self.ui.eventplot.addPlot()
        self.p3.hideAxis('bottom')
        self.p3.hideAxis('left')

        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.p3.setAspectLocked(True)

        ####### Initializing various variables used for analysis##############
        self.analysis_config = None
        self.load_config = None
        self.perfiledata = FileData()
        self.DSratio = 4096
        self.updateDSratioBox()
        self.enable_save_analysis = True

    def updateDSratioBox(self):
        self.ui.dsValueEntry.setText(str(self.DSratio))
        self.printlog(f"Downsampling ratio now is {self.DSratio:d}")

    def printlog(self, log):
        # print(log)
        text = '>>> '+ str(log) + '\n'
        print(text)
        self.perfiledata.logtext += text
        self.ui.logText.setPlainText(self.perfiledata.logtext)
        self.ui.logText.moveCursor(QtGui.QTextCursor.End)
        self.ui.logText.repaint()

    @property
    def ui_baseline(self):
        return self.perfiledata.baseline
    
    @ui_baseline.setter
    def ui_baseline(self, val):
        self.perfiledata.baseline = val
        self.ui.eventcounterlabel.setText(f'Baseline={self.perfiledata.baseline*1e9:.4f} nA')
        self.printlog(f'Updated baseline to {self.perfiledata.baseline*1e9:.6f} nA')

    @property
    def ui_baseline_std(self):
        return self.perfiledata.baseline_std
    
    @ui_baseline_std.setter
    def ui_baseline_std(self, val):
        self.perfiledata.baseline_std = val
        self.printlog(f'Updated baseline std to {self.perfiledata.baseline_std*1e9:.6f} nA')

    
    def clearPerFileDisplays(self):
        self.p3.clear()
        self.p3.setLabel('bottom', text='Current', units='A', unitprefix = 'n')
        self.p3.setLabel('left', text='', units = 'Counts')
        self.p3.setAspectLocked(False)

        # self.p2.setBrush(colors, mask=None)
        # self.p2std.setBrush(colors, mask=None)
        # self.p2skew.setBrush(colors, mask=None)
        # self.p2kurt.setBrush(colors, mask=None)

        # for p in self.p2s:
        #     for entry in self.scatter_entries:
        #         p[entry].setBrush(colors, mask=None)
        
        self.ui.eventinfolabel.clear()
        self.ui.eventcounterlabel.clear()
        self.ui.meandelilabel.clear()
        self.ui.meandwelllabel.clear()
        self.ui.meandtlabel.clear()
        self.ui.eventnumberentry.setText(str(0))
            

    def updateRawFiltVisibility(self):
        for handle in self.perfiledata.p1RawTraceHandles:
            handle.setVisible(self.ui.checkBox_showRaw.isChecked())
        for handle in self.perfiledata.p1FiltTraceHandles:
            handle.setVisible(self.ui.checkBox_showFilt.isChecked())  
    
    def updateThresholdLine(self):
        self.p1.removeItem(self.perfiledata.threshHandle)
        dscl = self.current_display_scale_factor
        self.perfiledata.threshHandle = self.p1.addLine(y=self.analysis_config.threshold_A*dscl,pen='r')

    def setSubeventStateVisibility(self, checkstate:bool):
        # print(f'checkstate: {checkstate}')
        if checkstate:
            for p in self.p2s:
                p['cusum_states'].show()
                p['events'].setSize(self.perfiledata.event_sizes)
        else:
            for p in self.p2s:
                p['cusum_states'].hide()
                p['events'].setSize(np.full_like(self.perfiledata.event_sizes, 3))
    
    
    def updateDSratio(self):
        self.DSratio = int(self.ui.dsValueEntry.text())
        for handle in self.perfiledata.p1RawTraceHandles:
            handle.setDownsampling(ds=self.DSratio, auto = False)
        for handle in self.perfiledata.p1FiltTraceHandles:
            handle.setDownsampling(ds=self.DSratio, auto = False)
        self.updateDSratioBox()
    
    def getSaveTimeStamp(self):
        ret = ""
        try: 
            ret = builtintime.strftime(r'%y%m%d%H%M%S',builtintime.localtime())
        except BaseException as e:
            self.printlog('Generation of timestamp encountered an error')
            self.printlog(e)
        return ret

    @abstractmethod
    def paintCurrentTrace(self):
        pass

    @abstractmethod
    def clearSelections(self):
        pass



class AutoSelectIVDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        self.parent = parent
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ui = Ui_AutoIVSelectDialog()
        self.ui.setupUi(self)
        self.accepted.connect(self.dialogAccept)
        self.rejected.connect(self.dialogReject)
        print('AutoSelectIVDialog init')

    def dialogAccept(self):
        offset_ms = float(self.ui.offsetLineEdit.text())
        start_ms = float(self.ui.startLineEdit.text())
        end_ms = float(self.ui.endLineEdit.text())
        params = {'offset_ms':offset_ms,
                  'start_ms':start_ms,
                  'end_ms':end_ms}
        self.close()
        self.parent.commitAutoIVSelection(params)
        
    def dialogReject(self):
        self.close()
