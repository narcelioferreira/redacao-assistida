# Validação por mutação

Gerado por `scripts/mutacao.py`. Cada linha desliga um controle de propósito;
o controle só conta como comprovado se pelo menos um teste falha.

| ID | Controle | Mutação (proteção desligada) | Testes que falharam | Resultado |
|---|---|---|---|---|
| M01 | ASI03 | Erro 500 devolve a mensagem da exceção | `test_erro_inesperado_nao_vaza_detalhe_interno` | ✅ morta |
| M02 | ASI03 · LGPD | Erro 422 ecoa o valor enviado | `test_validacao_lista_os_campos_sem_ecoar_o_valor` | ✅ morta |
| M03 | ASI03 | Connection string como texto comum (sem SecretStr) | `test_connection_string_nao_aparece_em_repr` | ✅ morta |
| M04 | ASI03 | Respostas sem cabeçalhos de segurança | `test_respostas_levam_cabecalhos_de_seguranca` | ✅ morta |
| M05 | ASI03 | Container roda como root | `test_container_roda_sem_privilegio` | ✅ morta |
| M06 | ASI03 | Checkout guarda a credencial do GitHub | `test_checkout_nao_guarda_credencial[cd.yml]` | ✅ morta |
| M07 | ASI03 | Deploy fora do environment demo | `test_token_oidc_so_no_job_de_deploy_e_no_environment_demo` | ✅ morta |
| M08 | ASI03 | Credencial federada aceita qualquer branch do repositório | `test_credencial_federada_presa_ao_environment` | ✅ morta |
| M24 | ASI03 | Credencial federada sem os IDs imutáveis (aceitaria um repositório recriado com o mesmo nome) | `test_credencial_federada_presa_ao_environment` | ✅ morta |
| M09 | ASI03 | Identidade do CD com Contributor na assinatura inteira | `test_papeis_do_cd_restritos_ao_projeto` | ✅ morta |
| M10 | ASI03 | Estado do Terraform aceita chave de acesso | `test_estado_do_terraform_sem_chave_de_acesso` | ✅ morta |
| M11 | ASI03 | Connection string como valor literal no container | `connection_string_como_secret` | ✅ morta |
| M12 | ASI04 · AST02 | Action fixada por tag em vez de SHA | `test_actions_fixadas_por_sha_de_commit[ci.yml]` | ✅ morta |
| M13 | ASI04 · AST07 | Imagem base sem digest | `test_dockerfile_tem_a_versao_do_uv_que_o_ci_le`<br>`test_imagens_base_por_digest` | ✅ morta |
| M14 | ASI04 · AST02 | Regra dos 14 dias desligada | `test_dependencias_com_14_dias_de_publicacao` | ✅ morta |
| M15 | ASI04 · AST07 | Deploy aceita tag móvel (latest) | `tag_movel_e_recusada` | ✅ morta |
| M16 | ASI04 | Segredo de repositório usado no workflow | `test_nenhum_segredo_alem_do_github_token[cd.yml]` | ✅ morta |
| M17 | ASI04 | Dependabot sem espera para as actions | `test_dependabot_cobre_todos_os_ecossistemas_com_espera` | ✅ morta |
| M18 | ASI08 | Trava de rede dos testes desligada | `test_trava_de_rede_bloqueia_endereco_externo` | ✅ morta |
| M19 | ASI08 · D10 | Probes de health rastreadas (custo de ingestão) | `test_probes_ficam_fora_do_trace` | ✅ morta |
| M20 | ASI08 · D2 | API sem escala a zero | `escala_limitada` | ✅ morta |
| M21 | ASI08 · D10 | Log Analytics sem teto diário | `logs_com_destino_e_teto` | ✅ morta |
| M22 | ASI08 · D3 | Smoke test aceita qualquer versão no ar | `test_recusa_quando_a_revisao_no_ar_e_outra` | ✅ morta |
| M23 | ASI02 | Smoke test aceita esquema file:// | `test_recusa_esquema_que_nao_e_http` | ✅ morta |
| M25 | ASI04 | Dependabot propõe troca de versão do Python (3.12 → 3.x) | `test_dependabot_cobre_todos_os_ecossistemas_com_espera` | ✅ morta |
| M26 | ASI04 · AST07 | CI com versão do uv escrita à mão (desalinha da imagem) | `test_uv_do_ci_vem_do_dockerfile[ci.yml]` | ✅ morta |

**26 de 26 mutações mortas.**
