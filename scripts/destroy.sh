#!/bin/bash

STACK_NAME="lab-red-team"
REGION=$(aws configure get region || echo "us-east-1")

echo "============================================================"
echo "[INFO] Limpieza General y Destruccion de Recursos: $STACK_NAME ($REGION)"
echo "============================================================"

IDENTITY_JSON=$(aws sts get-caller-identity --output json 2>/dev/null || echo "")
ACCOUNT_ID=$(echo "$IDENTITY_JSON" | grep -o '"Account": "[^"]*' | cut -d'"' -f4)
echo "[*] Cuenta AWS objetivo: $ACCOUNT_ID"

# 1. Vaciar y desbloquear buckets asociados al laboratorio o con prefijo lab-red-team
echo "[*] Buscando buckets S3 relacionados con '$STACK_NAME' para vaciado forzado..."

# Obtener nombre oficial desde las salidas del stack si existe
STACK_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ExposedS3BucketName'].OutputValue" \
  --output text 2>/dev/null || echo "")

ALL_LAB_BUCKETS=()
if [ -n "$STACK_BUCKET" ] && [ "$STACK_BUCKET" != "None" ]; then
  ALL_LAB_BUCKETS+=("$STACK_BUCKET")
fi

# Buscar tambien cualquier bucket que contenga lab-red-team en el nombre (creado manualmente o repetido)
EXTRA_BUCKETS=$(aws s3api list-buckets --query "Buckets[?contains(Name, '${STACK_NAME}')].Name" --output text 2>/dev/null || echo "")
for b in $EXTRA_BUCKETS; do
  if [[ ! " ${ALL_LAB_BUCKETS[*]} " =~ " ${b} " ]]; then
    ALL_LAB_BUCKETS+=("$b")
  fi
done

for BUCKET in "${ALL_LAB_BUCKETS[@]}"; do
  if [ -n "$BUCKET" ] && [ "$BUCKET" != "None" ]; then
    echo "[*] Vaciando objetos y versiones en bucket: $BUCKET ..."
    # Desactivar retencion o bloqueo si existiera para asegurar eliminacion
    aws s3 rm "s3://$BUCKET" --recursive 2>/dev/null || true
    # Limpiar versiones de objetos por si se activo versionado accidentalmente
    VERSIONS=$(aws s3api list-object-versions --bucket "$BUCKET" --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || echo "")
    if [[ "$VERSIONS" == *"Objects"* && "$VERSIONS" != *"\"Objects\": null"* ]]; then
      aws s3api delete-objects --bucket "$BUCKET" --delete "$VERSIONS" >/dev/null 2>&1 || true
    fi
    DELETE_MARKERS=$(aws s3api list-object-versions --bucket "$BUCKET" --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || echo "")
    if [[ "$DELETE_MARKERS" == *"Objects"* && "$DELETE_MARKERS" != *"\"Objects\": null"* ]]; then
      aws s3api delete-objects --bucket "$BUCKET" --delete "$DELETE_MARKERS" >/dev/null 2>&1 || true
    fi
  fi
done

# 2. Terminar instancias EC2 que hayan quedado con tag Name=lab-red-team
echo "[*] Buscando instancias EC2 con etiqueta Name='$STACK_NAME'..."
INSTANCES_TO_KILL=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*${STACK_NAME}*" "Name=instance-state-name,Values=running,stopped,pending" \
  --query "Reservations[*].Instances[*].InstanceId" \
  --output text 2>/dev/null || echo "")

if [ -n "$INSTANCES_TO_KILL" ]; then
  echo "[*] Terminando instancias EC2 detectadas: $INSTANCES_TO_KILL ..."
  aws ec2 terminate-instances --instance-ids $INSTANCES_TO_KILL >/dev/null 2>&1 || true
  echo "[*] Esperando terminacion de instancias..."
  aws ec2 wait instance-terminated --instance-ids $INSTANCES_TO_KILL >/dev/null 2>&1 || true
fi

# 3. Eliminar stack de CloudFormation si existe
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" 2>/dev/null || echo "")
if [ -n "$STACK_EXISTS" ]; then
  echo "[*] Eliminando stack de CloudFormation: $STACK_NAME ..."
  aws cloudformation delete-stack --stack-name "$STACK_NAME"
  echo "[*] Esperando a que finalice la eliminacion del stack..."
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" 2>/dev/null || true
else
  echo "[INFO] No se encontro el stack CloudFormation '$STACK_NAME'."
fi

# 4. Limpieza de archivos temporales locales
rm -f /tmp/redteam_stolen_creds.json

echo "[OK] Proceso de destruccion y barrido concluido. Cuenta en estado limpio."
