from .__version__ import __version__
from .BaseApp import *
from . import Selections

def doCut(app:BaseAppMainWindow):
    with app.awaitresponse:
        if len(app.perfiledata.LRs)>0:
            app.printlog('Executing batch cutting...')
            app.perfiledata.isFullTrace = False
            cutString = ''
            # cutMask = np.zeros_like(app.perfiledata.data.filt, bool)
            # dummy_cutregion = None
            for cutLR in app.perfiledata.LRs:
                cutRegion = np.round(cutLR.getRegion()).astype(int)
                cutIndexL, cutIndexR = cutRegion
                # dummy_cutregion = cutRegion
                # cutIndexL = max(0, int(cutRegion[0]))
                # cutIndexR = min(len(app.perfiledata.data.filt), int(cutRegion[1]))    
                cutString += f' {cutRegion!s}'
                # cutMask[cutIndexL:cutIndexR] = True
                
                app.perfiledata.data.trim(cutRegion)
                # app.perfiledata.data.trim(np.nonzero(cutMask)[0])
            app.printlog(f'Regions: {cutString:s}')
            app.perfiledata.LRs.clear()

            if app.perfiledata.hasbaselinebeenset==0:
                app.ui_baseline = np.median(app.perfiledata.data.filt[0])
                app.ui_baseline_std=np.std(app.perfiledata.data.filt[0])
            
            app.paintCurrentTrace()
            app.p3.clear()
            aphy, aphx = np.histogram(app.perfiledata.data.filt[0], bins = 1000)
            aphhist = pg.BarGraphItem(height = aphy, x0 = aphx[:-1], x1 = aphx[1:],brush = 'b', pen = None)
            app.p3.addItem(aphhist)
            app.p3.setXRange(np.min(app.perfiledata.data.filt[0]), np.max(app.perfiledata.data.filt[0]))

            app.printlog('Cut done.')


def doBaseline(app:BaseAppMainWindow):
    with app.awaitresponse:
        if len(app.perfiledata.LRs)>0:
            baseline_lr = app.perfiledata.LRs[0]
            calcregion= np.round(baseline_lr.getRegion()).astype(int)
            filt_data = app.perfiledata.data.getConcatDataPoints(calcregion)
            app.ui_baseline=np.median(filt_data)
            app.ui_baseline_std=np.std(filt_data)
            # app.baseline=np.median(app.perfiledata.data.filt[np.arange(int(calcregion[0]),int(calcregion[1]))])
            # app.var=np.std(app.perfiledata.data.filt[np.arange(int(calcregion[0]),int(calcregion[1]))])
            app.clearSelections()
            app.paintCurrentTrace()
            app.perfiledata.hasbaselinebeenset=1
            app.printlog(f'Baseline measured on {calcregion!s}. Baseline is {app.ui_baseline*1e9:.4f} nA. Stdev is {app.ui_baseline_std*1e9:.5f} nA')

def invertData(app:BaseAppMainWindow):
    
    app.perfiledata.data.invert()
    if app.perfiledata.hasbaselinebeenset==0:
        app.ui_baseline=np.median(app.perfiledata.data.filt[0])
        app.ui_baseline_std=np.std(app.perfiledata.data.filt[0])
    app.paintCurrentTrace()
    app.printlog('Data inverted')