# -*- coding: utf-8 -*-
"""Calcula las fechas de vencimiento de las licencias mensuales de SEMS Pro
ajustadas a dias habiles en Colombia (Ley 51 de 1983, 'Ley Emiliani').

No firma nada: solo calcula. Es la entrada para emitir_lote.py
"""
from datetime import date, timedelta

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo anonimo gregoriano)."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(anio, mes, dia + 1)


def siguiente_lunes(d: date) -> date:
    """Ley Emiliani: traslada al lunes siguiente si no cae en lunes."""
    return d if d.weekday() == 0 else d + timedelta(days=(7 - d.weekday()))


def festivos(anio: int) -> dict:
    """Festivos oficiales de Colombia con su nombre."""
    p = pascua(anio)
    fijos = {
        date(anio, 1, 1): "Ano Nuevo",
        date(anio, 5, 1): "Dia del Trabajo",
        date(anio, 7, 20): "Independencia",
        date(anio, 8, 7): "Batalla de Boyaca",
        date(anio, 12, 8): "Inmaculada Concepcion",
        date(anio, 12, 25): "Navidad",
    }
    # Trasladables al lunes siguiente
    trasladables = {
        date(anio, 1, 6): "Reyes Magos",
        date(anio, 3, 19): "San Jose",
        date(anio, 6, 29): "San Pedro y San Pablo",
        date(anio, 8, 15): "Asuncion de la Virgen",
        date(anio, 10, 12): "Dia de la Raza",
        date(anio, 11, 1): "Todos los Santos",
        date(anio, 11, 11): "Independencia de Cartagena",
    }
    res = dict(fijos)
    for d, nombre in trasladables.items():
        res[siguiente_lunes(d)] = nombre
    # Basados en Pascua
    res[p - timedelta(days=3)] = "Jueves Santo"
    res[p - timedelta(days=2)] = "Viernes Santo"
    res[siguiente_lunes(p + timedelta(days=39))] = "Ascension"
    res[siguiente_lunes(p + timedelta(days=60))] = "Corpus Christi"
    res[siguiente_lunes(p + timedelta(days=68))] = "Sagrado Corazon"
    return res


FESTIVOS = {}
for a in (2026, 2027):
    FESTIVOS.update(festivos(a))


def es_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in FESTIVOS


def siguiente_habil(d: date) -> date:
    while not es_habil(d):
        d += timedelta(days=1)
    return d


def motivo_no_habil(d: date) -> str:
    if d in FESTIVOS:
        return f"festivo ({FESTIVOS[d]})"
    if d.weekday() == 5:
        return "sabado"
    if d.weekday() == 6:
        return "domingo"
    return ""


def fmt(d: date) -> str:
    return f"{d.strftime('%d/%m/%Y')} {DIAS[d.weekday()]}"


def calcular(dia_cobro: int = 24, desde=(2026, 9), hasta=(2027, 2)):
    """Devuelve [(fecha_cobro, fecha_vencimiento_ajustada, nota), ...]"""
    filas = []
    anio, mes = desde
    while (anio, mes) <= hasta:
        cobro = date(anio, mes, dia_cobro)
        venc = siguiente_habil(cobro)
        nota = "" if venc == cobro else f"{motivo_no_habil(cobro)} -> se corre al {DIAS[venc.weekday()]}"
        filas.append((cobro, venc, nota))
        mes += 1
        if mes > 12:
            mes, anio = 1, anio + 1
    return filas


if __name__ == "__main__":
    print("FESTIVOS COLOMBIA en el rango (sep 2026 - feb 2027)")
    print("=" * 62)
    for d in sorted(FESTIVOS):
        if date(2026, 9, 1) <= d <= date(2027, 3, 1):
            print(f"  {fmt(d):26} {FESTIVOS[d]}")

    print("\nVENCIMIENTOS DE LICENCIA (ajustados a dia habil)")
    print("=" * 62)
    for i, (cobro, venc, nota) in enumerate(calcular(), start=1):
        etiqueta = f"Licencia {i}"
        print(f"  {etiqueta:12} cobro {fmt(cobro):22} vence {fmt(venc):22} {nota}")
