import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


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

	# Instrucoes para um agente focado em atendimento de RH.
	instructions = (
		"Voce e um assistente virtual do setor de RH de uma empresa. "
		"Responda perguntas sobre ferias, beneficios, folha de pagamento, "
		"jornada de trabalho e politicas internas com clareza e objetividade. "
		"Quando nao souber, informe que precisa validar com o RH humano."
	)

	# Cria (ou atualiza versão de) um agente de IA no Foundry com a instrucao informada.
	agent_name = "agente-rh-demo"
	agent = project_client.agents.create_version(
		agent_name=agent_name,
		definition=PromptAgentDefinition(
			model=model_deployment,
			instructions=instructions,
		),
	)

	print("\nAgente criado com sucesso no Azure Foundry:")
	print(f"agent_name={agent_name}")
	print(f"agent_id={getattr(agent, 'id', '(sem id)')}")
	print(f"agent_version={getattr(agent, 'version', '(sem version)')}")

	# Conecta ao agente criado e envia um prompt de teste.
	openai_client = project_client.get_openai_client()
	prompt = "Quais documentos preciso enviar para solicitar ferias?"

	response = openai_client.responses.create(
		input=prompt,
		extra_body={
			"agent_reference": {
				"name": agent_name,
				"type": "agent_reference",
			}
		},
	)

	response_text = getattr(response, "output_text", None)
	if not response_text:
		response_text = "(sem resposta textual)"

	print("\nPergunta enviada ao agente:")
	print(prompt)
	print("\nResposta do agente:")
	print(response_text)

    
    
if __name__ == "__main__":
	main()
