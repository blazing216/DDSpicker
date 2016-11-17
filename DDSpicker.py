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

        self.setUpMenuBar()
        
        # Radio buttons for reduced time
        ReducedVelocity6 = QtGui.QRadioButton("t-x/6")
        ReducedVelocity8 = QtGui.QRadioButton("t-x/8")
        ReducedVelocityNone = QtGui.QRadioButton("t")
        ReducedVelocityNone.setChecked(True)
        
        # enclose all the radio button to make them exclusively
        # i.e., only one radio button can be checked at one time
        self.ReducedTimeButtonGroup = QtGui.QButtonGroup()
        self.ReducedTimeButtonGroup.addButton(ReducedVelocity6)
        self.ReducedTimeButtonGroup.addButton(ReducedVelocity8)
        self.ReducedTimeButtonGroup.addButton(ReducedVelocityNone)
        self.connect(self.ReducedTimeButtonGroup, QtCore.SIGNAL('buttonClicked(QAbstractButton*)'),
                     self.rtPlot)
                                                       
        # button for clear picks
        self.ClearButton = QtGui.QPushButton("Clear", self)
        self.ClearButton.setGeometry(10, 10, 64, 35)
        self.connect(self.ClearButton, QtCore.SIGNAL('clicked()'),
                     self.clearPicks)
        
        # add matplotlib figure
        self.main_widget = QtGui.QWidget(self)
        
        self.canvas = ProfileCanvas(self.main_widget)
        self.canvas.mpl_connect('button_press_event', self.clickOnProfile)
        
        # add navigation toolbar for zoom in/out and drag
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_widget)

           
        # set layouts
        vboxRT = QtGui.QVBoxLayout()
        vboxRT.addWidget(ReducedVelocity6)
        vboxRT.addWidget(ReducedVelocity8)
        vboxRT.addWidget(ReducedVelocityNone) 
        vboxRT.addStretch(1)
        GroupBoxRT = QtGui.QGroupBox("Reduced time")
        GroupBoxRT.setLayout(vboxRT)          
           
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(GroupBoxRT, stretch=10, alignment=QtCore.Qt.AlignCenter)
        hbox.addWidget(self.ClearButton)
        
        vbox = QtGui.QVBoxLayout(self.main_widget)
        vbox.addLayout(hbox)
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        
        # list for save arrival times picked
        self.picks = None
        self.pickmarkers = None
        
    def setUpMenuBar(self):
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
    
    def clearPicks(self):
        self.picks = None
        self.updatePicks()
        
    def rtPlot(self):
        """Plot profile with reduced time
        """
        #TODO(xuyihe): take similar parts of rtPlot and loadFromFolder to a
        # individual method, to update profile
        # set reduced velocity from radio button checked
        id = self.ReducedTimeButtonGroup.checkedId()
        if id == -2:
            reducedV = 6.0
        elif id == -3:
            reducedV = 8.0
        elif id == -4:
            reducedV = np.inf
        else:
            reducedV = np.inf
        
        # clear the axes and plot, with x_offset, y_offset and scale
        self.canvas.axes.cla()
        for tr in self.st:
            scale = 1.0/np.max(tr.data)
            x_offset = tr.stats.sac['dist']
            y_offset = -x_offset/reducedV
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
