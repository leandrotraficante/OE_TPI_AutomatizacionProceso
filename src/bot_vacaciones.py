# Bot de vacaciones (Jack) — TPI Organización Empresarial
# Simulador en consola con datos en CSV y máquina de estados.

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

# --- Rutas a la carpeta data (funciona desde cualquier directorio) ---
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

# --- Reglas de negocio (política de la empresa simulada) ---
MAX_INTENTOS = 3
# Si pide MÁS de 7 días → el jefe debe aprobar
DIAS_REQUIERE_JEFE = 7
# Si el inicio es en MENOS de 15 días desde fecha actual → también va al jefe
DIAS_ANTICIPACION_MIN = 15

# Orden de prioridad al validar (de mayor a menor):
# 1) Blackout → rechazo directo (no llega al jefe)
# 2) Saldo → rechazo directo
# 3) Reglas de jefe (>7 días o poca anticipación) → pendiente
# 4) Si no aplica nada anterior → aprobación automática

CAMPOS_SOLICITUD = [
    "id",
    "legajo",
    "nombre",
    "fecha_inicio",
    "fecha_fin",
    "cant_dias",
    "estado",
    "motivo",
    "fecha_registro",
]

# Estados en los que termina el flujo del empleado
ESTADOS_TERMINALES = {
    "FIN_APROBADA",
    "FIN_RECHAZADA_SALDO",
    "FIN_RECHAZADA_BLACKOUT",
    "FIN_CANCELADA",
    "FIN_PENDIENTE_APROBACION",
}


# Muestra un mensaje del bot con el prefijo Jack
def jack(mensaje):
    print(f"Jack: {mensaje}")


# Pide un dato al usuario y devuelve el texto ingresado
def pedir(mensaje):
    return input(f"Jack: {mensaje}").strip()


# ---------- Lectura y escritura de CSV ----------


# Carga empleados.csv en un diccionario: legajo → fila
def cargar_empleados():
    empleados = {}
    with open(DATA / "empleados.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            empleados[int(row["legajo"])] = row
    return empleados


# Carga períodos en los que no se pueden pedir vacaciones
def cargar_blackouts():
    blackouts = []
    with open(DATA / "blackout.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            blackouts.append(row)
    return blackouts


# Lee el historial de solicitudes
def cargar_solicitudes():
    with open(DATA / "solicitudes.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- Reglas de negocio ----------


def es_cancelar(texto):
    return texto.strip().lower() == "cancelar"


# Comprueba si las fechas chocan con un período bloqueado (devuelve motivo o None)
def en_blackout(fecha_inicio, fecha_fin, blackouts):
    for b in blackouts:
        ini = datetime.strptime(b["fecha_inicio"], "%Y-%m-%d").date()
        fin = datetime.strptime(b["fecha_fin"], "%Y-%m-%d").date()
        if fecha_inicio <= fin and fecha_fin >= ini:
            return b["motivo"]
    return None


# True si la solicitud debe quedar pendiente de aprobación del jefe
def requiere_revision_jefe(cant_dias, fecha_inicio):
    if cant_dias > DIAS_REQUIERE_JEFE:
        return True
    dias_hasta_inicio = (fecha_inicio - date.today()).days
    return dias_hasta_inicio < DIAS_ANTICIPACION_MIN


# Texto del motivo que se guarda en solicitudes.csv
def motivo_requiere_jefe(cant_dias, fecha_inicio):
    if cant_dias > DIAS_REQUIERE_JEFE:
        return f"Más de {DIAS_REQUIERE_JEFE} días solicitados"
    dias_hasta = (fecha_inicio - date.today()).days
    return f"Inicio en {dias_hasta} día(s) — menos de {DIAS_ANTICIPACION_MIN} días de anticipación"


# Aviso antes de que el empleado confirme
def mensaje_resumen_revision_jefe(cant_dias, fecha_inicio):
    if cant_dias > DIAS_REQUIERE_JEFE:
        return (
            f"Tu solicitud será enviada a tu jefe para revisión por la "
            f"cantidad de días solicitados ({cant_dias})."
        )
    dias_hasta = (fecha_inicio - date.today()).days
    return (
        "Tu solicitud será enviada a tu jefe para revisión porque "
        f"el inicio es en {dias_hasta} día(s) y la empresa pide al menos "
        f"{DIAS_ANTICIPACION_MIN} días de anticipación."
    )


def siguiente_id_solicitud():
    filas = cargar_solicitudes()
    if not filas:
        return 1
    return max(int(r["id"]) for r in filas) + 1


# Agrega una fila nueva al final de solicitudes.csv
def guardar_solicitud(sesion):
    nuevo_id = siguiente_id_solicitud()
    fila = {
        "id": str(nuevo_id),
        "legajo": str(sesion["legajo"]),
        "nombre": sesion["nombre"],
        "fecha_inicio": sesion["fecha_inicio"].strftime("%Y-%m-%d"),
        "fecha_fin": sesion["fecha_fin"].strftime("%Y-%m-%d"),
        "cant_dias": str(sesion["cant_dias"]),
        "estado": sesion["resultado"],
        "motivo": sesion.get("motivo", ""),
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    existe = (DATA / "solicitudes.csv").stat().st_size > 0
    with open(DATA / "solicitudes.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_SOLICITUD)
        if not existe:
            writer.writeheader()
        writer.writerow(fila)
    return nuevo_id


# Actualiza el saldo de vacaciones en empleados.csv
def actualizar_saldo(legajo, nuevo_saldo):
    filas = []
    with open(DATA / "empleados.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for row in filas:
        if int(row["legajo"]) == legajo:
            row["saldo_vacaciones"] = str(nuevo_saldo)
    with open(DATA / "empleados.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["legajo", "nombre", "saldo_vacaciones"])
        writer.writeheader()
        writer.writerows(filas)


# Cuenta errores de tipeo; a la 3ra vez cancela la solicitud
def demasiados_intentos(sesion):
    sesion["intentos"] += 1
    if sesion["intentos"] >= MAX_INTENTOS:
        jack(
            "Llegamos al máximo de intentos y tengo que cerrar esta solicitud. "
            "Cuando quieras, podés volver a empezar."
        )
        sesion["resultado"] = "CANCELADA"
        sesion["motivo"] = "Demasiados intentos fallidos"
        return True
    return False


# Datos que el bot va guardando mientras dura una solicitud
def nueva_sesion():
    return {
        "legajo": None,
        "nombre": None,
        "saldo_actual": None,
        "fecha_inicio": None,
        "cant_dias": None,
        "fecha_fin": None,
        "intentos": 0,
        "resultado": None,
        "motivo": "",
    }


# ---------- Flujo del empleado (máquina de estados) ----------


# Máquina de estados: el empleado solicita vacaciones paso a paso
def flujo_empleado(empleados, blackouts):
    sesion = nueva_sesion()
    estado = "INICIO"

    while estado not in ESTADOS_TERMINALES:

        if estado == "INICIO":
            jack("Vamos con tu solicitud de vacaciones.")
            jack(
                f"Si pedís más de {DIAS_REQUIERE_JEFE} días, tu jefe deberá "
                "aprobar la solicitud antes de que se confirmen."
            )
            sesion["intentos"] = 0
            estado = "ESPERA_LEGAJO"

        elif estado == "ESPERA_LEGAJO":
            texto = pedir("¿Cuál es tu número de legajo? ")
            if es_cancelar(texto):
                sesion["resultado"] = "CANCELADA"
                sesion["motivo"] = "Usuario canceló"
                jack("Listo, cancelé la solicitud. ¡Hasta la próxima!")
                estado = "FIN_CANCELADA"
                continue
            try:
                legajo = int(texto)
            except ValueError:
                jack(
                    "Ups, el legajo tiene que ser un número. ¿Podés intentarlo de nuevo?"
                )
                if demasiados_intentos(sesion):
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue
            if legajo not in empleados:
                jack(
                    "No encontré ese legajo en el sistema. "
                    "Revisá el número e intentá otra vez."
                )
                if demasiados_intentos(sesion):
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue
            emp = empleados[legajo]
            sesion["legajo"] = legajo
            sesion["nombre"] = emp["nombre"]
            sesion["saldo_actual"] = int(emp["saldo_vacaciones"])
            sesion["intentos"] = 0
            jack(f"¡Hola, {sesion['nombre']}! Te tengo registrado/a.")
            estado = "ESPERA_FECHA_INICIO"

        elif estado == "ESPERA_FECHA_INICIO":
            texto = pedir(
                "¿Desde qué fecha querés tomarte las vacaciones? "
                "Escribila así: AAAA-MM-DD (ejemplo: 2026-03-10) "
            )
            if es_cancelar(texto):
                sesion["resultado"] = "CANCELADA"
                sesion["motivo"] = "Usuario canceló"
                jack("Listo, cancelé la solicitud. ¡Hasta la próxima!")
                estado = "FIN_CANCELADA"
                continue
            try:
                fecha = datetime.strptime(texto, "%Y-%m-%d").date()
            except ValueError:
                jack(
                    "Esa fecha no la pude leer. Usá el formato AAAA-MM-DD, "
                    "por ejemplo: 2026-03-10."
                )
                if demasiados_intentos(sesion):
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue
            if fecha < date.today():
                jack("La fecha de inicio no puede ser anterior a hoy.")
                if demasiados_intentos(sesion):
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue
            sesion["fecha_inicio"] = fecha
            sesion["intentos"] = 0
            estado = "ESPERA_CANT_DIAS"

        elif estado == "ESPERA_CANT_DIAS":
            texto = pedir("¿Cuántos días de vacaciones necesitás? ")
            if es_cancelar(texto):
                sesion["resultado"] = "CANCELADA"
                sesion["motivo"] = "Usuario canceló"
                jack("Listo, cancelé la solicitud. ¡Hasta la próxima!")
                estado = "FIN_CANCELADA"
                continue
            try:
                dias = int(texto)
                if dias <= 0:
                    raise ValueError
            except ValueError:
                jack("Necesito un número entero mayor a cero. ¿Cuántos días serían?")
                if demasiados_intentos(sesion):
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue
            sesion["cant_dias"] = dias
            # Último día incluido: 5 días desde el 10 → terminan el 14
            sesion["fecha_fin"] = sesion["fecha_inicio"] + timedelta(days=dias - 1)
            sesion["intentos"] = 0
            estado = "MUESTRA_RESUMEN"

        elif estado == "MUESTRA_RESUMEN":
            dias_hasta = (sesion["fecha_inicio"] - date.today()).days
            va_a_jefe = requiere_revision_jefe(
                sesion["cant_dias"], sesion["fecha_inicio"]
            )

            jack(f"Perfecto, {sesion['nombre']}. Este es el resumen de tu solicitud:")
            jack(f"  · Inicio: {sesion['fecha_inicio']} (en {dias_hasta} día(s))")
            jack(f"  · Fin: {sesion['fecha_fin']}")
            jack(f"  · Días solicitados: {sesion['cant_dias']}")
            jack(f"  · Tu saldo actual: {sesion['saldo_actual']} día(s)")
            if va_a_jefe:
                jack(
                    f"  · {mensaje_resumen_revision_jefe(sesion['cant_dias'], sesion['fecha_inicio'])}"
                )

            texto = pedir("¿Confirmás que los datos son correctos? (s/n) ").lower()
            if es_cancelar(texto) or texto == "n":
                sesion["resultado"] = "CANCELADA"
                sesion["motivo"] = "No confirmó la solicitud"
                guardar_solicitud(sesion)
                jack(
                    "No hay problema, dejé la solicitud sin confirmar. ¡Hasta la próxima!"
                )
                estado = "FIN_CANCELADA"
                continue
            if texto != "s":
                jack('Por favor respondé con "s" (sí) o "n" (no).')
                if demasiados_intentos(sesion):
                    guardar_solicitud(sesion)
                    jack("Cierro la solicitud por hoy. ¡Nos vemos!")
                    estado = "FIN_CANCELADA"
                continue

            # A partir de acá el bot valida reglas (orden de prioridad en comentarios del inicio)
            jack("Gracias. Primero reviso períodos bloqueados y saldo...")
            estado = "GW_BLACKOUT"

        elif estado == "GW_BLACKOUT":
            # Prioridad 1: blackout rechaza aunque el resto estuviera bien
            motivo_blk = en_blackout(
                sesion["fecha_inicio"], sesion["fecha_fin"], blackouts
            )
            if motivo_blk:
                sesion["resultado"] = "RECHAZADA_BLACKOUT"
                sesion["motivo"] = motivo_blk
                guardar_solicitud(sesion)
                jack(
                    f"Disculpá, no puedo aprobar esas fechas porque caen en un "
                    f"período bloqueado: {motivo_blk}."
                )
                jack("Probá con otras fechas cuando quieras volver a consultarme.")
                estado = "FIN_RECHAZADA_BLACKOUT"
            else:
                estado = "GW_SALDO"

        elif estado == "GW_SALDO":
            # Prioridad 2: sin saldo suficiente tampoco llega al jefe
            if sesion["cant_dias"] > sesion["saldo_actual"]:
                sesion["resultado"] = "RECHAZADA_FALTA_SALDO"
                sesion["motivo"] = (
                    f"Saldo insuficiente ({sesion['saldo_actual']} días disponibles)"
                )
                guardar_solicitud(sesion)
                jack(
                    f"Por ahora no alcanza el saldo: tenés {sesion['saldo_actual']} día(s) "
                    f"y pediste {sesion['cant_dias']}."
                )
                jack("Cuando tengas más días disponibles, volvé a intentarlo.")
                estado = "FIN_RECHAZADA_SALDO"
            else:
                estado = "GW_REQUIERE_JEFE"

        elif estado == "GW_REQUIERE_JEFE":
            # Prioridad 3: >7 días O poca anticipación → pendiente (el jefe aprueba fuera del bot)
            if requiere_revision_jefe(sesion["cant_dias"], sesion["fecha_inicio"]):
                sesion["resultado"] = "PENDIENTE_APROBACION"
                sesion["motivo"] = motivo_requiere_jefe(
                    sesion["cant_dias"], sesion["fecha_inicio"]
                )
                id_sol = guardar_solicitud(sesion)
                jack(
                    f"Listo. Tu solicitud Nº {id_sol} quedó en estado "
                    '"Pendiente de aprobación".'
                )
                jack(
                    "Todavía no desconté días de tu saldo. "
                    "Tu jefe recibirá el pedido para revisarlo."
                )
                estado = "FIN_PENDIENTE_APROBACION"
            else:
                estado = "REGISTRA_APROBADA"

        elif estado == "REGISTRA_APROBADA":
            # Prioridad 4: cumple todo → aprobación automática al instante
            nuevo_saldo = sesion["saldo_actual"] - sesion["cant_dias"]
            actualizar_saldo(sesion["legajo"], nuevo_saldo)
            empleados[sesion["legajo"]]["saldo_vacaciones"] = str(nuevo_saldo)
            sesion["resultado"] = "APROBADA"
            sesion["motivo"] = "Aprobación automática (reglas estándar)"
            guardar_solicitud(sesion)
            jack(
                f"¡Genial, {sesion['nombre']}! Tu solicitud quedó aprobada al instante. "
                f"Te quedan {nuevo_saldo} día(s) de vacaciones."
            )
            jack("¡Que los disfrutes!")
            estado = "FIN_APROBADA"


# ---------- Punto de entrada (solo empleado ↔ bot) ----------


# En Windows, la consola suele usar cp1252 y las tildes de Jack se ven mal
def _configurar_salida_consola():
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


# Arranca el bot: carga datos y ejecuta el flujo del empleado
def main():
    _configurar_salida_consola()
    empleados = cargar_empleados()
    blackouts = cargar_blackouts()

    jack("¡Bienvenido/a! Soy Jack, tu asistente para la gestión de vacaciones.")
    jack(
        'Recordá que podés escribir "cancelar" en cualquier momento '
        "para salir del proceso."
    )

    flujo_empleado(empleados, blackouts)

    jack(
        "Gracias por usar el sistema. Soy Jack, y estoy acá cuando "
        "necesites gestionar vacaciones otra vez."
    )


if __name__ == "__main__":
    main()
