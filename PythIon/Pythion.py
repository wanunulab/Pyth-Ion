#!/usr/bin/python
# -*- coding: utf8 -*-
import os
import sys

from .__version__ import __version__
from .BaseApp import *
from . import Painting
from . import Analysis
from . import IO
from . import Selections
from . import Edits



class ExtAppMainWindow(BaseAppMainWindow):
    
    def __init__(self, width, height, master=None):
        super().__init__(width, height, master)
        ##########Linking buttons to main functions############
        self.ui.actionLoad.triggered.connect(self.doFileLoad)
        self.ui.actionReload.triggered.connect(lambda: IO.loadFile(self))
        # self.ui.actionNext_File.triggered.connect(self.fileNext)
        # self.ui.actionPrevious_File.triggered.connect(self.filePrev)
        self.ui.actionSave_Traces.triggered.connect(lambda:IO.saveTrace(self))
        self.ui.actionSave_Segment_Info.triggered.connect(lambda:IO.saveSegInfo(self))

        self.ui.actionCut.triggered.connect(lambda:Edits.doCut(self))
        self.ui.actionSet_Baseline.triggered.connect(lambda:Edits.doBaseline(self))
        self.ui.actionInvert_Current_Sign.triggered.connect(lambda:Edits.invertData(self))
        
        self.ui.actionAuto_Detect_Clears_Alt_A.triggered.connect(lambda:Selections.autoFindCutLRs(self))
        self.ui.actionAdd_One_Cut_Region_Alt_D.triggered.connect(lambda:Selections.addOneManualCutLR(self))
        self.ui.actionDelete_Last_Cut_Region_Alt_D.triggered.connect(lambda:Selections.deleteOneCutLR(self))
        self.ui.actionClear_Selections.triggered.connect(lambda:Selections.clearLRs(self))
        self.ui.actionAuto_Select_IV_Region.triggered.connect(lambda:Selections.autoIVSelection(self))
        self.ui.actionSelection_Export_Data.triggered.connect(lambda:IO.exportSelection(self))
        self.ui.actionExport_measurement.triggered.connect(lambda:Selections.measureSelections(self))
        self.ui.actionInspect_Selection.triggered.connect(lambda:Painting.inspectSelection(self))

        self.ui.actionAnalyze.triggered.connect(self.doAnalysis)
        self.ui.actionSubevent_State_Settings.triggered.connect(self.setSubEventStateSettingsDialog)
        self.ui.actionRepaint_Analysis.triggered.connect(lambda: Painting.plotAnalysis(self))

        self.ui.gobutton.clicked.connect(lambda: Painting.inspectEvent(self))
        self.ui.previousbutton.clicked.connect(self.prevEvent)
        self.ui.nextbutton.clicked.connect(self.nextEvent)      
        
        self.ui.checkBox_showRaw.clicked.connect(self.updateRawFiltVisibility)
        self.ui.checkBox_showFilt.clicked.connect(self.updateRawFiltVisibility)
        
        
        self.ui.statusbar.showMessage(str(__version__))
        self.ui.dsUpdateButton.clicked.connect(self.updateDSratio)
        

        self.ui.checkBoxShowSubeventStates.clicked.connect(self.setSubeventStateVisibility)
        for p in self.p2s:
            for entry in self.scatter_entries:
                p[entry].sigClicked.connect(lambda a, b: Painting.scatterClicked(self, a, b))
    
        self.analysis_config = Analysis.Config()
        self.load_config = IO.LoadConfig()
    
    def paintCurrentTrace(self):
        Painting.paintCurrentTrace(self)
    
    def clearSelections(self):
        Selections.clearLRs(self)

    def setSubEventStateSettingsDialog(self):
        dialog = Analysis.SubEventStateSettingsDialog(parent=self)
        dialog.exec()

    def doFileLoad(self):
        dialog = IO.LoadFileDialog(parent=self)
        dialog.exec()
    
    def uiShowAnalysisInfo(self):
        pass
        # app.ui.eventcounterlabel.setText('Events:'+str(app.perfiledata.numberofevents))
        # app.ui.meandelilabel.setText('Deli:'+str(round(np.mean(app.perfiledata.deli_list*10**9),2))+' nA')
        # app.ui.meandwelllabel.setText('Dwell:'+str(round(np.median(app.perfiledata.dwell_list),2))+ u' μs')
        # app.ui.meandtlabel.setText(
        #     f'Rate:{app.perfiledata.numberofevents/app.perfiledata.data.total_data_points*app.perfiledata.ADC_samplerate_Hz:.4f} events/s'
        #     )

    def doAnalysis(self):
        def analysisSequence(app:ExtAppMainWindow):
            Analysis.computeAnalysis(app)
            Painting.plotAnalysis(app)
            if app.enable_save_analysis:
                IO.saveAnalysis(app)
            app.uiShowAnalysisInfo()
        dialog = Analysis.AnalyzeDialog(parent=self)
        dialog.accepted.connect(lambda : analysisSequence(self))
        dialog.exec()

    def nextEvent(self):
        eventnumber=int(self.ui.eventnumberentry.text())
        self.ui.eventnumberentry.setText(str(eventnumber+1))
        Painting.inspectEvent(self)

    def prevEvent(self):
        eventnumber=int(self.ui.eventnumberentry.text())
        self.ui.eventnumberentry.setText(str(eventnumber-1))
        Painting.inspectEvent(self)

    def keyPressEvent(self, event):
        pass

def start():
    print('Starting with __name__:', __name__)
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    resolution = app.desktop().screenGeometry()
    width,height = resolution.width(), resolution.height()
    myapp = ExtAppMainWindow(width=width, height=height)
    myapp.show()
    sys.exit(app.exec_())


print('Imported with __name__:', __name__)
if __name__ == "__main__":
    print('Starting in Pythion.py')
    start()

