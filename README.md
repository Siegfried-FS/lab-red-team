# AWS Cloud Red Team & Blue Defense Lab

Laboratorio práctico demostrativo y educativo para ilustrar la mentalidad de un atacante (Red Team) frente a las malas configuraciones más comunes en Amazon Web Services (AWS), y cómo implementar controles defensivos efectivos (Blue Team).

---

## Arquitectura del Laboratorio

```text
Internet (Atacante)
       |
       v
 +--------------------------------------------------------+
 | Amazon VPC (10.0.0.0/16)                               |
 |                                                        |
 |  Subred Pública (10.0.1.0/24)                          |
 |  +--------------------------------------------------+  |
 |  | EC2 (t2.micro - Amazon Linux 2023)               |  |
 |  |  - App Web con SSRF (Flask, puerto 80)           |  |
 |  |  - IMDSv1 habilitado (HttpTokens=optional)       |  |
 |  |  - Security Group con 0.0.0.0/0 en puerto 22 SSH |  |
 |  |  - Rol IAM sobreprivilegiado                     |  |
 |  +-----------+--------------------------------------+  |
 |              | (Extracción de Token STS vía SSRF)      |
 +--------------+-----------------------------------------+
                v
      +--------------------+      +-------------------------+
      | Amazon S3 Bucket   |      | AWS IAM & EC2 API       |
      | - Facturas SAT XML |      | - Reconocimiento lateral|
      | - Backup DB .SQL   |      | - Mapeo de instancias   |
      | - Lectura pública  |      | - Listado de roles      |
      +--------------------+      +-------------------------+
```

---

## Vectores Evaluados

| Fase | Vector Evaluado | Descuido Típico | Demostración Práctica | Opción en `./redteam` |
|:---:|---|---|---|:---:|
| **Setup** | Despliegue Automatizado | Configuración manual propensa a error | CloudFormation nativo en ~2 min 40 seg | `Opción [1]` |
| **Fase 1** | S3 Public Access | Block Public Access inactivo + GetObject | Fuga de facturas fiscales simuladas y respaldo DB | `Opción [2]` y `[2b]` |
| **Fase 2** | SSRF & IMDSv1 | Formulario sin sanitizar y tokens opcionales | Consulta a 169.254.169.254 y extracción de credenciales STS | `Opción [3]` |
| **Fase 3** | Movimiento Lateral | Rol IAM con permisos excesivos (`*`) | Enumeración de buckets, instancias y roles con llaves robadas | `Opción [4]` |
| **Fase 4** | Auditoría CloudTrail | Creer que todo se registra por omisión | Cero coincidencias para descargas (Data Events apagados) | `Opción [5]` |
| **Fase 5** | Remediación Blue Team | Parchear solo en código y no en la nube | Forzado de IMDSv2 en caliente y activación de S3 BPA | `Opción [6]` |
| **Fase 6** | Security Headers | Desplegar sitios web a las prisas | Análisis de cabeceras HTTP y generación de `customHttp.yml` | `Opción [7]` |

---

## Requisitos Previos

- **Cuenta de AWS activa:** Con permisos para desplegar VPC, CloudFormation, EC2, IAM y S3.
- **Python 3.9+**
- **AWS CLI v2 configurado:**
  ```bash
  aws configure
  ```

---

## Inicio Rápido

Clona el repositorio e inicia el asistente interactivo:

```bash
git clone https://github.com/Siegfried-FS/lab-red-team.git
cd lab-red-team
./redteam
```

El script detecta automáticamente tu sesión activa de AWS (cuenta, perfil y región) y te presenta el menú:

| Opción | Módulo | Descripción Detallada | Script Asociado |
|:---:|:---|:---|:---|
| **`[1]`** | **Desplegar Laboratorio** | Ejecuta CloudFormation para aprovisionar VPC, subred pública, EC2 (`t2.micro`), app Flask vulnerable y bucket S3. | `scripts/deploy.sh` |
| **`[2]`** | **Fase 1: Exfiltración S3** | Demuestra la descarga no autenticada de archivos sensibles (`factura_sat_ejemplo.xml` y `backup_db_clientes.sql`). | `scripts/01_explotar_s3.py` |
| **`[2b]`** | **Escanear con s3scanner** | Ejecuta un escaneo automatizado con `s3scanner` utilizando un diccionario enfocado en patrones de nombres comunes. | `scripts/wordlist_s3_mexico.txt` |
| **`[3]`** | **Fase 2: SSRF e IMDSv1** | Explota el formulario web para forzar a la instancia a consultar `169.254.169.254`, extrayendo credenciales STS. | `scripts/02_explotar_ssrf_imds.py` |
| **`[4]`** | **Fase 3: Movimiento Lateral** | Carga las credenciales robadas y ejecuta llamadas a la API (`sts get-caller-identity`, `s3 ls`, `ec2 describe-instances`). | `scripts/03_movimiento_lateral.py` |
| **`[5]`** | **Auditoría CloudTrail** | Evidencia que CloudTrail tiene cero eventos para `GetObject` porque los Data Events no vienen activos por omisión. | `scripts/05_auditoria_cloudtrail.py` |
| **`[6]`** | **Modo Blue Team** | Aplica remediaciones en caliente: fuerza IMDSv2 (`--http-tokens required`), activa S3 Block Public Access y SSM. | `scripts/04_blue_remediation.py` |
| **`[7]`** | **Security Headers** | Analiza cabeceras HTTP de respuesta y genera el archivo `customHttp.yml` para mitigar Clickjacking y MIME-sniffing. | `scripts/06_analizar_headers.py` |
| **`[8]`** | **Ver Estado del Stack** | Consulta en tiempo real con `aws cloudformation describe-stacks` las salidas activas del laboratorio. | AWS CLI Nativo |
| **`[9]`** | **Presentación Interactiva** | Abre en el navegador las diapositivas interactivas en HTML (`presentacion/slides.html` - presiona **F** para pantalla completa). | `presentacion/slides.html` |
| **`[10]`** | **Destruir Laboratorio** | Pide confirmación, vacía completamente el bucket S3 y destruye el stack en ~2 minutos para garantizar costo de $0 USD. | `scripts/destroy.sh` |
| **`[0]`** | **Salir** | Cierra la sesión del asistente. | - |

---

## Costos y Free Tier

Este laboratorio está diseñado para correr 100% dentro de los límites del **AWS Free Tier**:
- 1 instancia `t2.micro` (750 horas mensuales gratuitas).
- 1 VPC básica sin costos por hora (sin NAT Gateway).
- 1 bucket S3 con archivos de pocos kilobytes.

### Destrucción Limpia
Al terminar tus pruebas, ejecuta la **Opción `[10]`** en `./redteam` o corre directamente:
```bash
./scripts/destroy.sh
```

> 💡 **Regla de oro de auditoría financiera:**  
> Tras ejecutar la destrucción, verifica en la consola de AWS o mediante `aws ec2 describe-instances` que la máquina figure en estado `terminated` para garantizar que no existan cobros residuales.

---

## Estructura del Repositorio

```text
lab-red-team/
├── redteam                      # Asistente interactivo CLI principal
├── infra/
│   └── cloudformation.yaml      # Plantilla declarativa de infraestructura (t2.micro)
├── presentacion/
│   ├── slides.html              # Diapositivas interactivas para proyector (19 slides)
│   ├── Guia_Oportunidades_Becas_AWS_2026.pdf # Catálogo de becas y programas gratuitos
│   └── imagenes/                # Diagramas, logos comunitarios y códigos QR
├── scripts/
│   ├── deploy.sh                # Script de despliegue automatizado y carga de datos simulados
│   ├── destroy.sh               # Script de destrucción limpia y vaciado de S3
│   ├── 01_explotar_s3.py        # Fase 1: Descarga pública anónima en S3
│   ├── 02_explotar_ssrf_imds.py # Fase 2: Explotación SSRF y extracción IMDSv1
│   ├── 03_movimiento_lateral.py # Fase 3: Enumeración con credenciales STS asumidas
│   ├── 04_blue_remediation.py   # Fase 4: Remediación en caliente (IMDSv2 + S3 BPA)
│   ├── 05_auditoria_cloudtrail.py # Fase 5: Auditoría forense CloudTrail (Management vs Data)
│   ├── 06_analizar_headers.py   # Fase 6: Análisis de Security Headers y customHttp.yml
│   ├── cleanup_workshop_user.sh # Limpieza de credenciales temporales
│   └── wordlist_s3_mexico.txt   # Diccionario de nombres de buckets para pruebas
└── README.md
```

---

## Aviso de Responsabilidad (Disclaimer)

Este repositorio tiene propósitos estrictamente educativos y de investigación en seguridad defensiva. Todos los ataques deben realizarse únicamente dentro de cuentas de AWS propias y autorizadas. Los autores no se hacen responsables por el mal uso de las herramientas o técnicas descritas.
