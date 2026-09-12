from types import SimpleNamespace
import numpy as np
from app.services.plate_ocr import PlateOCR


def reader(prediction):
    obj = PlateOCR.__new__(PlateOCR)
    obj.minimum_char_confidence = .90
    obj.model = SimpleNamespace(run=lambda *a,**kw:[prediction])
    return obj


def test_one_weak_character_cannot_hide_behind_high_average_confidence():
    model = reader(SimpleNamespace(plate='GJ01AB1234',char_probs=np.array([.99]*9+[.60])))
    assert model.readtext(np.zeros((40,160,3),dtype=np.uint8)) == []


def test_nonfinite_or_absent_confidence_never_yields_a_plate():
    for probs in [None, np.array([]), np.array([np.nan]), np.array([np.inf])]:
        model = reader(SimpleNamespace(plate='GJ01AB1234',char_probs=probs))
        assert model.readtext(np.zeros((40,160),dtype=np.uint8)) == []


def test_plate_ocr_uses_rgb_pixels_and_keeps_the_exact_text():
    seen=[]
    obj=reader(SimpleNamespace(plate='GJ01AB1234',char_probs=np.array([.99]*10)))
    def run(image,**kwargs):
        seen.append(image.copy())
        return [SimpleNamespace(plate='GJ01AB1234',char_probs=np.array([.99]*10))]
    obj.model.run=run
    image=np.zeros((40,160,3),dtype=np.uint8);image[:]=[10,20,30]
    output=obj.readtext(image)
    assert seen[0][0,0].tolist()==[30,20,10]
    assert output[0][1:] == ('GJ01AB1234',.99)
