# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mock-up.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

#########################################gui modules #############################3
import sys

from PyQt5 import QtWidgets, uic
from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot
from threading import Thread
from astropy.io import fits
import numpy as np
from rawkit import raw

import threading

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pythoncom
import time
import os
from PIL import Image


##########################camera control modules ##########################33
#겹치는거는 주석처리했다.
#import sys
#from PyQt5 import  QtWidgets, uic
#from PyQt5 import QtCore
#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from threading import Thread
#import threading
from ctypes import *

#import os
import datetime
#import time
from cr2fits import cr2fits
import glob



##################################### 카메라 부분 #################################################

edsdk = windll.edsdk

    
dir_path = "C:"
dir_name = "sky"

if(os.path.isdir(dir_path+'/' + dir_name) == False):
    os.mkdir(dir_path + '/' + dir_name)


def AddTime(fname):
    now = datetime.datetime.now()
    nname = fname[:-4]+'_'+now.isoformat()[:-7].replace(':','-')+fname[-4:]
    nnname = nname.replace('T','-')
    return nnname


class EDSDKError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def EDErrorMsg(code):
	return "EDSDK error code"+hex(code)
	
def Call(code):
	if code != 0:
		raise Exception(EDSDKError and EDErrorMsg(code))
		
def Release(ref):
	edsdk.EdsRelease(ref)
	
def GetChildCount(ref):
	i = c_int()
	Call(edsdk.EdsGetChildCount(ref,byref(i)))
	return i.value

def GetChild(ref,number):
	c = c_void_p()
	Call(edsdk.EdsGetChildAtIndex(ref,number,byref(c)))
	return c
	

kEdsObjectEvent_DirItemRequestTransfer  =    0x00000208
kEdsObjectEvent_DirItemCreated       =       0x00000204


ObjectHandlerType = WINFUNCTYPE   (c_int,c_int,c_void_p,c_void_p)
def ObjectHandler_py(event,object,context):
	if event==kEdsObjectEvent_DirItemRequestTransfer:
		DownloadImage(object)
	return 0
ObjectHandler = ObjectHandlerType(ObjectHandler_py)


kEdsStateEvent_WillSoonShutDown       =      0x00000303

StateHandlerType = WINFUNCTYPE   (c_int,c_int,c_int,c_void_p)
def StateHandler_py(event,state,context):
	if event==kEdsStateEvent_WillSoonShutDown:
		print ("cam about to shut off")
		Call(edsdk.EdsSendCommand(context,1,0))
	return 0
StateHandler = StateHandlerType(StateHandler_py)


PropertyHandlerType = WINFUNCTYPE   (c_int,c_int,c_int,c_int,c_void_p)
def PropertyHandler_py(event,property,param,context):
	return 0
PropertyHandler = PropertyHandlerType(PropertyHandler_py)


class DirectoryItemInfo(Structure):
	_fields_ = [("size", c_int),
				("isFolder", c_int),
				("groupID",c_int),
				("option",c_int),
				("szFileName",c_char*256),
				("format",c_int)]

WaitingForImage = False
ImageFilename = None


def DownloadImage(image):
	dirinfo = DirectoryItemInfo()
	Call(edsdk.EdsGetDirectoryItemInfo((c_ulonglong(image)),byref(dirinfo)))
	stream = c_void_p()
#	stream_jpg = c_void_p()
    
	global ImageFilename
#	global ImageFilename_jpg

    
	if ImageFilename is None:
		print ("Image was taken manually")
		ImageFilename =  AddTime("IMG.CR2")
		# ImageFilename =  AddTime("IMG.JPG")
               
	print ("Saving as",ImageFilename)
	e = "C:\\sky\\" + ImageFilename 
#	e_jpg = "C:\\sky\\" + ImageFilename_jpg 
	b = e.encode()
#	b_jpg = e_jpg.encode()
    
	print(b)
	ImageFilename_fohere = c_char_p(b)
#	ImageFilename_fohere_jpg = c_char_p(b_jpg)    
	Call(edsdk.EdsCreateFileStream(ImageFilename_fohere,1,2,byref(stream)))
	print(ImageFilename)
	print(type(ImageFilename))
	print(ImageFilename_fohere)
	Call(edsdk.EdsDownload(c_ulonglong(image),dirinfo.size,stream))
	Call(edsdk.EdsDownloadComplete(c_ulonglong(image)))
	Release(stream)
    
	global WaitingForImage  
	WaitingForImage = False
    
    #################################cr2fits convertion code ###############################

	a = cr2fits(e, 3)
	a.read_cr2()    
    
    
    #im_blue = a.get_color(im_ppm, a.colorInput)
	im_ppm = a.read_pbm(a.pbm_bytes)
    
    
    # Create FITS file from Blue Image and EXIF data
	fits_image = a.create_fits(im_ppm)   
    
    # If you want to write output, _generate_destination gets filename
	dest = a._generate_destination(a.filename, a.colorInput)
	
    # Write FITS file to generated destination (or elsewhere)
	a.write_fits(fits_image, dest)

kEdsSaveTo_Camera       =   1
kEdsSaveTo_Host         =   2
kEdsSaveTo_Both         =   kEdsSaveTo_Camera | kEdsSaveTo_Host
kEdsPropID_SaveTo  = 0x0000000b



class EdsCapacity(Structure):
	_fields_ = [("numberOfFreeClusters", c_int),
				("bytesPerSector", c_int),
				("reset",c_int)]



class Camera:
	def Connect(self,camnum=0):
		err = edsdk.EdsInitializeSDK()
		self.cam = None
		l = CameraList()
		self.cam = l.GetCam(camnum)
		Call(edsdk.EdsSetObjectEventHandler(self.cam,0x200,ObjectHandler,None))
		Call(edsdk.EdsSetPropertyEventHandler(self.cam,0x100,PropertyHandler,None))
		Call(edsdk.EdsSetCameraStateEventHandler(self.cam,0x300,StateHandler,self.cam))
		Call(edsdk.EdsOpenSession(self.cam))
		
		self.SetProperty(kEdsPropID_SaveTo,kEdsSaveTo_Host)
		
		# set large capacity
		cap = EdsCapacity(10000000,512,1)
		Call(edsdk.EdsSetCapacity(self.cam,cap))
		
		#msg.showinfo('.', '연결되었습니다.')
        
	def __del__(self):
		if self.cam is not None:
			Call(edsdk.EdsCloseSession(self.cam))
			Call(Release(self.cam))
	def disconnect(self):
		if self.cam is not None:
			Call(edsdk.EdsCloseSession(self.cam))
			Call(Release(self.cam))
			edsdk.EdsTerminateSDK() 
            
	def SetProperty(self,property,param):
		d = c_int(param)
		Call(edsdk.EdsSetPropertyData(self.cam,property,0,4,byref(d)))
	def AutoFocus(self):
#	kEdsCameraCommand_ShutterButton_OFF					= 0x00000000,
#	kEdsCameraCommand_ShutterButton_Halfway				= 0x00000001,
#	kEdsCameraCommand_ShutterButton_Completely			= 0x00000003,
#	kEdsCameraCommand_ShutterButton_Halfway_NonAF		= 0x00010001,
#	kEdsCameraCommand_ShutterButton_Completely_NonAF	= 0x00010003,
		# note that this can fail when AF fails (error code 0x8D01)
		self.SendCommand(4,1)
	def Shoot(self,fname=None):
		# set saving flag
		global WaitingForImage
		WaitingForImage = True

		# set filename
		global ImageFilename
		#global ImageFilename_jpg        
		if fname is None:
			ImageFilename = AddTime("IMG.CR2")
			# ImageFilename = AddTime("IMG.JPG")            
		else:
			ImageFilename = fname

		# note that this can fail when AF fails (error code 0x8D01)
		self.SendCommand(0)
		# capture succeeded so go on to download image
		while WaitingForImage:
			pythoncom.PumpWaitingMessages()
		return ImageFilename
	def KeepOn(self):
		# important command - keeps the camera connected when not used
		self.SendCommand(1)
	def SendCommand(self,command,param=0):
		#define kEdsCameraCommand_TakePicture                     0x00000000
		#define kEdsCameraCommand_ExtendShutDownTimer             0x00000001
		#define kEdsCameraCommand_BulbStart						  0x00000002 
		#define kEdsCameraCommand_BulbEnd						  0x00000003 
		#define kEdsCameraCommand_DoEvfAf                         0x00000102
		#define kEdsCameraCommand_DriveLensEvf                    0x00000103
		#define kEdsCameraCommand_DoClickWBEvf                    0x00000104		
		#define kEdsCameraCommand_PressShutterButton			  0x00000004
		Call(edsdk.EdsSendCommand(self.cam,command,param))

class CameraList:
	def __init__(self):
		self.list = c_void_p(None)
		Call(edsdk.EdsGetCameraList(byref(self.list)))
		print ("found",GetChildCount(self.list),"cameras")
	def Count(self):
		return GetChildCount(self.list)
	def GetCam(self,number=0):
		print ("get cam")
		if self.Count()<(number+1):
			raise ValueError("Camera not found, make sure it's on and connected")
		return GetChild(self.list,number)
	def __del__(self):
		Release(self.list)
	
c= Camera()


class TestThread_cam(QThread):
    # 쓰레드의 커스텀 이벤트
    # 데이터 전달 시 형을 명시해야 함
    threadEvent = QtCore.pyqtSignal(int)
 
    def __init__(self, parent=None):
        super().__init__()
        self.main = parent
        self.isRun_cam = False
 
    def run(self):
        while self.isRun_cam:
 #           c.AutoFocus()
            c.Shoot()
            # time.sleep(5)
            #make_slideshow(ui)
            path = "C:/sky/"
            #path = "C:/Python/time/"
        # 읽어온 파일들
            files = []

        #해당 path의 모든파일을 읽는것
            for r, d, f in os.walk(path):
                for file in f:
                    if '.CR2' in file:
                        files.append(os.path.join(r, file))

        # 파일 리스트
            #print(files)
            #print(files[0])
        
        # 파일 이름 정렬
            files.sort()
            files.reverse()    

            print(f"file is {files[0]}")           
            

            print(f"filename is {files[0]}")
            # parse CR2 image
            file_timestamp = os.path.getmtime(files[0])
            raw_image_process = raw.Raw(files[0])
            print(raw_image_process)
            buffered_image = np.array(raw_image_process.to_buffer())
            print(buffered_image)
        
            # check orientation due to PIL image stretch issue
            if raw_image_process.metadata.orientation == 0:
                jpg_image_height = raw_image_process.metadata.height
                jpg_image_width = raw_image_process.metadata.width
            else:
                jpg_image_height = raw_image_process.metadata.width
                jpg_image_width = raw_image_process.metadata.height

            print(jpg_image_width, jpg_image_height)
            
            # prep JPG details
            jpg_image_location = files[0].replace('.CR2','.jpg')
            jpg_image = Image.frombytes('RGB', (jpg_image_width, jpg_image_height), buffered_image)
            jpg_image.save(jpg_image_location, format="jpeg")
            print(jpg_image)
            # update JPG file timestamp to match CR2
            os.utime(jpg_image_location, (file_timestamp,file_timestamp))

            # close to prevent too many open files error
            jpg_image.close()
            raw_image_process.close()
            
            jpg_files = []
            
        #해당 path의 모든파일을 읽는것
            for r, d, f in os.walk(path):
                for file in f:
                    if '.jpg' in file:
                        jpg_files.append(os.path.join(r, file))
                        
            jpg_files.sort()
            jpg_files.reverse()
                        
            ui.qPixmapFileVar = QPixmap()
            print(f"file for Qpixmap is here {jpg_files[0]}")
            ui.qPixmapFileVar.load(jpg_files[0])         
            print("here")
            
            ui.qPixmapFileVar = ui.qPixmapFileVar.scaled(671, 481)
            ui.label_11.setPixmap(ui.qPixmapFileVar)   
            
    ############################  removing CR2 ################################################
#	fileList = glob.glob('C:/sky/*.CR2')   
#	for filePath in fileList:
#           try:
#                os.remove(filePath)
#            except:
#                print("Error while deleting file : ", filePath)
####################################################################################################

        """
        # fits to jpg test code by CK 20220427
        #해당 path의 모든파일을 읽는것
            for r, d, f in os.walk(path):
                for file in f:
                    if '.fits' in file:
                        files.append(os.path.join(r, file))

        # 파일 리스트
            #print(files)
            #print(files[0])
        
        # 파일 이름 정렬
            files.sort()
            files.reverse()    
            
            print(f"file is {files[0]}")
            
            data = []
            jpg_images = []
            
            for filename in files:
                data.append(fits.open(filename)[0].data)
            
            kiri = len(data)
            
            print(kiri)
            
            # Read command line arguments
            vmax = np.percentile(data, 99)
            vmin = np.percentile(data, 70)
            
            print(f"vamx and vmin is {vmax} {vmin}")
            
            for image_data in data:
                # Clip data to brightness limits
                
                image_data[image_data > vmax] = vmax
                image_data[image_data < vmin] = vmin
                print(f"image_data is  {image_data}")

                # Scale image_data to range [0, 1] 
                image_data = (image_data - vmin)/(vmax - vmin)
                # Convert to 8-bit integer  
                image_data = (255*image_data).astype(np.uint8)
                # Invert y axis
                image_data = image_data[::-1, :]                
                
                # Create image from data array and save as jpg
                jpg_images.append(Image.fromarray(image_data, 'L'))
                
                print(jpg_images[0])
                imagename = files[0].replace('.fits', '.jpg')
                print(imagename)
                jpg_images[0].save(imagename)
            
        """
           

######################################### UI 부분 ######################################################


class Ui_Dialog(object):
 
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1557, 886)
        self.verticalWidget = QtWidgets.QWidget(Dialog)
        self.verticalWidget.setGeometry(QtCore.QRect(50, 580, 171, 261))
        self.verticalWidget.setObjectName("verticalWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalWidget)
        self.verticalLayout.setContentsMargins(30, 30, 30, 30)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton_2 = QtWidgets.QPushButton(self.verticalWidget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.verticalLayout.addWidget(self.pushButton_2)
        self.pushButton_2.clicked.connect(c.Connect)
        
        self.pushButton_4 = QtWidgets.QPushButton(self.verticalWidget)
        self.pushButton_4.setObjectName("pushButton_4")
        self.verticalLayout.addWidget(self.pushButton_4)
        self.pushButton_4.clicked.connect(self.threadStart_cam)
        
        self.pushButton_3 = QtWidgets.QPushButton(self.verticalWidget)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.clicked.connect(self.threadStop_cam)
        
        self.verticalLayout.addWidget(self.pushButton_3)
        self.pushButton = QtWidgets.QPushButton(self.verticalWidget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.clicked.connect(c.disconnect)
        
        self.verticalLayout.addWidget(self.pushButton)
        self.verticalLayoutWidget_2 = QtWidgets.QWidget(Dialog)
        self.verticalLayoutWidget_2.setGeometry(QtCore.QRect(230, 580, 171, 261))
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setContentsMargins(10, 20, 10, 20)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setContentsMargins(20, 30, 20, 20)
        self.verticalLayout_5.setSpacing(5)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.comboBox = QtWidgets.QComboBox(self.verticalLayoutWidget_2)
        self.comboBox.setObjectName("comboBox")
        self.verticalLayout_5.addWidget(self.comboBox)
        self.pushButton_5 = QtWidgets.QPushButton(self.verticalLayoutWidget_2)
        self.pushButton_5.setObjectName("pushButton_5")
        self.verticalLayout_5.addWidget(self.pushButton_5)
        self.verticalLayout_2.addLayout(self.verticalLayout_5)
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        self.verticalLayout_6.setContentsMargins(20, 20, 20, 30)
        self.verticalLayout_6.setSpacing(5)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.pushButton_6 = QtWidgets.QPushButton(self.verticalLayoutWidget_2)
        self.pushButton_6.setObjectName("pushButton_6")
        self.verticalLayout_6.addWidget(self.pushButton_6)
        self.lineEdit = QtWidgets.QLineEdit(self.verticalLayoutWidget_2)
        self.lineEdit.setObjectName("lineEdit")
        self.verticalLayout_6.addWidget(self.lineEdit)
        self.verticalLayout_2.addLayout(self.verticalLayout_6)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(Dialog)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(410, 580, 241, 121))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setContentsMargins(30, 0, 30, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.load_button = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.load_button.setObjectName("load_button")
        self.load_button.clicked.connect(self.threadStart)
        self.horizontalLayout_2.addWidget(self.load_button)
        self.pushButton_7 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_7.setObjectName("pushButton_7")
        self.pushButton_7.clicked.connect(self.threadStop)
        self.horizontalLayout_2.addWidget(self.pushButton_7)
        self.horizontalLayoutWidget_3 = QtWidgets.QWidget(Dialog)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(410, 720, 241, 121))
        self.horizontalLayoutWidget_3.setObjectName("horizontalLayoutWidget_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.horizontalLayout_3.setContentsMargins(65, 0, 65, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.spinBox = QtWidgets.QSpinBox(self.horizontalLayoutWidget_3)
        self.spinBox.setObjectName("spinBox")
        self.horizontalLayout_3.addWidget(self.spinBox)
        self.verticalLayoutWidget_3 = QtWidgets.QWidget(Dialog)
        self.verticalLayoutWidget_3.setGeometry(QtCore.QRect(660, 580, 101, 261))
        self.verticalLayoutWidget_3.setObjectName("verticalLayoutWidget_3")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_3)
        self.verticalLayout_3.setContentsMargins(10, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.radioButton_2 = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton_2.setObjectName("radioButton_2")
        self.verticalLayout_3.addWidget(self.radioButton_2)
        self.radioButton_5 = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton_5.setObjectName("radioButton_5")
        self.verticalLayout_3.addWidget(self.radioButton_5)
        self.radioButton_4 = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton_4.setObjectName("radioButton_4")
        self.verticalLayout_3.addWidget(self.radioButton_4)
        self.radioButton_6 = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton_6.setObjectName("radioButton_6")
        self.verticalLayout_3.addWidget(self.radioButton_6)
        self.radioButton_3 = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton_3.setObjectName("radioButton_3")
        self.verticalLayout_3.addWidget(self.radioButton_3)
        self.radioButton = QtWidgets.QRadioButton(self.verticalLayoutWidget_3)
        self.radioButton.setObjectName("radioButton")
        self.verticalLayout_3.addWidget(self.radioButton)
        self.verticalLayoutWidget_4 = QtWidgets.QWidget(Dialog)
        self.verticalLayoutWidget_4.setGeometry(QtCore.QRect(810, 580, 711, 101))
        self.verticalLayoutWidget_4.setObjectName("verticalLayoutWidget_4")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_4)
        self.verticalLayout_4.setContentsMargins(50, 0, 30, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.horizontalSlider = QtWidgets.QSlider(self.verticalLayoutWidget_4)
        self.horizontalSlider.setMaximumSize(QtCore.QSize(600, 16777215))
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.verticalLayout_4.addWidget(self.horizontalSlider)
        self.horizontalLayoutWidget_4 = QtWidgets.QWidget(Dialog)
        self.horizontalLayoutWidget_4.setGeometry(QtCore.QRect(810, 690, 711, 111))
        self.horizontalLayoutWidget_4.setObjectName("horizontalLayoutWidget_4")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_4)
        self.horizontalLayout_4.setContentsMargins(60, 0, 40, 0)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalSlider_2 = QtWidgets.QSlider(self.horizontalLayoutWidget_4)
        self.horizontalSlider_2.setMaximumSize(QtCore.QSize(300, 16777215))
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.horizontalLayout_4.addWidget(self.horizontalSlider_2)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.horizontalLayoutWidget_4)
        self.lineEdit_2.setMinimumSize(QtCore.QSize(100, 0))
        self.lineEdit_2.setMaximumSize(QtCore.QSize(100, 16777215))
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.horizontalLayout_4.addWidget(self.lineEdit_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(1320, 820, 193, 28))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.line = QtWidgets.QFrame(Dialog)
        self.line.setGeometry(QtCore.QRect(120, 570, 101, 20))
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.line_2 = QtWidgets.QFrame(Dialog)
        self.line_2.setGeometry(QtCore.QRect(40, 580, 20, 261))
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.line_3 = QtWidgets.QFrame(Dialog)
        self.line_3.setGeometry(QtCore.QRect(210, 580, 20, 261))
        self.line_3.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")
        self.line_4 = QtWidgets.QFrame(Dialog)
        self.line_4.setGeometry(QtCore.QRect(50, 830, 171, 20))
        self.line_4.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_4.setObjectName("line_4")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(60, 570, 64, 15))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(240, 570, 64, 15))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setGeometry(QtCore.QRect(420, 570, 81, 16))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setGeometry(QtCore.QRect(420, 710, 64, 15))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(Dialog)
        self.label_5.setGeometry(QtCore.QRect(670, 570, 64, 15))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(Dialog)
        self.label_6.setGeometry(QtCore.QRect(820, 570, 64, 15))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(Dialog)
        self.label_7.setGeometry(QtCore.QRect(820, 680, 64, 15))
        self.label_7.setObjectName("label_7")
        self.line_5 = QtWidgets.QFrame(Dialog)
        self.line_5.setGeometry(QtCore.QRect(310, 570, 91, 20))
        self.line_5.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_5.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_5.setObjectName("line_5")
        self.line_6 = QtWidgets.QFrame(Dialog)
        self.line_6.setGeometry(QtCore.QRect(220, 580, 20, 261))
        self.line_6.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_6.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_6.setObjectName("line_6")
        self.line_7 = QtWidgets.QFrame(Dialog)
        self.line_7.setGeometry(QtCore.QRect(390, 580, 20, 261))
        self.line_7.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_7.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_7.setObjectName("line_7")
        self.line_8 = QtWidgets.QFrame(Dialog)
        self.line_8.setGeometry(QtCore.QRect(230, 830, 171, 20))
        self.line_8.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_8.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_8.setObjectName("line_8")
        self.line_9 = QtWidgets.QFrame(Dialog)
        self.line_9.setGeometry(QtCore.QRect(500, 570, 151, 20))
        self.line_9.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_9.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_9.setObjectName("line_9")
        self.line_10 = QtWidgets.QFrame(Dialog)
        self.line_10.setGeometry(QtCore.QRect(410, 690, 241, 20))
        self.line_10.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_10.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_10.setObjectName("line_10")
        self.line_11 = QtWidgets.QFrame(Dialog)
        self.line_11.setGeometry(QtCore.QRect(400, 580, 20, 121))
        self.line_11.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_11.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_11.setObjectName("line_11")
        self.line_12 = QtWidgets.QFrame(Dialog)
        self.line_12.setGeometry(QtCore.QRect(640, 580, 21, 121))
        self.line_12.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_12.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_12.setObjectName("line_12")
        self.line_13 = QtWidgets.QFrame(Dialog)
        self.line_13.setGeometry(QtCore.QRect(470, 710, 181, 20))
        self.line_13.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_13.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_13.setObjectName("line_13")
        self.line_14 = QtWidgets.QFrame(Dialog)
        self.line_14.setGeometry(QtCore.QRect(410, 830, 241, 20))
        self.line_14.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_14.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_14.setObjectName("line_14")
        self.line_15 = QtWidgets.QFrame(Dialog)
        self.line_15.setGeometry(QtCore.QRect(640, 720, 20, 121))
        self.line_15.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_15.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_15.setObjectName("line_15")
        self.line_16 = QtWidgets.QFrame(Dialog)
        self.line_16.setGeometry(QtCore.QRect(400, 720, 20, 121))
        self.line_16.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_16.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_16.setObjectName("line_16")
        self.line_17 = QtWidgets.QFrame(Dialog)
        self.line_17.setGeometry(QtCore.QRect(650, 580, 20, 261))
        self.line_17.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_17.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_17.setObjectName("line_17")
        self.line_18 = QtWidgets.QFrame(Dialog)
        self.line_18.setGeometry(QtCore.QRect(750, 580, 20, 261))
        self.line_18.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_18.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_18.setObjectName("line_18")
        self.line_19 = QtWidgets.QFrame(Dialog)
        self.line_19.setGeometry(QtCore.QRect(720, 570, 41, 20))
        self.line_19.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_19.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_19.setObjectName("line_19")
        self.line_20 = QtWidgets.QFrame(Dialog)
        self.line_20.setGeometry(QtCore.QRect(660, 830, 101, 20))
        self.line_20.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_20.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_20.setObjectName("line_20")
        self.line_21 = QtWidgets.QFrame(Dialog)
        self.line_21.setGeometry(QtCore.QRect(800, 690, 20, 111))
        self.line_21.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_21.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_21.setObjectName("line_21")
        self.line_22 = QtWidgets.QFrame(Dialog)
        self.line_22.setGeometry(QtCore.QRect(800, 580, 20, 101))
        self.line_22.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_22.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_22.setObjectName("line_22")
        self.line_23 = QtWidgets.QFrame(Dialog)
        self.line_23.setGeometry(QtCore.QRect(1510, 580, 20, 101))
        self.line_23.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_23.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_23.setObjectName("line_23")
        self.line_24 = QtWidgets.QFrame(Dialog)
        self.line_24.setGeometry(QtCore.QRect(1510, 690, 20, 111))
        self.line_24.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_24.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_24.setObjectName("line_24")
        self.line_25 = QtWidgets.QFrame(Dialog)
        self.line_25.setGeometry(QtCore.QRect(810, 790, 711, 20))
        self.line_25.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_25.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_25.setObjectName("line_25")
        self.line_26 = QtWidgets.QFrame(Dialog)
        self.line_26.setGeometry(QtCore.QRect(850, 680, 671, 20))
        self.line_26.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_26.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_26.setObjectName("line_26")
        self.line_27 = QtWidgets.QFrame(Dialog)
        self.line_27.setGeometry(QtCore.QRect(810, 670, 711, 20))
        self.line_27.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_27.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_27.setObjectName("line_27")
        self.line_28 = QtWidgets.QFrame(Dialog)
        self.line_28.setGeometry(QtCore.QRect(860, 570, 661, 20))
        self.line_28.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_28.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_28.setObjectName("line_28")
        self.line_29 = QtWidgets.QFrame(Dialog)
        self.line_29.setGeometry(QtCore.QRect(50, 540, 711, 20))
        self.line_29.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_29.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_29.setObjectName("line_29")
        self.line_30 = QtWidgets.QFrame(Dialog)
        self.line_30.setGeometry(QtCore.QRect(100, 20, 661, 20))
        self.line_30.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_30.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_30.setObjectName("line_30")
        self.line_31 = QtWidgets.QFrame(Dialog)
        self.line_31.setGeometry(QtCore.QRect(40, 30, 20, 521))
        self.line_31.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_31.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_31.setObjectName("line_31")
        self.line_32 = QtWidgets.QFrame(Dialog)
        self.line_32.setGeometry(QtCore.QRect(1510, 30, 20, 521))
        self.line_32.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_32.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_32.setObjectName("line_32")
        self.line_33 = QtWidgets.QFrame(Dialog)
        self.line_33.setGeometry(QtCore.QRect(750, 30, 20, 521))
        self.line_33.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_33.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_33.setObjectName("line_33")
        self.line_34 = QtWidgets.QFrame(Dialog)
        self.line_34.setGeometry(QtCore.QRect(800, 30, 20, 521))
        self.line_34.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_34.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_34.setObjectName("line_34")
        self.line_35 = QtWidgets.QFrame(Dialog)
        self.line_35.setGeometry(QtCore.QRect(810, 540, 711, 20))
        self.line_35.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_35.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_35.setObjectName("line_35")
        self.line_36 = QtWidgets.QFrame(Dialog)
        self.line_36.setGeometry(QtCore.QRect(870, 20, 651, 20))
        self.line_36.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_36.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_36.setObjectName("line_36")
        self.label_8 = QtWidgets.QLabel(Dialog)
        self.label_8.setGeometry(QtCore.QRect(60, 20, 64, 15))
        self.label_8.setObjectName("label_8")
        self.label_9 = QtWidgets.QLabel(Dialog)
        self.label_9.setGeometry(QtCore.QRect(820, 20, 64, 15))
        self.label_9.setObjectName("label_9")
        self.label_10 = QtWidgets.QLabel(Dialog)
        self.label_10.setGeometry(QtCore.QRect(830, 50, 671, 481))
        self.label_10.setText("")
        self.label_10.setObjectName("label_10")
        self.label_10.setPixmap(QPixmap())
        self.label_11 = QtWidgets.QLabel(Dialog)
        self.label_11.setGeometry(QtCore.QRect(70, 50, 671, 481))
        self.label_11.setText("")
        self.label_11.setObjectName("label_11")
        self.th = TestThread(self)
        self.th_cam = TestThread_cam(self)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)


    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.pushButton_2.setText(_translate("Dialog", "Connect"))
        self.pushButton_4.setText(_translate("Dialog", "Start"))
        self.pushButton_3.setText(_translate("Dialog", "End"))
        self.pushButton.setText(_translate("Dialog", "Disconnect"))
        self.pushButton_5.setText(_translate("Dialog", "Set exposure"))
        self.pushButton_6.setText(_translate("Dialog", "Get exposure"))
        self.load_button.setText(_translate("Dialog", "Load"))
        self.pushButton_7.setText(_translate("Dialog", "Stop"))
        self.radioButton_2.setText(_translate("Dialog", "5 m"))
        self.radioButton_5.setText(_translate("Dialog", "30 m"))
        self.radioButton_4.setText(_translate("Dialog", "1 h"))
        self.radioButton_6.setText(_translate("Dialog", "1.5 h"))
        self.radioButton_3.setText(_translate("Dialog", "2 h"))
        self.radioButton.setText(_translate("Dialog", "3 h"))
        self.label.setText(_translate("Dialog", "Camera"))
        self.label_2.setText(_translate("Dialog", "Exposure"))
        self.label_3.setText(_translate("Dialog", "Load Image"))
        self.label_4.setText(_translate("Dialog", "Interval"))
        self.label_5.setText(_translate("Dialog", "Before"))
        self.label_6.setText(_translate("Dialog", "Time"))
        self.label_7.setText(_translate("Dialog", "fps"))
        self.label_8.setText(_translate("Dialog", "Live"))
        self.label_9.setText(_translate("Dialog", "Movie"))
        
    def drawImages(self, painter):
        painter.drawImage(5,15,self.sid)    

    def threadStart(self):
         if not self.th.isRun:
            print('쓰레드 시작')
            self.th.isRun = True
            self.th.start()

    def threadStop(self):
         if self.th.isRun:
            print('쓰레드 정지')
            self.th.isRun = False

    def threadStart_cam(self):
         if not self.th_cam.isRun_cam:
            print('쓰레드 시작')
            self.th_cam.isRun_cam = True
            self.th_cam.start()

    def threadStop_cam(self):
         if self.th_cam.isRun_cam:
            print('쓰레드 정지')
            self.th_cam.isRun_cam = False
    

           
class TestThread(QThread):
    # 쓰레드의 커스텀 이벤트
    # 데이터 전달 시 형을 명시해야 함
    threadEvent = QtCore.pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__()
        self.main = parent
        self.isRun = False
 
    def run(self):
        while self.isRun:
            global ui
            #make_slideshow(ui)
            path = "C:/sky/"
            #path = "C:/Python/time/"
        # 읽어온 파일들
            files = []
        #해당 path의 모든파일을 읽는것
            for r, d, f in os.walk(path):
                for file in f:
                    if '.png' in file or '.jpg' in file or '.PNG' in file or '.JPG' in file:
                        files.append(os.path.join(r, file))

        # 파일 리스트
            print(files)
            print(files[0])
        
        # 파일 이름 정렬
            files.sort()
            flag = 0
            for file in files:
               # image_file = fits.open(file)
                #image_data = fits.getdata(image_file, ext=0)

              #  ui.qimage_raw = QImage(image_data, 5184, 3456,  QImage.Format_RGB16)
                
                ui.qPixmapFileVar = QPixmap()
                
                #ui.qimage_raw.conv
                ui.qPixmapFileVar.load(file)         
                ui.qPixmapFileVar = ui.qPixmapFileVar.scaled(671, 481)
                ui.label_10.setPixmap(ui.qPixmapFileVar)        
                if self.isRun == False:
                    flag = 1
                    break
                loop = QEventLoop()
                time_interval = 2000
                QTimer.singleShot(time_interval, loop.quit) #시간간격 msec
                loop.exec_()     
            if flag == 1:
                break            


"""def make_slideshow(dial):
        # 이미지들을 읽어올 경로
    path = "C:/Python/time/"

        # 읽어온 파일들
    files = []
        #해당 path의 모든파일을 읽는것
    for r, d, f in os.walk(path):
        for file in f:
            if '.png' in file or '.jpg' in file or '.PNG' in file or '.JPG' in file:
                files.append(os.path.join(r, file))

        # 파일 리스트
    print(files)
    print(files[0])

        # 파일 이름 정렬
    files.sort()

    for file in files:      
        dial.qPixmapFileVar = QPixmap()
        dial.qPixmapFileVar.load(file)
            
        dial.qPixmapFileVar = dial.qPixmapFileVar.scaled(671, 481)
        dial.label_10.setPixmap(dial.qPixmapFileVar)        

        loop = QEventLoop()
        time_interval = 2000
        QTimer.singleShot(time_interval, loop.quit) #시간간격 msec
        loop.exec_()                 """


if __name__== "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    global ui
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

