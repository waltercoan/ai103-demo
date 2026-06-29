import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def print_tool_output(response) -> None:
	# Imprime os itens de retorno da tool MCP para depuracao.
	outputs = getattr(response, "output", None) or []
	found = False

	print("\nRetorno da chamada da tool:")
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


def get_mcp_approval_request_id(response) -> str | None:
	# Retorna o id da solicitacao de aprovacao MCP, se existir.
	outputs = getattr(response, "output", None) or []
	for item in outputs:
		if str(getattr(item, "type", "")).lower() == "mcp_approval_request":
			return getattr(item, "id", None)
	return None


def main() -> None:
	# Carrega variaveis de ambiente do .env na raiz do projeto.
	load_dotenv()

	# Endpoint do projeto Foundry e deployment do modelo para o agente.
	project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
	model_deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "deploy-gpt-4.1")

	if not project_endpoint:
		raise ValueError(
			"A variavel FOUNDRY_PROJECT_ENDPOINT nao foi definida no arquivo .env"
		)

	print("Configuracao:")
	print(f"FOUNDRY_PROJECT_ENDPOINT={project_endpoint}")
	print(f"FOUNDRY_MODEL_DEPLOYMENT_NAME={model_deployment}")

	# Autenticacao via identidade local do Azure CLI.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)

	# Cria o cliente do projeto Foundry.
	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
		allow_preview=True,
	)

	# Instrucoes para um agente de Treinamento com acesso ao MCP do Microsoft Learn.
	instructions = (
		"Voce e um assistente virtual do setor de Treinamento de uma empresa. "
		"Use o MCP Server do Microsoft Learn quando precisar buscar referencia "
		"tecnica sobre produtos Microsoft."
	)

	# Tool MCP apontando para o servidor MCP publico do Microsoft Learn.
	mcp_tool = MCPTool(
		server_label="mslearn",
		server_url="https://learn.microsoft.com/api/mcp",
	)

	# Cria (ou atualiza versão de) um agente de IA no Foundry com a tool MCP.
	agent_name = "agente-train-mcp-mslearn-demo"
	agent = project_client.agents.create_version(
		agent_name=agent_name,
		definition=PromptAgentDefinition(
			model=model_deployment,
			instructions=instructions,
			tools=[mcp_tool],
		),
	)

	print("\nAgente criado com sucesso no Azure Foundry:")
	print(f"agent_name={agent_name}")
	print(f"agent_id={getattr(agent, 'id', '(sem id)')}")
	print(f"agent_version={getattr(agent, 'version', '(sem version)')}")

	# Conecta ao agente criado e envia um prompt de teste.
	openai_client = project_client.get_openai_client()
	prompt = (
		"Use a tool MCP do Microsoft Learn para encontrar uma referencia oficial "
		"sobre Azure AI Foundry Agent Service e resuma em portugues."
	)

	print("\nPergunta enviada ao agente:")
	print(prompt)

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

	# Se o servidor MCP exigir aprovacao, aprova e continua a execucao.
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

	print("\nResposta do agente:")
	print(response_text)


if __name__ == "__main__":
	main()
