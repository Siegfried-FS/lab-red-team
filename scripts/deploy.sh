#!/bin/bash
set -e

STACK_NAME="lab-red-team"
REGION=$(aws configure get region || echo "us-east-1")
TEMPLATE_FILE="$(dirname "$0")/../infra/cloudformation.yaml"

echo "============================================================"
echo "[INFO] Verificacion de Estado y Despliegue del Laboratorio"
echo "============================================================"

IDENTITY_JSON=$(aws sts get-caller-identity --output json 2>/dev/null || echo "")

if [ -z "$IDENTITY_JSON" ]; then
  echo "[ERROR] No se pudieron obtener credenciales activas de AWS."
  echo "Por favor inicia sesion con AWS CLI (ej. 'aws sso login' o 'aws configure')."
  exit 1
fi

ACCOUNT_ID=$(echo "$IDENTITY_JSON" | grep -o '"Account": "[^"]*' | cut -d'"' -f4)
ARN=$(echo "$IDENTITY_JSON" | grep -o '"Arn": "[^"]*' | cut -d'"' -f4)

echo "[*] Cuenta AWS ID:   $ACCOUNT_ID"
echo "[*] Identidad (ARN): $ARN"
echo "[*] Region AWS:      $REGION"
echo "[*] Stack objetivo:  $STACK_NAME"
echo "------------------------------------------------------------"

# 1. Validar si el stack ya existe y su estado
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].StackStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" != "NOT_FOUND" ]; then
  echo "[AVISO] El stack '$STACK_NAME' ya existe en la cuenta con estado: $STACK_STATUS."
  
  if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    echo "[INFO] La infraestructura ya se encuentra desplegada y lista para operar."
    echo -n "¿Deseas actualizar el stack existente o mantenerlo tal como esta? (actualizar/mantener): "
    read -r ACCION
    if [[ "$ACCION" != "actualizar" && "$ACCION" != "a" ]]; then
      echo "[OK] Operacion finalizada sin cambios. Mostrando salidas existentes:"
      aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs" \
        --output table
      exit 0
    fi
  elif [ "$STACK_STATUS" == "CREATE_FAILED" ] || [ "$STACK_STATUS" == "ROLLBACK_COMPLETE" ]; then
    echo "[ALERTA] El stack se encuentra en estado fallido ($STACK_STATUS)."
    echo "[*] Eliminando stack previo para permitir un despliegue limpio..."
    bash "$(dirname "$0")/destroy.sh"
  fi
fi

# 2. Confirmacion de cuenta
if [ -t 0 ]; then
  echo -e "\033[1;33m[ALERTA DE SEGURIDAD]:\033[0m"
  echo "Este laboratorio desplegara recursos con vulnerabilidades intencionales de prueba."
  echo -n "¿Confirmas que esta es tu cuenta aislada (Sandbox/Lab) para el taller? (s/n): "
  read -r CONFIRM
  if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" && "$CONFIRM" != "y" && "$CONFIRM" != "yes" ]]; then
    echo "[INFO] Operacion cancelada por el usuario."
    exit 0
  fi
fi

echo ""
echo "[+] Desplegando infraestructura con CloudFormation..."
aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectName="$STACK_NAME"

echo ""
echo "[OK] Despliegue completado con exito."

# Subida automatica de datos simulados y archivo premio de la comunidad
EXPOSED_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ExposedS3BucketName'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -n "$EXPOSED_BUCKET" ]; then
  echo "[+] Subiendo datos de prueba inmediatamente al bucket expuesto..."
  TMP_DIR=$(mktemp -d)
  cat << 'EOF' > "$TMP_DIR/factura_sat_ejemplo.xml"
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante Version="4.0" Total="45200.00" Moneda="MXN" xmlns:cfdi="http://www.sat.gob.mx/cfd/4">
  <cfdi:Emisor Rfc="PME120304AA1" Nombre="PYME SERVICIOS CLOUD MEXICO SA DE CV"/>
  <cfdi:Receptor Rfc="XAXX010101000" Nombre="PUBLICO EN GENERAL"/>
  <cfdi:Conceptos>
    <cfdi:Concepto Descripcion="Auditoria de Sistemas y Respaldos" Importe="45200.00"/>
  </cfdi:Conceptos>
</cfdi:Comprobante>
EOF

  cat << 'EOF' > "$TMP_DIR/backup_db_clientes.sql"
-- DUMP DE BASE DE DATOS DE CLIENTES (SIMULACION LAB)
-- Fecha: 2026-09-19
INSERT INTO clientes (nombre, curp, telefono, email, saldo) VALUES
('Juan Perez Lopez', 'PELJ880101HDFR02', '5512345678', 'juan.perez@empresa.mx', 12500.00),
('Maria Rodriguez Gomez', 'ROGM920415MVER09', '2299876543', 'maria.rodriguez@veracruz.gob.mx', 48000.00);
EOF

  cat << 'EOF' > "$TMP_DIR/credenciales_acceso.txt"
# CREDENCIALES INTERNAS DEL SERVICIO (SIMULACION LAB)
VPN_HOST=vpn.interno.lab.local
VPN_USER=admin_temporal
VPN_TOKEN=tok_simulado_99812_seguro
EOF

  aws s3 cp "$TMP_DIR/factura_sat_ejemplo.xml" "s3://$EXPOSED_BUCKET/facturas/factura_sat_ejemplo.xml" --quiet || true
  aws s3 cp "$TMP_DIR/backup_db_clientes.sql" "s3://$EXPOSED_BUCKET/backups/backup_db_clientes.sql" --quiet || true
  aws s3 cp "$TMP_DIR/credenciales_acceso.txt" "s3://$EXPOSED_BUCKET/confidencial/credenciales_acceso.txt" --quiet || true
  rm -rf "$TMP_DIR"

  PDF_PREMIO="$(dirname "$0")/../presentacion/Guia_Oportunidades_Becas_AWS_2026.pdf"
  if [ -f "$PDF_PREMIO" ]; then
    aws s3 cp "$PDF_PREMIO" "s3://$EXPOSED_BUCKET/premios/Guia_Oportunidades_Becas_AWS_2026.pdf" --quiet || true
  fi

  echo "    [OK] Archivos de prueba (Factura SAT, Respaldo SQL, Credenciales y Guía de Becas) cargados en S3."
fi

echo ""
echo "Obteniendo salidas de la infraestructura..."
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs" \
  --output table
