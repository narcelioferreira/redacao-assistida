# Deploy no Azure (T07 e primeiro deploy)

Feito uma vez. Depois disso, todo push na `main` publica uma nova revisão sozinho.

**Antes de começar:** a F0 precisa estar na `main` do GitHub. O primeiro push já roda o CD, que
publica a imagem no GHCR. O job de deploy aparece como pulado até o passo 5.

## 1. Criar a conta

Crie uma conta gratuita do Azure (pede cartão de crédito para verificar identidade). A conta nova traz
crédito inicial e 12 meses de alguns serviços grátis, entre eles o PostgreSQL B1ms usado na F1.

## 2. Abrir o Cloud Shell

No [portal do Azure](https://portal.azure.com), abra o Cloud Shell (ícone `>_` no topo) no modo
**Bash**. Ele já vem com `az`, `git` e `terraform`, e já está autenticado com o seu usuário.

```bash
git clone https://github.com/narcelioferreira/redacao-assistida.git
cd redacao-assistida
```

## 3. Rodar o bootstrap

```bash
ALERT_EMAIL=seu-email@exemplo.com bash infra/bootstrap/bootstrap.sh
```

O script cria os grupos `rg-redacao-demo` e `rg-redacao-tfstate`, o Storage Account do estado, a
identidade do GitHub Actions com credencial federada (OIDC) e os papéis dela. No fim, imprime as
variáveis para o passo 5. Pode rodar de novo sem problema.

Para outra região ou outro nome de repositório: `LOCATION=eastus2 GITHUB_REPO=usuario/repo ...`.

## 4. Tornar a imagem pública

O Container Apps baixa a imagem do GHCR sem credencial (decisão D3), e o GHCR cria pacotes privados
por padrão. No GitHub: seu perfil → **Packages** → `redacao-assistida` → **Package settings** →
**Change visibility** → **Public**.

## 5. Cadastrar as variáveis no GitHub

No repositório: **Settings → Secrets and variables → Actions → Variables → New repository
variable**. Cadastre as que o bootstrap imprimiu:

| Variável | Exemplo |
|---|---|
| `AZURE_CLIENT_ID` | id da identidade do GitHub Actions |
| `AZURE_TENANT_ID` | id do tenant |
| `AZURE_SUBSCRIPTION_ID` | id da assinatura |
| `AZURE_RESOURCE_GROUP` | `rg-redacao-demo` |
| `TFSTATE_RESOURCE_GROUP` | `rg-redacao-tfstate` |
| `TFSTATE_STORAGE_ACCOUNT` | `stredacaotf…` |
| `ALERT_EMAIL` | e-mail dos alertas de orçamento |
| `AZURE_DEPLOY_ENABLED` | `true` (cadastre por último) |

São variáveis, não secrets: sem a credencial federada, esses IDs não dão acesso a nada.

## 6. Rodar o CD

**Actions → CD → Run workflow** (branch `main`). Esperado: `Publicar a imagem no GHCR` ✅, `Deploy no
Azure (demo)` ✅ e, no resumo da execução, a URL da API. Abra `<url>/docs`.

A primeira requisição depois de um tempo parado demora alguns segundos: é a escala a zero acordando
uma réplica (decisão D2).

## 7. Conferir

- **App Insights** (`appi-redacao-demo`) → *Transaction search*: as requisições aparecem, sem as
  probes. O `trace_id` de uma resposta de erro é o *Operation ID*.
- **Log Analytics** (`log-redacao-demo`) → *Logs*: tabela `ContainerAppConsoleLogs_CL`.
- **Cost Management → Budgets**: `budget-redacao-demo`, com alertas em 50%, 80% e na previsão de 100%.

## Rodar o Terraform fora do CD (opcional)

No Cloud Shell ou na sua máquina, depois de `az login`:

```bash
cd infra
terraform init \
  -backend-config="resource_group_name=rg-redacao-tfstate" \
  -backend-config="storage_account_name=<TFSTATE_STORAGE_ACCOUNT>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=demo.tfstate"
terraform plan \
  -var "image=ghcr.io/narcelioferreira/redacao-assistida:<sha-do-commit>" \
  -var "alert_email=<seu-email>"
```

## Desligar e religar

- `terraform destroy` (com as mesmas variáveis do `plan`) remove tudo dentro do grupo do projeto e
  mantém o grupo, o estado e a identidade. O próximo deploy recria o ambiente.
- Para apagar de vez, inclusive o bootstrap: exclua os dois grupos de recursos e a app registration
  `github-redacao-assistida`.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `AADSTS700213` ou `AADSTS70021` (no matching federated identity) no `terraform init` | O *subject* cadastrado não bate com o que o GitHub envia. O formato é `repo:<dono>@<id-do-dono>/<repo>@<id-do-repo>:environment:demo` (o log do erro mostra o valor enviado). Rode o bootstrap de novo: ele recalcula e corrige a credencial |
| 403 ao ler o estado logo depois do bootstrap | O papel `Storage Blob Data Contributor` ainda está propagando. Espere 1 a 2 minutos e rode de novo |
| A revisão não sobe, com erro de pull da imagem | O pacote do GHCR ainda está privado (passo 4) |
| `MissingSubscriptionRegistration` | Faltou registrar um provedor de recurso. Rode o bootstrap de novo |
| O smoke test falha por tempo | Veja os logs da revisão em *Container App → Revisions* e *Log stream* |
| O valor do orçamento parece estranho | Ele é na moeda da conta de cobrança (BRL numa conta brasileira). Ajuste `monthly_budget` |
