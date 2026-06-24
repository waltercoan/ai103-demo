import os

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

	# Usa a cadeia padrao de credenciais do Azure (CLI, VS Code, Managed Identity, etc.).
	credential = DefaultAzureCredential()
	# Cria o cliente do projeto para autenticar e comunicar com o endpoint Foundry.
	project_client = AIProjectClient(
		endpoint=project_endpoint,
		credential=credential,
	)

	# A conexao com o endpoint e estabelecida ao criar o client.
	print("Conectado ao Microsoft Foundry com sucesso.")
	print(f"Endpoint: {project_endpoint}")


if __name__ == "__main__":
	main()
