"""Genera docs/Guia_Exposicion_HM.docx: guion de la exposicion del examen final (orden, que mostrar, que decir,
preguntas probables y consultas listas para copiar). Sin cifras fijas: los numeros se leen en vivo.
Uso (con Word cerrado): python generar_guia_exposicion.py
"""
import os
import docx
from docx.shared import Pt, RGBColor, Cm

DIR = os.path.dirname(os.path.abspath(__file__))
NAVY = "1F3A5F"

PASOS_DIA = [
    "Copiar los archivos nuevos del profesor a proyecto\\data\\examen_bi (mismos nombres: transaction.csv, customers.csv, "
    "articles.csv, DimFecha.csv, Temporada.csv, GoalsHyM.xlsx).",
    "(Opcional, para partir de cero) Ejecutar sql\\13_vaciar_para_demo.sql y vaciar el cubo (SSMS → Analysis Services → "
    "Tabular_HM → Procesar base de datos → Procesar borrado).",
    "SSMS → Agente SQL Server → Trabajos → Job_HM → Iniciar trabajo en el paso… → paso 1.",
    "Seguirlo en Monitor de actividad de trabajos o en Ver historial (3 pasos: Stage → DWH → Cubo).",
    "Al terminar: sql\\03_validaciones.sql (Diferencia = 0, SinExplicar = 0) y abrir PowerBI\\HM_Dashboard.pbip → Actualizar.",
]

GUION = [  # (bloque, minutos, que mostrar, que decir)
    ("1. Contexto y pregunta", "1",
     "Caso_HM.docx, secciones 1 a 3.",
     "H&M vende en tienda y online; queremos saber quién compra, qué se vende, cómo evoluciona la venta, cómo se comparan "
     "las temporadas y si se cumplen las metas. La solución es de punta a punta: un Job deja todo listo en Power BI."),
    ("2. Arquitectura", "1",
     "Explorador de soluciones en Visual Studio (H&M.sln: stage_H&M, DWH_H&M, Tabular_HM).",
     "Archivos → Stage (copia fiel, texto) → Datamart (limpieza, modelo estrella) → Cubo tabular → Power BI. Proyectos "
     "separados, como pidió el profesor (divide y vencerás)."),
    ("3. Ejecutar el Job", "1",
     "SSMS → Agente SQL Server → Job_HM → Propiedades (Pasos y Avanzado) → Iniciar en el paso 1.",
     "Paso 1 carga el Stage, paso 2 el Datamart, paso 3 procesa el cubo; cada paso pasa al siguiente solo si terminó bien. "
     "Configurado como en el Laboratorio 4."),
    ("4. Stage", "2",
     "STAGE_HM → Tablas → Seleccionar las primeras 1000 filas; consulta de conteo por archivo.",
     "Todo como texto y sin valores por defecto: si viene data sucia, la carga no se cae; la limpieza se hace en el DWH."),
    ("5. Calidad de datos por tabla", "3",
     "sql\\14_inconsistencias_stage.sql (un bloque por archivo: filas, inconsistencias en el Stage y cómo quedó en el DWH). "
     "Consultas de la sección “Consultas”: duplicados (COUNT(1)…GROUP BY…ORDER BY 1 DESC), una línea repetida en el "
     "Stage frente a una sola fila en FactVentas con LineasOrigen, tablas de error y CalidadDatos.",
     "Lo que se puede recalcular se corrige (Fin_Semana desde la fecha); lo ambiguo sigue una regla explícita; lo que no "
     "sirve va a la tabla de error con su valor original. Nada se pierde sin explicación."),
    ("6. Datamart y ETL de hechos", "2",
     "FactVentas.dtsx → flujo FACT VENTAS: Origen de OLE DB (consulta), Lookups, División condicional, destinos.",
     "La consulta de origen agrupa las líneas idénticas, convierte los tipos, multiplica el precio por 40 000 con 4 "
     "decimales y asigna la temporada por la fecha; los Lookups traen las llaves; lo inválido va a ErrorFactVentas."),
    ("7. Auditoría", "1",
     "SELECT de DIM_AUDIT (columnas del laboratorio + FilasInsertadas, FilasActualizadas, FilasDuplicadas, FilasError, "
     "MensajeError).",
     "Cada paquete registra antes y después, cuánto insertó, actualizó, descartó y rechazó; si falla, guarda el mensaje "
     "(controlador OnError)."),
    ("8. Cubo", "1",
     "Tabular_HM: tablas, relaciones (FactVentas y FactMetas con DimTemporada, DimFecha, DimDepartamento) y medidas.",
     "Las medidas DAX se definen una vez; los 5 dashboards las usan. La meta se usa tal como viene (por mes)."),
    ("9. Los 5 dashboards", "4",
     "Power BI: 1 Clientes, 2 Artículos, 3 Transacciones, 4 Temporadas y fechas, 5 Metas. Usar los filtros Año, Comparar "
     "con, Temporada y Escenario.",
     "Cada uno responde una pregunta; nada está escrito a mano: si llegan años nuevos aparecen solos."),
    ("10. Cierre", "1",
     "sql\\03_validaciones.sql.",
     "Stage = cargado + duplicados + error, diferencia 0: el dato del dashboard es confiable."),
]

QA = [
    ("¿Cómo detectaste los duplicados?", "Con COUNT(1)…GROUP BY de todas las columnas…ORDER BY 1 DESC. Si la fila completa "
     "se repite, es el mismo registro y me quedo con uno (criterio del profesor). En ventas lo hago en la consulta de origen "
     "de FactVentas; LineasOrigen guarda cuántas venían. En las maestras uso ROW_NUMBER y la copia va a ErrorMaestro."),
    ("¿Por qué no usaste DISTINCT?", "Porque DISTINCT pierde la cuenta. Con GROUP BY + COUNT conservo cuántas venían "
     "(LineasOrigen) y el cuadre da exacto; en las maestras uso ROW_NUMBER, como recomendó el profesor."),
    ("¿Y si solo cambia el precio o el canal?", "No es el mismo registro: puede ser otra compra (con descuento, o en "
     "otro canal). Se cargan las dos; elegir una sería un supuesto."),
    ("¿Dónde multiplicaste por 40 000?", "En el ETL del DWH, después del Stage: FactVentas.dtsx → FACT VENTAS → Origen de "
     "OLE DB, con 4 decimales. El Stage guarda el price original para poder comparar."),
    ("¿Y si el precio viene con coma, letras o vacío?", "La coma se lee como decimal (regla del proyecto) y se multiplica. "
     "Letras o vacío no son un número: la fila va a ErrorFactVentas con su valor original. 0 o negativo se carga tal cual "
     "(oferta o devolución)."),
    ("¿Cómo manejas las fechas?", "Formatos del caso: yyyymmdd y yyyy-mm-dd. Con “/” se lee día/mes/año; si el segundo "
     "número es mayor que 12 solo puede ser mes/día. Una fecha imposible va a error."),
    ("¿Cómo relacionas las ventas con la temporada?", "Con la fecha de cada venta busco en qué rango de Temporada.csv "
     "cae (Lookup “DimTemporada (por fecha)”). El día de cambio aparece en dos temporadas: lo asigno a la que termina, "
     "igual que el TemporadaID del archivo de ventas."),
    ("¿De dónde salen las metas?", "De GoalsHyM.xlsx: monto por escenario, departamento, sección, temporada y año-mes. Se "
     "cargan tal como vienen; se comparan con la venta por sección, temporada y mes. Por defecto el Escenario 2."),
    ("¿Por qué el cumplimiento sale tan lejos de 100 %?", "Porque, tal como viene, la meta no está en la escala de la "
     "venta (el precio se multiplica por 40 000 y la meta no). No la ajusté para no suponer: es un hallazgo a validar."),
    ("¿Qué errores encontraste?", "Leer CalidadDatos (sección 7 de 03_validaciones): Fin_Semana mal calculado, datos "
     "ausentes en clientes y artículos, clientes con datos contradictorios, código postal por defecto, escenarios de "
     "metas desordenados, y los duplicados en ventas."),
    ("¿Por qué las tablas de error están vacías?", "Porque con esta data no hubo filas inválidas: cada carga limpia la "
     "tabla y muestra solo los errores de esa ejecución. Lo que entró con problemas está en CalidadDatos."),
    ("¿Por qué MERGE y no DELETE en las dimensiones?", "Las dimensiones de cliente y producto son dinámicas: MERGE inserta "
     "lo nuevo y actualiza lo que cambió sin borrar ni regenerar las llaves (como dijo el profesor)."),
    ("¿Por qué el Stage es todo texto?", "Para que llegue el dato crudo: si le pongo tipos o valores por defecto, un "
     "error queda escondido (como el 0 por defecto que vio el profesor en otro grupo)."),
    ("¿Cómo sé que no se perdió nada?", "03_validaciones: por cada archivo, Stage = cargado + duplicados + error; "
     "Diferencia y SinExplicar en 0."),
    ("¿Qué pasa si un paquete falla?", "El Job se detiene en ese paso; DIM_AUDIT queda en N con el MensajeError; el cubo "
     "sigue con la última carga buena."),
    ("¿Por qué ventas y no utilidad?", "Los archivos no traen costos; el descuento implícito es el sustituto del margen."),
]

CONSULTAS = [
    ("Filas por archivo en el Stage",
     "SELECT 'transaction' Archivo, COUNT_BIG(*) Filas FROM STAGE_HM.HM.StageTransactions\n"
     "UNION ALL SELECT 'customers', COUNT_BIG(*) FROM STAGE_HM.HM.StageCustomers\n"
     "UNION ALL SELECT 'articles',  COUNT_BIG(*) FROM STAGE_HM.HM.StageArticles\n"
     "UNION ALL SELECT 'goals',     COUNT_BIG(*) FROM STAGE_HM.HM.StageGoals\n"
     "UNION ALL SELECT 'fecha',     COUNT_BIG(*) FROM STAGE_HM.HM.StageFecha\n"
     "UNION ALL SELECT 'temporada', COUNT_BIG(*) FROM STAGE_HM.HM.StageTemporada;"),
    ("Duplicados en ventas (método del profesor)",
     "SELECT TOP 10 COUNT(1) Veces, t_dat, customer_id, article_id, price, sales_channel_id, TemporadaID\n"
     "FROM STAGE_HM.HM.StageTransactions\n"
     "GROUP BY t_dat, customer_id, article_id, price, sales_channel_id, TemporadaID ORDER BY 1 DESC;"),
    ("La misma venta en el DWH (cambiar cliente, artículo y fecha)",
     "SELECT c.CustomerID, a.ArticleID, f.FechaKey, f.Precio, f.LineasOrigen\n"
     "FROM DWH_HM.Ventas.FactVentas f\n"
     "JOIN DWH_HM.Ventas.DimCliente c ON c.ClienteKey = f.ClienteKey\n"
     "JOIN DWH_HM.Ventas.DimArticulo a ON a.ArticuloKey = f.ArticuloKey\n"
     "WHERE c.CustomerID = '<cliente>' AND a.ArticleID = <articulo> AND f.FechaKey = <yyyymmdd>;"),
    ("Cuadre de ventas",
     "SELECT (SELECT COUNT_BIG(*) FROM STAGE_HM.HM.StageTransactions) Lineas_Stage,\n"
     "       (SELECT COUNT_BIG(*) FROM DWH_HM.Ventas.FactVentas) Filas_Fact,\n"
     "       (SELECT SUM(CAST(LineasOrigen AS BIGINT)) - COUNT_BIG(*) FROM DWH_HM.Ventas.FactVentas) Duplicados,\n"
     "       (SELECT ISNULL(SUM(CAST(LineasOrigen AS BIGINT)), 0) FROM DWH_HM.Ventas.ErrorFactVentas) Lineas_Error;"),
    ("Precio × 40 000 (archivo frente a DWH)",
     "SELECT TOP 5 s.price, f.Precio, f.Precio / TRY_CONVERT(FLOAT, s.price) Factor\n"
     "FROM STAGE_HM.HM.StageTransactions s\n"
     "JOIN DWH_HM.Ventas.DimCliente c ON c.CustomerID = s.customer_id\n"
     "JOIN DWH_HM.Ventas.DimArticulo a ON a.ArticleID = TRY_CONVERT(INT, s.article_id)\n"
     "JOIN DWH_HM.Ventas.FactVentas f ON f.ClienteKey = c.ClienteKey AND f.ArticuloKey = a.ArticuloKey\n"
     "                               AND f.FechaKey = TRY_CONVERT(INT, s.t_dat);"),
    ("Auditoría de la última carga",
     "SELECT TOP 20 AuditKey, TableName, ExecStartDT, TableInitialRowCnt, TableFinalRowCnt, FilasInsertadas,\n"
     "       FilasActualizadas, FilasDuplicadas, FilasError, SuccessfulProcessingInd, MensajeError\n"
     "FROM DWH_HM.dbo.DIM_AUDIT ORDER BY AuditKey DESC;"),
    ("Tablas de error",
     "SELECT * FROM DWH_HM.Ventas.ErrorFactVentas;\nSELECT * FROM DWH_HM.Ventas.ErrorFactMetas;\n"
     "SELECT * FROM DWH_HM.dbo.ErrorMaestro;   -- una fila del archivo: WHERE FilaOrigen = <n> en su tabla del Stage"),
    ("Calidad de datos de la carga",
     "SELECT Entidad, Campo, TipoProblema, Descripcion, Tratamiento, Cantidad\n"
     "FROM DWH_HM.dbo.CalidadDatos ORDER BY AuditKey DESC, Entidad, Campo;"),
    ("Fecha imposible (TRY_CONVERT)",
     "SELECT TRY_CONVERT(DATE, '2019-02-28') Valida, TRY_CONVERT(DATE, '2019-02-30') Invalida;"),
]

RIESGOS = [
    ("F5 en Visual Studio da “Unexpected internal error”", "Usar clic derecho en el paquete → Ejecutar paquete."),
    ("Disco lleno", "Liberar espacio antes (15–20 GB libres); no correr consultas pesadas mientras corre el Job."),
    ("El Job falla", "Ver historial del Job y la columna MensajeError de DIM_AUDIT; el cubo conserva la última carga buena."),
    ("La carga de 31 millones tarda", "Mientras corre, explicar el Stage, la calidad de datos y el ETL; el cubo se procesa al final."),
    ("Power BI no muestra datos nuevos", "Inicio → Actualizar (conexión en vivo al cubo)."),
]


def titulo(d, t, size=14):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = True; r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(NAVY)


def vineta(d, k, v=None):
    p = d.add_paragraph(style="List Bullet")
    if v is None: p.add_run(k)
    else: r = p.add_run(k + " "); r.bold = True; p.add_run(v)


def tabla(d, enc, filas, anchos=None):
    t = d.add_table(rows=1, cols=len(enc)); t.style = "Light Grid Accent 1"
    for i, h in enumerate(enc): t.rows[0].cells[i].text = h
    for f in filas:
        c = t.add_row().cells
        for i, v in enumerate(f): c[i].text = v
    for row in t.rows:
        for i, c in enumerate(row.cells):
            if anchos: c.width = Cm(anchos[i])
            for p in c.paragraphs:
                for r in p.runs: r.font.size = Pt(9)
    d.add_paragraph()


def guia():
    d = docx.Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2); s.top_margin = s.bottom_margin = Cm(1.8)
    titulo(d, "Guía de exposición · Caso H&M (examen final)", 17)
    d.add_paragraph("Orden de la exposición, qué mostrar, qué decir, preguntas probables y consultas listas para copiar. "
                    "Los números se leen en vivo: cambian con los datos que envíe el profesor.")

    titulo(d, "1. El día del examen (datos nuevos)")
    for i, t in enumerate(PASOS_DIA, 1):
        d.add_paragraph(f"{i}. {t}")

    titulo(d, "2. Guion de la exposición (≈ 18 minutos)")
    tabla(d, ["Bloque", "Min", "Qué mostrar", "Qué decir"], GUION, [3.2, 1, 5.8, 7])

    titulo(d, "3. Preguntas probables y respuestas")
    for q, a in QA:
        vineta(d, q, a)

    titulo(d, "4. Consultas listas para copiar")
    for t, q in CONSULTAS:
        p = d.add_paragraph(); r = p.add_run(t); r.bold = True
        p = d.add_paragraph(); r = p.add_run(q); r.font.name = "Consolas"; r.font.size = Pt(8.5)

    titulo(d, "5. Si algo sale mal")
    tabla(d, ["Problema", "Qué hacer"], RIESGOS, [6, 11])

    titulo(d, "6. Frases clave")
    for t in ["“Nunca confiar en los datos: el Stage recibe todo tal como viene y la limpieza se demuestra en SQL.”",
              "“Si es el mismo registro, me quedo con uno; si cambia algún dato, es otra compra.”",
              "“Lo que se puede recalcular se corrige; lo ambiguo sigue una regla explícita; lo que no sirve va a error con su valor original.”",
              "“Nada se pierde sin explicación: Stage = cargado + duplicados + error, diferencia 0.”",
              "“Trabajo con los datos que tengo: lo demás son supuestos.”"]:
        vineta(d, t)

    ruta = os.path.join(DIR, "Guia_Exposicion_HM.docx")
    d.save(ruta)
    return ruta


if __name__ == "__main__":
    print("OK:", guia())
