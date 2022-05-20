import re

def contiene_caracteres_ilegales(palabra):
    x = re.findall("[+/!#$%&(=?¡*¨+´}[_-.:,;><|°¬~`^])]", palabra)
    if x:
        return True
    else:
        return False

def contiene_letras(numero):
    x = re.findall("[a-zA-Z]", numero)
    if x:
        return True
    else:
        return False

def es_precio(precio):
    x = re.findall("[+/!#$%&\(=?¡*¨+´\}_\\\[:,;><|°¬~`^\)\]]", precio)
    if x:
        return False
    else:
        return True