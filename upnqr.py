import datetime
import re
import math
import PIL.Image
from pydantic import validator
from pydantic.dataclasses import dataclass
from qrcodegen import QrSegment, QrCode

ENCODING = "ISO-8859-2"
PATTERN_KODA_NAMENA = re.compile("^[A-Z]{4}$")
PATTERN_IBAN = re.compile("^[A-Z]{2}\d{2}(\d{4}){3}\d{3}$") # Not really IBAN, but good enough
PATTERN_REFERENCA = re.compile("^[A-Z]{2}[0-9]{2}[A-Z0-9-]{0,22}$")

def _constrain_length(field, maxLength):
    """Validator: ensures that the string does not exceed the given length."""
    def validatorFn(value):
        if len(value) > maxLength:
            raise ValueError('field too long')
        return value
    return validator(field, allow_reuse=True)(validatorFn)

def _constrain_pattern(field, regex):
    """Validator: ensures that the string matches the given regular expression."""
    def validatorFn(value):
        if not regex.match(value):
            raise ValueError('incorrectly formatted field')
        return value
    return validator(field, allow_reuse=True)(validatorFn)

# NOTE: This whole UPN QR thing is somewhat specific to Slovenia, and to keep a clear
# relation to the UPN QR specification, the field names in the data classes below are
# in Slovene.

@dataclass
class Oseba:
    """Dataclass representing a person/entity."""
    ime : str
    ulica : str
    kraj : str

    _validator_ime = _constrain_length('ime', 33)
    _validator_ulica = _constrain_length('ulica', 33)
    _validator_kraj = _constrain_length('kraj', 33)

@dataclass
class Placnik(Oseba):
    """Payer data."""
    pass

@dataclass
class Prejemnik(Oseba):
    """Recipient data."""
    iban : str

    _validator_iban = _constrain_pattern('iban', PATTERN_IBAN)

@dataclass
class Data:
    """Data in the UPN form."""
    placnik : Placnik
    prejemnik : Prejemnik
    znesek : float
    koda_namena : str
    namen_placila : str
    rok_placila : datetime.date
    referenca : str

    _validator_koda_namena = _constrain_pattern('koda_namena', PATTERN_KODA_NAMENA)
    _validator_namen_placila = _constrain_length('namen_placila', 42)
    _validator_referenca = _constrain_pattern('referenca', PATTERN_REFERENCA)

    @validator('znesek')
    def _validator_znesek(cls, value):
        if value < 0 or value >= 1e9:
            raise ValueError('invalid amount')
        return value

def control_sum(inputStrings):
    """Calculates the control sum for the given UPN string."""
    return str(sum([len(string) for string in inputStrings]) + 19).zfill(3)

def upn_string(data):
    """Formats the UPN data according to the UPN QR specification."""
    fields = [
        'UPNQR',
        '', # IBAN plačnika
        '', # polog
        '', # dvig
        '', # referenca plačnika
        data.placnik.ime,
        data.placnik.ulica,
        data.placnik.kraj,
        f'{math.floor(data.znesek * 100)}'.zfill(11),
        '', # datum plačila
        '', # nujno
        data.koda_namena,
        data.namen_placila,
        data.rok_placila.strftime('%d.%m.%Y'),
        data.prejemnik.iban,
        data.referenca,
        data.prejemnik.ime,
        data.prejemnik.ulica,
        data.prejemnik.kraj,
    ]

    reserved = ''
    return '\n'.join(fields + [control_sum(fields)] + [reserved])

def make_from_string(string, mask=-1):
    """Creates a QR object from the string formatted by upn_string()."""
    segments = [QrSegment.make_eci(4), QrSegment.make_bytes(string.encode(ENCODING))]
    return QrCode.encode_segments(
        segments,
        ecl=QrCode.Ecc.MEDIUM,
        minversion=15,
        maxversion=15,
        boostecl=False,
        mask=mask)

def make_from_data(data):
    """Convenience function that generates a QR object directly from a Data object."""
    return make_from_string(upn_string(data))

def transform(qr, fn, border=0):
    """Transforms a QR object to a list. Each element in the list represents one line of
    the QR code, and is itself a list of elements representing the modules (pixels) within
    the line. Each element is formed by calling the given transformation function.
    
        qr: The code to transform.
        fn: The transformation function with a signature fn(x, y, value). x and y are the
            coordinates of the module, and value is a boolean: True for black, False for
            white.
        border: The number of additional (white) border modules around the QR code.
    """
    size = qr.get_size()
    element = lambda x, y: fn(x, y, qr.get_module(x, y))
    line = lambda y: [element(x, y) for x in range(-border, size + border)]
    return [line(y) for y in range(-border, size + border)]

def to_text(qr, black=' '*2, white='\u2588'*2, border=0):
    """Transforms a QR object to text.
        qr: The code to transform.
        black: The string to use for a black module.
        white: The string to use for a white module.
        border: The number of additional (white) border modules around the QR code.
    """
    to_chars = lambda x, y, module: black if module else white
    transformed = transform(qr, to_chars, border)
    return '\n'.join(''.join(line) for line in transformed)

def to_svg(qr, border: int = 0) -> str:
    """Transforms a QR object to an SVG image.
        qr: The code to transform.
        border: The number of additional (white) border modules around the QR code.
    """
    if border < 0:
        raise ValueError("Border must be non-negative")
    to_paths = lambda x, y, module: f"M{x+border},{y+border}h1v1h-1z" if module else ''
    transformed = transform(qr, to_paths, border)
    parts = [elm for line in transformed for elm in line if elm]
    box_size = qr.get_size() + border*2
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 {box_size} {box_size}" stroke="none">
        <rect width="100%" height="100%" fill="#FFFFFF"/>
        <path d="{' '.join(parts)}" fill="#000000"/>
</svg>
"""

def to_pil(qr, border=0):
    """Transforms a QR object to a PIL Image. The resulting image has one pixel per QR
    module (plus border, if any). If you need a larger one, simply resize it afterwards:
    img.resize((new_size, new_size), PIL.Image.Resampling.NEAREST)

        qr: The code to transform.
        border: The number of additional (white) border modules around the QR code.
    """
    flatten = lambda lst: [elm for sublist in lst for elm in sublist]
    to_pixels = lambda x, y, module: 0 if module else 1
    size = qr.get_size() + 2 * border
    img = PIL.Image.new('1', (size, size))
    img.putdata(flatten(transform(qr, to_pixels, border)))
    return img
