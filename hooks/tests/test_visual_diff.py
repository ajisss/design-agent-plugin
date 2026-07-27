import os
import importlib.util
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "visual_diff", os.path.join(os.path.dirname(__file__), "..", "visual-diff.py")
)
visual_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual_diff)


def test_prepare_for_diff_same_size_no_mismatch_flag():
    ref = Image.new("RGB", (800, 600), "white")
    res = Image.new("RGB", (800, 600), "white")
    ref_c, res_c, meta = visual_diff.prepare_for_diff(ref, res)
    assert ref_c.size == res_c.size == (800, 600)
    assert meta["size_mismatch"] is False


def test_prepare_for_diff_crops_to_common_region_without_stretching():
    ref = Image.new("RGB", (800, 600), "white")
    res = Image.new("RGB", (1000, 900), "white")  # aspect ratio beda
    ref_c, res_c, meta = visual_diff.prepare_for_diff(ref, res)
    # harus di-crop ke area overlap (800x600), BUKAN di-resize/stretch ke (800,600)
    assert ref_c.size == (800, 600)
    assert res_c.size == (800, 600)
    assert meta["size_mismatch"] is True
    assert meta["reference_size"] == (800, 600)
    assert meta["result_size"] == (1000, 900)
