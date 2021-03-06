import os
import cv2
import numpy as np
import random

interpolation_flag = dict(nearest=cv2.INTER_NEAREST, linear=cv2.INTER_LINEAR, area=cv2.INTER_AREA)


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


def get_tforms(rois, target_shape, input_shape):
    # Cropping:
    # tx, ty: offset
    # target_size gives image size
    sz = [0, 0]
    if len(rois) == 0:
        rois = [[[0, 0], input_shape[1::-1]]]
    t_forms = [None] * len(rois)
    target_shapes = [None] * len(rois)
    for ii, roi in enumerate(rois):
        crop_x = roi[0][0]
        crop_y = roi[0][1]
        sz_x = roi[1][0] - roi[0][0]
        if ii > 0:
            assert sz[0] == sz_x
        else:
            sz[0] = sz_x
        sz[1] += roi[1][1] - roi[0][1]
        t_forms[ii] = np.array([[1, 0, -crop_x], [0, 1, -crop_y], [0, 0, 1]], dtype=np.float32)
        target_shapes[ii] = [roi[1][0]-roi[0][0], roi[1][1]-roi[0][1], target_shape[-1]]
    sc = [target_shape[1-jj] / float(sz[jj]) for jj in range(2)]
    t_scale = np.array([[sc[1], 0, 0], [0, sc[0], 0], [0, 0, 1]], dtype=np.float32)
    target_shapes = [tuple([int(ts[1-ii] * sc[1-ii]) for ii in range(2)]+[ts[-1]]) for ts in target_shapes]
    t_forms = [t_scale.dot(t_form) for t_form in t_forms]
    return t_forms, target_shapes


def random_affine_transform(target_shape,
                            augmentation):
    if augmentation is None:
        return np.eye(2, 3)

    sc = (random.random() - 0.5) * 2 * (augmentation.scaling_range / 100)

    a = (random.random() - 0.5) * np.pi / 90 * augmentation.rotation_angle
    sh = (random.random() - 0.5) * 2 * augmentation.shear_range

    t1 = (random.random() - 0.5) * 2 * (augmentation.horizontal_translation_range / 100) * target_shape[1]
    t2 = (random.random() - 0.5) * 2 * (augmentation.vertical_translation_range / 100) * target_shape[0]

    r1 = (-1 if random.random() < 0.5 else 1) if augmentation.flip_horizontal else 1
    r2 = (-1 if random.random() < 0.5 else 1) if augmentation.flip_vertical else 1

    A = affine(sc, r1, r2, a, sh, t1, t2)

    T1 = np.array([[1, 0, -0.5 * (target_shape[1] - 1)],
                   [0, 1, -0.5 * (target_shape[0] - 1)],
                   [0, 0, 1]])

    T2 = np.array([[1, 0, 0.5 * (target_shape[1] - 1)],
                   [0, 1, 0.5 * (target_shape[0] - 1)],
                   [0, 0, 1]])

    A = T2.dot(A.dot(T1))

    return A[0:2, :]


def transform(im, A, target_shape, interpolation='linear', anti_aliasing=None):
    if anti_aliasing:
        sigmas = [anti_aliasing * float(im.shape[1-ii]) / target_shape[1-ii] for ii in range(2)]
    interpolation = interpolation_flag[interpolation]
    n_dim = im.ndim
    if n_dim > 2:
        im_t = np.zeros(target_shape, dtype=np.float32)
        for ii in range(im.shape[2]):
            im_ii = cv2.GaussianBlur(im[:, :, ii],(0,0), *sigmas) if anti_aliasing else im[:, :, ii]
            im_t[:, :, ii] = cv2.warpAffine(im_ii, A, target_shape[1::-1], flags=interpolation)
    else:
        im_ii = cv2.GaussianBlur(im, (0, 0), *sigmas) if anti_aliasing else im
        im_t = cv2.warpAffine(im_ii, A, target_shape[1::-1], flags=interpolation)
    return im_t


def apply_transforms(images, aug, rois, target_shape, *args, rescale=127.5, offset=-1.0, **kwargs):
    input_shape = images[0].shape
    t_forms, target_shapes = get_tforms(rois, target_shape, input_shape)
    img_t = [np.concatenate([transform(im, aug.dot(t_form), ts, *args, **kwargs) for t_form, ts in zip(t_forms, target_shapes)], axis=0)/rescale+offset for im in images]
    for jj in range(len(img_t)):
        if img_t[jj].ndim == 2:
            img_t[jj] = np.expand_dims(img_t[jj], axis=-1)
    return img_t
