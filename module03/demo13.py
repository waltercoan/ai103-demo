import os

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def _create_client() -> TextAnalyticsClient:
	# Carrega as variaveis de ambiente do arquivo .env na raiz do projeto.
	load_dotenv()

	# Le o endpoint do recurso de Language usado para analise de texto.
	text_analytics_endpoint = os.getenv("FOUNDRY_TEXT_ANALYTICS_ENDPOINT")
	if not text_analytics_endpoint:
		raise ValueError(
			"A variavel FOUNDRY_TEXT_ANALYTICS_ENDPOINT nao foi definida no arquivo .env"
		)

	# Se existir chave no .env, usa autenticacao por chave.
	# Caso contrario, usa identidade Azure (CLI) seguindo o mesmo padrao do demo01.
	text_analytics_key = os.getenv("FOUNDRY_TEXT_ANALYTICS_KEY")
	if text_analytics_key:
		credential = AzureKeyCredential(text_analytics_key)
	else:
		credential = DefaultAzureCredential(
			exclude_environment_credential=True,
			exclude_managed_identity_credential=True,
			exclude_shared_token_cache_credential=True,
			exclude_visual_studio_code_credential=True,
			exclude_powershell_credential=True,
			exclude_developer_cli_credential=False,
			exclude_interactive_browser_credential=True,
		)

	return TextAnalyticsClient(
		endpoint=text_analytics_endpoint,
		credential=credential,
	)


def main() -> None:
	client = _create_client()

	print("Conectado ao servico de Text Analytics com sucesso.")

	texto = (
		"Meu nome e Carlos Silva. Meu CPF e 123.456.789-09, "
		"meu e-mail e carlos.silva@contoso.com e meu telefone e +55 11 91234-5678."
	)

	resultado = client.recognize_pii_entities(
		documents=[texto],
		language="pt",
	)

	for i, documento in enumerate(resultado, start=1):
		if documento.is_error:
			print(f"Documento {i} retornou erro: {documento.error.code} - {documento.error.message}")
			continue

		print(f"\nDocumento {i}:")
		print(f"Texto original: {texto}")
		print(f"Texto anonimizado: {documento.redacted_text}")

		if not documento.entities:
			print("Nenhuma entidade PII foi encontrada.")
			continue

		print("Entidades PII identificadas:")
		for entidade in documento.entities:
			print(
				f"- Texto: {entidade.text} | Categoria: {entidade.category} "
				f"| Subcategoria: {entidade.subcategory or 'N/A'} "
				f"| Confianca: {entidade.confidence_score:.2f}"
			)


if __name__ == "__main__":
	main()
