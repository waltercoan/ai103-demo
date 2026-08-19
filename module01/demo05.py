import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
	# Carrega as variaveis de ambiente definidas no arquivo .env.
	load_dotenv()

	# Le o endpoint do Azure OpenAI e o deployment do modelo.
	azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment_name = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")

	# Falha cedo com mensagem clara caso o endpoint nao esteja configurado.
	if not azure_openai_endpoint:
		raise ValueError("A variavel AZURE_OPENAI_ENDPOINT nao foi definida no .env")

	# Exibe os valores de configuracao usados nesta execucao.
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
	# O token acima e enviado ao endpoint do Azure OpenAI como credencial da requisicao.

	# Cria o cliente OpenAI padrao apontando para o endpoint Azure OpenAI.
	client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token,
	)

	# Historico da conversa para manter contexto entre chamadas de chat completions.
	messages = []

	prompt_1 = "Meu nome e Walter. Responda com um cumprimento curto em portugues."
	print(f"\nUsuario (1): {prompt_1}")
	messages.append({"role": "user", "content": prompt_1})

	response_1 = client.chat.completions.create(
		model=deployment_name,
		messages=messages,  # Envia todo o historico acumulado ate aqui.
	)

	assistant_1 = (
		response_1.choices[0].message.content if response_1.choices else "(sem resposta)"
	)
	print(f"Assistente (1): {assistant_1}")
	# Guarda a resposta do assistente no historico para o proximo turno.
	messages.append({"role": "assistant", "content": assistant_1})

	prompt_2 = "Qual e o meu nome? Responda em uma frase curta."
	print(f"\nUsuario (2): {prompt_2}")
	messages.append({"role": "user", "content": prompt_2})

	response_2 = client.chat.completions.create(
		model=deployment_name,
		messages=messages,  # Inclui o turno anterior para manter o contexto.
	)

	assistant_2 = (
		response_2.choices[0].message.content if response_2.choices else "(sem resposta)"
	)
	print(f"Assistente (2): {assistant_2}")


if __name__ == "__main__":
	main()
