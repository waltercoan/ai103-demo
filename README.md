# AI103 Demos

## Indice dos Demos

- [module01/demo01.py](module01/demo01.py): Lista os 10 primeiros modelos (deployments) publicados no Microsoft Foundry.
- [module01/demo02.py](module01/demo02.py): Envia um prompt simples ao Azure OpenAI com autenticacao por token Entra ID.
- [module01/demo03.py](module01/demo03.py): Lista as primeiras 10 connections/tools configuradas no projeto Foundry.
- [module01/demo04.py](module01/demo04.py): Envia prompt ao Azure OpenAI e extrai resposta de output_text.
- [module01/demo05.py](module01/demo05.py): Implementa conversacao multi-turn mantendo contexto entre mensagens.
- [module01/demo06.py](module01/demo06.py): Utiliza Azure OpenAI com function calling e code interpreter tool.
- [module01/demo07.py](module01/demo07.py): Integra web search tool com Azure OpenAI para buscas na internet.
- [module01/demo08.py](module01/demo08.py): Implementa file search tool para buscar informacoes em arquivos.
- [module01/demo09.py](module01/demo09.py): Coleta informacoes de hardware do sistema e expoe como Function Tool.
- [module02/demo10.py](module02/demo10.py): Cria agente de RH com instrucoes customizadas usando PromptAgentDefinition.
- [module02/demo11.py](module02/demo11.py): Cria agente com OpenAPI tools para integracao de APIs customizadas.
- [module02/demo12.py](module02/demo12.py): Cria agente com MCP tools e gerencia solicitacoes de aprovacao MCP.
- [module03/demo13.py](module03/demo13.py): Detecta e extrai PII usando servico de Text Analytics do Azure.
- [module03/demo14.py](module03/demo14.py): Chama MCP tools remotos para extracao de PII via HTTP.
- [module03/demo15.py](module03/demo15.py): Usa modelo GPT para remocao de PII com retorno estruturado em JSON.
- [module03/demo16.py](module03/demo16.py): Cria agente com MCP tools usando endpoints remotos com autenticacao.
- [module04/demo17.py](module04/demo17.py): Descreve imagem JPG com Chat Completions no Azure OpenAI.
- [module04/demo18.py](module04/demo18.py): Descreve imagem JPG com a API de Responses no Azure OpenAI.
- [module04/demo19.py](module04/demo19.py): Analisa imagem com Content Understanding e imprime resultado estruturado.

## Login Azure CLI

```bash
 az login --use-device-code
```

## Criar um venv do Python

```bash
python -m venv .venv
```

Ative o ambiente virtual:

- **Windows (PowerShell):**

	```powershell
	.\.venv\Scripts\Activate.ps1
	```

- **Windows (CMD):**

	```cmd
	.\.venv\Scripts\activate.bat
	```

- **Linux/macOS:**

	```bash
	source .venv/bin/activate
	```

## .env File
```
FOUNDRY_PROJECT_ENDPOINT=https://<FOUNDRY_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>
FOUNDRY_MODEL_DEPLOYMENT_NAME=deploy-gpt-5.2
AZURE_OPENAI_ENDPOINT=https://<FOUNDRY_NAME>.openai.azure.com/openai/v1
#IMPORTANTE URL COGNITIVE SERVICES DIFERENTE DO PORTAL
FOUNDRY_TEXT_ANALYTICS_ENDPOINT=https://<FOUNDRY_NAME>.cognitiveservices.azure.com/
FOUNDRY_REMOTE_MCP_URL=https://<FOUNDRY_NAME>.cognitiveservices.azure.com/language/mcp?api-version=2025-11-15-preview
FOUNDRY_REMOTE_MCP_PROJECT_CONNECTION_ID=<NOME_DA_CONEXAO_REMOTE_TOOL>
CONTENTUNDERSTANDING_ENDPOINT=https://<FOUNDRY_NAME>.cognitiveservices.azure.com/
```