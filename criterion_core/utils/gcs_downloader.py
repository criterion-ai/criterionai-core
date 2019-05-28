import os
import cv2
import numpy as np
import time
import multiprocessing
import random


def affine(sc, r1, r2, a, sh, t1, t2):
    ref = np.array([[r1, 0, 0],
                    [0, r2, 0],
                    [0, 0, 1]])
    scale = np.array([[1 + sc, 0, 0],
                      [0, 1 + sc, 0],
                      [0, 0, 1]])
    rot = np.array([[np.cos(a), -np.sin(a), 0],
                    [np.sin(a), np.cos(a), 0],
                    [0, 0, 1]])
    she = np.array([[1, sh, 0],
                    [0, 1, 0],
                    [0, 0, 1]])
    tra = np.array([[1, 0, t1],
                    [0, 1, t2],
                    [0, 0, 1]])
    return tra.dot(she.dot(ref.dot(scale.dot(rot))))


def random_affine_transform(images,
                            rotRange=180,
                            zoomRange=0.15,
                            shearRange=0.1,
                            shiftRange=0.1,
                            doFliplr=False,
                            doFlipud=False):
    sc = (random.random() - 0.5) * 2 * zoomRange
    a = (random.random() - 0.5) * np.pi / 90 * rotRange
    sh = (random.random() - 0.5) * 2 * shearRange

    shape = images[0].shape
    t1 = (random.random() - 0.5) * 2 * shape[1] * shiftRange
    t2 = (random.random() - 0.5) * 2 * shape[0] * shiftRange

    r1 = (-1 if random.random() < 0.5 else 1) if doFliplr else 1
    r2 = (-1 if random.random() < 0.5 else 1) if doFlipud else 1

    A = affine(sc, r1, r2, a, sh, t1, t2)

    T1 = np.array([[1, 0, -0.5 * (shape[1] - 1)],
                   [0, 1, -0.5 * (shape[0] - 1)],
                   [0, 0, 1]])

    T2 = np.array([[1, 0, 0.5 * (shape[1] - 1)],
                   [0, 1, 0.5 * (shape[0] - 1)],
                   [0, 0, 1]])

    A = T2.dot(A.dot(T1))

    A = A[0:2, :]

    def transform(im):
        n_dim = im.ndim
        if n_dim > 2:
            im_t = im.copy()
            for ii in range(im.shape[2]):
                im_t[:, :, ii] = cv2.warpAffine(im[:, :, ii], A, im.shape[0:2])
        else:
            im_t = cv2.warpAffine(im, A, im.shape)
        return im_t

    return [transform(im) for im in images], A


def main(bucket_name="4679259e-7a0a-4e85-90cf-a52f3451cf38.datasets.criterion.ai",
         service_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", r'urlsigner.json')):
    if service_file == "urlsigner.json" and not file_io.file_exists(service_file):
        try:
            file_io.copy('gs://security.criterion.ai/urlsigner.json', service_file, overwrite=True)
        except:
            pass

    q_in = multiprocessing.JoinableQueue()
    q_done = multiprocessing.JoinableQueue(maxsize=10)

    blobs = gcs_walk(bucket_name, service_file=service_file)
    [bb.update({'class': bb['name'].split('/')[-2]}) for bb in blobs]
    batchsize = 16
    num_steps = int(np.ceil(len(blobs) / batchsize))
    for ii in range(num_steps):
        q_in.put(blobs[ii*batchsize:(ii+1)*batchsize])
    downloader = GcsDownloader(q_in, q_done, service_file=service_file)
    imgs = []
    y = []
    for ii in range(num_steps):
        t0 = time.time()
        buffers, cls = q_done.get()
        t1 = time.time()
        for buffer in buffers:
            img = cv2.imdecode(np.frombuffer(buffer, np.uint8), flags=cv2.IMREAD_GRAYSCALE)
            img, t_form = random_affine_transform([img])
            imgs.append(img[0])
            time.sleep(.01)
        t2 = time.time()
        q_done.task_done()
        print(t2-t0, t1-t0, q_done.qsize(), imgs[-1].shape)
    return imgs



if __name__ == "__main__":

    print("Entering")
    t0 = time.time()
    imgs = main()
    t1 = time.time()
    print("Download done!", t1 - t0)
    print(len(imgs))
