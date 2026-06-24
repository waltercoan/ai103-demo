import os
from itertools import islice

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main() -> None:
	# Carrega as variaveis de ambiente do arquivo .env na raiz do projeto.
	load_dotenv()

	# Le o endpoint do projeto Microsoft Foundry definido no .env.
	project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")


	# Usa DefaultAzureCredential forcando o provider do Azure CLI.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,   # Unico provedor ativo: Azure CLI.
		exclude_interactive_browser_credential=True,
	)

	# Cria o cliente do projeto para autenticar e comunicar com o endpoint Foundry.
	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
		allow_preview=True,
	)

	print("Conectado ao Microsoft Foundry com sucesso.")
	print(f"Endpoint: {project_endpoint}")

	# Connections representam as integrações de tools configuradas no projeto Foundry,
	# como Azure AI Search, Bing Grounding, Azure OpenAI, APIs customizadas, entre outras.
	print("\nPrimeiras 10 connections (tools) configuradas no projeto:")
	connections = project_client.connections.list()

	for i, conn in enumerate(islice(connections, 10), start=1):
		# Obtem os campos da connection: nome amigavel, tipo/categoria e URL de destino.
		nome = getattr(conn, "name", "(sem nome)")
		tipo = getattr(conn, "type", "(sem tipo)")          # Ex: AzureOpenAI, CognitiveSearch, ApiKey
		target = getattr(conn, "target", "(sem target)")    # URL do servico conectado.
		is_default = getattr(conn, "is_default", False)     # Indica se e a connection padrao do tipo.

		print(
			f"{i}. [{tipo}] {nome}"
			f"{' (default)' if is_default else ''}"
			f" -> {target}"
		)

	# Exibe os tipos de tools disponiveis no SDK para uso com agentes do Foundry.
	# Estas tools podem ser associadas a um agente no momento da sua criacao.
	print("\nTipos de connection disponiveis no SDK (ConnectionType):")
	for tipo in ConnectionType:
		print(f"  - {tipo}")


if __name__ == "__main__":
	main()
