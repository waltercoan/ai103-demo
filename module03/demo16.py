import json
import os
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def _get_required_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise ValueError(f"A variavel {name} nao foi definida no arquivo .env")
	return value


def _build_credential() -> DefaultAzureCredential:
	return DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)


def _build_mcp_authorization() -> str:
	bearer_token = os.getenv("FOUNDRY_REMOTE_MCP_BEARER_TOKEN")
	if bearer_token:
		# MCPTool.authorization espera token OAuth, sem prefixo "Bearer ".
		if bearer_token.lower().startswith("bearer "):
			return bearer_token[7:].strip()
		return bearer_token

	credential = _build_credential()
	token = credential.get_token("https://ai.azure.com/.default")
	return token.token


def print_tool_output(response: Any) -> None:
	# Imprime itens de tool MCP retornados para facilitar depuracao.
	outputs = getattr(response, "output", None) or []
	found = False

	print("\nRetorno da chamada da tool MCP:")
	for item in outputs:
		item_type = str(getattr(item, "type", "")).lower()
		if "mcp" in item_type or "tool" in item_type:
			found = True
			if hasattr(item, "model_dump"):
				print(json.dumps(item.model_dump(), indent=2, ensure_ascii=False))
			elif hasattr(item, "to_dict"):
				print(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
			else:
				print(repr(item))

	if not found:
		print("(nenhum item de tool retornado)")


def get_mcp_approval_request_id(response: Any) -> str | None:
	outputs = getattr(response, "output", None) or []
	for item in outputs:
		if str(getattr(item, "type", "")).lower() == "mcp_approval_request":
			return getattr(item, "id", None)
	return None


def _create_or_update_pii_agent(project_client: AIProjectClient, model_deployment: str) -> str:
	instructions = (
		"Voce e um assistente de privacidade de dados. "
		"Use a tool MCP de PII para analisar o texto recebido e extrair/redigir dados pessoais. "
		"Sempre responda em portugues, destaque entidades sensiveis e apresente o texto sanitizado."
	)
	mcp_url = _get_required_env("FOUNDRY_REMOTE_MCP_URL")
	project_connection_id = os.getenv("FOUNDRY_REMOTE_MCP_PROJECT_CONNECTION_ID")
	authorization = _build_mcp_authorization()

	mcp_tool_kwargs: dict[str, Any] = {
		"server_label": "pii-remote-server",
		"server_url": mcp_url,
		"server_description": "Servidor MCP remoto para extracao/remocao de PII",
		"allowed_tools": ["redact_pii_from_text", "redact_pii_from_document"],
	}

	if project_connection_id:
		mcp_tool_kwargs["project_connection_id"] = project_connection_id
	else:
		mcp_tool_kwargs["authorization"] = authorization

	mcp_tool = MCPTool(**mcp_tool_kwargs)

	agent_name = "agente-pii-mcp-demo"
	project_client.agents.create_version(
		agent_name=agent_name,
		definition=PromptAgentDefinition(
			model=model_deployment,
			instructions=instructions,
			tools=[mcp_tool],
		),
	)

	return agent_name


def main() -> None:
	# Carrega variaveis de ambiente do .env na raiz do projeto.
	load_dotenv()

	project_endpoint = _get_required_env("FOUNDRY_PROJECT_ENDPOINT")
	model_deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "deploy-gpt-4.1")

	print("Configuracao:")
	print(f"FOUNDRY_PROJECT_ENDPOINT={project_endpoint}")
	print(f"FOUNDRY_MODEL_DEPLOYMENT_NAME={model_deployment}")

	credential = _build_credential()
	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
		allow_preview=True,
	)

	agent_name = _create_or_update_pii_agent(project_client, model_deployment)
	print(f"\nAgente pronto no Azure Foundry: {agent_name}")

	texto = (
		"Meu nome e Mariana Lima. Meu CPF e 321.654.987-00, "
		"meu e-mail e mariana.lima@contoso.com e meu telefone e +55 11 95555-1111."
	)

	print("\nSolicitando ao agente para usar a tool MCP de PII...")
	openai_client = project_client.get_openai_client()
	prompt = (
		"Use a tool MCP de PII para processar o texto abaixo e gere uma resposta com:\n"
		"1) resumo das entidades de PII detectadas\n"
		"2) texto final anonimizado\n"
		"3) recomendacoes breves de privacidade.\n\n"
		f"Texto original:\n{texto}"
	)

	response = openai_client.responses.create(
		input=prompt,
		extra_body={
			"agent_reference": {
				"name": agent_name,
				"type": "agent_reference",
			}
		},
	)

	print_tool_output(response)

	approval_request_id = get_mcp_approval_request_id(response)
	if approval_request_id:
		response = openai_client.responses.create(
			previous_response_id=response.id,
			input=[
				{
					"type": "mcp_approval_response",
					"approval_request_id": approval_request_id,
					"approve": True,
				}
			],
			extra_body={
				"agent_reference": {
					"name": agent_name,
					"type": "agent_reference",
				}
			},
		)

		print("\nAprovacao MCP enviada automaticamente.")
		print_tool_output(response)

	response_text = getattr(response, "output_text", None)
	if not response_text:
		response_text = "(sem resposta textual)"

	print("\nResposta final do agente:")
	print(response_text)


if __name__ == "__main__":
	main()
