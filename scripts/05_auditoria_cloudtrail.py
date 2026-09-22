#!/usr/bin/env python3
"""
Demostracion CloudTrail: 'El Mito de la Vecina Chismosa'
Management Events vs Data Events.
AWS User Group Minatitlan.
"""
import sys
import subprocess
import json
from datetime import datetime, timezone, timedelta

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def get_cfn_output(output_key):
    try:
        cmd = [
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", "lab-red-team",
            "--query", f"Stacks[0].Outputs[?OutputKey=='{output_key}'].OutputValue",
            "--output", "text"
        ]
        res = subprocess.check_output(cmd, text=True).strip()
        return res
    except Exception:
        return None

def lookup_events(event_name=None):
    cmd = ["aws", "cloudtrail", "lookup-events", "--max-items", "10", "--output", "json"]
    if event_name:
        cmd.extend(["--lookup-attributes", f"AttributeKey=EventName,AttributeValue={event_name}"])
    try:
        res = subprocess.check_output(cmd, text=True)
        data = json.loads(res)
        return data.get("Events", [])
    except Exception as e:
        return []

def main():
    print(f"\n{BOLD}{CYAN}=== [AUDITORIA CLOUDTRAIL] ¿La Vecina Chismosa Realmente lo Ve Todo? ==={RESET}\n")

    print(f"{YELLOW}Pregunta para la audiencia:{RESET}")
    print(f"{BOLD}\"Siempre nos dicen que AWS CloudTrail es como la vecina chismosa:")
    print(f" que siempre está viendo la ventana y guardando todo lo que pasa... ¿Será cierto?\"{RESET}\n")

    bucket_name = get_cfn_output("ExposedS3BucketName")
    print(f"[*] Verificando registros recientes en CloudTrail Event History...")

    # 1. Buscar eventos de Management (Control Plane)
    print(f"\n{BOLD}--> [1] Buscando Management Events (Eventos de Gestion):{RESET}")
    print("    Buscando eventos de creacion o modificacion de infraestructura...")
    mgmt_events = lookup_events()

    if mgmt_events:
        print(f"    {GREEN}[+] CloudTrail SI registro llamadas de gestion (Management Events):{RESET}")
        for ev in mgmt_events[:4]:
            name = ev.get("EventName", "Desconocido")
            user = ev.get("Username", "Desconocido")
            event_time = ev.get("EventTime", "")
            print(f"        • {CYAN}{event_time}{RESET} | Evento: {BOLD}{name}{RESET} | Usuario: {user}")
    else:
        print(f"    {YELLOW}[*] No se recuperaron eventos recientes en los ultimos minutos.{RESET}")

    # 2. Buscar Data Events (Descarga de archivos en S3: GetObject)
    print(f"\n{BOLD}--> [2] Buscando Data Events (¿Quién descargo el archivo sensible 'factura_sat_ejemplo.xml'?):{RESET}")
    print("    Consultando si CloudTrail registro la llamada 'GetObject'...")
    get_object_events = lookup_events(event_name="GetObject")

    if not get_object_events:
        print(f"    {RED}{BOLD}[VACIO / 0 RESULTADOS] ¡CloudTrail NO REGISTRO NINGUNA DESCARGA!{RESET}")
        print(f"\n{BOLD}{RED}[LA REVELACION EN VIVO]:{RESET}")
        print("  1. CloudTrail Event History viene gratis por defecto en todas las cuentas,")
        print("     PERO SOLO guarda 'Management Events' (crear bucket, lanzar EC2, asociar rol).")
        print("  2. 'Data Events' (leer un objeto en S3 con GetObject, invocar una Lambda)")
        print("     VIENEN DESACTIVADOS POR DEFECTO.")
        print("  3. Si un atacante entra y descarga 50,000 registros médicos, estados de cuenta")
        print("     o facturas del SAT, LA VECINA CHISMOSA ESTA CIEGA y en tu consola no aparece nada.")
        print(f"\n{BOLD}{GREEN}[BUENA PRACTICA / DEFENSA]:{RESET}")
        print("  Para auditar descargas sensibles, debes crear un Trail dedicado")
        print("  y activar explicitamente 'Data Events' para los buckets criticos,")
        print("  o activar 'Amazon GuardDuty' para deteccion de anomalías de exfiltracion.\n")
    else:
        print(f"    {GREEN}[!] Se detectaron Data Events configurados.{RESET}")

if __name__ == "__main__":
    main()
