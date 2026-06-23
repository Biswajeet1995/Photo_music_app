import numpy as np
import cv2

from verify import verify_image


def test_verify_image_missing_files_returns_false_zero():
    matched, score = verify_image("missing_uploaded.jpg", "missing_target.jpg")
    assert matched is False
    assert score == 0


def test_verify_image_blank_image_returns_false_zero(tmp_path):
    blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
    blank_path = tmp_path / "blank.jpg"
    cv2.imwrite(str(blank_path), blank_image)

    matched, score = verify_image(str(blank_path), str(blank_path))
    assert matched is False
    assert isinstance(score, int)
