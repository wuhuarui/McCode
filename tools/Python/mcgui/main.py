#!/usr/bin/env python

'''mgcui 

Initial version written during Winter/spring of 2015

@author: jaga
'''
import sys
import os
import webbrowser
import subprocess
import time
import threading
from PyQt4 import QtGui
from PyQt4 import QtCore
from viewclasses import McView


''' State
Holds unique state values.
'''
class McGuiState(QtCore.QObject):    
    def initState(self):
        self.setWorkDir(os.getcwd())
        
        for a in sys.argv:
            if os.path.splitext(a)[1] == '.instr':
                instr_file = os.path.abspath(a)
                self.loadInstument(instr_file)
                break
        
        self.fireSimStateUpdate()
    
    status = ''
    statusUpdated = QtCore.pyqtSignal(QtCore.QString)
    def setStatus(self, status):
        self.status = status
        self.statusUpdated.emit(self.status)
        
    logUpdated = QtCore.pyqtSignal(QtCore.QString)
    def __logLine(self, logline):
        if logline != None:
            self.logUpdated.emit(logline)
    
        
    __instrFile = ''
    filesUpdated = QtCore.pyqtSignal(QtCore.QStringList)
    def fireFilesUpdate(self):
        self.filesUpdated.emit([self.__instrFile, self.getWorkDir()])
    def getInstrumentFile(self):
        return self.__instrFile
    def loadInstument(self, instrFile):
        if not os.path.isfile(instrFile):
            if os.path.splitext(instrFile)[1] != '.instr':
                raise Exception('Invalid instrument file.')
        
        self.__instrFile = str(instrFile)
        self.fireFilesUpdate() 
        self.setStatus("Instrument: " + instrFile)
        self.fireSimStateUpdate()
    def getWorkDir(self):
        return os.getcwd()
    def setWorkDir(self, newdir):
        if not os.path.isdir(newdir):
            raise Exception('Invalid work dir.')
        
        olddir = os.getcwd()
        os.chdir(newdir)
        
        if newdir != olddir:
            self.__binaryFile = ''
            self.__cFile = ''
        
        self.setStatus("Work dir: " + newdir)
        self.fireFilesUpdate()
    
    __cFile = ""
    __binaryFile = ""
    __resultFile = ""
    def canCompile(self):
        return self.__instrFile != ""
    def canRun(self):
        return self.__binaryFile != ""
    def canPlot(self):
        return self.__resultFile != ""
    # [<canRun>, <canCompile>, <canPlot>] each can be 'True' or 'False'
    simStateUpdated = QtCore.pyqtSignal(QtCore.QStringList)
    def fireSimStateUpdate(self):
        self.simStateUpdated.emit([str(self.canRun()), str(self.canCompile()), str(self.canPlot())])
    
    def compile(self):
        # create mcstas .c file from instrument
        nf = self.__instrFile
        process = subprocess.Popen(['mcstas', nf], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        self.setStatus('Compiling instrument to c ...')
        #process.wait()
        while process.poll() <> 0:
            for l in process.communicate():
                self.__logLine(l)
            time.sleep(0.1)
        
        spl = os.path.splitext(os.path.basename(str(nf)))
        basef = os.path.join(self.getWorkDir(), spl[0])
        cf = basef + '.c'
        if os.path.isfile(cf):
            self.__cFile = cf
        else:
            raise Exception('C file not found')
        
        # compile binary from mcstas .c file 
        bf = basef + '.out'
        process = subprocess.Popen(['cc', '-O', '-o', bf, cf, '-lm'], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        self.setStatus('Compiling instrument to binary ...')
        process.wait()
        stdout_stderr_lines = process.communicate()
        for l in stdout_stderr_lines:
            self.__logLine(l)
        
        if os.path.isfile(bf):
            self.__binaryFile = bf
        else:
            raise Exception('Binary not found.')
        
        self.setStatus('Instrument compiled (' + self.__binaryFile + ')')
        self.fireSimStateUpdate()
    def run(self, pars):
        # run simulation in a background thread
        thread = threading.Thread(target=self.runSimAsync)
        thread.start()
        
    def runSimAsync(self):
        process = subprocess.Popen(['./' + os.path.basename(self.__binaryFile)], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT)
        self.__logLine('sim started (' + './' + os.path.basename(self.__binaryFile) + ')')
        # TODO: implement communication
        #stdout_stderr_lines = process.communicate()
        #for l in stdout_stderr_lines:
        #    self.__logLine(l)
        #while process.poll() <> 0:
        #    self.__logLine('process returncode:    ' + str(process.poll()))
        #    time.sleep(0.5)

''' Controller
Implements ui and data callbacks.
'''
class McGuiAppController():
    def __init__(self):
        self.view = McView()
        self.state = McGuiState()
        self.connectAllCallbacks()    
        self.state.initState()
    
    ''' UI callbacks
    '''
    def handleLoadInstrument(self):
        instrFile = self.view.showOpenInstrumentDlg(self.state.getWorkDir())
        if instrFile:
            self.state.loadInstument(instrFile)
            
    def handleChangeWorkDir(self):
        workDir = self.view.showChangeWorkDirDlg(self.state.getWorkDir())
        if workDir:
            self.state.setWorkDir(workDir)
        
    def handleExit(self):
        sys.exit()
        
    def handlePlotResults(self):
        print("not implemented")
        
    def handleHelpWeb(self):
        '''open the mcstas homepage'''
        mcurl = 'http://www.mcstas.org'
        webbrowser.open_new_tab(mcurl)
        
    def handleHelpPdf(self):
        # TODO: make it cross-platform (e.g. os.path.realpath(__file__) +  ..)
        mcman = '/usr/share/mcstas/2.1/doc/manuals/mcstas-manual.pdf'
        webbrowser.open_new_tab(mcman)
        
    def handleHelpPdfComponents(self):
        # TODO: make it cross-platform (e.g. os.path.realpath(__file__) +  ...)
        mcman = '/usr/share/mcstas/2.1/doc/manuals/mcstas-components.pdf'
        webbrowser.open_new_tab(mcman)
        
    def handleHelpAbout(self):
        print("not implemented")
        
    ''' Connect UI and state callbacks 
    '''
    def connectAllCallbacks(self):        
        # connect UI widget signals to our handlers/logics
        # WARNING: NEVER update ui widget state from this class, always delegate to view. This explicit widget access is AN EXCEPTION
        mwui = self.view.mwui
        mwui.actionQuit.triggered.connect(self.handleExit)
        mwui.actionOpen_instrument.triggered.connect(self.handleLoadInstrument)
        mwui.actionChange_Working_Dir.triggered.connect(self.handleChangeWorkDir)
        
        mwui.tbtnInstrument.clicked.connect(self.handleLoadInstrument)
        mwui.tbtnWorkDir.clicked.connect(self.handleChangeWorkDir)
        
        mwui.actionCompile_Instrument.triggered.connect(self.state.compile)
        mwui.actionRun_Simulation.triggered.connect(self.state.run)
        
        mwui.actionCS.triggered.connect(self.state.compile)
        mwui.actionRS.triggered.connect(self.state.run)
        mwui.actionPS.triggered.connect(self.handlePlotResults)
        
        mwui.actionMcstas_Web_Page.triggered.connect(self.handleHelpWeb)
        mwui.actionMcstas_User_Manual.triggered.connect(self.handleHelpPdf)
        mwui.actionMcstas_Component_Manual.triggered.connect(self.handleHelpPdfComponents)
        mwui.actionAbout.triggered.connect(self.handleHelpAbout)

        st = self.state
        st.filesUpdated.connect(self.view.updateLabels)
        st.statusUpdated.connect(self.view.updateStatus)
        st.logUpdated.connect(self.view.updateLog)
        st.simStateUpdated.connect(self.view.updateSimState)
        
        
''' Program execution
'''
def main():
    mcguiApp = QtGui.QApplication(sys.argv)
    
    ctr = McGuiAppController()
    ctr.view.showMainWindow()
    
    sys.exit(mcguiApp.exec_())

if __name__ == '__main__':
    main()
