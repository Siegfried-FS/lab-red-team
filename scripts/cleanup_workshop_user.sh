#!/bin/bash
# Script de limpieza post-evento: Elimina el usuario IAM y el perfil local de AWS CLI
set -e

USER_NAME="workshop-minatitlan"

echo "============================================================"
echo "[INFO] Limpieza de Usuario IAM de Demostración: $USER_NAME"
echo "============================================================"

# 1. Obtener y eliminar Access Keys asociadas
KEYS=$(aws iam list-access-keys --user-name "$USER_NAME" --query "AccessKeyMetadata[*].AccessKeyId" --output text 2>/dev/null || echo "")
for KEY in $KEYS; do
  echo "[*] Eliminando Access Key: $KEY..."
  aws iam delete-access-key --user-name "$USER_NAME" --access-key-id "$KEY"
done

# 2. Desasociar políticas administradas
POLICIES=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --query "AttachedPolicies[*].PolicyArn" --output text 2>/dev/null || echo "")
for POL in $POLICIES; do
  echo "[*] Desasociando política: $POL..."
  aws iam detach-user-policy --user-name "$USER_NAME" --policy-arn "$POL"
done

# 3. Eliminar el usuario IAM
echo "[*] Eliminando usuario IAM: $USER_NAME..."
aws iam delete-user --user-name "$USER_NAME" 2>/dev/null || true

# 4. Limpiar el perfil en ~/.aws/credentials y ~/.aws/config
echo "[*] Limpiando perfil local 'workshop-minatitlan' de AWS CLI..."
sed -i '/\[workshop-minatitlan\]/,/^$/d' ~/.aws/credentials 2>/dev/null || true
sed -i '/\[profile workshop-minatitlan\]/,/^$/d' ~/.aws/config 2>/dev/null || true

echo ""
echo "[OK] Usuario IAM '$USER_NAME' y perfil local eliminados con éxito."
