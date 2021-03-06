#!/usr/bin/env python
#-*-coding:utf-8-*-

import sys
import os
from PyQt4 import QtGui
from PyQt4 import QtCore
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
#import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
from obspy import read

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.resize(800,600)
        self.setWindowTitle('DDS picker')

        # Obspy.Stream for storing profile
        self.st = None
        # array used for "delete traces"
        self.mask = None
        # array used for converting between km/s and deg/s
        self.x_offset = None
        # array used for plotting reduced time profile
        self.y_offset = None
        # array used for scale the amplitude of traces
        self.scale = None
        # scaling factor multiple self.scale
        self.scale_factor = None
        # indicator the units of distance
        self.iskm = None

        # list of auxiliary lines for storing theoretical travel times
        self.AuxiliaryLines = None

        # map limits
        self.limit = None

        # list for save arrival times picked
        self.picks = None 
        # mask array for picks
        self.pick_mask = None
        # handler for pick markers plot
        self.pickmarkers = None

        self.initUI()

    def initUI(self):
        self.setUpMenuBar()
        self.setUpToolBar()

        self.GroupBoxRTKm, self.LineEditRTKm = self.groupBoxReducedTimeKm()
        self.GroupBoxRTDeg, self.LineEditRTDeg = self.groupBoxReducedTimeDeg()

        # button for manipulate picks
        self.LoadButton = QtGui.QPushButton('Load Picks', self)
        self.SaveButton = QtGui.QPushButton('Save Picks', self)
        self.ClearButton = QtGui.QPushButton("Clear Picks", self)
#        self.ClearButton.setGeometry(10, 10, 64, 35)
        self.connect(self.LoadButton, QtCore.SIGNAL('clicked()'),
                     self.loadPicks)
        self.connect(self.SaveButton, QtCore.SIGNAL('clicked()'),
                     self.savePicks)
        self.connect(self.ClearButton, QtCore.SIGNAL('clicked()'),
                     self.clearPicks)
        PicksButtons = QtGui.QVBoxLayout()
        PicksButtons.addWidget(self.LoadButton)
        PicksButtons.addWidget(self.SaveButton)
        PicksButtons.addWidget(self.ClearButton)

        # add matplotlib figure
        self.main_widget = QtGui.QWidget(self)

        self.canvas = ProfileCanvas(self.main_widget)
        self.canvas.mpl_connect('button_press_event', self.clickOnProfile)

        # add navigation toolbar for zoom in/out and drag
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_widget)

        # set layouts
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.GroupBoxRTKm, stretch=10, alignment=QtCore.Qt.AlignCenter)
        hbox.addWidget(self.GroupBoxRTDeg, stretch=10, alignment=QtCore.Qt.AlignCenter)
        hbox.addLayout(PicksButtons)

        vbox = QtGui.QVBoxLayout(self.main_widget)
        vbox.addLayout(hbox)
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

    def setUpMenuBar(self):
        """menubar
        """
        # 'File' menu
        self.file_menu = QtGui.QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.fileQuit,
                QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.file_menu.addAction('&Load from Folder', self.loadFromFolder,
                QtCore.Qt.CTRL + QtCore.Qt.Key_L)
        self.file_menu.addAction('&Import from File List', self.loadFromFileList,
                QtCore.Qt.CTRL + QtCore.Qt.Key_I,
                )

        # 'View' menu
        self.view_menu = QtGui.QMenu('&View', self)
        self.view_menu.addAction('Set Profile &Boundary',
                                 self.setProfileBoundary,
                                 QtCore.Qt.CTRL+QtCore.Qt.Key_B)
        self.view_menu.addAction('Reduce Time (km/s)',
                                 self.reduceTimeKms,
                                 )
        self.view_menu.addAction('Reduce Time (deg/s)',
                                 self.reduceTimeDegs,
                                 )
        self.view_menu.addAction('Scale',
                                 self.changeScale,
                                )

        # 'Help' menu
        self.help_menu = QtGui.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)

        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.view_menu)
        self.menuBar().addMenu(self.help_menu)

    def setUpToolBar(self):
        pass

    def groupBoxReducedTimeKm(self):
        """Radio buttons for reduced time
        """
        ReducedVelocity6 = QtGui.QRadioButton("t-x/6")
        ReducedVelocity8 = QtGui.QRadioButton("t-x/8")
        ReducedVelocityNone = QtGui.QRadioButton("t")
        ReducedVelocityArb = QtGui.QRadioButton("t-x/?(km/s)")
        ReducedVelocityArbValue = QtGui.QLineEdit("6.0")
        ReducedVelocityNone.setChecked(True)
        
        # enclose all the radio button to make them exclusively
        # i.e., only one radio button can be checked at one time
        self.ReducedTimeButtonGroupKm = QtGui.QButtonGroup()
        self.ReducedTimeButtonGroupKm.addButton(ReducedVelocity6)
        self.ReducedTimeButtonGroupKm.addButton(ReducedVelocity8)
        self.ReducedTimeButtonGroupKm.addButton(ReducedVelocityNone)
        self.ReducedTimeButtonGroupKm.addButton(ReducedVelocityArb)
        self.connect(self.ReducedTimeButtonGroupKm, QtCore.SIGNAL('buttonClicked(QAbstractButton*)'),
                     self.rtKmPlot)
        self.connect(ReducedVelocityArbValue, QtCore.SIGNAL('returnPressed()'),
                     self.rtKmPlot)
        
        vboxRT = QtGui.QVBoxLayout()
        vboxRT.addWidget(ReducedVelocity6)
        vboxRT.addWidget(ReducedVelocity8)
        vboxRT.addWidget(ReducedVelocityNone) 
        
        hboxArb = QtGui.QHBoxLayout()
        hboxArb.addWidget(ReducedVelocityArb)
        hboxArb.addWidget(ReducedVelocityArbValue)
        hboxArb.addStretch(1)
        
        vboxRT.addLayout(hboxArb)
        vboxRT.addStretch(1)
        GroupBoxRT = QtGui.QGroupBox("Reduced time (km/s)")
        GroupBoxRT.setLayout(vboxRT)
        
        return GroupBoxRT, ReducedVelocityArbValue

    def groupBoxReducedTimeDeg(self):
        # DONE(xuyihe): ref to groupBoxReducedTimeKm
    
        # Radio buttons for reduced time
#        ReducedVelocity = QtGui.QRadioButton("t-x/v(deg/s)")
#        ReducedVelocityValue = QtGui.QTextEdit()
#        ReducedVelocity = QtGui.QRadioButton("t-x/v(deg/s)")
        ReducedVelocityNone = QtGui.QRadioButton("t")
        ReducedVelocityNone.setChecked(True)
        ReducedVelocityArb = QtGui.QRadioButton("t-x/?(deg/s)")
        ReducedVelocityArbValue = QtGui.QLineEdit()
        
        # enclose all the radio button to make them exclusively
        # i.e., only one radio button can be checked at one time
        self.ReducedTimeButtonGroupDeg = QtGui.QButtonGroup()
        self.ReducedTimeButtonGroupDeg.addButton(ReducedVelocityNone)
        self.ReducedTimeButtonGroupDeg.addButton(ReducedVelocityArb)
        self.connect(self.ReducedTimeButtonGroupDeg, QtCore.SIGNAL('buttonClicked(QAbstractButton*)'),
                     self.rtDegPlot)
        self.connect(ReducedVelocityArbValue, QtCore.SIGNAL('returnPressed()'),
                     self.rtDegPlot)
        
        vboxRT = QtGui.QVBoxLayout()
        vboxRT.addWidget(ReducedVelocityNone) 
        
        hboxArb = QtGui.QHBoxLayout()
        hboxArb.addWidget(ReducedVelocityArb)
        hboxArb.addWidget(ReducedVelocityArbValue)
        hboxArb.addStretch(1)
        
        vboxRT.addLayout(hboxArb)
        vboxRT.addStretch(1)
        GroupBoxRT = QtGui.QGroupBox("Reduced time (deg/s)")
        GroupBoxRT.setLayout(vboxRT)
        
        return GroupBoxRT, ReducedVelocityArbValue

    def clickOnProfile(self, event):
        if event.inaxes is not None:
            points = np.array([event.xdata, event.ydata])
            sort_index = np.argsort(self.x_offset)
            index = self._find_nearest_trace(points[0])
            points[0] = self.x_offset[index]
            points[1] = points[1] - self.y_offset[index]

            if event.button == 1:
                if self.picks is None:
                    self.picks[index,:] = points
                    self.pick_mask[index] = False
                    self.updatePicks()
                else:
                    #print self.picks
                    self.picks[index,:] = points
                    self.pick_mask[index] = False
                    self.updatePicks()
            elif event.button == 3:
                if self.picks is not None:
                    self.pick_mask[index] = True
                    self.updatePicks()

    def _find_nearest_trace(self, x):
        dx = np.abs(self.x_offset - x)
        index = np.argmin(dx)
        return index

    def updatePicks(self, refresh=False):
        if np.all(self.pick_mask) is True:
            # no picks, erase pick markers
            try:
                self.pickmarkers.set_xdata([])
                self.pickmarkers.set_ydata([])
                self.canvas.draw()
            except:
                pass
            self.pickmarkers = None
        else:
            # otherwise, replot picks
            #print self.pickmarkers
            picks = np.array(self.picks)
            #sort_index = np.argsort(self.x_offset)
            #picks_y_offset = picks[:,1] + np.interp(picks[:,0],
            #            self.x_offset[sort_index],
            #            self.y_offset[sort_index])
            picks_y_offset = picks[:,1] + self.y_offset
            if self.pickmarkers is None or refresh is True:
            # refresh is used by 'self.setReducedVelocity' after 
            # self.updateProfile() to redraw picks on the redrawed
            # profile
                self.pickmarkers, = self.canvas.axes.plot(
                    picks[~self.pick_mask,0],
                    picks_y_offset[~self.pick_mask],
                    'r_',
                    markersize=10, mew=4)
                #print picks[:,0]
                #print picks[:,1] + np.interp(picks[:,0], self.x_offset, self.y_offset)
                #print picks[:,1]
                #print np.interp(picks[:,0], self.x_offset, self.y_offset)
                #print self.y_offset
                #print self.x_offset
            else:
                self.pickmarkers.set_xdata(picks[~self.pick_mask,0])
                self.pickmarkers.set_ydata(picks_y_offset[~self.pick_mask])
            self.canvas.draw()

    def loadPicks(self):
        pickFileName = QtGui.QFileDialog.getOpenFileName(
            self, 'select a Pick file', '.')

        if len(pickFileName) == 0:
            return

        pickFileName = str(pickFileName)
        self.picks = np.loadtxt(pickFileName) 
        picks_index = map(lambda x:self._find_nearest_trace(x), 
                          self.picks[:,0])
        self.pick_mask[picks_index] = False
        self.updatePicks()

    def savePicks(self):
        if self.picks is None:
            pass
        else:
            filename = QtGui.QFileDialog.getSaveFileName(self, 'Save as ...',
                                                         '.')
            filename = str(filename)
            np.savetxt(str(filename), self.picks, fmt='%.6e')

    def clearPicks(self):
        self.pick_mask = np.ones(self.pick_mask.shape, dtype=bool)
        self.updatePicks()

    def setReducedVelocity(self, rv, IsKms=True):
        if IsKms:
            self.reducedVelocity = rv
        else:
            self.reducedVelocity = rv * np.pi/180.0 * 6371.0
        self.y_offset = -self.x_offset/self.reducedVelocity

        self.updateProfile()
        self.updatePicks(refresh=True)

    def rtKmPlot(self):
        """Plot profile with reduced velocity with units of km/s
        """
        #DONE(xuyihe): take similar parts of rtPlot and loadFromFolder to a
        # individual method, to update profile
        # set reduced velocity from radio button checked
        id = self.ReducedTimeButtonGroupKm.checkedId()
        ArbValueString = self.LineEditRTKm.text()
        try:
            ArbValue = float(ArbValueString)
        except ValueError:
            ArbValue = np.inf
        
        id2rv = {-2:6.0, -3:8.0, -4:np.inf, -5:ArbValue}
        self.setReducedVelocity(id2rv[id], IsKms=True)

#    def rtKmPlot2(self):
#        """Plot profile with arbitary reduced velocity
#        """
##        print 'rtPlot2'
#        rv = self.LineEditRTKm.text()
##        print rv
#        id = self.ReducedTimeButtonGroupKm.checkedId()
#        if id == -5:
#            self.reducedVelocity = float(rv)
#        self.updateProfile()
        
    def rtDegPlot(self):
        """Plot profile with pre-defined reduced velocity with units of deg/s
        """
        id = self.ReducedTimeButtonGroupDeg.checkedId()
        ArbValueString = self.LineEditRTDeg.text()
        try:
            ArbValue = float(ArbValueString)
        except ValueError:
            ArbValue = np.inf
        
        id2rv = {-2:np.inf, -3:ArbValue}
        self.setReducedVelocity(id2rv[id], IsKms=False)
    
#    def rtDegPlot2(self):
#        """Plot profile with arbitary reduced velocity with units of deg/s
#        """
#        pass


    def updateProfile(self):
        """clear the axes and plot, with x_offset, y_offset and scale
        """

        if self.st is None:
            return

        scale = self.scale
        x_offset = self.x_offset
        y_offset = self.y_offset

        # clear the axes
        self.canvas.axes.cla()
        for tr, scale, x_offset, y_offset in zip(
                self.st, self.scale, self.x_offset, self.y_offset):
            #scale = 1.0/np.max(tr.data)
            #x_offset = tr.stats.sac['dist']
            #y_offset = -x_offset/self.reducedVelocity
            self.canvas.axes.plot(
                tr.data*scale*self.scale_factor + x_offset,
                tr.times() + y_offset , 'k')
        self.canvas.axes.set_xlim(self.xlim)
        self.canvas.axes.set_ylim(self.ylim)
        self.canvas.axes.set_xlabel('Distance (km)')
        self.canvas.axes.set_ylabel('Time (s)')
        self.canvas.draw()

    def changeScale(self):
        scale, ok = QtGui.QInputDialog.getDouble(
            self, 'Set Scale', 'set scale', 1.0, decimals=0.1)
        if ok:
            self.scale_factor = scale
            self.updateProfile()
            self.updatePicks(refresh=True)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def loadFromFolder(self):
        # read all sac files in a folder
        folder_name = QtGui.QFileDialog.getExistingDirectory(self, 'Select a Folder',
                                                             '.')
        if len(folder_name) == 0:
            return

        self.st = read(os.path.join(str(folder_name), '*.sac'))

        # clear the axes for new plot
        #self.canvas.axes.cla()

        # set offset, scale
        scale = []
        x_offset = []
        y_offset = []
        for tr in self.st:
            scale.append(1.0/np.max(tr.data))
            x_offset.append(tr.stats.sac['dist'])
            #self.canvas.axes.plot(tr.data * scale + offset, tr.times() , 'k')

        self.scale = np.array(scale)
        self.scale_factor = 1.0
        self.x_offset = np.array(x_offset)
        self.y_offset = np.zeros(self.x_offset.shape)

        self.picks = np.zeros((len(self.x_offset), 2))
        self.pick_mask = np.ones(self.x_offset.shape, dtype=bool)

        self.xlim = [self.x_offset.min()-5, self.x_offset.max()+5]
        self.ylim = [0, 90]
        #self.canvas.axes.set_xlim(-1,151)
        #self.canvas.axes.set_ylim(0,90)
        #self.canvas.axes.set_xlabel('Distance (km)')
        #self.canvas.axes.set_ylabel('Time (s)')
        #self.canvas.draw()

        # update the profile
        self.updateProfile()

    def loadFromFileList(self):
        
        #print os.getcwd()

        filelistname = QtGui.QFileDialog.getOpenFileName(self, 'select a list file',
                                                         '.',
                                                         "list files(*.lst)")
        #print filelistname
        #print str(filelistname)
        #print len(str(filelistname))
        #print len(filelistname)
        if len(filelistname) == 0:
            return
        
        with open(filelistname, 'ru') as fl:
            fs = map(lambda x: x.strip(), fl.readlines())
            for i, f in enumerate(fs):
                if i == 0:
                    st = read(f)
                else:
                    st += read(f)
        
        self.st = st

        # clear the canvas
        #self.canvas.axes.cla()

        # set offset, scale
        scale = []
        x_offset = []
        y_offset = []
        for tr in self.st:
            scale.append(1.0/np.max(tr.data))
            x_offset.append(tr.stats.sac['dist'])
            #self.canvas.axes.plot(tr.data * scale + offset, tr.times() , 'k')

        self.scale = np.array(scale)
        self.scale_factor = 1.0
        self.x_offset = np.array(x_offset)
        self.y_offset = np.zeros(self.x_offset.shape)

        self.picks = np.zeros((len(self.x_offset), 2))
        self.pick_mask = np.ones(self.x_offset.shape, dtype=bool)

        self.xlim = [self.x_offset.min()-5, self.x_offset.max()+5]
        self.ylim = [0, 90]
        #for tr in self.st:
        #    scale = 1.0/np.max(tr.data)
        #    offset = tr.stats.sac['dist']
        #    self.canvas.axes.plot(tr.data * scale + offset, tr.times() , 'k')
        #self.canvas.axes.set_xlim(-1,151)
        #self.canvas.axes.set_ylim(0,90)
        #self.canvas.axes.set_xlabel('Distance (km)')
        #self.canvas.axes.set_ylabel('Time (s)')
        #self.canvas.draw()

        self.updateProfile()

    def setProfileBoundary(self):
        dialog = MapMarginDialog(self)
        dialog.exec_()

        limit = dialog.getLimit()
        self.xlim = limit[:2]
        self.ylim = limit[2:]
        self.updateLimit()
    
    def updateLimit(self):
        self.canvas.axes.set_xlim(self.xlim)
        self.canvas.axes.set_ylim(self.ylim)
        self.canvas.draw()

    def reduceTimeKms(self):
        pass

    def reduceTimeDegs(self):
        pass

    def about(self):
        QtGui.QMessageBox.about(self, "About",
                """DDSpicker (v.0000001)

Laboratory of Seismic Observation and Geophysical Imaging 

The very first version of arrival time picker for active sources profile."""
                )

# Custom-designed dialog for setting map margins
class MapMarginDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
                
        self.XMinLabel = QtGui.QLabel("xmin")
        self.XMaxLabel = QtGui.QLabel("xmax")
        self.YMinLabel = QtGui.QLabel("ymin")
        self.YMaxLabel = QtGui.QLabel("ymax")
     
        self.XMinText = QtGui.QDoubleSpinBox()
        self.XMaxText = QtGui.QDoubleSpinBox()
        self.YMinText = QtGui.QDoubleSpinBox()
        self.YMaxText = QtGui.QDoubleSpinBox()
        
        self.XMinText.setMaximum(1e6)
        self.XMinText.setMinimum(-1e6)
        self.XMaxText.setMaximum(1e6)
        self.XMaxText.setMinimum(-1e6)
        self.YMinText.setMaximum(1e6)
        self.YMinText.setMinimum(-1e6)
        self.YMaxText.setMaximum(1e6)
        self.YMaxText.setMinimum(-1e6)
        
        xlim = self.parent().canvas.axes.get_xlim()
        ylim = self.parent().canvas.axes.get_ylim()
        
        self.XMinText.setValue(xlim[0])
        self.XMaxText.setValue(xlim[1])
        self.YMinText.setValue(ylim[0])
        self.YMaxText.setValue(ylim[1])
        
        self.OKButton = QtGui.QPushButton("OK")
        self.CancelButton = QtGui.QPushButton("Cancel")
        
        self.connect(self.OKButton, QtCore.SIGNAL('clicked()'),
                     self.accept)       
        self.connect(self.CancelButton, QtCore.SIGNAL('clicked()'),
                     self.reject)
        
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(self.XMinLabel, 1, 0)
        grid.addWidget(self.XMaxLabel, 1, 1)
        grid.addWidget(self.XMinText, 2, 0)
        grid.addWidget(self.XMaxText, 2, 1)
        grid.addWidget(self.YMinLabel, 3, 0)
        grid.addWidget(self.YMaxLabel, 3, 1)
        grid.addWidget(self.YMinText, 4, 0)
        grid.addWidget(self.YMaxText, 4, 1)
        
        grid.addWidget(self.OKButton, 5, 0)
        grid.addWidget(self.CancelButton, 5, 1)
         
        self.setLayout(grid)
        
        self.setWindowTitle("Map Margins")  
    
    def getLimit(self):
        xmin = self.XMinText.value()
        xmax = self.XMaxText.value()
        ymin = self.YMinText.value()
        ymax = self.YMaxText.value()
        
        return (xmin, xmax, ymin, ymax)


# class for embedding matplotlib figure into PyQt4
class ProfileCanvas(FigureCanvas):
    def __init__(self, parent=None, width=400, height=100, dpi=100):
        # preparation for plotting
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.axis('off')
        
        # embed to the pyqt4 widget 'FigureCanvas'
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        
        # what is the effect of the following 2 lines?
        FigureCanvas.setSizePolicy(self,
                QtGui.QSizePolicy.Expanding,
                QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


app = QtGui.QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
