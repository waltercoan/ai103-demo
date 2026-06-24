import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
	# Carrega as variaveis de ambiente definidas no arquivo .env.
	load_dotenv()

	# Le o endpoint do Azure OpenAI e o nome do deployment a partir do ambiente.
	azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment_name = "deploy-gpt-4.1"  # Nome do deployment criado no Azure OpenAI Studio.

	# Exibe as variaveis ativas para facilitar o diagnostico em caso de erro.
	print("Variaveis de configuracao:")
	print(f"AZURE_OPENAI_ENDPOINT={azure_openai_endpoint}")
	print(f"AZURE_OPENAI_DEPLOYMENT={deployment_name}")

	# Autentica usando a identidade do Azure CLI (DefaultAzureCredential).
	# Os provedores nao utilizados sao desativados para forcar o uso do Azure CLI Developer.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,   # Unico provedor ativo: Azure CLI.
		exclude_interactive_browser_credential=True,
	)

	# Obtem um bearer token valido para o escopo do Azure Cognitive Services.
	token = credential.get_token("https://cognitiveservices.azure.com/.default").token

	# Instancia o cliente OpenAI padrao apontando para o endpoint do Azure OpenAI.
	# O token Entra ID e passado como api_key para autenticar as requisicoes.
	openai_client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token
	)

	prompt = "Escreva uma frase curta sobre inteligencia artificial em portugues."
	print(f"Prompt: {prompt}")

	# Envia o prompt ao modelo usando a API de chat completions.
	response = openai_client.chat.completions.create(
		model=deployment_name,  # Nome do deployment no Azure OpenAI.
		messages=[
			{
				"role": "user",
				"content": prompt,
			}
		],
	)

	# Extrai o texto da primeira escolha retornada pelo modelo.
	content = response.choices[0].message.content if response.choices else "(sem resposta)"

	print("Resposta do modelo:")
	print(content)


if __name__ == "__main__":
	main()
