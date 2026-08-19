import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def get_text(response) -> str:
	# A API de Responses expõe o texto final em output_text.
	text = getattr(response, "output_text", None)
	if text:
		return text

	# Fallback para cenarios em que output_text nao venha preenchido.
	return "(sem resposta textual)"


def main() -> None:
	# Carrega as variaveis de ambiente definidas no arquivo .env.
	load_dotenv()

	# Le o endpoint do Azure OpenAI e o deployment do modelo.
	azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment_name = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")

	if not azure_openai_endpoint:
		raise ValueError("A variavel AZURE_OPENAI_ENDPOINT nao foi definida no .env")

	print("Variaveis de configuracao:")
	print(f"AZURE_OPENAI_ENDPOINT={azure_openai_endpoint}")
	print(f"AZURE_OPENAI_DEPLOYMENT={deployment_name}")

	# Autentica via identidade (Azure CLI) para obter token Entra ID.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=False,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)

	token = credential.get_token("https://cognitiveservices.azure.com/.default").token

	# Cria o cliente OpenAI padrao apontando para o endpoint Azure OpenAI.
	client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token,
	)

	# Primeira interacao da conversa usando Responses API.
	prompt_1 = "Meu nome e Walter. Responda com um cumprimento curto em portugues."
	print(f"\nUsuario (1): {prompt_1}")
	response_1 = client.responses.create(
		model=deployment_name,
		input=prompt_1,
	)
	print(f"Assistente (1): {get_text(response_1)}")

	# Segunda interacao reutilizando o contexto da resposta anterior.
	prompt_2 = "Qual e o meu nome? Responda em uma frase curta."
	print(f"\nUsuario (2): {prompt_2}")
	response_2 = client.responses.create(
		model=deployment_name,
		input=prompt_2,
		previous_response_id=response_1.id,
	)
	print(f"Assistente (2): {get_text(response_2)}")


if __name__ == "__main__":
	main()
