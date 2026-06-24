import os
from itertools import islice

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main() -> None:
	# Carrega as variaveis de ambiente do arquivo .env na raiz do projeto.
	load_dotenv()

	# Le o endpoint do projeto Microsoft Foundry definido no .env.
	project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
	if not project_endpoint:
		# Falha cedo com mensagem clara caso a variavel nao exista.
		raise ValueError(
			"A variavel FOUNDRY_PROJECT_ENDPOINT nao foi definida no arquivo .env"
		)

	# Usa DefaultAzureCredential forçando o provider do Azure CLI.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)
	
	
	# Cria o cliente do projeto para autenticar e comunicar com o endpoint Foundry.
	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
		allow_preview=True,
	)

	# A conexao com o endpoint e estabelecida ao criar o client.
	print("Conectado ao Microsoft Foundry com sucesso.")
	print(f"Endpoint: {project_endpoint}")

	# Lista os 10 primeiros itens da colecao paginada de modelos publicados.
	print("\nPrimeiros 10 modelos publicados:")
	modelos = project_client.deployments.list()
	
	for i, modelo in enumerate(islice(modelos, 10), start=1):
		nome = getattr(modelo, "name", "(sem nome)")
		modelName = getattr(modelo, "model_name", "(sem model_name)")
		sku = getattr(modelo, "sku", "(sem sku)")
		print(f"{i}. deployment_name {nome} | model_name: {modelName} | sku: {sku}")
	

if __name__ == "__main__":
	main()
