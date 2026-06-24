import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
	# Carrega o .env da raiz do repositorio.
	load_dotenv()

	azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment_name = "deploy-gpt-4.1"

	print("Variaveis de configuracao:")
	print(f"AZURE_OPENAI_ENDPOINT={azure_openai_endpoint}")
	print(f"AZURE_OPENAI_DEPLOYMENT={deployment_name}")
	

	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)

	token = credential.get_token("https://cognitiveservices.azure.com/.default").token

	openai_client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token
	)
	prompt = "Escreva uma frase curta sobre inteligencia artificial em portugues."
	print(f"Prompt: {prompt}")
	response = openai_client.chat.completions.create(
		model=deployment_name,
		messages=[
			{
				"role": "user",
				"content": prompt,
			}
		],
	)

	content = response.choices[0].message.content if response.choices else "(sem resposta)"

	print("Resposta do modelo:")
	print(content)


if __name__ == "__main__":
	main()
