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
        self.St = None
        # array used for "delete traces"
        self.Mask = None
        # array used for converting between km/s and deg/s
        self.XOffset = None
        # array used for plotting reduced time profile
        self.YOffset = None
        # array used for scale the amplitude of traces
        self.Scale = None
        # indicator the units of distance
        self.IsKm = None
        
        # list of auxiliary lines for storing theoretical travel times
        self.AuxiliaryLines = None
               
        # list for save arrival times picked
        self.picks = None 
        # handler for pick markers plot
        self.pickmarkers = None
        
        self.initUI()
    
    def initUI(self):
        self.setUpMenuBar()
        
        self.GroupBoxRTKm, self.LineEditRTKm = self.groupBoxReducedTimeKm()
        self.GroupBoxRTDeg, self.LineEditRTDeg = self.groupBoxReducedTimeDeg()
                                                               
        # button for manipulate picks
        self.SaveButton = QtGui.QPushButton('Save Picks', self)
        self.ClearButton = QtGui.QPushButton("Clear Picks", self)
#        self.ClearButton.setGeometry(10, 10, 64, 35)
        self.connect(self.SaveButton, QtCore.SIGNAL('clicked()'),
                     self.savePicks)
        self.connect(self.ClearButton, QtCore.SIGNAL('clicked()'),
                     self.clearPicks)
        PicksButtons = QtGui.QVBoxLayout()
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

        # 'Help' menu
        self.help_menu = QtGui.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)

        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.help_menu)
    
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
            points = (event.xdata, event.ydata)
            if self.picks is None:
                self.picks = [points]
                self.updatePicks()
            else:
                self.picks.append(points)
                self.updatePicks()
    
    def updatePicks(self):
        if self.picks is None:
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
            picks = np.array(self.picks)
            if self.pickmarkers is None:
                self.pickmarkers, = self.canvas.axes.plot(picks[:,0], picks[:,1], 'r+',
                                                 markersize=8, mew=1)  
            else:
                self.pickmarkers.set_xdata(picks[:,0])
                self.pickmarkers.set_ydata(picks[:,1])
            self.canvas.draw() 
    
    def savePicks(self):
        if self.picks is None:
            pass
        else:
            filename = QtGui.QFileDialog.getSaveFileName(self, 'Save as ...',
                                                         '..')
            np.savetxt(filename, self.picks, fmt='%.6e')
            
    
    def clearPicks(self):
        self.picks = None
        self.updatePicks()
        
    def setReducedVelocity(self, rv, IsKms=True):
        if IsKms:
            self.reducedVelocity = rv
        else:
            self.reducedVelocity = rv * np.pi/180.0 * 6371.0
        self.updateProfile()
        
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
        # clear the axes and plot, with x_offset, y_offset and scale
        self.canvas.axes.cla()
        for tr in self.st:
            scale = 1.0/np.max(tr.data)
            x_offset = tr.stats.sac['dist']
            y_offset = -x_offset/self.reducedVelocity
            self.canvas.axes.plot(tr.data * scale + x_offset, 
                                  tr.times() + y_offset , 'k')
        self.canvas.axes.set_xlim(-1,151)
        self.canvas.axes.set_ylim(0,90)
        self.canvas.axes.set_xlabel('Distance (km)')
        self.canvas.axes.set_ylabel('Time (s)')
        self.canvas.draw()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def loadFromFolder(self):
        # clear the axes for new plot
        self.canvas.axes.cla()
        
        # read all sac files in a folder
        folder_name = QtGui.QFileDialog.getExistingDirectory(self, 'Select a Folder',
                                                             '../demo_data')
        if folder_name is None:
            return
        self.st = read(os.path.join(folder_name, '*.BHZ*.sac'))
        
        # plot it with offset, scale
        for tr in self.st:
            scale = 1.0/np.max(tr.data)
            offset = tr.stats.sac['dist']
            self.canvas.axes.plot(tr.data * scale + offset, tr.times() , 'k')
        self.canvas.axes.set_xlim(-1,151)
        self.canvas.axes.set_ylim(0,90)
        self.canvas.axes.set_xlabel('Distance (km)')
        self.canvas.axes.set_ylabel('Time (s)')
        self.canvas.draw()


    def about(self):
        QtGui.QMessageBox.about(self, "About",
                """DDSpicker (v.0000001)

Laboratory of Seismic Observation and Geophysical Imaging 

The very first version of arrival time picker for active sources profile."""
                )


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
