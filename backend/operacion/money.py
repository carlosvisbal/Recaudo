from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

TWOPLACES = Decimal("0.01")

_UNIDADES = [
    "",
    "UN",
    "DOS",
    "TRES",
    "CUATRO",
    "CINCO",
    "SEIS",
    "SIETE",
    "OCHO",
    "NUEVE",
]
_ESPECIALES = {
    10: "DIEZ",
    11: "ONCE",
    12: "DOCE",
    13: "TRECE",
    14: "CATORCE",
    15: "QUINCE",
    16: "DIECISEIS",
    17: "DIECISIETE",
    18: "DIECIOCHO",
    19: "DIECINUEVE",
}
_DECENAS = [
    "",
    "",
    "VEINTE",
    "TREINTA",
    "CUARENTA",
    "CINCUENTA",
    "SESENTA",
    "SETENTA",
    "OCHENTA",
    "NOVENTA",
]
_CENTENAS = [
    "",
    "CIENTO",
    "DOSCIENTOS",
    "TRESCIENTOS",
    "CUATROCIENTOS",
    "QUINIENTOS",
    "SEISCIENTOS",
    "SETECIENTOS",
    "OCHOCIENTOS",
    "NOVECIENTOS",
]


def money(valor) -> Decimal:
    try:
        cuantia = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("El valor no es un importe válido.") from exc
    if not cuantia.is_finite():
        raise ValueError("El valor no es un importe válido.")
    return cuantia.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_cop(valor: Decimal) -> str:
    cuantia = money(valor)
    negativo = cuantia < 0
    cuantia = abs(cuantia)
    entero, frac = f"{cuantia:.2f}".split(".")
    grupos = []
    while entero:
        grupos.append(entero[-3:])
        entero = entero[:-3]
    cuerpo = ".".join(reversed(grupos))
    texto = f"${cuerpo},{frac}"
    return f"-{texto}" if negativo else texto


def _cientos(n: int, sucesor_mil: bool = False) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    centena, resto = divmod(n, 100)
    partes = []
    if centena:
        partes.append(_CENTENAS[centena])
    if resto == 0:
        return " ".join(partes)
    if resto in _ESPECIALES:
        partes.append(_ESPECIALES[resto])
        return " ".join(partes)
    decena, unidad = divmod(resto, 10)
    if decena == 2:
        if unidad == 0:
            partes.append("VEINTE")
        elif unidad == 1:
            partes.append("VEINTIUN" if sucesor_mil else "VEINTIUNO")
        else:
            partes.append("VEINTI" + _UNIDADES[unidad])
    elif decena:
        if unidad == 0:
            partes.append(_DECENAS[decena])
        elif unidad == 1:
            partes.append(f"{_DECENAS[decena]} Y {'UN' if sucesor_mil else 'UNO'}")
        else:
            partes.append(f"{_DECENAS[decena]} Y {_UNIDADES[unidad]}")
    else:
        if unidad == 1:
            partes.append("UN" if sucesor_mil else "UNO")
        else:
            partes.append(_UNIDADES[unidad])
    return " ".join(partes)


def _miles(n: int) -> str:
    if n == 0:
        return ""
    miles, resto = divmod(n, 1000)
    partes = []
    if miles == 1:
        partes.append("MIL")
    elif miles:
        partes.append(f"{_cientos(miles, sucesor_mil=True)} MIL")
    if resto:
        partes.append(_cientos(resto))
    return " ".join(partes)


def entero_a_letras(n: int) -> str:
    if n < 0:
        return "MENOS " + entero_a_letras(-n)
    if n == 0:
        return "CERO"
    millones, resto = divmod(n, 1_000_000)
    billones, millones = divmod(millones, 1_000_000)
    partes = []
    if billones == 1:
        partes.append("UN BILLON")
    elif billones:
        partes.append(f"{_miles(billones)} BILLONES")
    if millones == 1:
        partes.append("UN MILLON")
    elif millones:
        partes.append(f"{_miles(millones)} MILLONES")
    if resto:
        partes.append(_miles(resto))
    return " ".join(partes)


def numero_a_letras(valor) -> str:
    cuantia = money(valor)
    pesos = int(cuantia)
    centavos = int((cuantia - Decimal(pesos)) * 100)
    letras = entero_a_letras(pesos)
    if pesos == 1:
        texto = "UN PESO"
    else:
        texto = f"{letras} PESOS"
    if centavos:
        texto += f" CON {centavos:02d}/100"
    else:
        texto += " M/CTE"
    return texto
