import os

import cv2
import dlib
import numpy as np
from keras.callbacks import ModelCheckpoint
from keras.layers import Activation, Dense, Dropout, Flatten
from keras.layers.normalization import BatchNormalization
from keras.models import Sequential
from sklearn.cluster.hierarchical import AgglomerativeClustering

from core.analysis.deep_learning.keras_callback import VIANKerasCallback
from core.data.computation import overlap_rect, contains_rect


def sub_image(img, r):
    return img[int(r[1]):int(r[3]), int(r[0]):int(r[2])]


def same_face_rect(r1, r2):
    if r2[0] < r1[0] + (r1[2] / 2) < (r2[0] + r2[2]) and r2[1] < r1[1] + (r1[3] / 2) < (r2[1] + r2[3]):
        return True
    t = r2
    r2 = r1
    r1 = r2
    if r2[0] < r1[0] + (r1[2] / 2) < (r2[0] + r2[2]) and r2[1] < r1[1] + (r1[3] / 2) < (r2[1] + r2[3]):
        return True
    return False


def FaceRecKeras(n_classes, dropout = 0.25):
    """ Definition of the model """
    model = Sequential()
    model.add(Dense(68, input_shape=(68, 1), kernel_initializer='TruncatedNormal'))
    model.add(BatchNormalization())
    model.add(Activation('tanh'))

    model.add(Dense(32))
    model.add(Activation('sigmoid'))

    model.add(Dropout(dropout))

    model.add(Flatten())
    model.add(Dense(n_classes))

    model.add(Activation('softmax'))
    return model


class FaceRecognitionModel():
    def __init__(self, cascPath = "user/models/face_identification/haarcascade_frontalface_default.xml",
                 predictor_path = "user/models/face_identification/shape_predictor_68_face_landmarks.dat",
                 weights_path = "user/models/face_identification/weights.hdf5",
                 cascPathside="user/models/face_identification/haarcascade_profileface.xml"):
        self.cascade = cv2.CascadeClassifier(cascPath)
        self.cascade_side = cv2.CascadeClassifier(cascPathside)
        self.predictor = dlib.shape_predictor(predictor_path)
        self.weights_path = weights_path
        self.detector = dlib.get_frontal_face_detector()
        self.dnn_model = None
        self.nose_point_idx = 30

    def init_model(self, n_classes, dropout):
        self.dnn_model = FaceRecKeras(n_classes, dropout)

    def extract_faces(self, frame_bgr, preview = False):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        rects = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
        )

        if preview:
            for (x, y, w, h) in rects:
                cv2.rectangle(gray, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("Faces found", gray)
            cv2.waitKey(2)

        rside = self.cascade_side.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
        )
        if len(rside) == 0:
            rside = []
        if len(rects) == 0:
            rects = []
        else:
            rects = rects.tolist()

        to_append = []
        for r in rects:
            for r2 in rside:
                if not same_face_rect(r, r2):
                    to_append.append(r2)
        rects.extend(to_append)
        return rects

    def draw_faces(self, frame_bgr):
        subimgs = self.extract_faces(frame_bgr)
        for r in subimgs:
            print(r)
            img = sub_image(frame_bgr, [r[0], r[1], r[0] + r[2], r[1] + r[3]])
            vecs = self.get_vector(img)
            cv2.rectangle(frame_bgr, (r[0], r[1]), (r[0] + r[2], r[1] + r[3]), (0, 180, 235), 2)
            for v in vecs:
                try:
                    vec = np.add(v[1], [r[0], r[1]])
                    for i in range(68):
                        cv2.circle(frame_bgr, (int(vec[i][0]), int(vec[i][1])), 1, (0, 235, 235), thickness=2)
                except Exception as e:
                    raise e
                    pass
        return frame_bgr

    def get_vector(self, img, preview = True):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        dets = self.detector(img)
        if len(dets) == 0:
            return []

        res = []

        for k, d in enumerate(dets):
            # eucl_dist = np.zeros(shape=68)
            # vectors = np.zeros(shape=(68, 2))
            # rectangle = np.zeros(shape=4)


            # Get the landmarks/parts for the face in box d.
            shape = self.predictor(img, d)
            rectangle = [d.left(), d.top(), d.right(), d.bottom()]
            new = np.zeros(shape=(68, 2))
            for idx in range(68):
                p = shape.part(idx)
                new[idx] = [p.x, p.y]

            norm_vec = new - np.amin(new)
            norm_vec /= np.amax(norm_vec)
            eucl_dist = np.linalg.norm(norm_vec - norm_vec[self.nose_point_idx], axis=1)

            vectors = new
            res.append((rectangle, vectors, eucl_dist))


        return res

    def cluster_faces(self, eucl_dist_vecs, n_clusters = 30):
        """
        
        :param eucl_dist_vecs: A list of euclidian distances as returned from FaceRecognitionModel.get_vector() 
        :param cluster_range_min: Minimal number of clusters to produce
        :param cluster_range_max: Maximal number of clusters to produce
        :return: A dict(key:n_clusters, val=list[label_idx][data_idx])
        """

        X = np.array(eucl_dist_vecs)
        clustering = AgglomerativeClustering(n_clusters=n_clusters).fit(X)

        # print(clustering.labels_)
        # lbl_cluster = [[]] * int(np.amax(clustering.labels_) + 1)
        # for idx, lbl in enumerate(clustering.labels_):
        #     lbl_cluster[lbl].append(idx)

        return clustering.labels_

    def load_weights(self, path = None):
        if self.dnn_model is None:
            raise RuntimeError("Model not initialized")

        if path is None:
            self.dnn_model.load_weights(self.weights_path)
        else:
            self.dnn_model.load_weights(path)

    def store_weights(self, path = None):
        if self.dnn_model is None:
            raise RuntimeError("Model not initialized")

        if path is None:
            self.dnn_model.save_weights(self.weights_path)
        else:
            self.dnn_model.save_weights(path)

    def train_model(self, X_train, y_train, X_test, y_test, load=False, callback=None):
        if self.dnn_model is None:
            raise RuntimeError("Model not initialized")

        self.dnn_model.compile(loss='categorical_crossentropy', optimizer='nadam', metrics=['accuracy'])

        checkpoint = ModelCheckpoint(self.weights_path, monitor='loss', verbose=0, save_best_only=True, mode='auto')

        # tensorboard = TensorBoard(
        #     log_dir='./logs/' + now, histogram_freq=1, write_graph=True
        # )
        # callbacks_list = [checkpoint, tensorboard]
        if callback is not None:
            cb = VIANKerasCallback()
            cb.onCallback.connect(callback)
            callbacks_list = [checkpoint, cb]
        else:
            callbacks_list = [checkpoint]


        self.dnn_model.fit(
            X_train,
            y_train,
            epochs=100,
            batch_size=10,
            shuffle='batch',
            callbacks=callbacks_list,
            verbose=1)

        (loss, accuracy) = self.dnn_model.evaluate(X_test, y_test, batch_size=10)

        print("[INFO] loss={:.4f}, accuracy: {:.4f}%".format(loss, accuracy * 100))

    def predict(self, face_vec):
        """ Predict the class of a particular image """
        if self.dnn_model is None:
            raise RuntimeError("Model not initialized")

        X = face_vec

        X = np.expand_dims(X, axis=0)
        X = np.array(X).astype('float64')

        try:
            self.dnn_model.load_weights(self.weights_path)
        except OSError:
            print("creating new weights file")

        pred = self.dnn_model.predict(X, batch_size=1, verbose=0)[0]

        class_idx = np.argmax(pred)
        prob = pred[class_idx]
        return class_idx, prob


