import re
import sys
from qrcodegen import QrSegment, QrCode

ENCODING = "ISO-8859-2"
PATTERN_DATE = re.compile("^(?:0[1-9]|[12][0-9]|3[01])\.(?:0[1-9]|1[0-2])\.20[0-9]{2}$") # don't need to be too clever...
PATTERN_KODA_NAMENA = re.compile("^[A-Z]{4}$")
PATTERN_IBAN = re.compile("^[A-Z]{2}\d{2} ?\d{4} ?\d{4} ?\d{4} ?\d{3}$") # TODO: not really IBAN...
PATTERN_REFERENCA = re.compile("^[A-Z]{2}[0-9]{2}[ ]?[A-Z0-9]{0,22}$")

class UPNQR:
    def __init__(self, imePlacnika, ulicaStPlacnika, krajPlacnika, znesek, kodaNamena, namenPlacila, rokPlacila, ibanPrejemnika, referencaPrejemnika, imePrejemnika, ulicaStPrejemnika, krajPrejemnika, mask=-1):
        self.upnString = generateUpnString(imePlacnika, ulicaStPlacnika, krajPlacnika, znesek, kodaNamena, namenPlacila, rokPlacila, ibanPrejemnika, referencaPrejemnika, imePrejemnika, ulicaStPrejemnika, krajPrejemnika)
        self.qr = generateQr(self.upnString, mask=mask)
    
    def exportSvg(self, outputName, borderSize=4):
        with open(outputName, "w") as file:
            file.write(self.upnqr.to_svg_str(borderSize))

def calcKontrolnaVsota(inputStrings):
    checksum = str(5 + sum([len(string) for string in inputStrings]) + 19).zfill(3)
    return checksum

def generateUpnString(imePlacnika, ulicaStPlacnika, krajPlacnika, znesek, kodaNamena, namenPlacila, rokPlacila, ibanPrejemnika, referencaPrejemnika, imePrejemnika, ulicaStPrejemnika, krajPrejemnika):

    checkString(imePlacnika, 33)
    checkString(ulicaStPlacnika, 33)
    checkString(krajPlacnika, 33)
    formattedZnesek = formatAmount(znesek)
    checkKodaNamena(kodaNamena)
    checkString(namenPlacila, 42)
    checkDate(rokPlacila)
    formattedIban = formatIban(ibanPrejemnika)
    formattedReferenca = formatReferenca(referencaPrejemnika)
    checkString(imePrejemnika, 33)
    checkString(ulicaStPrejemnika, 33)
    checkString(krajPrejemnika, 33)
    kontrolnaVsota = calcKontrolnaVsota([imePlacnika, ulicaStPlacnika, krajPlacnika, formattedZnesek, kodaNamena, namenPlacila, rokPlacila, formattedIban, formattedReferenca, imePrejemnika, ulicaStPrejemnika, krajPrejemnika])
    
    string = f"""UPNQR




{imePlacnika}
{ulicaStPlacnika}
{krajPlacnika}
{formattedZnesek}


{kodaNamena}
{namenPlacila}
{rokPlacila}
{formattedIban}
{formattedReferenca}
{imePrejemnika}
{ulicaStPrejemnika}
{krajPrejemnika}
{kontrolnaVsota}
"""
    return string
        
def generateQr(inputString, mask=-1):
    segments = [QrSegment.make_eci(4), QrSegment.make_bytes(inputString.encode(ENCODING))]
    qr = QrCode.encode_segments(segments, ecl=QrCode.Ecc.MEDIUM, minversion=15, maxversion=15, boostecl=False, mask=mask)
    return qr

def checkDate(inputString):
    if not PATTERN_DATE.match(inputString):
        raise Exception(f"Input string \"{inputString}\" is not a valid date!")

def checkKodaNamena(inputString):
    if not PATTERN_KODA_NAMENA.match(inputString):
        raise Exception(f"Input string \"{inputString}\" is not a koda namena!")

def formatAmount(inputString, maxLen=11):
    outputString = ''.join(filter(lambda i: i.isdigit(), inputString))
    outputString = outputString.zfill(maxLen)
    if len(outputString) > maxLen:
        raise Exception(f"Input string \"{inputString}\" too long!")
    return outputString

def formatIban(inputString):
    if not PATTERN_IBAN.match(inputString):
        raise Exception(f"Input string \"{inputString}\" is not an IBAN!")
    return inputString.replace(" ", "")

def formatReferenca(inputString):
    if not PATTERN_REFERENCA.match(inputString):
        raise Exception(f"Input string \"{inputString}\" is not a referenca!")
    return inputString.replace(" ", "")

def checkString(inputString, maxLen):
    if inputString.strip() != inputString:
        raise Exception(f"Input string \"{inputString}\" must not start or end with whitespaces!")
    if len(inputString) > maxLen:
        raise Exception(f"Input string \"{inputString}\" too long!")
    checkEncoding(inputString)

def checkEncoding(inputString):
    try:
        inputString.encode(ENCODING)
    except UnicodeDecodeError:
        print(f"Cannot encode \"{inputString}\" to {ENCODING}!")
        raise
        
if __name__ == "__main__":
    if len(sys.argv) >= 13:
        upnqr = UPNQR(*sys.argv[1:14])
        print(upnqr.upnString)
    else:
        print("No input provided!")