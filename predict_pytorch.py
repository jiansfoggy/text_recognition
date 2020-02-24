import numpy as np
import torch, cv2, math
import os, time
from DB_Liao.concern.config import Configurable, Config
from BoundingBox import bbox
import argparse

detector_model = ''
detector_box_thres = 0.5

# classifier
classifier_ckpt_path = ''
classifier_width = 256
classifier_height = 32
debug = False


class Detector_DB:
    def __init__(self, experiment, args, gpu='0', cmd=dict()):
        self.RGB_MEAN = np.array([122.67891434, 116.66876762, 104.00698793])
        self.experiment = experiment
        self.gpu = gpu
        experiment.load('evaluation', **args)
        self.args = cmd
        self.structure = experiment.structure
        self.init_torch_tensor()
        self.init_model(self.args['resume'])
        self.model.eval()

    def init_torch_tensor(self):
        if torch.cuda.is_available() and self.gpu != None:
            self.device = torch.device('cuda')
            torch.set_default_tensor_type('torch.cuda.FloatTensor')
        else:
            self.device = torch.device('cpu')
            torch.set_default_tensor_type('torch.FloatTensor')

    def init_model(self, path):
        self.model = self.structure.builder.build(self.device)
        if not os.path.exists(path):
            print("Checkpoint not found: " + path)
            return
        print("Resuming from " + path)
        states = torch.load(path, map_location=self.device)
        self.model.load_state_dict(states, strict=False)
        print("Resumed from " + path)

    def resize_image(self, img):
        height, width, _ = img.shape
        if height < width:
            new_height = self.args['image_short_side']
            new_width = int(math.ceil(new_height / height * width / 32) * 32)
        else:
            new_width = self.args['image_short_side']
            new_height = int(math.ceil(new_width / width * height / 32) * 32)
        resized_img = cv2.resize(img, (new_width, new_height))
        return resized_img

    def load_image(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR).astype('float32')
        original_shape = img.shape[:2]
        img = self.resize_image(img)
        img -= self.RGB_MEAN
        img /= 255.
        img = torch.from_numpy(img).permute(2, 0, 1).float().unsqueeze(0)
        return img, original_shape

    def format_output(self, batch, output):
        batch_boxes, batch_scores = output
        for index in range(batch['image'].size(0)):
            original_shape = batch['shape'][index]
            filename = batch['filename'][index]
            result_file_name = 'res_' + filename.split('/')[-1].split('.')[0] + '.txt'
            result_file_path = os.path.join(self.args['result_dir'], result_file_name)
            boxes = batch_boxes[index]
            scores = batch_scores[index]
            if self.args['polygon']:
                with open(result_file_path, 'wt') as res:
                    for i, box in enumerate(boxes):
                        box = np.array(box).reshape(-1).tolist()
                        result = ",".join([str(int(x)) for x in box])
                        score = scores[i]
                        res.write(result + ',' + str(score) + "\n")
            else:
                with open(result_file_path, 'wt') as res:
                    for i in range(boxes.shape[0]):
                        score = scores[i]
                        if score < self.args['box_thresh']:
                            continue
                        box = boxes[i, :, :].reshape(-1).tolist()
                        result = ",".join([str(int(x)) for x in box])
                        res.write(result + ',' + str(score) + "\n")

    def inference(self, image_path, visualize=False):
        batch = dict()
        batch['filename'] = [image_path]
        img, original_shape = self.load_image(image_path)
        batch['shape'] = [original_shape]
        with torch.no_grad():
            batch['image'] = img
            pred = self.model.forward(batch, training=False)
            output = self.structure.representer.represent(batch, pred, is_output_polygon=self.args['polygon'])
            if not os.path.isdir(self.args['result_dir']):
                os.mkdir(self.args['result_dir'])
            self.format_output(batch, output)
            boxes, _ = output
            boxes = boxes[0]
            if visualize and self.structure.visualizer:
                vis_image = self.structure.visualizer.demo_visualize(image_path, output)
                cv2.imwrite(os.path.join(self.args['result_dir'],
                                         image_path.split('/')[-1].split('.')[0] + '_ ' + detector_model + '_ ' + str
                                         (detector_box_thres) + '.jpg'), vis_image)
            return boxes


from crnn_pbcquoc.models.utils import strLabelConverter
from torch.autograd import Variable
import crnn_pbcquoc.models.crnn as crnn
import crnn_pbcquoc.models.utils as utils
from crnn_pbcquoc.loader import NumpyListLoader, alignCollate


class Classifier_CRNN:
    def __init__(self, ckpt_path='', gpu='0', batch_sz=16, workers=4, num_channel=3, imgW=128, imgH=64,
                 alphabet_path='crnn_pbcquoc/data/char_246'):
        self.imgW = imgW
        self.imgH = imgH
        self.batch_sz = batch_sz
        alphabet = open(alphabet_path).read().rstrip()
        nclass = len(alphabet) + 1
        self.image = torch.FloatTensor(batch_sz, 3, imgH, imgH)
        self.text = torch.IntTensor(batch_sz * 5)
        self.length = torch.IntTensor(batch_sz)
        self.model = crnn.CRNN2(imgH, num_channel, nclass, 256)
        if gpu != None and torch.cuda.is_available():
            print('Classifier use GPU', gpu)
            self.model = self.model.cuda()
            self.image = self.image.cuda()
        print('loading pretrained model from %s' % ckpt_path)
        self.model.load_state_dict(torch.load(ckpt_path, map_location='cpu'))
        self.converter = strLabelConverter(alphabet, ignore_case=False)
        self.image = Variable(self.image)
        self.text = Variable(self.text)
        self.length = Variable(self.length)
        self.workers = workers
        self.model.eval()

    def inference(self, img_list, visualize=False):
        val_dataset = NumpyListLoader(img_list)
        num_files = len(val_dataset)
        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=self.batch_sz,
            num_workers=self.workers,
            shuffle=False,
            collate_fn=alignCollate(self.imgW, self.imgH)
        )

        val_iter = iter(val_loader)
        max_iter = len(val_loader)
        # print('Number of samples', num_files)
        # begin = time.time()
        with torch.no_grad():
            for i in range(max_iter):
                data = val_iter.next()
                cpu_images, cpu_texts = data
                batch_size = cpu_images.size(0)
                utils.loadData(self.image, cpu_images)
                preds = self.model(self.image)
                preds_size = Variable(torch.IntTensor([preds.size(0)] * batch_size))
                _, preds = preds.max(2)
                preds = preds.transpose(1, 0).contiguous().view(-1)
                sim_pred = self.converter.decode(preds.data, preds_size.data, raw=False)
                raw_pred = self.converter.decode(preds.data, preds_size.data, raw=True)
                if debug:
                    print('\n    ', raw_pred, '\n =>', sim_pred, '\ngt:', cpu_texts[0])
                    cv_img = cpu_images[0].permute(1, 2, 0).numpy()
                    cv_img_bgr = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    cv2.imshow('result', cv_img_bgr)
                    cv2.waitKey(0)
        # end = time.time()
        # processing_time = end - begin
        # print('Processing time:', processing_time)
        # print('Speed:', num_files / processing_time, 'fps')


exp = 'DB_Liao/config/aicr_ic15_resnet18.yaml'
img_path = 'data/Eval/imgs/SCAN_20191128_145142994_002.jpg'
model_name = 'model_epoch_115_minibatch_72000'
ckpt_path = 'DB_Liao/outputs/' + model_name
polygon = False
visualize = False
box_thres = 0.315
img_short_side = 736  # 736


def crop_from_img_rectangle(img, left, top, right, bottom):
    extend_y = max(int((bottom - top) / 3), 4)
    extend_x = int(extend_y / 2)
    top = max(0, top - extend_y)
    bottom = min(img.shape[0], bottom + extend_y)
    left = max(0, left - extend_x)
    right = min(img.shape[1], right + extend_x)
    if left >= right or top >= bottom or left < 0 or right < 0 or left >= img.shape[1] or right >= img.shape[1]:
        return None
    return img[top:bottom, left:right]


def get_boxes_data(img, boxes):
    boxes_data = []
    for box in boxes:
        box = np.array(box).astype(np.int32).reshape(-1, 2)
        left = min(box[0][0], box[3][0])
        top = min(box[0][1], box[1][1])
        right = max(box[1][0], box[2][0])
        bottom = max(box[2][1], box[3][1])
        if (right - left) < 20 or (bottom - top) < 10:
            continue
        box_data = crop_from_img_rectangle(img, left, top, right, bottom)
        boxes_data.append(box_data)
    return boxes_data


def init_models(args, gpu='0'):
    if gpu != None:
        print('Use GPU',gpu)
        os.environ['CUDA_VISIBLE_DEVICES'] = gpu
    else:
        print('Use CPU')
    conf = Config()
    experiment_args = conf.compile(conf.load(args['exp']))['Experiment']
    experiment_args.update(cmd=args)
    experiment = Configurable.construct_class_from_config(experiment_args)
    detector = Detector_DB(experiment, experiment_args,gpu=gpu, cmd=args)
    classifier = Classifier_CRNN(ckpt_path='crnn_pbcquoc/outputs/AICR_pretrained_48.pth', gpu=gpu)
    return detector, classifier


def main():
    parser = argparse.ArgumentParser(description='Text Recognition Training')
    parser.add_argument('--exp', type=str, default=exp)
    parser.add_argument('--resume', type=str, help='Resume from checkpoint', default=ckpt_path)
    parser.add_argument('--result_dir', type=str, default='./demo_results/', help='path to save results')
    parser.add_argument('--data', type=str,
                        help='The name of dataloader which will be evaluated on.')
    parser.add_argument('--image_short_side', type=int, default=img_short_side,
                        help='The threshold to replace it in the representers')
    parser.add_argument('--thresh', type=float,
                        help='The threshold to replace it in the representers')
    parser.add_argument('--box_thresh', type=float, default=box_thres,
                        help='The threshold to replace it in the representers')
    parser.add_argument('--resize', action='store_true', help='resize')
    parser.add_argument('--visualize', default = visualize, help='visualize maps in tensorboard')
    parser.add_argument('--polygon', help='output polygons if true', default=polygon)
    parser.add_argument('--eager', '--eager_show', action='store_true', dest='eager_show',
                        help='Show iamges eagerly')

    args = parser.parse_args()
    args = vars(args)
    args = {k: v for k, v in args.items() if v is not None}

    # initialize
    begin_init = time.time()
    detector, classifier = init_models(args, gpu=None)
    end_init = time.time()
    print('Init models time:', end_init - begin_init, 'seconds')

    boxes_list = detector.inference(img_path, visualize)

    end_detector = time.time()
    print('Detector time:', end_detector - end_init, 'seconds')

    test_img = cv2.imread(img_path)

    boxes_data = get_boxes_data(test_img, boxes_list)

    end_get_boxes_data = time.time()
    print('Get boxes time:', end_get_boxes_data - end_detector, 'seconds')
    classifier.inference(boxes_data)

    end_classifier = time.time()
    print('Classifier time:', end_classifier - end_get_boxes_data, 'seconds')
    print('\nTotal predict time:', end_classifier - end_init, 'seconds')
    print('Done')


if __name__ == '__main__':
    main()
