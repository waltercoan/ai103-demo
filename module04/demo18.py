import base64
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def _get_required_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise ValueError(f"A variavel {name} nao foi definida no arquivo .env")
	return value


def _get_text(response) -> str:
	text = getattr(response, "output_text", None)
	if text:
		return text
	return "(sem resposta textual)"


def _build_data_url_from_jpg(image_path: Path) -> str:
	if not image_path.exists():
		raise FileNotFoundError(f"Imagem nao encontrada: {image_path}")

	if image_path.suffix.lower() not in {".jpg", ".jpeg"}:
		raise ValueError("A imagem deve estar no formato JPG/JPEG.")

	image_bytes = image_path.read_bytes()
	base64_image = base64.b64encode(image_bytes).decode("utf-8")
	return f"data:image/jpeg;base64,{base64_image}"


def main() -> None:
	# Carrega as variaveis de ambiente definidas no arquivo .env.
	load_dotenv()

	# Le endpoint/deployment do Azure OpenAI e caminho da imagem.
	azure_openai_endpoint = _get_required_env("AZURE_OPENAI_ENDPOINT")
	deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "deploy-gpt-4.1")
	image_path_env = os.getenv("IMAGE_JPG_PATH")
	if image_path_env:
		image_path = Path(image_path_env)
		if not image_path.is_absolute():
			image_path = (Path.cwd() / image_path).resolve()
	else:
		# Default fixo no diretorio do script para funcionar de qualquer cwd.
		image_path = Path(__file__).resolve().with_name("exemplo.jpg")

	print("Variaveis de configuracao:")
	print(f"AZURE_OPENAI_ENDPOINT={azure_openai_endpoint}")
	print(f"AZURE_OPENAI_DEPLOYMENT={deployment_name}")
	print(f"IMAGE_JPG_PATH={image_path}")

	# Autentica via identidade (Azure CLI) para obter token Entra ID.
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

	# Cria o cliente OpenAI padrao apontando para o endpoint Azure OpenAI.
	client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token,
	)

	data_url = _build_data_url_from_jpg(image_path)

	prompt = (
		"Descreva esta imagem em portugues com foco em objetos principais, "
		"cenario e possivel contexto. Responda em no maximo 5 frases."
	)

	response = client.responses.create(
		model=deployment_name,
		input=[
			{
				"role": "user",
				"content": [
					{"type": "input_text", "text": prompt},
					{"type": "input_image", "image_url": data_url},
				],
			}
		],
	)

	print("\nDescricao da imagem:")
	print(_get_text(response))


if __name__ == "__main__":
	main()
