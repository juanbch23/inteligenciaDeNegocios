# H&M: recuperar la tienda sin regalar el margen

*Indicadores verificados y propuesta de dashboards — estructura del caso integrador “Grupo Comercial Andino”,
aplicada a los datos reales del proyecto.*

> Todas las cifras salen del DWH cargado (`DWH_HM`, 31,788,324 transacciones del 20/09/2018 al 22/09/2020)
> y se pueden reproducir con `sql/05_indicadores.sql`. Los importes están en la unidad de `price` del archivo
> (la fuente no declara moneda).

---

## 1. Contexto y origen del problema

H&M vende moda por **dos canales**: tienda física (canal 1) y online (canal 2). En dos años registra
**88,465 M** en ventas, **1.36 M de clientes compradores** y **105 mil artículos**, organizados en 56 secciones.
El área comercial fija **metas diarias por departamento/sección y temporada** en tres escenarios (GoalsHyM.xlsx).

La foto global parece sana: las ventas **superan la meta del Escenario 2 en 110 %**. Pero al mirar el mismo periodo
de 2020 contra 2019, la calidad del resultado se deterioró:

| Síntoma (ene – 22 sep) | 2019 | 2020 | Cambio |
|---|---|---|---|
| Ventas totales | 33,348 M | 29,817 M | **−10.6 %** |
| Ventas tienda física | 8,316 M | 6,496 M | **−21.9 %** |
| Ventas online | 25,032 M | 23,321 M | −6.8 % |
| Participación online | 75.1 % | 78.2 % | +3.1 pp |
| Ticket por cesta online (año) | 12,724 | 11,528 | −9.4 % |
| Artículos por cesta online (año) | 4.25 | 3.96 | −0.29 |
| Descuento implícito en tienda (año) | 19.4 % | 20.9 % | +1.5 pp |
| Clientes nuevos | 535,691 (año completo) | 245,404 (hasta septiembre) | menos captación |

**Lo que pasó:** en **abril de 2020 la tienda física vendió 0** (100 % online) y en marzo cayó a 381 M, frente a
~900 M de un mes normal: el cierre por la pandemia. El online absorbió parte del golpe (abril 2020: 3,781 M vs
3,230 M en abril 2019, **+17 %**), pero **la caída empezó antes**: enero y febrero de 2020 ya estaban 14 % y 8 %
debajo de 2019, y la temporada *verano-2020* (dic-2019 a mar-2020) es la **única por debajo de la meta**.

La pregunta de negocio: **“Las metas globales se cumplen, pero vendemos menos que el año pasado, con más descuento
en tienda y menos clientes nuevos. ¿Dónde está el problema y qué palanca lo corrige?”**

La solución de BI responde tres preguntas:

1. **¿Estamos vendiendo por el canal correcto?** (tienda vs online, omnicanalidad)
2. **¿A los clientes correctos?** (captación, recompra, retención, club)
3. **¿Con el precio y las metas correctas?** (descuento, cumplimiento por sección y temporada)

---

## 2. Origen de los datos

| Fuente | Contenido | Tabla DWH | Grano | Riesgo de calidad detectado |
|---|---|---|---|---|
| transaction.csv | Línea de compra (fecha, cliente, artículo, precio, canal, temporada) | `Ventas.FactVentas` | 1 fila = 1 artículo vendido | Sin número de pedido → la cesta se reconstruye |
| customers.csv | Cliente, club, frecuencia de noticias, edad | `Ventas.DimCliente` | Cliente | 65 % sin `FN`/`Active`; `fashion_news` con NONE/None/vacío |
| articles.csv | Artículo, tipo, grupo, color, departamento, sección | `Ventas.DimArticulo`, `DimDepartamento` | Artículo | Texto con codificación mixta (“ChloÃ©”) |
| DimFecha.csv | Calendario | `GENERICO.DimFecha` | Día | `Fin_Semana` siempre 0 → recalculado |
| Temporada.csv | 9 temporadas | `Ventas.DimTemporada` | Temporada | Fechas límite compartidas entre temporadas |
| GoalsHyM.xlsx | Meta por escenario, depto/sección, temporada, mes | `Ventas.FactMetas` | Escenario × sección × temporada × mes | El monto es **diario** (ver regla 4) |

**Reglas de negocio clave**

1. **Cesta** = mismo cliente + mismo día + mismo canal (no existe ID de pedido; es la convención usada con este dataset).
2. **Ticket** = ventas / cestas (no ventas / líneas: eso es *precio medio por línea*).
3. **Descuento implícito** = 1 − precio cobrado / precio máximo observado del mismo artículo en el periodo.
4. **Meta**: el `Monto` de GoalsHyM se comporta como **meta diaria** (ventas ÷ (Monto × días) = 127 % / 110 % / 95 %
   en los escenarios 1/2/3; como meta mensual daría ~2.800 %). Se toma el **Escenario 2** como meta oficial.
5. **Cliente nuevo** = primera compra observada en el año (los datos empiezan el 20/09/2018).
6. **Retención** = compradores de 2019 que vuelven a comprar en 2020.
7. Canal 1 = tienda física, canal 2 = online (interpretación habitual del dataset; la fuente no lo rotula).

---

## 3. Indicadores críticos

> *Meta (propuesta)*: el dataset solo trae metas de venta. Las demás metas son una **propuesta** basada en el
> desempeño histórico 2018–2019 y deben validarse con el área comercial.

### 3.1 Ventas netas y variación interanual
- **Fórmula:** Σ precio; variación = ventas periodo / ventas mismo periodo año anterior − 1.
- **Meta (propuesta):** variación ≥ 0 %.
- **Origen:** transaction.csv → FactVentas. **Frecuencia:** semanal / mensual.
- **Valor:** 88,465 M acumulado; **−10.6 %** ene–sep 2020 vs 2019.
- **Interpretación:** tienda **−21.9 %**, online −6.8 %. Abril 2020: tienda 0, online +17 %. Ene–feb 2020 ya caían 14 % y 8 %.
- **Lectura:** la caída no es solo la pandemia: hubo un enfriamiento previo, y la tienda explica la mayor parte de la brecha.
- **Acción:** separar la meta 2020 en “efecto cierre” y “desempeño comparable”; plan de reactivación de tiendas por temporada.

### 3.2 Cumplimiento de meta
- **Fórmula:** ventas / meta diaria acumulada (Escenario 2).
- **Meta:** ≥ 100 %.
- **Origen:** FactVentas + GoalsHyM.xlsx. **Frecuencia:** diaria / por temporada.
- **Valor:** **110.3 %** global (Escenario 1: 127.3 %; Escenario 3: 95.5 %).
- **Interpretación:** solo **16 de 56 secciones** cumplen y **35 están bajo el 50 %**. Extremos: “Ladies Other” 1 %,
  “Men Other” 1 % frente a “Womens Swimwear” 1,918 % y “Womens Jackets” 1,039 %. Por temporada, *verano-2020* 86.8 %.
- **Lectura:** el cumplimiento global esconde metas mal repartidas: casi iguales para todas las secciones, sin importar su tamaño.
- **Acción:** recalcular metas por sección con base en su participación histórica (como la recomendación “recalcular cuotas” del caso Andino).

### 3.3 Participación online
- **Fórmula:** ventas online / ventas totales.
- **Meta (propuesta):** monitorear; alerta si la tienda baja de 20 %.
- **Origen:** FactVentas + DimCanal. **Frecuencia:** semanal.
- **Valor:** 75.6 % acumulado; 75.1 % → **78.2 %** (ene–sep 2019 vs 2020); **100 %** en abril 2020.
- **Lectura:** H&M ya era mayoritariamente online; la pandemia aceleró la dependencia de un solo canal.
- **Acción:** proteger el canal online (capacidad, surtido) y usar la tienda para captar y fidelizar (ver 3.10).

### 3.4 Ticket por cesta
- **Fórmula:** ventas / cestas (cliente + día + canal).
- **Meta (propuesta):** ≥ ticket del mismo periodo del año anterior.
- **Origen:** FactVentas. **Frecuencia:** semanal.
- **Valor:** 9,643 promedio; online **12,724 → 11,528 (−9.4 %)** de 2019 a 2020; tienda estable (5,764 → 5,766).
- **Lectura:** en online el cliente compra **menos por visita**; más visitas, cestas más pequeñas.
- **Acción:** venta cruzada en el checkout (*completa el look*), umbral de envío gratis por encima del ticket actual.

### 3.5 Artículos por cesta (UPT)
- **Fórmula:** líneas / cestas.
- **Meta (propuesta):** ≥ 4.0 online, ≥ 2.5 tienda.
- **Valor:** 3.46 global; online **4.25 → 3.96**; tienda 2.52 → 2.64.
- **Lectura:** la caída del ticket online se explica por menos artículos, no por precios más bajos.
- **Acción:** recomendaciones de producto y *bundles* por sección.

### 3.6 Clientes compradores y captación
- **Fórmula:** clientes distintos con compra; nuevos = primera compra en el periodo.
- **Meta (propuesta):** nuevos ≥ 40 mil por mes.
- **Valor:** 1,362,281 compradores (99.3 % de los registrados); nuevos **535,691 en 2019** vs **245,404 en 2020** (hasta septiembre).
- **Lectura:** la captación cayó: sin tiendas abiertas se pierde la principal puerta de entrada de clientes nuevos.
- **Acción:** campañas de primera compra online y registro en el club desde la tienda.

### 3.7 Tasa de recompra
- **Fórmula:** clientes que compran en más de un mes / compradores.
- **Meta (propuesta):** ≥ 65 %.
- **Valor:** **63.9 %**.
- **Acción:** comunicación por frecuencia de noticias (`fashion_news_frequency`) a quien compró una sola vez.

### 3.8 Retención interanual
- **Fórmula:** compradores 2019 que compran en 2020 / compradores 2019.
- **Meta (propuesta):** ≥ 65 %.
- **Valor:** **60.8 %** (de 976,801 compradores de 2019, unos 594 mil vuelven en 2020).
- **Lectura:** 4 de cada 10 clientes de 2019 no volvieron (a septiembre).
- **Acción:** campaña de reactivación segmentada por rango de edad y canal habitual.

### 3.9 Valor del club activo
- **Fórmula:** venta por cliente con `Active = 1` vs. sin él; penetración = compradores activos / compradores.
- **Meta (propuesta):** penetración ≥ 40 %.
- **Valor:** penetración **33.8 %**; venta por cliente **80,059 con `Active = 1` vs 57,207 del resto (+40 %)**.
- **Lectura:** el cliente activo vale un tercio más, pero solo 1 de cada 3 compradores lo es.
- **Acción:** activar a los 808 mil compradores con estado ACTIVE pero sin `Active = 1`.

### 3.10 Clientes omnicanal
- **Fórmula:** clientes que compran en ambos canales / compradores; venta por cliente omnicanal vs un canal.
- **Meta (propuesta):** ≥ 40 %.
- **Valor:** **35.5 %** son omnicanal y valen **123,992 vs 32,473 por cliente (3.8 veces)**.
- **Lectura:** es la palanca de mayor impacto: el cliente que usa los dos canales compra casi 4 veces más.
- **Acción:** *click & collect*, devoluciones en tienda de compras online, cupón online para clientes de tienda.

### 3.11 Descuento implícito
- **Fórmula:** 1 − Σ precio / Σ precio máximo del artículo.
- **Meta (propuesta):** ≤ 17 % (promedio 2018–2019).
- **Valor:** 17.1 % global; **tienda 17.1 % → 19.4 % → 20.9 %** (2018 → 2020); online estable (~16 %).
  En 2020 el **29.6 %** de las líneas de tienda se vendió con más de 30 % de descuento.
- **Lectura:** la tienda está liquidando inventario: vende menos y más barato.
- **Acción:** política de rebajas por temporada y traslado de stock de tienda al canal online.

### 3.12 Concentración de ventas
- **Fórmula:** participación del 20 % de clientes con más compras; secciones que suman el 80 % de las ventas.
- **Meta:** monitorear (riesgo de dependencia).
- **Valor:** el **top 20 % de clientes genera el 69.6 %** de la venta; **14 de 56 secciones** hacen el 80 %; el 67.1 %
  de los clientes compra en 2 o más grupos de producto.
- **Lectura:** pocos clientes y pocas secciones sostienen el negocio; perder clientes top cuesta mucho.
- **Acción:** programa de fidelización para el top 20 % y revisión del surtido de las 42 secciones de cola.

---

## 4. Del dato a la decisión

| KPI | Fuente | Caso detectado | Decisión que habilita |
|---|---|---|---|
| Ventas e interanual | FactVentas | Caída −10.6 %, tienda −21.9 % | Separar efecto cierre vs desempeño; plan de tiendas |
| Cumplimiento de meta | FactVentas + Goals | 16/56 secciones cumplen | Recalcular metas por peso de la sección |
| Participación online | FactVentas | 78 % y 100 % en abril | Asegurar operación online; rol de la tienda |
| Ticket por cesta | FactVentas | Online −9.4 % | Venta cruzada en checkout |
| Artículos por cesta | FactVentas | 4.25 → 3.96 | Recomendaciones y *bundles* |
| Captación | FactVentas | Nuevos a la baja | Primera compra online + registro en club |
| Recompra | FactVentas | 63.9 % | Comunicación a compradores de una vez |
| Retención | FactVentas | 60.8 % | Reactivación segmentada |
| Club activo | DimCliente | +40 % de valor, 33.8 % penetración | Activar socios ACTIVE |
| Omnicanal | FactVentas | 3.8 veces más valor | *Click & collect*, cupones cruzados |
| Descuento | FactVentas | Tienda 20.9 % | Política de rebajas y traslado de stock |
| Concentración | FactVentas | Top 20 % = 69.6 % | Fidelización de clientes top |

---

## 5. Los 3 dashboards con data storytelling

### 5.1 Dashboard 1 — Estratégico: “¿Crecemos de forma sana?”
- **Audiencia:** gerencia general, comercial y finanzas. **Frecuencia:** mensual.
- **KPIs:** ventas e interanual, cumplimiento de meta, participación online, retención, descuento implícito, clientes nuevos.
- **Diseño visual:**
  - Franja de 6 KPIs con **semáforo** contra meta y flecha ▲▼ contra el año anterior.
  - Líneas **2019 vs 2020 mes a mes** con anotación del cierre de tiendas (marzo–abril 2020).
  - **Cascada** que explica el paso de 2019 a 2020: aporte de tienda y de online.
  - Área 100 % apilada tienda/online por mes (se ve el 100 % online de abril).
  - Recuadro de narrativa que cambia con los filtros.
- **Data storytelling:**
  - *Inicio:* cumplimos la meta (110 %).
  - *Conflicto:* pero vendemos 10.6 % menos que el año pasado.
  - *Evidencia:* la tienda cae 21.9 % y el descuento sube.
  - *Resolución:* el online sostiene la venta y el cliente omnicanal vale 3.8 veces más.
  - *Acción:* reactivar la tienda como puerta al omnicanal.

### 5.2 Dashboard 2 — Táctico: “Torre de control de metas”
- **Audiencia:** jefes de sección y de temporada. **Frecuencia:** diaria / por temporada.
- **KPIs:** cumplimiento por sección y temporada, brecha contra la meta, ventas diarias contra la meta diaria acumulada.
- **Diseño visual:**
  - Selector de escenario.
  - **Mapa de calor** sección × temporada con el % de cumplimiento.
  - **Dispersión meta vs venta** por sección (burbuja = clientes) con la línea del 100 %: muestra de un vistazo las metas mal asignadas.
  - Top 5 y bottom 5 secciones.
  - Curva de **venta acumulada vs meta acumulada** dentro de la temporada.
- **Data storytelling:**
  - *Inicio:* la meta global se cumple.
  - *Conflicto:* 35 secciones están bajo el 50 %.
  - *Evidencia:* metas casi iguales para secciones de tamaño muy distinto.
  - *Resolución:* redistribuir según el peso histórico.
  - *Acción:* plan de metas por sección para la próxima temporada.

### 5.3 Dashboard 3 — Analítico: “Laboratorio de cliente y precio”
- **Audiencia:** marketing, pricing y BI. **Frecuencia:** semanal / mensual.
- **KPIs:** ticket y artículos por cesta, recompra, retención, club, omnicanal, descuento implícito, concentración.
- **Diseño visual:**
  - **Árbol de descomposición** de ventas (canal → grupo índice → sección).
  - Comparación **omnicanal vs un canal** y **club activo vs no** (venta por cliente).
  - Tendencia del **descuento implícito** por canal, con bandas de descuento.
  - **Pareto de clientes** (top 20 % = 69.6 %).
  - Ticket y artículos por cesta por mes y canal.
  - Venta por cliente por rango de edad.
- **Data storytelling:**
  - *Inicio:* 1.36 M de clientes compran.
  - *Conflicto:* compran menos por visita y cada vez se capta menos.
  - *Evidencia:* ticket online −9.4 % y nuevos a la baja; el cliente omnicanal y el del club valen más.
  - *Resolución:* convertir clientes de un canal en omnicanal y activar el club.
  - *Acción:* campañas segmentadas por edad y canal.
