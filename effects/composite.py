"""Multiple exposure compositing via additive blending."""

import numpy as np
from PyQt6.QtGui import QImage
from .postprocess import qimage_to_array, array_to_qimage


class ExposureCompositor:
    """Accumulates multiple rhythmogram exposures via additive blending.

    Mimics light accumulation on photographic paper.
    """

    def __init__(self):
        self._accumulator = None

    def add_exposure(self, image: QImage):
        """Add a new exposure to the composite."""
        arr = qimage_to_array(image).astype(np.float32)
        if self._accumulator is None:
            self._accumulator = arr
        else:
            self._accumulator = np.minimum(self._accumulator + arr, 255.0)

    def get_composite(self) -> QImage:
        """Return the current composite as a QImage."""
        if self._accumulator is None:
            return QImage()
        return array_to_qimage(self._accumulator.astype(np.uint8))

    def reset(self):
        self._accumulator = None

    @property
    def exposure_count(self) -> int:
        return 0 if self._accumulator is None else 1
