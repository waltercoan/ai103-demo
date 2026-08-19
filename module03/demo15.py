import json
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def _get_required_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise ValueError(f"A variavel {name} nao foi definida no arquivo .env")
	return value


def _build_openai_client() -> tuple[OpenAI, str]:
	azure_openai_endpoint = _get_required_env("AZURE_OPENAI_ENDPOINT")
	deployment_name = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")

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

	# Mantem o mesmo padrao de cliente do demo02, usando token Entra ID como api_key.
	openai_client = OpenAI(
		base_url=azure_openai_endpoint,
		api_key=token,
	)

	return openai_client, deployment_name


def _extract_json(raw_text: str) -> dict[str, Any]:
	try:
		payload = json.loads(raw_text)
		if isinstance(payload, dict):
			return payload
	except json.JSONDecodeError:
		pass

	start = raw_text.find("{")
	end = raw_text.rfind("}")
	if start != -1 and end != -1 and end > start:
		candidate = raw_text[start : end + 1]
		payload = json.loads(candidate)
		if isinstance(payload, dict):
			return payload

	raise ValueError(
		"Nao foi possivel interpretar a saida do modelo como JSON. Retorno bruto:\n"
		f"{raw_text}"
	)


def _redact_pii_with_gpt(texto: str) -> dict[str, Any]:
	client, deployment_name = _build_openai_client()

	system_prompt = (
		"Voce e um assistente para anonimizar textos em portugues. "
		"Identifique e substitua dados pessoais (PII), incluindo nome completo, CPF, RG, "
		"e-mail, telefone e endereco, por marcadores como [NOME], [CPF], [EMAIL], [TELEFONE], [ENDERECO]. "
		"Nao invente dados nem altere informacoes nao sensiveis. "
		"Responda apenas em JSON valido, sem markdown, no formato: "
		"{\"redacted_text\": \"...\", \"detected_entities\": [{\"type\": \"...\", \"value\": \"...\"}]}"
	)

	user_prompt = (
		"Remova/mascare o PII do texto abaixo e retorne no formato JSON solicitado.\n\n"
		f"TEXTO:\n{texto}"
	)

	response = client.chat.completions.create(
		model=deployment_name,
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		temperature=0,
	)

	content = response.choices[0].message.content if response.choices else ""
	if not content:
		raise ValueError("O modelo nao retornou conteudo na resposta.")

	return _extract_json(content)


def main() -> None:
	# Carrega variaveis de ambiente do arquivo .env.
	load_dotenv()

	texto = (
		"Meu nome e Ana Souza, meu CPF e 987.654.321-00, "
		"meu e-mail e ana.souza@contoso.com e meu telefone e +55 11 99876-5432."
	)

	print("Executando remocao de PII com modelo GPT no Azure OpenAI...")
	print("\nTexto original:")
	print(texto)

	resultado = _redact_pii_with_gpt(texto)

	print("\nResultado (JSON):")
	print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
	main()
