
from __future__ import annotations

import cv2
import numpy as np


def calculate_ndvi_rgb(image_bgr: np.ndarray) -> tuple[float, np.ndarray]:
    """
    Estimate a vegetation index from an RGB image (BGR channel order).

    :param image_bgr: image as BGR numpy array (OpenCV convention)
    :return: (ndvi_mean, ndvi_image) — mean index in [-1, 1] and a colour-mapped
             visualisation image with the same height/width as the input.
    """
    b = image_bgr[:, :, 0].astype(np.float32)
    g = image_bgr[:, :, 1].astype(np.float32)
    r = image_bgr[:, :, 2].astype(np.float32)

    denom = 2.0 * g + r + b
    denom[denom == 0.0] = 1.0  # guard fully-black pixels
    index = (2.0 * g - r - b) / denom
    index = np.clip(index, -1.0, 1.0)

    ndvi_mean = float(np.mean(index))

    # Visualisation: map [-1, 1] → [0, 255], green areas = healthier vegetation.
    norm = ((index + 1.0) / 2.0 * 255.0).astype(np.uint8)
    ndvi_image = cv2.applyColorMap(norm, cv2.COLORMAP_JET)

    return ndvi_mean, ndvi_image
