import sys
import os

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))


print(sys.path)
from config.config_manager import ConfigManager
import codecs
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime
#Using old model from Korean team
from predict_korean_core import SSD_Predict
#Using tuan-anh model
#from predict_core import SSD_Predict
from aicr_dssd_train.utils.split_image import split_image_to_objs
from aicr_dssd_train.utils.run_util import drawAnnotation, calculateIOU, calculateIOU2, showTableDocument, showLineUpDocument, showTableDocument2, showLineUpDocument2
from aicr_dssd_train.utils.image_processing_util import zoomScaleFinder, skew_detect, skew_detect2

import os, cv2, sys
import tensorflow as tf
from keras import backend as k

from metric.BoundingBox import BoundingBox
from metric.BoundingBoxes import BoundingBoxes
from metric.Evaluator import *
from metric.utils import BBFormat, CoordinatesType


from general_utils.full_width_half_width import halfen, fullen, is_half_width, is_full_width

configfile = 'config/chinese_config.ini'
configmanager = ConfigManager(configfile)

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = configmanager.infer_gpu_num
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
k.tensorflow_backend.set_session(tf.Session(config=config))
training_time = datetime.today().strftime('%Y-%m-%d_%H-%M')

img_shape = configmanager.img_shape
classes = configmanager.classes
conf_thres = 0.5
iouThreshold = 0.35
nms_thres = 0.45
max_size = 2000
# result_save_dir = '/home/advlab/data_thang/detection_outputs/predict_'+training_time
# result_save_dir = '/data/aicr_hanh/data_hanh/detection_outputs/predict_'+training_time
result_save_dir = '/data/data_thang/detection_outputs/predict_'+training_time
save_anno_image = True
is_get_mAP = True

img_font_idle_size = configmanager.img_font_idle_size
img_font_idle_size2 = configmanager.img_font_idle_size2
NMS_ALGORITHM = configmanager.nms_algorithm

split_overap_size = configmanager.split_overap_size

weight_path = configmanager.ssd_weight_path
# img_dir = '/home/advlab/data_thang/detection/ground_truth_chinese10/images'
# GT_dir = '/home/advlab/data_thang/detection/ground_truth_chinese10/TXT'
# GT_dir = '/data/aicr_hanh/data_hanh/detection/ground_truth_chinese_10/TXT'
# img_dir = '/data/aicr_hanh/data_hanh/detection/ground_truth_chinese_10/images'
# GT_dir = '/data/aicr_hanh/data_xau/detection/ground_truth_chinese_10/TXT'
# img_dir = '/data/aicr_hanh/data_xau/detection/ground_truth_chinese_10/images'
GT_dir = '/data/chinese_images/SDSC2_TXT'
img_dir = '/data/chinese_images/SDSC2_IMG'
# #img_dir = 'data'
# file_list = [
#     '20190731_144554',
#     '20190731_144540',
#     '190715070245517_8478000669_pod',
#     '190715070249216_8477872491_pod',
#     '190715070317353_8479413342_pod'
#     # '190715070245517_8478000669_pod_resize_2.5',
#     # '190715070249216_8477872491_pod_resize_2.5',
#     # '190715070317353_8479413342_pod_resize_2.5'
# ]
#file_list=['test_1_200k_a']
# classes_vn = "ĂÂÊÔƠƯÁẮẤÉẾÍÓỐỚÚỨÝÀẰẦÈỀÌÒỒỜÙỪỲẢẲẨĐẺỂỈỎỔỞỦỬỶÃẴẪẼỄĨÕỖỠŨỮỸẠẶẬẸỆỊỌỘỢỤỰỴăâêôơưáắấéếíóốớúứýàằầèềìòồờùừỳảẳẩđẻểỉỏổởủửỷãẵẫẽễĩõỗỡũữỹạặậẹệịọộợụựỵ"
# class_list_vn = [x for x in classes_vn]
#
chinese_file_path = "../textimg_data_generator_dev/dataprovision/config/chinese.txt"
class_list_chinese = list()
if chinese_file_path is not None:
    with open(chinese_file_path) as fp:
        class_list_chinese = [c for c in fp.read(-1)]

classes_symbol = '*:,@$.-(#%\'\")/~!^&_+={}[]\;<>?※”'
class_list_symbol = [x for x in classes_symbol]


classes_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
class_list_alphabet = [x for x in classes_alphabet]

classes_number = '0123456789'
class_list_number = [x for x in classes_number]



def load_imgfilepaths(dirpath):
    file_list = []
    for root, dirs, files in os.walk(dirpath):
        for f in files:
            file_list.append(f[:-4])
            # file_list.append(os.path.join(root, f))

    return file_list

def save_predict_result(coord_list, save_result_filename='test.txt', zoom_rate=1):
    result=''
    for c in coord_list:
        class_nm = c.class_nm
        conf = round(c.confidence, 2)
        c = c.getAbsolute_coord()
        x_min = int(round(c[0]/zoom_rate, 2))
        y_min = int(round(c[1] / zoom_rate, 2))
        width = int(round((c[2] - c[0]) / zoom_rate, 2))
        height = int(round((c[3] - c[1]) / zoom_rate, 2))
        result_line = class_nm + ' ' + str(conf) + ' ' + str(x_min) + ' ' + str(y_min) + ' ' + str(width) + ' ' + str(height)
        #print(result_line)
        result += result_line + '\n'
    with open(save_result_filename, "w") as f:
        f.write(result)

def predict(get_map=True):
    print('Begin predict with checkpoint:', weight_path, '\nSave result to:', result_save_dir)
    ssd_predict = SSD_Predict(classes=classes,
                              weight_path=weight_path,
                              input_shape=img_shape,
                              nms_thresh=nms_thres,
                              NMS_ALGORITHM=NMS_ALGORITHM)
    for file_name in file_list:
        # print(file_name)
        ori_img_path = os.path.join(img_dir, file_name + '.png')
        if os.path.exists(os.path.join(img_dir, file_name + '.jpg')):
            ori_img_path = os.path.join(img_dir, file_name + '.jpg')
        # load original image with grayscale
        ori_img = cv2.imread(ori_img_path, cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_COLOR)
        # 이미지 Grayscale로 변환
        if len(ori_img.shape) > 2:
            ori_img_gray = cv2.cvtColor(ori_img, cv2.COLOR_RGB2GRAY)
        else:
            ori_img_gray = ori_img.copy()
        print('\nTest image:', ori_img_path, ', original shape(h,w):', ori_img_gray.shape)


        h_, w_ = ori_img_gray.shape
        z_ = 1
        while min(w_, h_) < max_size:
            z__ = 2
            z_ = z_ * 2
            ori_img_gray = cv2.resize(ori_img_gray, (int(w_ * z__), int(h_ * z__)), interpolation=cv2.INTER_LANCZOS4)
            h_, w_ = ori_img_gray.shape
            print('Shape of resize image (h,w):', ori_img_gray.shape, 'zoom_ratio', z_)

        # 문서 내 대다수의 폰트 크기 추정
        img_font_regular_size, avg_character_height = zoomScaleFinder(ori_img_gray, h=float(max_size), AVG_RATIO=0.8,
                                                                      DEBUG=False)
        # Zoom In/Out 비율 획득

        zoom_ratio1 = round(img_font_idle_size / img_font_regular_size, 2)
        print('img_font_regular_size : %.2f' % img_font_regular_size + ' , zoom_ratio : %.2f' % zoom_ratio1)

        # 이미지 리사이즈
        ori_img_gray_resize = cv2.resize(ori_img_gray, None, fx=zoom_ratio1, fy=zoom_ratio1,
                                         interpolation=cv2.INTER_CUBIC)

        # split image for object detection
        img_obj_list, img_coord_list = split_image_to_objs(imgage_obj=ori_img_gray_resize,
                                                           img_shape=img_shape, overap_size=split_overap_size,
                                                           zoom_ratio=zoom_ratio1)

        # Zoom In/Out 비율 획득
        zoom_ratio2 = round(img_font_idle_size2 / img_font_regular_size, 2)
        # zoom_ratio2 = 0.4
        print('img_font_regular_size : %.2f' % img_font_regular_size + ' , zoom_ratio : %.2f' % zoom_ratio2)

        # 이미지 리사이즈
        ori_img_gray_resize = cv2.resize(ori_img_gray, None, fx=zoom_ratio2, fy=zoom_ratio2,
                                         interpolation=cv2.INTER_CUBIC)

        # split image for object detection
        img_obj_list2, img_coord_list2 = split_image_to_objs(imgage_obj=ori_img_gray_resize,
                                                             img_shape=img_shape, overap_size=split_overap_size,
                                                             zoom_ratio=zoom_ratio2)

        img_obj_list = img_obj_list + img_obj_list2
        img_coord_list = img_coord_list + img_coord_list2

        ssd_predict_result_list = ssd_predict.predict_from_obj_list(img_obj_list, img_coord_list, conf_thres=conf_thres)
        ssd_predict_result_list = sorted(ssd_predict_result_list)

        print('ssd predict result list count: ', str(len(ssd_predict_result_list)))

        # Calculated IOU and applied
        applied_iou_list = calculateIOU(ssd_predict_result_list, iouThreshold)

        print('appied iou list count: ', str(len(applied_iou_list)))

        result_save_path = os.path.join(result_save_dir,
                                        file_name + '_annotation_nms_thresh_{}_{}.jpg'.format(iouThreshold,
                                                                                                     NMS_ALGORITHM))
        save_predict_result(applied_iou_list, os.path.join(result_save_dir, file_name + '.txt'), z_)
        if save_anno_image:
            drawAnnotation(applied_iou_list, ori_img_gray, show_conf=True, save_file_name=result_save_path)
        if get_map:
            get_mAP([file_name], type=file_name)
    #calculte mAP
    print()
    if get_map:
        get_mAP(file_list,type='all')

def getBoundingBoxes(directory, list_file, isGT, allBoundingBoxes=None, allClasses=None, imgSize=(0, 0)):
    """Read txt files containing bounding boxes (ground truth and detections)."""
    if allBoundingBoxes is None:
        allBoundingBoxes = BoundingBoxes()
    if allClasses is None:
        allClasses = []
    # Read ground truths
    # os.chdir(directory)
    for file_name in list_file:
        nameOfImage = file_name
        fh1 = codecs.open(os.path.join(directory, file_name+'.txt'), "r", encoding='utf8')
        for line in fh1:
            line = line.replace("\n", "")
            if line.replace(' ', '') == '':
                continue
            splitLine = line.split(" ")
            # print(line)
            if isGT:
                if splitLine[0] != '':
                    classID = "character"
                    # idClass = (splitLine[0])  # class
                    # if len(idClass) == 1:
                    #     if is_full_width(idClass):
                    #         idClass = halfen(idClass)

                    # classID = "unknown"
                    # if idClass in class_list_chinese:
                    #     classID = "character"
                    # elif idClass in class_list_alphabet:
                    #     classID = "character"
                    # elif idClass in class_list_number:
                    #     classID = "character"
                    # elif idClass in class_list_symbol:
                    #     classID = "character"
                    # else:
                    #     print("Unknown char: {} {} ".format(idClass, hex(ord(idClass))))
                    #     continue

                    # print("groundtruth {}".format(classID))
                    x = float(splitLine[1])
                    y = float(splitLine[2])
                    w = float(splitLine[3])
                    h = float(splitLine[4])
                    # classID = splitLine[0]
                    # x = float(splitLine[1])
                    # y = float(splitLine[2])
                    # w = float(splitLine[3])
                    # h = float(splitLine[4])

                    bb = BoundingBox(
                        nameOfImage,
                        classID, x, y, w, h,
                        'abs',
                        imgSize,
                        BBType.GroundTruth,
                        format=BBFormat.XYWH)
            else:  # detection
                if splitLine[0] != '':
                    idClass = splitLine[0]  # class
                    # print("detection {}".format(idClass))
                    confidence = float(splitLine[1])
                    x = float(splitLine[2])
                    y = float(splitLine[3])
                    w = float(splitLine[4])
                    h = float(splitLine[5])

                    classID = idClass
                    bb = BoundingBox(
                        nameOfImage,
                        classID, x, y, w, h,
                        'abs',
                        imgSize,
                        BBType.Detected,
                        confidence,
                        format=BBFormat.XYWH)
            if isGT:
                allBoundingBoxes.addBoundingBox(bb)
            if not isGT and (confidence >= conf_thres) and h > 0:
                allBoundingBoxes.addBoundingBox(bb)
            if classID not in allClasses:
                allClasses.append(classID)
        fh1.close()
    return allBoundingBoxes, allClasses

def get_mAP(list_file, type=''):
    # Get groundtruth boxes
    allBoundingBoxes, allClasses = getBoundingBoxes(GT_dir, list_file, True)
    # Get detected boxes
    allBoundingBoxes, allClasses = getBoundingBoxes(result_save_dir, list_file, False, allBoundingBoxes, allClasses)
    allClasses.sort()

    evaluator = Evaluator()
    acc_AP = 0
    validClasses = 0

    detections = evaluator.PlotPrecisionRecallCurve(
        allBoundingBoxes,  # Object containing all bounding boxes (ground truths and detections)
        IOUThreshold=iouThreshold,  # IOU threshold
        method=MethodAveragePrecision.EveryPointInterpolation,
        showAP=True,  # Show Average Precision in the title of the plot
        showInterpolatedPrecision=False,  # Don't plot the interpolated precision curve
        #saveDir=result_save_dir,
        showGraphic=False)

    f = open(os.path.join(result_save_dir, 'results_detector_'+type+'.txt'), 'w', encoding='utf-8')
    f.write('Object Detection Metrics\n')
    f.write('Average Precision (AP), Precision and Recall per class:')
    print('Result of '+type+':')

    # each detection is a class
    for metricsPerClass in detections:
        # Get metric values per each class
        cl = metricsPerClass['class']
        ap = metricsPerClass['AP']
        precision = metricsPerClass['precision']
        recall = metricsPerClass['recall']
        totalPositives = metricsPerClass['total positives']
        total_TP = metricsPerClass['total TP']
        total_FP = metricsPerClass['total FP']

        if totalPositives > 0:
            validClasses = validClasses + 1
            acc_AP = acc_AP + ap
            prec = ['%.2f' % p for p in precision]
            rec = ['%.2f' % r for r in recall]
            ap_str = "{0:.2f}%".format(ap * 100)
            result_each_class='Class: %s' % cl+', AP: %s' % ap_str
            result_PR='\nPrecision: %s' % prec+'\nRecall: %s' % rec
            f.write(result_each_class+result_PR)
            print(result_each_class)
    if(validClasses != 0):
        mAP = acc_AP / validClasses
    else:
        mAP = 0
    mAP_str = "{0:.2f}%".format(mAP * 100)
    print('Confident threshold: ', conf_thres, ', mAP: %s' % mAP_str)
    f.write('\n\n\nmAP: %s' % mAP_str)
    f.close()

if __name__== "__main__":
    file_list = load_imgfilepaths(img_dir)
    if not os.path.isdir(result_save_dir):
        os.mkdir(result_save_dir)
    log_file = os.path.join(result_save_dir, "predict.log")
    print('Please check result of predict in:', log_file)
    f = open(log_file, 'w')
    sys.stdout = f
    predict(get_map=is_get_mAP)
    f.close()
    print("Everything done")

