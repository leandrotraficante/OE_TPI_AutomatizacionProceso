# Pruebas de estrés y caminos infelices — Bot Jack

Documento de verificación manual del simulador. Cada caso indica **entrada**, **pasos** y **resultado esperado** según `src/bot_vacaciones.py`.

**Cómo ejecutar:** desde la raíz del proyecto, `python src/bot_vacaciones.py` (o `py` en Windows).

**Datos de referencia** (`data/empleados.csv` al momento de documentar):

| Legajo | Nombre | Saldo |
|--------|--------|-------|
| 1001 | Juan Pérez | 73 |
| 1002 | María Gómez | 2 |
| 1003 | Carlos López | 0 |
| 1004 | Ana Martínez | 10 |

**Blackouts** (`data/blackout.csv`): 2026-07-01 a 2026-07-15; 2026-12-22 a 2027-01-05.

> **Para el informe PDF:** copiá las tablas que necesites y agregá **capturas de pantalla** de los casos marcados con 📷.

---

## 1. Camino feliz (happy path)

| ID | Escenario | Entrada / secuencia | Resultado esperado | ¿Persiste en `solicitudes.csv`? | 📷 |
|----|-----------|---------------------|--------------------|----------------------------------|-----|
| H1 | Aprobación automática | Legajo `1001` → fecha `2026-10-10` → días `3` → confirmar `s` | Mensaje de aprobación; saldo de 1001 pasa a **70** en `empleados.csv` | Sí, fila `estado=APROBADA` | Recomendado |
| H2 | Pendiente de jefe (más de 7 días) | Legajo `1004` → fecha con ≥15 días desde hoy → días `8` → `s` | `PENDIENTE_APROBACION`; saldo de 1004 **sin cambiar** | Sí | Recomendado |
| H3 | Pendiente de jefe (poca anticipación) | Legajo `1004` → fecha = hoy + 10 días → días `3` → `s` | `PENDIENTE_APROBACION` (anticipación &lt; 15 días) | Sí | Opcional |

---

## 2. Rechazos por reglas de negocio (después de confirmar `s`)

| ID | Escenario | Entrada / secuencia | Resultado esperado | ¿Persiste? | 📷 |
|----|-----------|---------------------|--------------------|------------|-----|
| R1 | Blackout | Legajo `1004` → `2026-07-05` → días `3` → `s` | `RECHAZADA_BLACKOUT`; motivo relacionado con inventario | Sí | Recomendado |
| R2 | Sin saldo (legajo en cero) | Legajo `1003` → fecha válida lejana → días `1` → `s` | `RECHAZADA_FALTA_SALDO` | Sí | Recomendado |
| R3 | Sin saldo (pide más de lo disponible) | Legajo `1002` (saldo 2) → fecha lejana → días `5` → `s` | `RECHAZADA_FALTA_SALDO` | Sí | Opcional |

---

## 3. Cancelaciones y no confirmación

| ID | Escenario | Entrada / secuencia | Resultado esperado | ¿Persiste? | 📷 |
|----|-----------|---------------------|--------------------|------------|-----|
| C1 | Cancelar en legajo | Legajo: escribir `cancelar` | Mensaje de cancelación; fin sin fila nueva en CSV | No | Opcional |
| C2 | Cancelar en fecha | Legajo válido → `cancelar` en fecha | Igual que C1 | No | — |
| C3 | No confirmar resumen | Datos válidos → en resumen responder `n` | `CANCELADA`; motivo “No confirmó la solicitud” | Sí | Opcional |
| C4 | Cancelar en resumen | Datos válidos → `cancelar` en confirmación | Tratado como no confirmación (`CANCELADA`) | Sí | — |

---

## 4. Errores de entrada (camino infeliz por validación)

| ID | Paso | Entrada incorrecta (ejemplo) | Comportamiento esperado | Tras 3 errores seguidos | 📷 |
|----|------|------------------------------|-------------------------|-------------------------|-----|
| E1 | Legajo | `abc` o `9999` | Mensaje de error; vuelve a pedir legajo | `CANCELADA` por intentos; **no** guarda en CSV | Opcional |
| E2 | Fecha | `10-03-2026` o `ayer` | Pide formato AAAA-MM-DD | Igual | — |
| E3 | Fecha pasada | Fecha anterior a hoy | “No puede ser anterior a hoy” | Igual | — |
| E4 | Días | `0`, `-1`, `tres` | Pide entero &gt; 0 | Igual | — |
| E5 | Confirmación | `si` o `x` (no es s/n) | Pide `s` o `n` | Si agota intentos: `CANCELADA` y **sí** guarda | — |

---

## 5. Orden de prioridad de reglas (caso límite conceptual)

| ID | Escenario | Nota | Resultado esperado |
|----|-----------|------|--------------------|
| P1 | Blackout + saldo insuficiente | Pedir fechas en julio con legajo `1003` y muchos días | **Primero** blackout → `RECHAZADA_BLACKOUT` (no evalúa saldo ni jefe) |
| P2 | Saldo OK pero requiere jefe | Legajo `1001`, 8 días, fecha lejana | Pasa blackout y saldo → `PENDIENTE_APROBACION` |

---

## 6. Checklist de regresión rápida (antes del coloquio)

- [ ] H1 — Aprobación automática
- [ ] H2 o H3 — Pendiente jefe
- [ ] R1 — Blackout
- [ ] R2 — Sin saldo
- [ ] C1 o C3 — Cancelación
- [ ] E1 — Tres intentos fallidos en legajo
- [ ] Verificar que `data/solicitudes.csv` y `data/empleados.csv` reflejan lo esperado tras H1

---

## 7. Qué debés completar vos para el informe

| Ítem | Acción |
|------|--------|
| Capturas 📷 | Al menos 4: H1, H2 o H3, R1, R2 (terminal con diálogo Jack) |
| Fecha “hoy + 10 días” en H3 | Calculá la fecha al día de la demo y anotala en el PDF |
| Tabla resumida en PDF | Copiar secciones 1–4 (podés acortar a 6–8 filas) |
| Coloquio | Tener abierto `solicitudes.csv` y `empleados.csv` para mostrar persistencia tras H1 |

---

## 8. Plantilla para agregar tus propias pruebas

| ID | Escenario | Entrada | Resultado obtenido | ¿OK? | Observaciones |
|----|-----------|---------|-------------------|------|---------------|
| T1 | | | | ☐ | |
| T2 | | | | ☐ | |
