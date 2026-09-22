#!/usr/bin/env python3
"""
Analizador de Security Headers y Cabeceras HTTP
Demostracion: securityheaders.com, la trampa de la IA y la analogia de la prenda.
AWS User Group Minatitlan.
"""
import sys
import subprocess
import urllib.request

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

SECURITY_HEADERS = [
    ("Strict-Transport-Security", "Protege contra degradacion SSL/TLS (HSTS)"),
    ("X-Frame-Options", "Protege contra ataques de Clickjacking"),
    ("X-Content-Type-Options", "Evita MIME sniffing malicioso (nosniff)"),
    ("Content-Security-Policy", "Previene Cross-Site Scripting (XSS) e inyeccion de datos"),
    ("Referrer-Policy", "Controla la informacion del remitente enviada en peticiones")
]

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
    print(f"\n{BOLD}{CYAN}=== [WEB SECURITY] Analizador de Security Headers y Cabeceras HTTP ==={RESET}\n")

    app_url = get_cfn_output("AppURL")
    target_url = app_url or "http://ejemplo.com"

    print(f"URL objetivo detectada del laboratorio: {CYAN}{target_url}{RESET}")
    custom = input(f"Ingresa una URL a analizar [Enter para usar {target_url}]: ").strip()
    if custom:
        target_url = custom

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "http://" + target_url

    print(f"\n{BOLD}--> [1] Consultando cabeceras HTTP reales mediante 'curl -I':{RESET}")
    try:
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (SecurityScanner)'})
        with urllib.request.urlopen(req, timeout=6) as response:
            headers = dict(response.info())
    except urllib.error.HTTPError as e:
        headers = dict(e.headers)
    except Exception as e:
        print(f"{RED}[!] Error al conectar con {target_url}: {e}{RESET}")
        return

    print(f"{GREEN}[+] Cabeceras de respuesta recibidas del servidor:{RESET}")
    for k, v in list(headers.items())[:6]:
        print(f"    {CYAN}{k}:{RESET} {v}")

    print(f"\n{BOLD}--> [2] Evaluando Security Headers criticos (estandar securityheaders.com):{RESET}")
    missing_count = 0
    headers_lower = {k.lower(): v for k, v in headers.items()}

    for sec_header, desc in SECURITY_HEADERS:
        if sec_header.lower() in headers_lower:
            print(f"    {GREEN}[PRESENTE]{RESET} {sec_header} -> {CYAN}{headers_lower[sec_header.lower()]}{RESET}")
        else:
            print(f"    {RED}[FALTANTE]{RESET} {sec_header} ({desc})")
            missing_count += 1

    if missing_count >= 3:
        print(f"\n    {RED}{BOLD}CALIFICACION ESTIMADA EN SECURITYHEADERS.COM: [ F ]{RESET}")
    else:
        print(f"\n    {GREEN}{BOLD}CALIFICACION ESTIMADA: [ A / A+ ]{RESET}")

    # La trampa de la IA y la analogia tecnica
    print(f"\n{BOLD}{YELLOW}[LA TRAMPA DE LA IA Y LA ANALOGIA TECNICA]:{RESET}")
    print("  Muchos desarrolladores le consultan a herramientas de IA: '¿Como obtengo A+ en securityheaders?'")
    print("  Y con frecuencia se sugiere agregar etiquetas <meta> en el HTML:")
    print(f"    {RED}<meta http-equiv=\"X-Frame-Options\" content=\"DENY\">{RESET}  <-- Inutil")
    print("  Fundamento tecnico:")
    print("    Colocar directivas de seguridad en el cuerpo HTML equivale a coser la etiqueta de")
    print("    'No lavar con agua caliente' dentro de una prenda, pero leerla una vez que la prenda")
    print("    ya salio encogida de la lavadora.")
    print("    Los motores de navegadores IGNORAN directivas como HSTS y X-Frame-Options en <meta>.")
    print("    Deben suministrarse formalmente en las cabeceras HTTP de respuesta del servidor o CDN.")

    print(f"\n{BOLD}{GREEN}[CONFIGURACION EN AWS AMPLIFY: customHttp.yml]:{RESET}")
    print("  Crear un archivo 'customHttp.yml' en la raiz del proyecto:")
    print(f"""{CYAN}
  customHeaders:
    - pattern: '**/*'
      headers:
        - key: 'Strict-Transport-Security'
          value: 'max-age=31536000; includeSubDomains'
        - key: 'X-Frame-Options'
          value: 'SAMEORIGIN'
        - key: 'X-Content-Type-Options'
          value: 'nosniff'
        - key: 'Content-Security-Policy'
          value: "default-src 'self'"
  {RESET}""")
    print("  Al redesplegar la aplicacion en AWS Amplify, CloudFront inyecta las cabeceras en el Edge.")

    print(f"\n{BOLD}{MAGENTA}[DATO CURIOSO / PRO-TIP DE AMPLIFY PARA LA AUDIENCIA]:{RESET}")
    print("  ¿Subiste 'customHttp.yml' a GitHub y Amplify no aplico las cabeceras?")
    print("  ¡Es la maña clasica de Amplify! Si alguna vez tocaste la seccion de")
    print("  'App Settings -> Custom headers' en la consola web, la consola toma prioridad")
    print("  y sobreescribe/ignora en silencio el archivo que subiste por Git.")
    print("  Solucion infalible: Pegar el YAML directo en 'Custom headers' de la consola web")
    print("  o incrustar la seccion 'customHeaders:' dentro de tu 'amplify.yml' de build.\n")

if __name__ == "__main__":
    main()
