import sys
import os
from os import listdir
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
g_mode = 0 #0 repalce dir, 1 repalce GT
path_dir = ''
src_name = ''

class cl_dir:
    def __init__(self):
        self.path = ''
        self.list_path_GT = []
        self.list_path_img = []

list_class_dir = []
id_classdir = 0
id_gt       = 0

def list_files1(directory, extension):
    # print(listdir(directory))
    list_file = []
    for f in listdir(directory):
        if f.endswith('.' + extension):
            list_file.append(f)
    return list_file

def button_path():
    global path_dir
    dialog = QFileDialog()
    path_dir = dialog.getExistingDirectory(None, 'Select an awesome directory')
    print(path_dir)
    list_file_for_check()
    running_app()

def list_file_for_check():
    global path_dir
    if path_dir == '':
        return
    list_dir = os.listdir(path_dir)
    list_class_dir.clear()
    for dir in list_dir:
        classdir = cl_dir()
        pthd = os.path.join(path_dir,dir)
        classdir.path = pthd
        list_GT = list_files1(pthd,'txt')
        if len(list_GT) == 0:
            print(pthd+" don't have ground truth files!")
        for gt in list_GT:
            pthgt = os.path.join(pthd,gt)
            classdir.list_path_GT.append(pthgt)
        list_img = list_files1(pthd,'jpg')
        for imp in list_img:
            pthimg = os.path.join(pthd,imp)
            classdir.list_path_img.append(pthimg)
        list_class_dir.append(classdir)
    pass

def change_mode():
    global g_mode
    if checkbox_mode.isChecked():
        g_mode = 1
    else:
        g_mode = 0

def running_app():
    global  g_mode
    global src_name
    global  id_gt
    if path_dir == '':
        return
    if g_mode == 0:
        cld = list_class_dir[id_classdir]
        line_edit_name.setText(cld.path)
        pthimg = os.path.join(cld.path,'origine.jpg')
        print(cld.path)
        label_path.setText(cld.path)
        if os.path.isfile(pthimg):
            src_name = cld.path
            pixmap = QPixmap(pthimg)
            w = pixmap.width() / 2.5
            h = pixmap.height() / 2.5
            label_image.setFixedWidth(w)
            label_image.setFixedHeight(h)
            label_image.setPixmap(pixmap.scaled(w,h,Qt.KeepAspectRatio))
        else:
            label_image.clear()
            label_image.setText(pthimg+' not found')
    else:
        cld = list_class_dir[id_classdir]
        path_gt = cld.list_path_GT[id_gt]
        filegt = open(path_gt, "r", encoding="utf-8")
        line_edit_name.setText(filegt.readline())
        head, tail = os.path.split(path_gt)
        strl = tail.split('.')
        namefile = strl[0]
        print(path_gt)
        label_path.setText(path_gt)
        pthimg = os.path.join(cld.path, namefile + '.jpg')
        if os.path.isfile(pthimg):
            src_name = cld.path
            pixmap = QPixmap(pthimg)
            w = pixmap.width()/ 1.5
            h = pixmap.height()/ 1.5
            label_image.setFixedWidth(w)
            label_image.setFixedHeight(h)
            label_image.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio))
        else:
            label_image.clear()
            label_image.setText(pthimg + ' not found')

def next_step():
    global  g_mode
    global id_classdir
    global id_gt
    if g_mode == 0:
        id_classdir +=1
        if (id_classdir >= len(list_class_dir)):
            label_path.setText("FINISHED!")
            msg = QMessageBox()
            msg.setText("FINISHED!")
            msg.show()
        else:
            running_app()
    else:
        id_gt+=1
        print(id_gt)
        class_d = list_class_dir[id_classdir]
        print(len(class_d.list_path_GT))
        if id_gt >= len(class_d.list_path_GT):
            id_classdir += 1
            id_gt = 0
            if (id_classdir >= len(list_class_dir)):
                label_path.setText("FINISHED!")
                msg = QMessageBox()
                msg.setText("FINISHED!")
                msg.show()
            else:
                running_app()
        else:
            running_app()

def edit_event():
    print("edit event")
    global src_name
    global g_mode
    if g_mode == 0:
        if src_name == '':
            return
        dst_name = line_edit_name.text()
        os.rename(src_name,dst_name)
        src_name = ''
    else:
        cld = list_class_dir[id_classdir]
        path_gt = cld.list_path_GT[id_gt]
        dst_name = line_edit_name.text()
        filegt = open(path_gt, "w", encoding="utf-8")
        filegt.write(dst_name)
    next_step()


app = QApplication([])
window = uic.loadUi("ui/checking_ui.ui")
button_path_dir = window.findChild(QtWidgets.QPushButton, 'pb_pathdir') # Find the button
button_next = window.findChild(QtWidgets.QPushButton, 'pb_next') # Find the button
checkbox_mode =  window.findChild(QtWidgets.QCheckBox, 'cb_mode')
line_edit_name = window.findChild(QtWidgets.QLineEdit,'line_edit')
button_edit = window.findChild(QtWidgets.QPushButton,'pb_edit')
label_image = window.findChild(QtWidgets.QLabel,'lb_img')
label_path  = window.findChild(QtWidgets.QLabel,'lb_path')
checkbox_mode.stateChanged.connect(change_mode)
button_path_dir.clicked.connect(button_path)
button_edit.clicked.connect(edit_event)
button_next.clicked.connect(next_step)
window.show()
app.exec_()
