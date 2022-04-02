import upnqr

data = upnqr.Data(
    placnik = upnqr.Placnik(
        ime='Ime Plačnika',
        ulica='Plačnikova ulica 1',
        kraj='Kraj Plačnika'),
    prejemnik = upnqr.Prejemnik(
        ime='Ime Prejemnika',
        ulica='Prejemnikova ulica 1',
        kraj='Kraj Prejemnika',
        iban='SI56043020002997963'),
    znesek = 42.00,
    koda_namena = 'COST',
    namen_placila = 'Namen plačila',
    rok_placila = '2022-05-01',
    referenca = 'SI1212345678909'
)

qr = upnqr.make_from_data(data)
upnqr.to_pil(qr).save('out.png')

#print(upnqr.to_text(qr, border=4))
