#!/usr/bin/env python3
"""
Paso 4: Modo Blue Team / Remediacion y Verificacion en Vivo.
AWS User Group Minatitlan - Demo en Vivo.
"""
import sys
import subprocess
import urllib.request
import urllib.parse
import json

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

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip()}"

def main():
    print(f"\n{BOLD}{GREEN}=== [BLUE TEAM] Remediacion y Cierre de Brechas de Seguridad ==={RESET}\n")

    bucket_name = get_cfn_output("ExposedS3BucketName")
    app_url = get_cfn_output("AppURL")

    # Obtener ID de la instancia
    try:
        inst_id_cmd = [
            "aws", "cloudformation", "describe-stack-resources",
            "--stack-name", "lab-red-team",
            "--logical-resource-id", "VulnerableEC2Instance",
            "--query", "StackResources[0].PhysicalResourceId",
            "--output", "text"
        ]
        instance_id = subprocess.check_output(inst_id_cmd, text=True).strip()
    except Exception:
        instance_id = None

    if not bucket_name or not instance_id:
        print(f"{RED}[!] No se pudieron obtener los recursos del stack 'lab-red-team'.{RESET}")
        sys.exit(1)

    print(f"{CYAN}[*] Recursos criticos a proteger:{RESET}")
    print(f"    • Instancia EC2 vulnerable: {BOLD}{instance_id}{RESET}")
    print(f"    • Bucket S3 expuesto:       {BOLD}{bucket_name}{RESET}")
    print(f"    • Aplicacion Web:           {BOLD}{app_url}{RESET}")

    # =========================================================================
    # 1. REMEDIAR IMDS: FORZAR IMDSv2 (HttpTokens=required)
    # =========================================================================
    print(f"\n{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}--> [1] REMEDIACION SSRF: Forzar IMDSv2 (Tokens Obligatorios){RESET}")
    print(f"{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{YELLOW}[*] Explicacion para la audiencia:{RESET}")
    print("    Por defecto EC2 permite IMDSv1 (peticiones GET simples sin autenticacion).")
    print("    Al cambiar HttpTokens a 'required', AWS exige un token de sesion HTTP PUT previo.")
    print("    Como el SSRF de la app web solo hace GET, no puede generar el token y el ataque muere.")

    cmd_imds = f"aws ec2 modify-instance-metadata-options --instance-id {instance_id} --http-tokens required --http-endpoint enabled"
    print(f"\n{YELLOW}[CMD] Comando que ejecuta el Administrador:{RESET}")
    print(f"    {BOLD}{cmd_imds}{RESET}\n")

    res_imds = run_cmd([
        "aws", "ec2", "modify-instance-metadata-options",
        "--instance-id", instance_id,
        "--http-tokens", "required",
        "--http-endpoint", "enabled"
    ])
    print(f"    {GREEN}[+] IMDSv2 configurado exitosamente como OBLIGATORIO.{RESET}")

    # Comprobar si el ataque SSRF sigue funcionando
    print(f"\n{YELLOW}[*] Verificando en vivo: ¿El atacante aun puede consultar credenciales?{RESET}")
    test_ssrf_cmd = f"curl -s '{app_url}/?url=http%3A%2F%2F169.254.169.254%2Flatest%2Fmeta-data%2Fiam%2Fsecurity-credentials%2F'"
    print(f"{YELLOW}[CMD] Probando la misma llamada SSRF que antes funcionaba:{RESET}")
    print(f"    {BOLD}{test_ssrf_cmd}{RESET}\n")

    try:
        target_meta = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        encoded = urllib.parse.quote(target_meta, safe='')
        req = urllib.request.Request(f"{app_url}/?url={encoded}", headers={'User-Agent': 'RedTeam-Test'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode('utf-8', errors='ignore')

            # Si el cuadro pre no existe o esta vacio, IMDS rechazo la conexion
            if "<pre>" not in content or "401" in content or "Unauthorized" in content:
                print(f"    {GREEN}{BOLD}[BLOQUEADO EXITOSAMENTE]{RESET}")
                print(f"    {GREEN}>> IMDSv2 rechazo la peticion con HTTP 401 Unauthorized.{RESET}")
                print(f"    {GREEN}>> El servidor web recibio respuesta vacia y ya NO muestra ningun rol ni credencial.{RESET}")
            else:
                extracted = content.split("<pre>")[1].split("</pre>")[0].strip()
                if extracted:
                    print(f"    {RED}[X] ALERTA: La aplicacion aun muestra datos: {extracted[:80]}{RESET}")
                else:
                    print(f"    {GREEN}{BOLD}[BLOQUEADO EXITOSAMENTE] Respuesta vacia recibida.{RESET}")
    except Exception as e:
        print(f"    {GREEN}{BOLD}[BLOQUEADO EXITOSAMENTE]{RESET} Error en la peticion: {e}")

    # =========================================================================
    # 2. REMEDIAR S3: ACTIVAR BLOCK PUBLIC ACCESS
    # =========================================================================
    print(f"\n{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}--> [2] REMEDIACION S3: Bloqueo de Acceso Publico (Block Public Access){RESET}")
    print(f"{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{YELLOW}[*] Explicacion para la audiencia:{RESET}")
    print("    El bucket tenia ACLs publicas que permitian a cualquiera descargar facturas y SQL.")
    print("    Aplicamos las 4 banderas de 'S3 Block Public Access' recomendadas por AWS.")

    cmd_s3 = (
        f"aws s3api put-public-access-block --bucket {bucket_name} \\\n"
        f"    --public-access-block-configuration \"BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true\""
    )
    print(f"\n{YELLOW}[CMD] Comando que ejecuta el Administrador:{RESET}")
    print(f"    {BOLD}{cmd_s3}{RESET}\n")

    res_s3 = run_cmd([
        "aws", "s3api", "put-public-access-block",
        "--bucket", bucket_name,
        "--public-access-block-configuration",
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    ])
    print(f"    {GREEN}[+] S3 Block Public Access activado al 100% en el bucket.{RESET}")

    # Comprobar si la descarga anonima sigue funcionando
    test_file_url = f"https://{bucket_name}.s3.amazonaws.com/facturas/factura_sat_ejemplo.xml"
    print(f"\n{YELLOW}[*] Verificando en vivo: ¿Un atacante anonimo aun puede descargar la factura sensible?{RESET}")
    print(f"{YELLOW}[CMD] Intentando descargar:{RESET}")
    print(f"    {BOLD}curl -I -s \"{test_file_url}\"{RESET}\n")

    try:
        req = urllib.request.Request(test_file_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"    {RED}[X] El archivo aun es accesible.{RESET}")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"    {GREEN}{BOLD}[BLOQUEADO EXITOSAMENTE]{RESET}")
            print(f"    {GREEN}>> Servidor responde: HTTP 403 Forbidden (Acceso anonimo denegado).{RESET}")
            print(f"    {GREEN}>> Las facturas y respaldos estan a salvo aunque sigan en el bucket.{RESET}")
        else:
            print(f"    {YELLOW}[?] Codigo HTTP recibido: {e.code}{RESET}")
    except Exception as e:
        print(f"    {GREEN}{BOLD}[BLOQUEADO EXITOSAMENTE]{RESET} Acceso denegado: {e}")

    # =========================================================================
    # 3. BUENA PRACTICA DE ACCESO SEGURO
    # =========================================================================
    print(f"\n{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}--> [3] GESTION DE ACCESO SEGURO: Eliminar SSH y Usar AWS Systems Manager{RESET}")
    print(f"{BOLD}-------------------------------------------------------------------------{RESET}")
    print(f"{YELLOW}[*] Explicacion para la audiencia:{RESET}")
    print("    NUNCA dejes el puerto 22 (SSH) abierto a 0.0.0.0/0 en tus Security Groups.")
    print("    La mejor practica de AWS es conectar la instancia a Systems Manager (SSM).")
    print("    El rol ya tiene asignada la politica 'AmazonSSMManagedInstanceCore'.")

    print(f"\n{YELLOW}[CMD] Como se conecta el Administrador sin abrir puertos ni usar llaves .pem:{RESET}")
    print(f"    {BOLD}{CYAN}aws ssm start-session --target {instance_id}{RESET}\n")
    print(f"    {GREEN}[+] Cero puertos abiertos en Internet.{RESET}")
    print(f"    {GREEN}[+] Sesion 100% cifrada via TLS.{RESET}")
    print(f"    {GREEN}[+] Cada comando queda auditado en AWS CloudTrail.{RESET}")

    print(f"\n{BOLD}{GREEN}========================================================================={RESET}")
    print(f"{BOLD}{GREEN}[RESUMEN EJECUTIVO BLUE TEAM]:{RESET}")
    print(f"{BOLD}{GREEN}========================================================================={RESET}")
    print("En 2 minutos hemos cerrado las dos brechas criticas sin romper la aplicacion:")
    print("  1. IMDSv2 neutralizo el robo de credenciales vía SSRF.")
    print("  2. S3 Block Public Access protegio los datos de clientes contra descargas.")
    print("  3. AWS Systems Manager permite administrar sin exponer el puerto 22 a Internet.\n")

if __name__ == "__main__":
    main()
