# Manual de Usuario — Bot Jack

**Proyecto:** Automatización de solicitudes de vacaciones  
**Asistente:** Jack (bot de consola)  
**Versión:** 1.0 — Simulador para TPI

---

## 1. ¿Qué es Jack?

Jack es un asistente automatizado que reemplaza el trámite manual de solicitar vacaciones. Vos le decís cuándo querés tomarte días y él, en menos de un minuto, te dice si:

- te aprueba al instante (autoaprobación),
- queda pendiente de tu jefe,
- o no puede aprobarte (por blackout o falta de saldo).

Todo queda registrado automáticamente en el sistema.

---

## 2. Antes de empezar

### Requisitos

- Tener **Python 3.10 o superior** instalado.
- No necesitás instalar nada más: el bot usa solo la biblioteca estándar.

### Cómo abrirlo

1. Abrí una terminal en la carpeta del proyecto.
2. Ejecutá:

```bash
python src/bot_vacaciones.py
```

> En Windows, si `python` no responde, probá con `py src/bot_vacaciones.py`.

---

## 3. Qué te va a pedir Jack

Jack te guía paso a paso. Solo escribís y presionás **Enter**.

| Paso | Pregunta de Jack | Qué responder | Ejemplo |
|------|------------------|---------------|---------|
| 1 | Tu número de legajo | Número entero | `1001` |
| 2 | Fecha desde la que te tomás vacaciones | Fecha en formato `AAAA-MM-DD` | `2026-10-10` |
| 3 | Cantidad de días | Número entero mayor a cero | `5` |
| 4 | Confirmación del resumen | `s` para sí, `n` para no | `s` |

---

## 4. Comandos especiales

| Comando | Cuándo usarlo | Qué hace |
|---------|---------------|----------|
| `cancelar` | En cualquier momento | Sale del proceso sin guardar |
| `n` | En la pregunta final de confirmación | No registra los días y termina |
| `s` | En la pregunta final de confirmación | Confirma y dispara la validación de reglas |

---

## 5. Reglas que Jack aplica

Después de que confirmás, Jack valida en este orden:

1. **¿Esa fecha está bloqueada por la empresa?** (vacaciones en julio o fin de año, por ejemplo)
2. **¿Tenés saldo suficiente?**
3. **¿Hace falta que tu jefe lo apruebe?** Es necesario si:
   - pedís **más de 7 días**, **o**
   - la fecha de inicio es **dentro de los próximos 15 días**.
4. Si nada de lo anterior aplica → **te aprueba automáticamente** y descuenta los días.

---

## 6. Posibles resultados

| Resultado | ¿Qué significa? | ¿Qué hago? |
|-----------|----------------|------------|
| ✅ **Aprobada** | Ya está. Días descontados de tu saldo. | Disfrutar las vacaciones. |
| 🕒 **Pendiente de aprobación** | Tu jefe tiene que revisarla manualmente. | Esperar la respuesta del jefe. El saldo NO se descontó todavía. |
| ❌ **Rechazada por blackout** | Las fechas elegidas chocan con un período cerrado de la empresa. | Probar con otras fechas. |
| ❌ **Rechazada por falta de saldo** | Pediste más días de los que tenés disponibles. | Esperar a tener más saldo o pedir menos días. |
| 🚪 **Cancelada** | Saliste vos del proceso. | Volver a empezar cuando quieras. |

---

## 7. Si te equivocás escribiendo

Jack es tolerante a errores:

- Si escribís `abc` cuando pide un número → te lo pide de nuevo.
- Si escribís una fecha mal formateada → te explica el formato y te la pide de nuevo.
- Si pedís 0 o un número negativo de días → te pide otro.

**Tenés 3 intentos por paso.** Al cuarto error consecutivo, Jack cierra la solicitud por seguridad.

---

## 8. Ejemplo de una conversación completa

```
Jack: ¡Bienvenido/a! Soy Jack, tu asistente para la gestión de vacaciones.
Jack: Recordá que podés escribir "cancelar" en cualquier momento.
Jack: Vamos con tu solicitud de vacaciones.
Jack: ¿Cuál es tu número de legajo?
Vos:  1002

Jack: ¡Hola, María Gómez! Te tengo registrado/a.
Jack: ¿Desde qué fecha querés tomarte las vacaciones? AAAA-MM-DD
Vos:  2026-10-10

Jack: ¿Cuántos días de vacaciones necesitás?
Vos:  3

Jack: Perfecto, María Gómez. Este es el resumen de tu solicitud:
  · Inicio: 2026-10-10 (en 138 día(s))
  · Fin: 2026-10-12
  · Días solicitados: 3
  · Tu saldo actual: 5 día(s)

Jack: ¿Confirmás que los datos son correctos? (s/n)
Vos:  s

Jack: Gracias. Primero reviso períodos bloqueados y saldo...
Jack: ¡Genial, María Gómez! Tu solicitud quedó aprobada al instante.
      Te quedan 2 día(s) de vacaciones.
Jack: ¡Que los disfrutes!
```

---

## 9. ¿Y si necesito al administrador?

El bot Jack solo gestiona el carril del **empleado**. La aprobación del jefe (estado **Pendiente**) se resuelve fuera del simulador, como ocurriría en una empresa real:

- El jefe revisa el historial en `data/solicitudes.csv`.
- Si aprueba, edita la fila para cambiar `PENDIENTE_APROBACION` → `APROBADA` y descuenta el saldo en `data/empleados.csv`.
- Si rechaza, cambia el estado a `RECHAZADA_JEFE`.

En una versión futura este flujo podría sumarse al bot mediante un menú adicional o un canal separado para el rol jefe.

---

## 10. Preguntas frecuentes

**¿Puedo volver atrás un paso?**  
No. Si te equivocás de fecha, terminá esa solicitud (con `cancelar`) y empezá de nuevo.

**¿Puedo tener más de una solicitud activa?**  
Sí. Cada vez que ejecutás el bot se inicia una solicitud nueva e independiente.

**¿Dónde queda registrada mi solicitud?**  
En `data/solicitudes.csv`, con un `id` único y la marca de tiempo.

**¿Por qué me sale "Pendiente" si tengo saldo?**  
Porque pediste más de 7 días, o porque la fecha de inicio está muy próxima (menos de 15 días). Es una política de la empresa que el jefe lo revise.

**¿El bot funciona offline?**  
Sí, no necesita conexión a internet. Todos los datos están en archivos locales.
