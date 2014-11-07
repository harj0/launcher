#! /usr/bin/python
# -*- coding: utf-8 -*-
#########
#Copyright (C) 2014  Mark Spurgeon <markspurgeon96@hotmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#########
import os
import pickle
import platform 
import wnck
import dbus
import dbus.service
import dbus.mainloop.glib
import subprocess
import webbrowser
import gc
import imp
import sys
sys.dont_write_bytecode = True
import time
import math
#import Xlib
#import Xlib.display
from PyQt4 import QtGui,QtCore,QtWebKit
import Apps
import Config
import Window
import XlibStuff
import Files
import System
import DockAppsOptions
import Plugins
#########
########	
def getCurrentPluginModule(name):
	home=os.path.expanduser("~")
	pl_dir=os.path.join(home,".duck-plugins")
	if os.path.isfile(os.path.join(pl_dir,name,"plugin.py")):
		plugin =imp.load_source(str(name),os.path.join(pl_dir,name,"plugin.py"))
		return plugin
class Settings(QtCore.QThread):
	def __init__(self,parent=None):
		QtCore.QThread.__init__(self,parent)
		self.parent=parent
	def run(self):	
		subprocess.call(["python","/usr/lib/duck_settings/main.py"])
class Launch(QtCore.QThread):
	def __init__(self,parent=None):
		QtCore.QThread.__init__(self,parent)
		self.app=""
		self.parent=parent
	def run(self):
		exec_list=self.app.split(" ")
		subprocess.call(exec_list)
		QtGui.QApplication.processEvents()
##########
##########
class Launcher(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self,None,QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_X11NetWmWindowTypeDock)
		self.setWindowTitle("ducklauncher!!")#recognisable by wnck
		self.activateWindow()
		#screen size
		d = QtGui.QDesktopWidget()
		self.top_pos=0
		self.s_width = d.availableGeometry().width()
		self.s_height =d.availableGeometry().height()
		self.top_pos= d.availableGeometry().y()
		#bg_width
		#Config
		conf=Config.get()
		self.conf=conf
		self.HALF_OPEN_POS=int(conf['size'])
		self.ICO_TOP=self.HALF_OPEN_POS-5
		self.OPEN_STATE_TOP=self.ICO_TOP*4+5
		self.SIZE = 14
		#self.R=int(conf['r'])
		#self.G=int(conf['g'])
		#self.B=int(conf['b'])
		self.ICON_SIZE=int(conf['icon-size'])
		#Geometry
		self.setGeometry(0,self.top_pos,self.HALF_OPEN_POS+6,self.s_height)
		#Values
		self.apps_per_row = math.trunc(((self.s_width/3)-30)/self.ICON_SIZE)
		self.apps_per_col = math.trunc(((self.s_height)-30)/self.ICON_SIZE)
		self.apps_per_page=self.apps_per_col*self.apps_per_row
		self.app_page_state=0
		self.appRect=None		
		self.drawAppRect=False
		self.files_page_state=0
		self.Files = Files.getFiles()
		self.pos_x=self.HALF_OPEN_POS-2
		self.move=False
		self.current_state="half_open"
		self.activity="apps"
		self.dock_apps = Apps.find_info(self.conf['dock-apps'])	
		self.current_text=''
		self.allApps=Apps.info(self.current_text)
		self.plugin=False
		#Open windows window
		self.open_windows=Window.get_open_windows()
		self.open_win = Window.open_windows()
		#Dock Apps Options Window
		self.dock_options_win=DockAppsOptions.Window(parent=self)
		#Webview for plugins
		self.webview=QtWebKit.QWebView(self)
		palette = self.webview.palette()
		palette.setBrush(QtGui.QPalette.Base, QtCore.Qt.transparent)
		self.webview.page().setPalette(palette)
		self.webview.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
		self.webview.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		self.webview.connect(self.webview, QtCore.SIGNAL("linkClicked(const QUrl&)"), self.web_linkClicked)
		self.webview.page().mainFrame().javaScriptWindowObjectCleared.connect(self.web_populateJavaScriptWindowObject)
		self.webview.setHtml("<body style='background:rgb(230,100,80);'><input type='text' placehodler='aaa'></input></body>")
		self.webview.setGeometry(2,50,self.s_width/3-20,self.s_height-50)
		self.webview.activateWindow()
		self.webview.hide()
		#System window
		self.sys_win=System.Window()
		#Fake window
		self.fakewin = Fakewin(10,10, self)
		self.fakewin.show()
		XlibStuff.fix_window(self.winId(),self.HALF_OPEN_POS+5,0,0,0)
		#
	def paintEvent(self,e):

		qp=QtGui.QPainter(self)
		qp.fillRect(e.rect(), QtCore.Qt.transparent)
		qp.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
		####DRAW
		qp.setBrush(QtGui.QColor(int(self.conf['r2']),int(self.conf['g2']),int(self.conf['b2']),int(self.conf["alpha"])))
		qp.drawRect(0,0,self.pos_x+7,self.s_height)
		qp.setPen(QtGui.QPen(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])), 3, QtCore.Qt.SolidLine))
		qp.drawRect(self.pos_x+5,0,2,self.s_height)
		if self.current_state!="half_open":
			qp.setPen(QtGui.QPen(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b']),30), 2, QtCore.Qt.SolidLine))
			qp.drawLine(self.pos_x-14,0,self.pos_x-14,self.s_height)
		qp.setPen(QtGui.QPen(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])), 4, QtCore.Qt.SolidLine))
		qp.setBrush(QtGui.QBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b']))))
		r_s=2
		a=10
		r = QtCore.QRectF(self.pos_x-7,self.s_height/2-r_s/2,r_s,r_s)
		qp.drawEllipse(r)
		r = QtCore.QRectF(self.pos_x-7,self.s_height/2-a-r_s/2,r_s,r_s)
		qp.drawEllipse(r)
		r = QtCore.QRectF(self.pos_x-7,self.s_height/2+a-r_s/2,r_s,r_s)
		qp.drawEllipse(r)
		##
		###
		if self.current_state == "half_open":
			qp.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0),1,QtCore.Qt.SolidLine))
			qp.setBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])))
			qp.drawRect(0,0,self.pos_x+7,self.OPEN_STATE_TOP)
			rect = QtCore.QRectF(50,0,150,50)
			####DRAW BUTTONS
			###Apps
			ICO_TOP=self.HALF_OPEN_POS-5
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/apps.svg")
			icon.paint(qp,5,ICO_TOP*0+5,ICO_TOP,ICO_TOP-6)
			#Files
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/file.svg")
			##temp_file
			icon.paint(qp,5,ICO_TOP*1+5,ICO_TOP,ICO_TOP-6)
			#Settings
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/settings.svg")
			icon.paint(qp,5,ICO_TOP*2+5,ICO_TOP,ICO_TOP-6)
			#Star
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/star.svg")
			icon.paint(qp,5,ICO_TOP*3+5,ICO_TOP,ICO_TOP-6)
			#####
			#Dock Apps
			for i,a in enumerate(self.dock_apps):
				try:
				####OFF WE GOOO!
					ico = Apps.ico_from_name(str(a['icon']))
					if ico!=None:
						ico.paint(qp,6,self.OPEN_STATE_TOP+ICO_TOP*i+10,ICO_TOP-5,ICO_TOP-5)
				except KeyError:
					print("[Duck Launcher] Error: Some apps could not be found ")
			
			#Open Windows Button
			qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 2, QtCore.Qt.SolidLine))
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/open-apps.svg")
			#icon = QtGui.QIcon("test-1.svg")
			icon.paint(qp,10,self.s_height-ICO_TOP*2-10,ICO_TOP-10,ICO_TOP-10)
			#rect = QtCore.QRectF(10,self.s_height-ICO_TOP*2-10,ICO_TOP-10,ICO_TOP-10)
			#qp.setFont(QtGui.QFont(self.conf["font"],self.HALF_OPEN_POS/3))
			#qp.drawText(rect, QtCore.Qt.AlignCenter, str(len(self.open_windows)))
			#System button
			icon = QtGui.QIcon("/usr/share/duck-launcher/icons/sys.svg")
			icon.paint(qp,10,self.s_height-self.HALF_OPEN_POS+8,self.HALF_OPEN_POS-15,self.HALF_OPEN_POS-15)
		##
		##
		if self.current_state=="open":
			close=QtGui.QIcon("/usr/share/duck-launcher/icons/remove.svg")
			close.paint(qp,self.pos_x-13,self.s_height-13,13,13)
			if self.activity=="apps":
				#Current Text
				qp.setPen(QtCore.Qt.NoPen)
				qp.setFont(QtGui.QFont(self.conf["font"],10))
				t_rect=QtCore.QRectF(20,20,self.s_width-36,20)
				if self.current_text=='':
					self.plugin=False
					qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 2, QtCore.Qt.SolidLine))
					qp.drawText(t_rect, QtCore.Qt.AlignLeft, "Type to search")
				else:
					if "#" in self.current_text.split(" ")[0]:
						plugins_list=[]						
						for p in Plugins.get_plugin_names():
							if str(self.current_text.split(" ")[0]).lower().replace("#","") in p:
								plugins_list.append(p)
						if plugins_list:
							what_in_text=str(self.current_text.split(" ")[0].replace("#","")).lower()
							query_name=plugins_list[0]
							fm=QtGui.QFontMetrics(QtGui.QFont(self.conf["font"],10))
							whole_width=0						
							for i,s in enumerate("#{}".format(query_name)):
								w = int(fm.charWidth("#{}".format(query_name),i))
								whole_width+=w
							if query_name==what_in_text:
								qp.setBrush(QtGui.QColor(int(self.conf["r"]),int(self.conf["g"]),int(self.conf["b"]),150))
								qp.drawRoundedRect(QtCore.QRectF(19,18,whole_width+4,20), 2,2)
							else:pass
							qp.setPen(QtGui.QPen(QtGui.QColor(255,255,255), 2, QtCore.Qt.SolidLine))
							qp.drawText(t_rect, QtCore.Qt.AlignLeft,self.current_text)
						else:
							qp.setPen(QtGui.QPen(QtGui.QColor(255,255,255), 2, QtCore.Qt.SolidLine))
							qp.drawText(t_rect, QtCore.Qt.AlignLeft,self.current_text)
					else:
						self.plugin=False
						qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 2, QtCore.Qt.SolidLine))
						qp.drawText(t_rect, QtCore.Qt.AlignLeft, self.current_text)
				max_apps=  math.trunc((len(self.allApps)-1)/self.apps_per_page)+1
				#Page
				if self.plugin==False:
					for i in range(0, max_apps):
							btn_size = 20
							x_pos = self.s_width/6-btn_size+(btn_size*i)
							rect = QtCore.QRectF(x_pos,2,btn_size,btn_size)
							if self.app_page_state==i:
								qp.setBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])))
							else:
								qp.setBrush(QtGui.QColor(100,100,100,60))
							qp.setPen(QtGui.QPen(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b']),100), 2, QtCore.Qt.SolidLine))
							qp.drawRect(rect)
							qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 2, QtCore.Qt.SolidLine))
							qp.drawText(rect,QtCore.Qt.AlignCenter,str(i+1))
					###app_buttons
					for i, app in enumerate(self.allApps):
							app_page = math.trunc(i/self.apps_per_page)
							if app_page==self.app_page_state:
								qp.setBrush(QtGui.QColor(int(self.conf['r2']),int(self.conf['g2']),int(self.conf['b2'])))
								row_pos = math.trunc(i/self.apps_per_row)
								x_pos = self.ICON_SIZE*(i-(row_pos*self.apps_per_row))+30
								y_pos = row_pos*self.ICON_SIZE+30-(app_page*(self.ICON_SIZE*self.apps_per_col))
								try:
									ico=Apps.ico_from_name(app["icon"])
									if ico!=None:
										Apps.ico_from_name(app["icon"]).paint(qp,x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
									else:
										i = QtGui.QIcon('/usr/share/duck-launcher/icons/apps.svg')
										i.paint(qp,x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
									
								except KeyError:
									i = QtGui.QIcon('/usr/share/duck-launcher/icons/apps.svg')
									i.paint(qp,x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
								qp.setPen(QtGui.QColor(250,250,250))
								text_rect = QtCore.QRectF(x_pos+5,y_pos+self.ICON_SIZE-10,self.ICON_SIZE-10,60)
								#qp.drawRect(text_rect)
								qp.setFont(QtGui.QFont(self.conf["font"],8))
								qp.drawText(text_rect,QtCore.Qt.TextWordWrap |QtCore.Qt.AlignHCenter,self.tr(app["name"]).replace(u"Â", ""))
			###
			if self.activity=="files":
				#Buttons
				#¼b1_rect=QtCore.QRectF(10,10,30,30)
				ico = QtGui.QIcon("/usr/share/duck-launcher/icons/home.svg")
				ico.paint(qp,self.s_width/3-40-self.SIZE,10,25,25)
				ico2 = QtGui.QIcon("/usr/share/duck-launcher/icons/back.svg")
				ico2.paint(qp,self.s_width/3-80-self.SIZE,10,25,25)
				max_files=  math.trunc(len(self.Files.all())/self.apps_per_page)+1
				for i in range(0, max_files):
						btn_size = 20
						x_pos = self.s_width/6-btn_size+(btn_size*i)
						rect = QtCore.QRectF(x_pos,2,btn_size,btn_size)
						if self.files_page_state==i:
							qp.setBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])))
						else:
							qp.setBrush(QtGui.QColor(100,100,100,100))
						qp.setPen(QtGui.QPen(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b']),100), 2, QtCore.Qt.SolidLine))
						qp.drawRect(rect)
						qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 2, QtCore.Qt.SolidLine))
						qp.setFont(QtGui.QFont(self.conf["font"],10))
						qp.drawText(rect,QtCore.Qt.TextWordWrap |QtCore.Qt.AlignHCenter,str(i+1))
				#Text
				t_rect=QtCore.QRectF(10,10,self.s_width/8,30)
				qp.drawText(t_rect,QtCore.Qt.AlignRight,self.Files.directory.replace(u"Â", ""))
				###app_buttons
				for i, f in enumerate(self.Files.all()):
						app_page = math.trunc(i/self.apps_per_page)
						if app_page==self.files_page_state:
							qp.setBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])))
							row_pos = math.trunc(i/self.apps_per_row)
							x_pos = self.ICON_SIZE*(i-(row_pos*self.apps_per_row))+30
							y_pos = row_pos*self.ICON_SIZE+30-(app_page*(self.ICON_SIZE*self.apps_per_col))
							try:
								if f["type"]=="directory":
									da_icon=QtGui.QIcon("/usr/share/duck-launcher/icons/folder.svg")
									da_icon.paint(qp,x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
								if f["type"]=="file":
									da_icon=Files.getFileIcon(f["whole_path"])
									da_icon.paint(qp,x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
							except KeyError:
								i = QtGui.QImage('images/apps.png')
								rect= QtCore.QRectF(x_pos+20,y_pos+20,self.ICON_SIZE-40,self.ICON_SIZE-40)
								qp.drawImage(rect,i)
							qp.setPen(QtGui.QColor(250,250,250))
							text_rect = QtCore.QRectF(x_pos-5,y_pos+self.ICON_SIZE-20,self.ICON_SIZE,30)
							qp.setFont(QtGui.QFont(self.conf["font"],8))
							qp.drawText(text_rect,QtCore.Qt.AlignCenter,f["name"].replace(u"Â", ""))
			if self.activity=="star" :
				qp.setPen(QtGui.QPen(QtGui.QColor(250,250,250), 3, QtCore.Qt.SolidLine))
				all_rows=0
				blocks_l=pickle.loads(Config.get()["blocks"])
				for i,b in enumerate(blocks_l):
					all_stuff = Config.get_from_block(b)
					if len(all_stuff)!=self.apps_per_row:
						row_num = math.trunc(len(all_stuff)/self.apps_per_row)+1
					else:
						row_num = math.trunc(len(all_stuff)/self.apps_per_row)
					h=self.ICON_SIZE*all_rows+i*50
					all_rows+=row_num
					qp.setFont(QtGui.QFont(self.conf["font"],8))
					for j, thing in enumerate(all_stuff):
						#same thing as for the apps
						row_pos = math.trunc(j/self.apps_per_row)
						x_pos = self.ICON_SIZE*(j-(row_pos*self.apps_per_row))+40
						y_pos = (row_pos*self.ICON_SIZE+20)+h+30
						if thing['type']=='app':
							icon = Apps.ico_from_app(thing['value'])
							to_write=thing['value']
						elif thing['type']=='directory':
							icon = QtGui.QIcon('/usr/share/duck-launcher/icons/folder.svg')
							splitted = thing['value'].split('/')
							to_write =  splitted[-1]
						elif thing['type']=='file':
							icon = QtGui.QIcon('/usr/share/duck-launcher/icons/file.svg')
							splitted = thing['value'].split('/')
							to_write =  splitted[-1]
						if icon!=None:
							icon.paint(qp, x_pos+15,y_pos+15, self.ICON_SIZE-50,self.ICON_SIZE-50)
							rect = QtCore.QRectF(x_pos-10, y_pos+self.ICON_SIZE-30, self.ICON_SIZE, 30)
							qp.drawText(rect,QtCore.Qt.TextWordWrap |QtCore.Qt.AlignHCenter,to_write)
					#Title
					qp.setPen(QtGui.QColor(0,0,0,0))
					qp.setBrush(QtGui.QColor(int(self.conf['r']),int(self.conf['g']),int(self.conf['b'])))
					qp.drawRect(18, h+40,self.s_width/6,2)
					qp.setPen(QtGui.QColor(250,250,250))
					qp.setFont(QtGui.QFont(self.conf["font"],16))
					if isinstance(b["name"],list):
						b["name"]="".join(b["name"])
					qp.drawText(QtCore.QRectF(20, h+10,self.s_width/3,200),b['name'])
		#Draw rect under clicked app
		if self.drawAppRect==True and self.appRect!=None:
			qp.setPen(QtGui.QPen(QtGui.QColor(0,0,0,0),1,QtCore.Qt.SolidLine))
			qp.setBrush(QtGui.QColor(252,252,255,40))
			qp.drawRoundedRect(self.appRect,2,2)
	def mouseMoveEvent(self,e):
		self.mousePressEvent(e)
		if e.x()>(self.pos_x-self.SIZE-5):
			if self.current_state=="half_open" and self.s_height/2-20<e.y()<self.s_height/2+20 :
				self.move=True
			if self.current_state=="open":
				self.move=True
		if self.move==True:
			self.webview.hide()
			self.current_state="nothing"
			self.update_pos(e.x())
		#repeat same as press event
	def mousePressEvent(self,e):
		x_m,y_m = e.x(),e.y()

		self.drawAppRect=False
		if self.current_state=="half_open":
			if 0<x_m<self.HALF_OPEN_POS:
				if y_m<self.ICO_TOP:
					self.appRect=QtCore.QRectF(0,2, self.HALF_OPEN_POS+4,self.ICO_TOP+3)
					self.drawAppRect=True
				if self.ICO_TOP<y_m<self.ICO_TOP*2:
					self.appRect=QtCore.QRectF(0,self.ICO_TOP+2, self.HALF_OPEN_POS+4,self.ICO_TOP+3)
					self.drawAppRect=True
				if self.ICO_TOP*2<y_m<self.ICO_TOP*3:
					self.appRect=QtCore.QRectF(0,self.ICO_TOP*2+2, self.HALF_OPEN_POS+4,self.ICO_TOP+3)
					self.drawAppRect=True
				if self.ICO_TOP*3<y_m<self.ICO_TOP*4:
					self.appRect=QtCore.QRectF(0,self.ICO_TOP*3+2, self.HALF_OPEN_POS+4,self.ICO_TOP+3)
					self.drawAppRect=True
			try:
				for i,a in enumerate(self.dock_apps):
					if self.OPEN_STATE_TOP+self.ICO_TOP*i+10<y_m<self.OPEN_STATE_TOP+self.ICO_TOP*(i+1)+10:
						self.appRect=QtCore.QRectF(0, self.OPEN_STATE_TOP+self.ICO_TOP*i+7, self.HALF_OPEN_POS+1,self.ICO_TOP)
						self.drawAppRect=True
			except KeyError:
				pass
			#
			if self.s_height-self.HALF_OPEN_POS-5<y_m:
				self.appRect=QtCore.QRectF(0,self.s_height-self.HALF_OPEN_POS,self.HALF_OPEN_POS+1,self.HALF_OPEN_POS)
				self.drawAppRect=True
			if  self.s_height-self.HALF_OPEN_POS*2<y_m<self.s_height-self.HALF_OPEN_POS-5:
				self.appRect=QtCore.QRectF(0,self.s_height-self.HALF_OPEN_POS*2-8,self.HALF_OPEN_POS+1,self.HALF_OPEN_POS+1)
				self.drawAppRect=True
		elif self.current_state=="open" and self.activity=="apps" and self.plugin==False:
			for i, app in enumerate(self.allApps):
				app_page = math.trunc(i/self.apps_per_page)
				if app_page==self.app_page_state:
					row_pos = math.trunc(i/self.apps_per_row)
					x_pos = self.ICON_SIZE*(i-(row_pos*self.apps_per_row))+30
					y_pos = row_pos*self.ICON_SIZE+30-(app_page*(self.ICON_SIZE*self.apps_per_col))
					if x_pos<x_m<x_pos+self.ICON_SIZE and y_pos<y_m<y_pos+self.ICON_SIZE:
						self.appRect=QtCore.QRectF(x_pos,y_pos+10, self.ICON_SIZE,self.ICON_SIZE)
						self.drawAppRect=True
		elif self.current_state=="open" and self.activity=="star":
			blocks=pickle.loads(Config.get()["blocks"])
			all_rows=0
			for i,b in enumerate(blocks):
				all_stuff = Config.get_from_block(b)
				if len(all_stuff)!=self.apps_per_row:
					row_num = math.trunc(len(all_stuff)/self.apps_per_row)+1
				else:
					row_num = math.trunc(len(all_stuff)/self.apps_per_row)
				h=self.ICON_SIZE*all_rows+i*50
				all_rows+=row_num
				for j, thing in enumerate(all_stuff):
					row_pos = math.trunc(j/self.apps_per_row)
					x_pos = self.ICON_SIZE*(j-(row_pos*self.apps_per_row))+40
					y_pos = (row_pos*self.ICON_SIZE+20)+h+30
					if x_pos-10<x_m<x_pos-10+self.ICON_SIZE and y_pos<y_m<y_pos+self.ICON_SIZE and x_m<self.pos_x-self.SIZE-3:
						self.appRect=QtCore.QRectF(x_pos-10,y_pos,self.ICON_SIZE,self.ICON_SIZE)						
						self.drawAppRect=True
		self.update()
	def mouseReleaseEvent(self,e):
		x_m,y_m = e.x(),e.y()
		self.drawAppRect=False
		Window.activateFakewin(self.fakewin.winId())
		#While moving
		if self.current_state=="nothing":
			if self.plugin==False:
				self.webview.hide()	
			
			self.move=False
			###sets position to right one
			pos_list = [self.HALF_OPEN_POS, self.s_width/3]
			closest = min(pos_list, key=lambda x: abs(x-self.pos_x))
			if closest<self.pos_x:
				while closest<self.pos_x:
					self.pos_x-=5
					self.setGeometry(0,self.top_pos,self.pos_x+7,self.s_height)
					QtGui.QApplication.processEvents()
					self.update()
				self.pos_x=closest
				QtGui.QApplication.processEvents()
				self.update()
			elif closest>self.pos_x:
				while closest>self.pos_x:
					self.pos_x+=5
					self.setGeometry(0,self.top_pos,self.pos_x+7,self.s_height)
					QtGui.QApplication.processEvents()
					self.update()
				self.pos_x=closest
				QtGui.QApplication.processEvents()
				self.update()
			##set the current state
			if self.pos_x==self.HALF_OPEN_POS:
				self.pos_x-=3
				self.current_state="half_open"
				self.update_all(self.conf)
			elif self.pos_x==self.s_width/3:
				self.pos_x-=3
				self.current_state="open"
			else: self.current_state="nothing"
			if self.plugin==True and self.current_state=='open' and self.activity=='apps':
				self.webview.show()
		#Events
		#
		elif self.current_state=="open":
			if self.pos_x-14<x_m<self.pos_x and self.move==False and e.button()==QtCore.Qt.LeftButton:
				self.close_it()
				if y_m>self.s_height-13:
					print("[Duck Launcher] Saving configuration.")
					Config.check_dict(self.conf)
					QtGui.QApplication.processEvents()
					print("[Duck Launcher] Quitting, Good Bye!")
					QtGui.qApp.quit()
			###app events
			if self.activity == "apps" and self.plugin==False:

				max_apps=  math.trunc((len(self.allApps)-1)/self.apps_per_page)+1
				##Change Page
				for i in range(0,max_apps):
						btn_size = 20
						x_pos = self.s_width/6-btn_size+(btn_size*i)
						if x_pos<x_m<x_pos+btn_size and 2<y_m<2+btn_size:
							self.app_page_state=i
							self.update()
							QtGui.QApplication.processEvents()
				## launch apps
				for i, app in enumerate(self.allApps):
					app_page = math.trunc(i/self.apps_per_page)
					if app_page==self.app_page_state:
						row_pos = math.trunc(i/self.apps_per_row)
						x_pos = self.ICON_SIZE*(i-(row_pos*self.apps_per_row))+30
						y_pos = row_pos*self.ICON_SIZE+30-(app_page*(self.ICON_SIZE*self.apps_per_col))
						if x_pos<x_m<(x_pos+self.ICON_SIZE) and y_pos<y_m<(y_pos+self.ICON_SIZE) and x_m<self.pos_x-self.SIZE-3:
							if e.button()==QtCore.Qt.LeftButton:
								print("[Duck Launcher] Launching '{0}' with '{1}'".format(app["name"],app["exec"]) )
								thread = Launch(parent=self)
								thread.app=app["exec"]
								thread.start()
								self.close_it()
			elif self.activity==False and self.plugin==True:
				self.webview.show()
			elif self.activity == "files":
				if self.s_width/3-80-self.SIZE<x_m<self.s_width/3-50-self.SIZE and 10<y_m<30:
					l= self.Files.directory.split("/")[:-1][1:]
					new_dir=''
					for a in l:
						new_dir+='/'
						new_dir+=a
					if new_dir=='':new_dir='/'
					self.files_page_state=0
					self.Files.directory=new_dir
					self.update()
				if self.s_width/3-54<x_m<self.s_width/3-14 and 10<y_m<30:
					self.Files.directory = self.Files.default
					self.files_page_state=0
					self.update()
				max_files=  math.trunc(len(self.Files.all())/self.apps_per_page)+1
				##Change Page
				for i in range(0,max_files):
						btn_size = 20
						x_pos = self.s_width/6-btn_size+(btn_size*i)
						if x_pos<x_m<x_pos+btn_size and 2<y_m<2+btn_size:
							self.files_page_state=i
							self.update()
							QtGui.QApplication.processEvents()
				## launch apps
				for i, f in enumerate(self.Files.all()):
					app_page = math.trunc(i/self.apps_per_page)
					if app_page==self.files_page_state:
						row_pos = math.trunc(i/self.apps_per_row)
						x_pos = self.ICON_SIZE*(i-(row_pos*self.apps_per_row))+30
						y_pos = row_pos*self.ICON_SIZE+30-(app_page*(self.ICON_SIZE*self.apps_per_col))
						if x_pos<x_m<(x_pos+self.ICON_SIZE) and y_pos<y_m<(y_pos+self.ICON_SIZE) and x_m<self.pos_x-self.SIZE-3:
							if e.button()==QtCore.Qt.LeftButton:
								if f["type"]=="file":
									import webbrowser
									webbrowser.open(f["whole_path"])
								elif  f["type"]=="directory":
									self.Files.directory=f["whole_path"]
									self.update()
									QtGui.QApplication.processEvents()
			elif self.activity=="star":
				blocks=pickle.loads(Config.get()["blocks"])
				all_rows=0
				for i,b in enumerate(blocks):
					all_stuff = Config.get_from_block(b)
					if len(all_stuff)!=self.apps_per_row:
						row_num = math.trunc(len(all_stuff)/self.apps_per_row)+1
					else:
						row_num = math.trunc(len(all_stuff)/self.apps_per_row)
					h=self.ICON_SIZE*all_rows+i*50
					all_rows+=row_num
					for j, thing in enumerate(all_stuff):
						row_pos = math.trunc(j/self.apps_per_row)
						x_pos = self.ICON_SIZE*(j-(row_pos*self.apps_per_row))+40
						y_pos = (row_pos*self.ICON_SIZE+20)+h+30
						if x_pos-10<x_m<x_pos-10+self.ICON_SIZE and y_pos<y_m<y_pos+self.ICON_SIZE and x_m<self.pos_x-self.SIZE-3:
							if e.button()==QtCore.Qt.LeftButton:
								if thing['type']=='app':
									the_exec=""
									for a in Apps.info(''):
										if thing['value'] in a['name']:
											the_exec=a['exec']
									thread = Launch(parent=self)
									thread.app=the_exec
									thread.start()
									print("[Duck Launcher] Launching '{0}' with '{1}'".format(thing["value"], the_exec) )
								else:
									import webbrowser
									webbrowser.open(thing['value'])
		elif self.current_state=="half_open":
			##buttons
			if self.pos_x-self.SIZE<x_m<self.pos_x and self.move==False and self.s_height/2-20<y_m<self.s_height/2+20:
				self.activity="apps"
				self.current_text=""
				self.open_it()
			if 0<x_m<self.HALF_OPEN_POS:
				if e.button()==QtCore.Qt.LeftButton:
					print self.ICO_TOP
					if y_m<self.ICO_TOP:
						self.activity="apps"
						self.current_text=''
						self.open_it()
					if self.ICO_TOP<y_m<self.ICO_TOP*2:
						import webbrowser
						HOME=os.path.expanduser("~")
						webbrowser.open(HOME)
						#self.activity="files"
						#self.Files.directory=self.Files.default
						#self.files_page_state=0
						#self.open_it()
					if self.ICO_TOP*2<y_m<self.ICO_TOP*3:
						self.activity="settings"
						Settings(parent=self).start()
					if self.ICO_TOP*3<y_m<self.ICO_TOP*4:
						self.activity="star"
						self.open_it()
				try:
					for i,a in enumerate(self.dock_apps):
						if self.OPEN_STATE_TOP+self.ICO_TOP*i+10<y_m<self.OPEN_STATE_TOP+self.ICO_TOP*(i+1)+10:
							if e.button()==QtCore.Qt.LeftButton:
								print("[Duck Launcher] Launching '{0}' with '{1}'".format(a["name"], a["exec"]) )
								thread = Launch(parent=self)
								thread.app=a["exec"]
								thread.start()
								self.dock_options_win.close()
							elif e.button()==QtCore.Qt.RightButton:
								#LaunchOption(y_pos, app_dict
								if self.dock_options_win.isHidden() or self.dock_options_win.app["name"]!=a["name"]:
									self.dock_options_win.update_all(self.conf)
									self.dock_options_win.setTopPosition(self.OPEN_STATE_TOP+self.ICO_TOP*i+10)
									self.dock_options_win.setApp(a)
									self.dock_options_win.updateWidth()
									self.dock_options_win.show()
								else:
									self.dock_options_win.close()
				except KeyError:
					pass
				if  self.s_height-self.HALF_OPEN_POS*2<y_m<self.s_height-self.HALF_OPEN_POS-5:
					##open windows
					self.sys_win.close()
					if self.open_win.isHidden():
						if len(self.open_windows)>0:
							self.open_win.updateApps()
							self.open_win.show()
						else:pass
					elif self.open_win.isHidden()==False:
						self.open_win.close()
				if  self.s_height-self.HALF_OPEN_POS-5<y_m:
					if self.sys_win.isHidden():
						self.open_win.close()
						self.sys_win.show()
					elif self.sys_win.isHidden()==False:
						self.sys_win.close()
		self.update()	
	def wheelEvent(self,e):
		Window.activateFakewin(self.fakewin.winId())
		if self.activity == 'apps':
			value= int(e.delta()/120)
			max_pages=math.trunc((len(self.allApps)-1)/self.apps_per_page)
			if value>0 and self.app_page_state>0:
				self.app_page_state-=1
			if value<0 and self.app_page_state<max_pages:
				self.app_page_state+=1
			self.update()
			QtGui.QApplication.processEvents()
		if self.activity == 'files':
			value= int(e.delta()/120)
			max_pages=math.trunc(len(self.Files.all())/self.apps_per_page)
			if value>0 and self.files_page_state>0:
				self.files_page_state-=1
			if value<0 and self.files_page_state<max_pages:
				self.files_page_state+=1
			self.update()
			QtGui.QApplication.processEvents()
	###ANIMATIONS
	def update_pos(self,pos):
		if pos>4 and pos<self.s_width/3+100:
			self.pos_x=pos
			self.setGeometry(0,self.top_pos,self.pos_x+self.SIZE/2,self.s_height)
			self.update()
			QtGui.QApplication.processEvents()
	def open_it(self):
		Window.activateFakewin(self.fakewin.winId())
		self.plugin=False
		self.sys_win.close()
		self.open_win.close()
		self.dock_options_win.close()
		while self.pos_x<self.s_width/3-5:
			self.current_state='nothing'
			if self.pos_x<self.s_width/7:
				self.pos_x=self.s_width/7
			else:
				self.pos_x+=float(self.conf["animation-speed"])
			self.setGeometry(0,self.top_pos,self.s_width/3+5,self.s_height)
			self.update()
			QtGui.QApplication.processEvents()
		if self.pos_x!=self.s_width/3-2 :
			self.pos_x=self.s_width/3-2
		self.current_state="open"
		if self.activity=="apps":
			self.allApps=Apps.info(self.current_text)
		self.update()
		QtGui.QApplication.processEvents()
	def close_it(self):
		self.webview.hide()
		while self.pos_x>self.HALF_OPEN_POS:
			#old_pos=self.pos_x
			if self.pos_x<self.s_width/10:
				self.pos_x-=float(self.conf["animation-speed"])/4
			else:
				if self.pos_x>self.s_width/4:
					self.pos_x=self.s_width/4
				else:
					self.pos_x-=float(self.conf["animation-speed"])
			self.current_state="nothing"
			self.update()
			QtGui.QApplication.processEvents()
		if self.pos_x!=self.HALF_OPEN_POS-2:
			self.pos_x=self.HALF_OPEN_POS-2
		self.current_state="half_open"
		self.setAttribute(QtCore.Qt.WA_X11NetWmWindowTypeDock,True)
		self.setGeometry(0,self.top_pos,self.pos_x+self.SIZE/2,self.s_height)
		self.update()
		QtGui.QApplication.processEvents()
	def updateOpenWindows(self):
		self.open_windows=Window.get_open_windows()
		try:
			if self.conf["size"]!=self.HALF_OPEN_POS:
				XlibStuff.fix_window(self.winId(),self.HALF_OPEN_POS+5,0,0,0)
		except:
			pass
		self.update()
		QtGui.QApplication.processEvents()
		Config.check_dict(self.conf)
	def update_all(self,conf):
		self.conf=conf
		if self.HALF_OPEN_POS!=int(conf["size"]):
			self.HALF_OPEN_POS=int(conf['size'])
			self.current_state="half_open"
			self.pos_x=int(conf["size"])
			self.setGeometry(0,self.top_pos,self.HALF_OPEN_POS+6,self.s_height)
			self.ICO_TOP=self.HALF_OPEN_POS-5
			self.OPEN_STATE_TOP=self.ICO_TOP*4+5
		elif self.ICON_SIZE!=int(conf['icon-size']):
			self.ICON_SIZE=int(conf['icon-size'])
			self.apps_per_row = math.trunc(((self.s_width/3)-30)/self.ICON_SIZE)
			self.apps_per_col = math.trunc(((self.s_height)-30)/self.ICON_SIZE)
			self.apps_per_page=self.apps_per_col*self.apps_per_row
		
		if self.conf["blocks"]==None:
			self.conf["blocks"]=[]
		if self.conf["dock-apps"]==None:
			self.conf["dock-apps"]=[]
		
		self.dock_apps = Apps.find_info(self.conf['dock-apps'])
		self.open_win.update_all(conf)
		self.sys_win.update_all(conf)
		self.dock_options_win.update_all(conf)
		self.update()
		QtGui.QApplication.processEvents()

	#
	def web_linkClicked(self, url):
		str_url=str(url.toString())
		if "%TERMINAL%" in str_url:
			command=str_url.split("%TERMINAL%")
			command = [a for a in command if "file://" not in a]
			command= command[0].split(" ")
			command=[a for a in command if a ]
			t=LaunchCommand(parent=self,call=command)
			t.start()
		else:
			webbrowser.open(str(url.toString()))
	def web_populateJavaScriptWindowObject(self):
		self.webview.page().mainFrame().addToJavaScriptWindowObject('Duck', self)
	@QtCore.pyqtSlot()
	def submitForm(self):
		elements=[]
		for e in self.webview.page().mainFrame().findAllElements("*"):
			el={}
			el["type"] = str(e.localName())
			if e.hasAttribute("id"):
				el["id"]=str(e.attribute("id"))
			if e.hasAttribute("name"):
				el["name"]=str(e.attribute("name"))
			val= e.evaluateJavaScript('this.value').toPyObject()
			if val!=None:
				el["value"]=val
			elements.append(el)


		if "#" in self.current_text.split(" ")[0]:
			plugins_list=[]						
			for p in Plugins.get_plugin_names():
				if str(self.current_text.split(" ")[0]).lower().replace("#","") in p:
					plugins_list.append(p)
			if plugins_list:
				plugin_name=plugins_list[0]
				pl=getCurrentPluginModule(plugin_name)
				try:
					pl.onFormSubmit(elements)
				except:
					print("[Duck Launcher] No 'onFormSubmit()' method present in the plugin.")
	@QtCore.pyqtSlot(str,str)
	def sendData(self, thing, value):
		print "data : " , thing, value
		if "#" in self.current_text.split(" ")[0]:
			plugins_list=[]						
			for p in Plugins.get_plugin_names():
				if str(self.current_text.split(" ")[0]).lower().replace("#","") in p:
					plugins_list.append(p)
			if plugins_list:
				plugin_name=plugins_list[0]	
				pl=getCurrentPluginModule(plugin_name)
				try:
					pl.onDataSent(thing, value)
				except:
					print("[Duck Launcher] No 'onDataSent()' method present in the plugin.")
class Fakewin(QtGui.QMainWindow):
	def __init__(self,width,height,parent):
		QtGui.QMainWindow.__init__(self, None,QtCore.Qt.WindowStaysOnBottomHint|QtCore.Qt.FramelessWindowHint)
		
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setWindowTitle("ducklauncher!!!")
		self.setGeometry(0,0,width,height)
		self.parent=parent
		##
		self.timer=QtCore.QTimer()
		self.timer.setInterval(6000)
		self.timer.start()
		self.timer.timeout.connect(self.parent.updateOpenWindows)
	def keyPressEvent(self, e):
		if e.key()==QtCore.Qt.Key_Backspace:
			if self.parent.plugin==False:
				self.parent.current_text=self.parent.current_text[:-1]
				self.parent.app_page_state=0

		elif e.key()==QtCore.Qt.Key_Return:
			if len(self.parent.allApps)==1:
				a=self.parent.allApps[0]
				print("[Duck Launcher] Launching '{0}' with '{1}'".format(a["name"], a["exec"]) )
				thread = Launch(parent=self.parent)
				thread.app=a["exec"]
				thread.start()
				self.parent.close_it()
				self.parent.current_text=''
				self.parent.allApps=Apps.find_info('')	

			html= Plugins.get(str(self.parent.current_text),color=(self.parent.conf["r"],self.parent.conf["g"],self.parent.conf["b"]),font=self.parent.conf["font"])
			if html!=None:
				self.parent.webview.load(QtCore.QUrl(html))
				self.parent.webview.show()
				self.parent.plugin=True
				self.parent.webview.page().mainFrame().setFocus()
				self.parent.setAttribute(QtCore.Qt.WA_X11NetWmWindowTypeDock,False)
				self.update()
		elif e.key()==16777216:
			self.parent.current_text=""
			self.parent.app_page_state=0
			self.parent.webview.hide()
		elif e.text()!='':
			self.parent.current_text+=e.text()
			self.parent.app_page_state=0
		else:
			if e.key()==16777250:
				if self.parent.current_state=="half_open":
					self.parent.activity="apps"
					self.parent.current_text=''
					self.parent.open_it()
				elif self.parent.current_state=="open":
					self.parent.close_it()
			elif e.key()==16777236:
				if self.parent.activity=="apps":
					max_pages=math.trunc(len(self.parent.allApps)/self.parent.apps_per_page)
					if max_pages>self.parent.app_page_state:
						self.parent.app_page_state+=1
				if self.parent.activity=="files":
					max_pages=math.trunc(len(self.parent.Files.all())/self.parent.apps_per_page)
					if max_pages>self.parent.files_page_state:
						self.parent.files_page_state+=1
			elif e.key()==16777234:
				if self.parent.activity=="apps":
					max_pages=math.trunc(len(self.parent.allApps)/self.parent.apps_per_page)
					if self.parent.app_page_state>0:
						self.parent.app_page_state-=1
				if self.parent.activity=="files":
					max_pages=math.trunc(len(self.parent.Files.all())/self.parent.apps_per_page)
					if self.parent.files_page_state>0:
						self.parent.files_page_state-=1
		self.parent.allApps=Apps.info(str(self.parent.current_text))
		self.parent.update()
	def quitApp(self):
		print "quit"

class DBusWidget(dbus.service.Object):
	def __init__(self,parent, name, session):
		# export this object to dbus
		self.parent=parent
		self.conf=Config.get()
		dbus.service.Object.__init__(self, name, session)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getR1(self):
		return int(self.conf["r"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getG1(self):
		return int(self.conf["g"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getB1(self):
		return int(self.conf["b"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getR2(self):
		return int(self.conf["r2"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getG2(self):
		return int(self.conf["g2"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getB2(self):
		return int(self.conf["b2"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getAlpha(self):
		return int(self.conf["alpha"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getIconSize(self):
		return int(self.conf["icon-size"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getLauncherWidth(self):
		return int(self.conf["size"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='i')
	def getAnimationSpeed(self):
		return float(self.conf["animation-speed"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='s')
	def getFont(self):
		return self.conf["font"]
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='v')
	def getDockApps(self):
		print "h"
		return list(self.conf["dock-apps"])
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='v')
	def getBlocks(self):
		return self.conf["blocks"]
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='s')
	def getInit(self):
		return self.conf["init-manager"]
	####SET
	@dbus.service.method("org.duck.Launcher", in_signature='',out_signature="")
	def setR1(self,v):
		self.conf["r"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setG1(self,v):
		self.conf["g"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setB1(self,v):
		self.conf["b"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setR2(self,v):
		self.conf["r2"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setG2(self,v):
		self.conf["g2"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setB2(self,v):
		self.conf["b2"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setAlpha(self,v):
		self.conf["alpha"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setIconSize(self,v):
		self.conf["icon-size"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setLauncherWidth(self,v):
		self.conf["size"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setAnimationSpeed(self,v):
		self.conf["animation-speed"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setFont(self,v):
		self.conf["font"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setDockApps(self,v):
		self.conf["dock-apps"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setBlocks(self,v):
		self.conf["blocks"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def setInit(self,v):
		self.conf["init-manager"]=v
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def update(self):
		self.parent.update_all(self.conf)
	@dbus.service.method("org.duck.Launcher", in_signature='', out_signature='')
	def exit(self):
		QtGui.qApp().quit()
		
	'''
	# A signal that will be exported to dbus
	@dbus.service.signal("com.example.SampleWidget", signature='')
	def clicked(self):
		print "clicked"

	# Another signal that will be exported to dbus
	@dbus.service.signal("com.example.SampleWidget", signature='')
	def lastWindowClosed(self):
		pass
	'''

if __name__ == "__main__":
	do=True

	version = platform.python_version()
	if "2.7" not in version:
		do=False
		print("Sorry, you need python 2.7 to run Duck Launcher")
	#check if there is already Duck Launcher...launched
	screen = wnck.screen_get_default()
	screen.force_update()
	win = screen.get_windows()
	for w in win:
		if "ducklauncher!!" in w.get_name():
			do=False 

	if do==True:

		gc.disable()
		app = QtGui.QApplication(sys.argv)
		QtGui.QApplication.setApplicationName("Duck Launcher")
		win = Launcher()
		win.show()
		#win.raise_()
	
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
		session_bus = dbus.SessionBus(private=True)
		name = dbus.service.BusName("org.duck.Launcher", session_bus)
		widget = DBusWidget(win,session_bus, '/DBusWidget')

		app.setActiveWindow(win)
		sys.exit(app.exec_())
	elif do==False:
		print("Quiting Duck Launcher")
