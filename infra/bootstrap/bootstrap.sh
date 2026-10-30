#!/usr/bin/env bash
# Bootstrap do Azure (T07). Roda UMA vez, com o seu usuário (dono da assinatura), de preferência no
# Azure Cloud Shell (Bash), que já vem com az e terraform. Cria o que o CD não deve criar sozinho:
#   1. o registro dos provedores de recurso na assinatura;
#   2. os grupos de recursos (projeto e estado do Terraform);
#   3. o Storage Account do estado remoto, sem chave de acesso (só Entra ID);
#   4. a identidade do GitHub Actions, com credencial federada (OIDC): nenhum segredo no GitHub;
#   5. os papéis dessa identidade, com escopo só nos recursos do projeto (decisões D4 e D5).
# Pode rodar de novo: cada passo confere se o recurso já existe antes de criar.
#
# Uso: ALERT_EMAIL=voce@exemplo.com bash infra/bootstrap/bootstrap.sh
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-narcelioferreira/redacao-assistida}"
GITHUB_ENVIRONMENT="${GITHUB_ENVIRONMENT:-demo}"
LOCATION="${LOCATION:-brazilsouth}"
APP_RG="${APP_RG:-rg-redacao-demo}"
STATE_RG="${STATE_RG:-rg-redacao-tfstate}"
APP_NAME="${APP_NAME:-github-redacao-assistida}"
: "${ALERT_EMAIL:?defina ALERT_EMAIL, o e-mail que recebe os alertas de orçamento}"

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
echo "Assinatura: $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"

echo "1/5 Provedores de recurso"
# A identidade do CD não tem permissão na assinatura, então o registro acontece aqui.
for namespace in Microsoft.App Microsoft.OperationalInsights Microsoft.Insights \
  Microsoft.Consumption Microsoft.Storage; do
  az provider register --namespace "$namespace" --wait --output none
done

echo "2/5 Grupos de recursos"
for rg in "$APP_RG" "$STATE_RG"; do
  az group create --name "$rg" --location "$LOCATION" --tags projeto=redacao-assistida --output none
done

echo "3/5 Estado remoto do Terraform"
STATE_ACCOUNT="$(az storage account list --resource-group "$STATE_RG" --query '[0].name' -o tsv)"
if [ -z "$STATE_ACCOUNT" ]; then
  # O nome é global: prefixo fixo e sufixo aleatório (só minúsculas e dígitos, até 24 caracteres).
  STATE_ACCOUNT="stredacaotf$(openssl rand -hex 4)"
  az storage account create --name "$STATE_ACCOUNT" --resource-group "$STATE_RG" \
    --location "$LOCATION" --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 \
    --allow-blob-public-access false --allow-shared-key-access false --output none
fi
# Versionamento de blobs: um estado corrompido ou apagado por engano pode ser recuperado.
az storage account blob-service-properties update --account-name "$STATE_ACCOUNT" \
  --resource-group "$STATE_RG" --enable-versioning true --output none
# container-rm usa o plano de controle: funciona sem chave de acesso e sem papel de dados.
if [ "$(az storage container-rm exists --storage-account "$STATE_ACCOUNT" \
  --resource-group "$STATE_RG" --name tfstate --query exists -o tsv)" != "true" ]; then
  az storage container-rm create --storage-account "$STATE_ACCOUNT" \
    --resource-group "$STATE_RG" --name tfstate --output none
fi
STATE_ACCOUNT_ID="$(az storage account show --name "$STATE_ACCOUNT" --resource-group "$STATE_RG" \
  --query id -o tsv)"
STATE_SCOPE="$STATE_ACCOUNT_ID/blobServices/default/containers/tfstate"

echo "4/5 Identidade do GitHub Actions (OIDC)"
APP_ID="$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
fi
if ! az ad sp show --id "$APP_ID" --output none 2>/dev/null; then
  az ad sp create --id "$APP_ID" --output none
fi
SP_OBJECT_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"
# Só jobs do environment "demo" deste repositório conseguem trocar o token do GitHub por um
# token do Azure. Um fork ou outro workflow recebe um "subject" diferente e é recusado.
# O GitHub emite o subject com os IDs imutáveis do dono e do repositório
# (repo:dono@ID/repo@ID:...). Se o repositório for apagado e alguém criar outro com o mesmo nome,
# o ID muda e o Azure recusa: mais seguro do que o formato só com nomes.
REPO_JSON="$(curl -fsSL "https://api.github.com/repos/${GITHUB_REPO}")"
REPO_ID="$(jq -r '.id' <<<"$REPO_JSON")"
OWNER_ID="$(jq -r '.owner.id' <<<"$REPO_JSON")"
SUBJECT="repo:${GITHUB_REPO%%/*}@${OWNER_ID}/${GITHUB_REPO#*/}@${REPO_ID}:environment:${GITHUB_ENVIRONMENT}"
CREDENTIAL_NAME="github-${GITHUB_ENVIRONMENT}"
CREDENTIAL="{
  \"name\": \"${CREDENTIAL_NAME}\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"${SUBJECT}\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"
CURRENT_SUBJECT="$(az ad app federated-credential list --id "$APP_ID" \
  --query "[?name=='${CREDENTIAL_NAME}'].subject" -o tsv)"
if [ -z "$CURRENT_SUBJECT" ]; then
  az ad app federated-credential create --id "$APP_ID" --output none --parameters "$CREDENTIAL"
elif [ "$CURRENT_SUBJECT" != "$SUBJECT" ]; then
  # Credencial de uma execução anterior com outro subject: corrige no lugar.
  az ad app federated-credential update --id "$APP_ID" \
    --federated-credential-id "$CREDENTIAL_NAME" --output none --parameters "$CREDENTIAL"
fi
echo "   subject aceito: $SUBJECT"

echo "5/5 Papéis (menor privilégio)"
assign() { # papel escopo object-id tipo
  if [ -z "$(az role assignment list --assignee "$3" --role "$1" --scope "$2" \
    --query '[0].id' -o tsv)" ]; then
    az role assignment create --assignee-object-id "$3" --assignee-principal-type "$4" \
      --role "$1" --scope "$2" --output none
  fi
}
APP_RG_ID="$(az group show --name "$APP_RG" --query id -o tsv)"
assign "Contributor" "$APP_RG_ID" "$SP_OBJECT_ID" ServicePrincipal
assign "Storage Blob Data Contributor" "$STATE_SCOPE" "$SP_OBJECT_ID" ServicePrincipal
# O seu usuário também precisa do estado para rodar o Terraform fora do CD.
assign "Storage Blob Data Contributor" "$STATE_SCOPE" \
  "$(az ad signed-in-user show --query id -o tsv)" User

cat <<EOF

Pronto. Cadastre estas variáveis no GitHub: Settings → Secrets and variables → Actions → Variables
(aba "Repository variables"). Não são segredos: sem a credencial federada, não dão acesso a nada.

  AZURE_CLIENT_ID          $APP_ID
  AZURE_TENANT_ID          $TENANT_ID
  AZURE_SUBSCRIPTION_ID    $SUBSCRIPTION_ID
  AZURE_RESOURCE_GROUP     $APP_RG
  TFSTATE_RESOURCE_GROUP   $STATE_RG
  TFSTATE_STORAGE_ACCOUNT  $STATE_ACCOUNT
  ALERT_EMAIL              $ALERT_EMAIL

Por último, depois de tornar a imagem do GHCR pública (docs/deploy-azure.md, passo 4):

  AZURE_DEPLOY_ENABLED     true
EOF
