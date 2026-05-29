# Diccionario de Datos

Documento que describe **todas las entidades y variables** que maneja el bot Jack y los archivos CSV que actúan como base de datos simulada.

**Fecha:** 2026  
**Proyecto:** TPI Organización Empresarial — Bot de vacaciones  
**Autor:** Leandro Traficante

---

## 1. Entidad `EMPLEADO`

**Archivo:** `data/empleados.csv`  
**Propósito:** Registrar el padrón de empleados con su saldo de días de vacaciones disponibles.  
**Operaciones del bot:** lectura al iniciar, escritura solo al aprobar (descuenta saldo).

| Campo | Tipo | Dominio / Restricción | Obligatorio | Ejemplo | Descripción |
|-------|------|----------------------|-------------|---------|-------------|
| `legajo` | entero | > 0, único | Sí | `1001` | Identificador único del empleado |
| `nombre` | texto | 1–60 caracteres | Sí | `Juan Pérez` | Nombre y apellido del empleado |
| `saldo_vacaciones` | entero | ≥ 0 | Sí | `15` | Días de vacaciones disponibles |

---

## 2. Entidad `BLACKOUT`

**Archivo:** `data/blackout.csv`  
**Propósito:** Definir los períodos en los que la empresa **no** permite tomar vacaciones (cierres, inventarios, etc.).  
**Operaciones del bot:** solo lectura (no se modifica desde el bot).

| Campo | Tipo | Dominio / Restricción | Obligatorio | Ejemplo | Descripción |
|-------|------|----------------------|-------------|---------|-------------|
| `fecha_inicio` | fecha | `AAAA-MM-DD` | Sí | `2026-07-01` | Primer día del período bloqueado |
| `fecha_fin` | fecha | `AAAA-MM-DD`, ≥ `fecha_inicio` | Sí | `2026-07-15` | Último día del período bloqueado |
| `motivo` | texto | 1–80 caracteres | Sí | `Inventario general` | Motivo del bloqueo (se muestra al usuario al rechazar) |

---

## 3. Entidad `SOLICITUD`

**Archivo:** `data/solicitudes.csv`  
**Propósito:** Historial de todas las solicitudes registradas por el bot (auditoría).  
**Operaciones del bot:** lectura para calcular el próximo `id`, escritura al cerrar el flujo con un estado final.

| Campo | Tipo | Dominio / Restricción | Obligatorio | Ejemplo | Descripción |
|-------|------|----------------------|-------------|---------|-------------|
| `id` | entero | > 0, autoincremental | Sí | `1` | Identificador único de la solicitud |
| `legajo` | entero | FK → `EMPLEADO.legajo` | Sí | `1001` | Empleado solicitante |
| `nombre` | texto | Copia de `EMPLEADO.nombre` al registrar | Sí | `Juan Pérez` | Snapshot del nombre al momento del registro |
| `fecha_inicio` | fecha | `AAAA-MM-DD`, ≥ hoy | Sí | `2026-10-10` | Inicio de las vacaciones solicitadas |
| `fecha_fin` | fecha | `AAAA-MM-DD`, ≥ `fecha_inicio` | Sí | `2026-10-14` | Calculado: `fecha_inicio + (cant_dias - 1)` |
| `cant_dias` | entero | > 0 | Sí | `5` | Cantidad de días solicitados |
| `estado` | enumerado | Ver tabla "Estados" | Sí | `APROBADA` | Resultado del proceso |
| `motivo` | texto | 0–100 caracteres | No | `Aprobación automática (reglas estándar)` | Detalle del resultado (auditoría) |
| `fecha_registro` | timestamp | `AAAA-MM-DD HH:MM` | Sí | `2026-05-25 14:33` | Momento en que se guardó la fila |

### Estados posibles (`SOLICITUD.estado`)

| Valor | Significado | ¿Modifica saldo? |
|-------|-------------|------------------|
| `APROBADA` | El bot aprobó automáticamente. | Sí (descuenta `cant_dias`) |
| `PENDIENTE_APROBACION` | Espera revisión del jefe (fuera del bot). | No |
| `RECHAZADA_BLACKOUT` | Fechas caen en `BLACKOUT`. | No |
| `RECHAZADA_FALTA_SALDO` | `cant_dias` > `saldo_vacaciones`. | No |
| `CANCELADA` | `n`/`cancelar` en resumen o 3 errores en confirmación (sí en CSV). Cancelar antes del resumen o 3 errores en legajo/fecha/días (sin CSV). | No |

---

## 4. Variables de sesión (memoria del bot)

**Ubicación:** diccionario `sesion` en `src/bot_vacaciones.py`.  
**Propósito:** Mantener el contexto del usuario mientras dura **una** solicitud (no se persiste, vive en memoria).

| Variable | Tipo | Valor inicial | Cuándo se completa | Descripción |
|----------|------|---------------|--------------------|-------------|
| `legajo` | `int \| None` | `None` | Al validar legajo en `ESPERA_LEGAJO` | Identificador del empleado activo |
| `nombre` | `str \| None` | `None` | Junto con `legajo` | Nombre copiado de `empleados.csv` |
| `saldo_actual` | `int \| None` | `None` | Junto con `legajo` | Saldo leído al iniciar la solicitud |
| `fecha_inicio` | `date \| None` | `None` | Tras `ESPERA_FECHA_INICIO` válido | Inicio solicitado por el empleado |
| `cant_dias` | `int \| None` | `None` | Tras `ESPERA_CANT_DIAS` válido | Días solicitados |
| `fecha_fin` | `date \| None` | `None` | Junto con `cant_dias` | `fecha_inicio + (cant_dias - 1)` |
| `intentos` | `int` | `0` | Se incrementa en errores | Errores consecutivos en el paso actual |
| `resultado` | `str \| None` | `None` | En cada compuerta o cancelación | Estado final (uno de los `estado` de SOLICITUD) |
| `motivo` | `str` | `""` | Junto con `resultado` | Texto descriptivo del resultado |

---

## 5. Estados de la máquina de estados

**Ubicación:** variable `estado` (string) en `flujo_empleado()`.

### Estados de entrada (esperan input del usuario)

| Estado | Espera | Validación |
|--------|--------|------------|
| `INICIO` | — | Inicializa la sesión y pasa al siguiente |
| `ESPERA_LEGAJO` | Número de legajo | Existe en `empleados.csv` |
| `ESPERA_FECHA_INICIO` | Fecha `AAAA-MM-DD` | Formato + no anterior a hoy |
| `ESPERA_CANT_DIAS` | Entero > 0 | Calcula `fecha_fin` |
| `MUESTRA_RESUMEN` | `s` / `n` | Confirmación final |

### Compuertas (no esperan input, deciden el flujo)

| Estado | Decisión |
|--------|----------|
| `GW_BLACKOUT` | ¿Fechas en `blackout.csv`? |
| `GW_SALDO` | ¿`cant_dias` ≤ `saldo_actual`? |
| `GW_REQUIERE_JEFE` | ¿`cant_dias` > 7 **o** anticipación < 15 días? |
| `REGISTRA_APROBADA` | Descuenta saldo y persiste |

### Estados terminales

| Estado | Estado CSV asociado |
|--------|---------------------|
| `FIN_APROBADA` | `APROBADA` |
| `FIN_PENDIENTE_APROBACION` | `PENDIENTE_APROBACION` |
| `FIN_RECHAZADA_BLACKOUT` | `RECHAZADA_BLACKOUT` |
| `FIN_RECHAZADA_SALDO` | `RECHAZADA_FALTA_SALDO` |
| `FIN_CANCELADA` | `CANCELADA` (con o sin fila en CSV según el paso) |

---

## 6. Reglas de negocio (constantes)

**Ubicación:** parte superior de `src/bot_vacaciones.py`.

| Constante | Valor | Significado |
|-----------|-------|-------------|
| `MAX_INTENTOS` | `3` | Cantidad de errores consecutivos permitidos antes de cerrar la solicitud |
| `DIAS_REQUIERE_JEFE` | `7` | Si el empleado pide **más** de este número de días, se necesita aprobación del jefe |
| `DIAS_ANTICIPACION_MIN` | `15` | Si el inicio es a menos de este número de días desde hoy, también requiere jefe |

---

## 7. Relaciones entre entidades

```
EMPLEADO (1) ──────── (N) SOLICITUD
   legajo (PK)            legajo (FK)

BLACKOUT (independiente) — se consulta al validar fechas de SOLICITUD
```

- Una `SOLICITUD` siempre pertenece a un `EMPLEADO` (relación uno a muchos).
- `BLACKOUT` no se relaciona directamente con `EMPLEADO` ni con `SOLICITUD` por FK; el bot **compara** rangos al validar.
