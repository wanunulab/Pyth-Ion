# -*- coding: utf8 -*-

from .__version__ import __version__
import numpy as np
import pyqtgraph as pg
from typing import TYPE_CHECKING

class TraceData():
    
    def __init__(self) -> None:
        self._raw : list[np.ndarray]= []
        self._filt : list[np.ndarray] = []
        self.srange : list[tuple] = []
        self.original_length = None
        self.isRawActive = True
        self.source_file_name = ''
        self.pythion_version = __version__

    @property
    def filt(self):
        return self._filt
    
    @filt.setter
    def filt(self, data):
        self._filt = data

    @property
    def raw(self):
        return self._raw
    
    @raw.setter
    def raw(self,data):
        self._filt = data
        self._raw = data

    @property
    def active(self):
        if self.isRawActive:
            return self.raw
        else:
            return self.filt
    
    @property
    def Nseg(self):
        self.checkLength()
        return len(self.srange)
    
    @property
    def total_data_points(self):
        return np.sum([len(seg_raw) for seg_raw in self._raw])
    
    def getSegCoord(self, k):
        self.checkLength()
        return np.arange(self.srange[k][0], self.srange[k][1])


    def setOriginalData(self, raw, filt, source:str):
        self._raw = [raw]
        self._filt = [filt]
        self.original_length = len(raw)
        self.srange = [(0,len(raw))]
        self.source_file_name = source

        
    def checkLength(self):
        assert(len(self._filt) == len(self._raw))
        assert(len(self._raw) == len(self.srange))
        for k,seg in enumerate(self.srange):
            seg_length = seg[1] - seg[0]
            assert(len(self._raw[k])==seg_length and len(self._filt[k])==seg_length)


    def trim(self, trange:tuple):
        trim_start, trim_end = (int(x) for x in trange)
        new_raw = []
        new_filt = []
        new_range = []
        for k, seg in enumerate(self.srange):
            seg_start, seg_end = seg
            isSegOverlapping = not (seg_start >= trim_end or seg_end <= trim_start)
            if isSegOverlapping:
                front = np.array([seg_start, trim_start])
                mid = np.array([trim_start, trim_end])
                rear = np.array([trim_end, seg_end])
                isProper = lambda x: x[1] > x[0]
                local_front = front - seg_start
                if isProper(local_front):
                    local_front_slice = np.s_[local_front[0]:local_front[1]]
                    front_raw = self._raw[k][local_front_slice].copy()
                    front_filt = self._filt[k][local_front_slice].copy()
                    new_range.append(tuple(front))
                    new_raw.append(front_raw)
                    new_filt.append(front_filt)
                local_rear = rear - seg_start
                if isProper(local_rear):
                    local_rear_slice = np.s_[local_rear[0]:local_rear[1]]
                    rear_raw = self._raw[k][local_rear_slice].copy()
                    rear_filt = self._filt[k][local_rear_slice].copy()
                    new_range.append(tuple(rear))
                    new_raw.append(rear_raw)
                    new_filt.append(rear_filt)
            else:
                new_range.append(seg)
                new_raw.append(self._raw[k])
                new_filt.append(self._filt[k])
        self.srange = new_range
        self._raw = new_raw
        self._filt = new_filt                
        self.checkLength()

    
    def invert(self):
        for k in range(len(self.srange)):
            self._raw[k] = -self._raw[k]
            self._filt[k] = -self._filt[k]

    def getConcatDataPoints(self, grange:tuple, rawdata = False, gap_filler=None):
        if rawdata:
            data = self._raw
        else:
            data = self._filt
        get_start, get_end = (int(x) for x in grange)
        if gap_filler is not None:
            data_points = np.full(get_end-get_start, gap_filler)
        else:
            data_points = np.array([])
        for k, seg in enumerate(self.srange):
            seg_start, seg_end = seg
            isSegOverlapping = not (seg_start >= get_end or seg_end <= get_start)
            if isSegOverlapping:
                mid = np.clip(np.array([get_start, get_end]), seg_start, seg_end)
                local_mid = mid-seg_start
                local_mid_slice = np.s_[local_mid[0]:local_mid[1]]
                local_mid_data = data[k][local_mid_slice]
                if gap_filler is not None:
                    m = mid - get_start
                    data_points[m[0]:m[1]] = local_mid_data
                else:
                    data_points = np.append(data_points, local_mid_data)
        return data_points

if TYPE_CHECKING:
    from .Analysis import AnalysisResults

class FileData():
    def __init__(self) -> None:
        self.datafilename = None
        self.direc = None
        # self.lr=[]
        self.lastClicked=[]
        self.hasbaselinebeenset=0

        self.event_sizes = None
        self.event_colors = None
        self.analysis_results:AnalysisResults = None
        self.data = TraceData()
        self.p1RawTraceHandles = []
        self.p1FiltTraceHandles = []
        self.xmltree = None
        self.xmlroot = None
        self.t_V_record = None
        self.usernote_record = None
        self.isFullTrace = False
        self.threshHandle = None
        self.matfilename = None
 
        self.ADC_samplerate_Hz = None
        self.LPFilter_cutoff_Hz = None
 
        self.baseline = None
        self.baseline_std = None
        self.LRs : list[pg.LinearRegionItem] = []
        self.logtext = ''
    
    def getT(self, ndx_list):
        arr = np.array(ndx_list)
        return arr/self.ADC_samplerate_Hz

# print(TraceData.__module__)
# print(TraceData.__qualname__)