import os
import os.path
import pickle
from io import BytesIO

import numpy as np
import requests
from PIL import Image
from sklearn import svm
from sklearn.metrics import classification_report


def load_pics(path, kind='train'):
    kind_path = os.path.join(path, kind)
    images = []
    labels = []
    # 验证码 0-8，没有 9
    for i in range(9):
        label_path = os.path.join(kind_path, str(i))
        for file in os.listdir(label_path):
            with Image.open(os.path.join(label_path, file), 'r') as img:
                images.append(np.asarray(img, dtype=np.uint8))
                labels.append(i)

    images = np.array(images).reshape(len(labels), 7 * 12)
    labels = np.array(labels)

    return images, labels


def get_bin_table(threshold=140):
    """
    获取灰度转二值的映射table
    :param threshold:
    :return:
    """
    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)

    return table


def get_crop_img(img):
    """
    按照图片的特点,进行切割
    :param img:
    :return:
    """
    child_img_list = []
    for i in range(5):
        x = 6 + i * (7 + 2)
        y = 5
        child_img = img.crop((x, y, x + 7, y + 12))
        # child_img.show()
        child_img_list.append(child_img)

    return child_img_list


def recognize_img(img, clf):
    """
    识别验证码
    :param img:
    :return:
    """
    imgry = img.convert('L')  # 转为灰度
    out = imgry.point(get_bin_table(), '1')  # 二值化
    child_img_list = get_crop_img(out)  # 切割

    numbers = []
    for child_img in child_img_list:
        image = np.asarray(child_img, dtype=np.int8).reshape(1, 7 * 12)
        y_number = clf.predict(image)
        numbers.append(y_number.tolist().pop())

    code = ''
    for i in range(0, len(numbers)):
        code = code + str(numbers[i])

    return code


def get_clf_by_train(file_path):
    clf = None
    # 读入数据
    if os.path.exists(file_path):
        X_train, y_train = load_pics(file_path, kind='train')

        clf = svm.SVC(C=1.0, kernel='poly', degree=1, gamma='auto')
        clf.fit(X_train, y_train)
        # 保存模型
        with open('hdu.pickle', 'wb') as f:
            pickle.dump(clf, f)
    else:
        print('没有发现图片数据路径！')

    return clf


def get_clf(file_path):
    clf = None
    try:
        with open('hdu.pickle', 'r') as f:
            clf = pickle.load(f)
    except:
        clf = get_clf_by_train(file_path)
    return clf


if __name__ == '__main__':
    file_path = os.path.abspath('../pics/')
    clf = get_clf(file_path)
    X_test, y_test = load_pics(file_path, kind='test')
    print(clf.score(X_test, y_test))
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    url = "http://jxgl.hdu.edu.cn/CheckCode.aspx"
    img = Image.open(BytesIO(requests.get(url).content))
    img.show()

    print(recognize_img(img, clf))
