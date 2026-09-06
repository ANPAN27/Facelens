import numpy as np

from face.detector import crop_face_only


def test_crop_face_only_returns_smaller_region():
    img = np.full((120, 100, 3), 255, dtype=np.uint8)
    crop = crop_face_only(img, [30, 40, 70, 90], mask_background=False)
    assert crop.shape[0] < 120
    assert crop.shape[1] < 100
    assert crop.size > 0


def test_crop_face_only_masks_background():
    img = np.full((120, 100, 3), 255, dtype=np.uint8)
    bbox = [30, 40, 70, 90]
    crop = crop_face_only(img, bbox)
    ch, cw = crop.shape[:2]
    assert crop[0, 0].tolist() == [0, 0, 0]
    assert crop[ch - 1, cw - 1].tolist() == [0, 0, 0]
    assert crop[ch // 2, cw // 2].tolist() == [255, 255, 255]


def test_crop_face_only_with_landmarks():
    img = np.full((200, 200, 3), 200, dtype=np.uint8)
    bbox = [70, 60, 130, 170]
    landmarks = [[90, 90], [110, 90], [100, 115], [95, 135], [105, 135]]
    crop = crop_face_only(img, bbox, landmarks)
    assert crop.size > 0
    assert crop.shape[0] >= bbox[3] - bbox[1]