"""Genera un juego de archivos H&M ensuciados a proposito para probar que el job limpia solo.

Simula lo que hara el profesor el dia del examen: mismos nombres de archivo, con datos sucios.
Toma los archivos de data\\examen_bi y escribe en data\\prueba_sucia:
  - transaction.csv : las primeras N lineas del original + lineas sucias (cada una con el resultado esperado)
  - customers.csv, articles.csv, DimFecha.csv : el original + filas sucias al final
  - Temporada.csv : el original + una temporada repetida
  - GoalsHyM.xlsx : el original + metas sucias
Uso: python generar_datos_sucios.py [lineas_de_transacciones]   (por defecto 300000)
"""
import csv, os, shutil, sys
import openpyxl

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
ORIG = os.path.join(BASE, "examen_bi")
DEST = os.path.join(BASE, "prueba_sucia")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300000
os.makedirs(DEST, exist_ok=True)

# ---------------------------------------------------------------- transacciones
with open(os.path.join(ORIG, "transaction.csv"), encoding="cp1252", newline="") as f:
    head = [next(f) for _ in range(N + 1)]
lineas = [l.rstrip("\r\n") for l in head]
ok = lineas[1].split(",")                       # una linea valida para usar de molde
fecha, cliente, articulo, precio, canal, temp = ok
vendidos = {l.split(",")[2] for l in lineas[1:]}
with open(os.path.join(ORIG, "articles.csv"), encoding="utf-8", newline="") as f:
    r = csv.reader(f); next(r)
    articulos = [row[0] for row in r]
sin_ventas = next(a for a in articulos if str(int(a)) not in vendidos)   # articulo que no aparece en la muestra

sucias = [  # (linea, resultado esperado)
    (f"{fecha},{cliente},{articulo},abc,{canal},{temp}",            "ERROR: Precio vacio o no numerico (no se rellena)"),
    (f"{fecha},{cliente},{articulo},,{canal},{temp}",               "ERROR: Precio vacio o no numerico (no se rellena)"),
    (f"{fecha},{cliente},{articulo},0,{canal},{temp}",              "precio 0 -> se carga tal cual (posible oferta)"),
    (f"{fecha},{cliente},{articulo},-5,{canal},{temp}",             "precio negativo -> se carga tal cual (posible devolucion)"),
    (f"{fecha},{cliente},{articulo},\"1184,74\",{canal},{temp}",    "precio 1184,74 -> regla: la coma es decimal, se carga 1184.74"),
    (f"{fecha},{cliente},{articulo},\"1,184\",{canal},{temp}",       "precio 1,184 -> regla: la coma es decimal, se carga 1.184"),
    (f"2019-13-45,{cliente},{articulo},{precio},{canal},{temp}",    "ERROR: Fecha invalida"),
    (f"2019-07-20,{cliente},{articulo},{precio},{canal},{temp}",    "fecha en formato yyyy-mm-dd -> se acepta"),
    (f"25/07/2019,{cliente},{articulo},{precio},{canal},{temp}",    "fecha 25/07/2019 -> sin ambiguedad (no hay mes 25), se acepta"),
    (f"01/02/2019,{cliente},{articulo},{precio},{canal},{temp}",    "fecha 01/02/2019 -> regla: dia/mes/anio, se carga 1 de febrero"),
    (f"20350101,{cliente},{articulo},{precio},{canal},{temp}",      "ERROR: Fecha fuera del calendario"),
    (f"{fecha},,{articulo},{precio},{canal},{temp}",                "ERROR: Cliente vacio"),
    (f"{fecha},NOEXISTE123,{articulo},{precio},{canal},{temp}",     "ERROR: Cliente inexistente"),
    (f"{fecha},{'x' * 300},{articulo},{precio},{canal},{temp}",     "ERROR: Cliente inexistente (ID de 300 caracteres)"),
    (f"{fecha},{cliente},ABC123,{precio},{canal},{temp}",           "ERROR: Articulo invalido"),
    (f"{fecha},{cliente},999999999,{precio},{canal},{temp}",        "ERROR: Articulo inexistente"),
    (f"{fecha},{cliente},{int(sin_ventas)},abc,{canal},{temp}",     "ERROR: Precio vacio o no numerico (no se rellena)"),
    (f"{fecha},{cliente},{articulo},{precio},3,{temp}",             "ERROR: Canal inexistente"),
    (f"{fecha},{cliente},{articulo},{precio},x,{temp}",             "ERROR: Canal invalido"),
    (f"{fecha},{cliente},{articulo},{precio}",                      "ERROR: faltan columnas -> Canal invalido (vacio)"),
    (f"{fecha},{cliente},{articulo},{precio},{canal},99",           "TemporadaID errada -> se deduce de la fecha"),
    (f"{fecha},{cliente},{articulo},{precio},{canal},{temp},EXTRA", "columna de mas -> se ignora (temporada se deduce)"),
] + [(f"20190801,{cliente},{articulo},{precio},{canal},{temp}", "linea identica x3 -> se conserva 1")] * 3

with open(os.path.join(DEST, "transaction.csv"), "w", encoding="cp1252", newline="") as f:
    f.write("\r\n".join(lineas + [s for s, _ in sucias]) + "\r\n")
with open(os.path.join(DEST, "LEEME_lineas_sucias.txt"), "w", encoding="utf-8") as f:
    for s, e in sucias:
        f.write(f"{e}\n    {s[:160]}\n")

# ---------------------------------------------------------------- clientes
shutil.copy(os.path.join(ORIG, "customers.csv"), DEST)
with open(os.path.join(ORIG, "customers.csv"), encoding="cp1252", newline="") as f:
    next(f); c1 = next(f).rstrip("\n").split(",")
with open(os.path.join(DEST, "customers.csv"), "a", encoding="cp1252", newline="") as f:
    f.write(",".join([c1[0], "1.0", "1.0", "ACTIVE", "Regularly", "33", c1[6]]) + "\n")   # ID repetido con otros datos
    f.write(",1.0,1.0,ACTIVE,NONE,40,abc\n")                                              # ID vacio
    f.write("cliente_sucio_01,1,,active ,none,veinte,\n")                                # edad texto, formatos raros
    f.write("cliente_sucio_02,,,,,150,\n")                                               # edad fuera de rango

# ---------------------------------------------------------------- articulos
shutil.copy(os.path.join(ORIG, "articles.csv"), DEST)
with open(os.path.join(ORIG, "articles.csv"), encoding="utf-8", newline="") as f:
    next(f); a1 = next(f).rstrip("\n")
with open(os.path.join(DEST, "articles.csv"), "a", encoding="utf-8", newline="") as f:
    f.write(a1 + "\n")                                   # articulo repetido
    f.write("XYZ" + a1[a1.index(","):] + "\n")           # codigo de articulo invalido

# ---------------------------------------------------------------- calendario y temporadas
shutil.copy(os.path.join(ORIG, "DimFecha.csv"), DEST)
with open(os.path.join(ORIG, "DimFecha.csv"), encoding="cp1252", newline="") as f:
    next(f); d1 = next(f).rstrip("\r\n")
with open(os.path.join(DEST, "DimFecha.csv"), "a", encoding="cp1252", newline="") as f:
    f.write(d1 + "\r\n")                                                  # fecha repetida
    f.write("20190230,2019-02-30,1,Monday,30,61,February,2,9,2019,1,1,1,1,0\r\n")   # fecha imposible
shutil.copy(os.path.join(ORIG, "Temporada.csv"), DEST)
with open(os.path.join(DEST, "Temporada.csv"), "a", encoding="cp1252", newline="") as f:
    f.write("2,primavera-2018,2018-09-22,2018-12-21\r\n")                # temporada repetida

# ---------------------------------------------------------------- metas (Excel)
wb = openpyxl.load_workbook(os.path.join(ORIG, "GoalsHyM.xlsx"))
ws = wb.worksheets[0]
fila = [c.value for c in ws[2]]
ws.append(fila)                                                     # meta repetida
ws.append([fila[0], None] + fila[2:])                               # monto vacio
ws.append([fila[0], -100] + fila[2:4] + [fila[4], 201913])          # monto negativo y mes 13
ws.append([None] + fila[1:])                                        # escenario vacio
ws.append([fila[0], fila[1], "Departamento X", "Seccion X"] + fila[4:])   # departamento inexistente
wb.save(os.path.join(DEST, "GoalsHyM.xlsx"))

print("Archivos sucios en", os.path.abspath(DEST))
print(f"transacciones: {N:,} validas + {len(sucias)} sucias (detalle en LEEME_lineas_sucias.txt)")
