import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
	OpenApiAnonymousAuthDetails,
	OpenApiFunctionDefinition,
	OpenApiFunctionDefinitionFunction,
	OpenApiTool,
	PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def print_tool_output(response) -> None:
	# Imprime os itens de retorno da tool para depuracao e estudo.
	outputs = getattr(response, "output", None) or []
	found = False

	print("\nRetorno da chamada da tool:")
	for item in outputs:
		item_type = str(getattr(item, "type", "")).lower()
		if "tool" in item_type or "openapi" in item_type:
			found = True
			if hasattr(item, "model_dump"):
				print(json.dumps(item.model_dump(), indent=2, ensure_ascii=False))
			elif hasattr(item, "to_dict"):
				print(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
			else:
				print(repr(item))

	if not found:
		print("(nenhum item de tool retornado)")


def main() -> None:
	# Carrega variaveis de ambiente do .env na raiz do projeto.
	load_dotenv()

	project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
	model_deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "deploy-gpt-4.1")

	if not project_endpoint:
		raise ValueError(
			"A variavel FOUNDRY_PROJECT_ENDPOINT nao foi definida no arquivo .env"
		)

	print("Configuracao:")
	print(f"FOUNDRY_PROJECT_ENDPOINT={project_endpoint}")
	print(f"FOUNDRY_MODEL_DEPLOYMENT_NAME={model_deployment}")

	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)

	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
		allow_preview=True,
	)

	# OpenAPI publica e gratuita (definicao inline): Agify API.
	# Endpoint real da API: https://api.agify.io
	openapi_spec = {
		"openapi": "3.0.3",
		"info": {
			"title": "Agify API",
			"version": "1.0.0",
			"description": "Prediz idade com base em um nome.",
		},
		"servers": [{"url": "https://api.agify.io"}],
		"paths": {
			"/": {
				"get": {
					"operationId": "getAgeByName",
					"summary": "Retorna predicao de idade por nome",
					"parameters": [
						{
							"name": "name",
							"in": "query",
							"required": True,
							"schema": {"type": "string"},
							"description": "Nome para predicao de idade",
						}
					],
					"responses": {
						"200": {
							"description": "Resposta com idade prevista",
							"content": {
								"application/json": {
									"schema": {
										"type": "object",
										"properties": {
											"name": {"type": "string"},
											"age": {"type": "integer", "nullable": True},
											"count": {"type": "integer"},
										},
									},
								}
							},
						}
					},
				}
			}
		},
	}

	# Tool OpenAPI para chamar endpoint publico sem autenticacao.
	openapi_tool = OpenApiTool(
		openapi=OpenApiFunctionDefinition(
			name="agify_api",
			description="Consulta dados da API publica Agify.",
			spec=openapi_spec,
			auth=OpenApiAnonymousAuthDetails(type="anonymous"),
			functions=[
				OpenApiFunctionDefinitionFunction(
					name="getAgeByName",
					description="Prediz idade a partir de um nome.",
					parameters={
						"type": "object",
						"properties": {
							"name": {"type": "string"},
						},
						"required": ["name"],
					},
				)
			],
		),
	)

	instructions = (
		"Voce e um assistente de RH. Quando necessario, use a tool OpenAPI para "
		"demonstrar integracao com API externa."
	)

	agent_name = "agente-rh-openapi-demo"
	agent = project_client.agents.create_version(
		agent_name=agent_name,
		definition=PromptAgentDefinition(
			model=model_deployment,
			instructions=instructions,
			tools=[openapi_tool],
		),
	)

	print("\nAgente criado com sucesso no Azure Foundry:")
	print(f"agent_name={agent_name}")
	print(f"agent_id={getattr(agent, 'id', '(sem id)')}")
	print(f"agent_version={getattr(agent, 'version', '(sem version)')}")

	openai_client = project_client.get_openai_client()
	prompt = (
		"Use a tool OpenAPI getAgeByName com name='Walter' e me retorne "
		"a idade prevista e o count retornado pela API."
	)

	# Imprime a chamada enviada ao agente.
	print("\nChamada enviada ao agente:")
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

	response_text = getattr(response, "output_text", None) or "(sem resposta textual)"
	print("\nResposta final do agente:")
	print(response_text)


if __name__ == "__main__":
	main()
