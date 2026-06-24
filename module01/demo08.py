import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI


def get_text(response) -> str:
	# A API de Responses expoe o texto final em output_text.
	text = getattr(response, "output_text", None)
	if text:
		return text

	# Fallback para cenarios em que output_text nao venha preenchido.
	return "(sem resposta textual)"


def print_tool_outputs(response, turn_label: str) -> None:
	# Procura itens de retorno da tool na lista de outputs.
	outputs = getattr(response, "output", None) or []
	tool_items = []

	for item in outputs:
		item_type = str(getattr(item, "type", "")).lower()
		if "tool" in item_type or "file_search" in item_type:
			tool_items.append(item)

	print(f"Retorno da tool ({turn_label}):")
	if not tool_items:
		print("(nenhum retorno de tool encontrado nesta resposta)")
		return

	for idx, item in enumerate(tool_items, start=1):
		print(f"- Tool item {idx}")
		if hasattr(item, "model_dump"):
			print(json.dumps(item.model_dump(), indent=2, ensure_ascii=False))
		elif hasattr(item, "to_dict"):
			print(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
		else:
			print(repr(item))


def main() -> None:
	# Carrega as variaveis de ambiente definidas no arquivo .env.
	load_dotenv()

	# Le o endpoint do Azure OpenAI e o deployment do modelo.
	azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
	deployment_name = "deploy-gpt-4.1"

	if not azure_openai_endpoint:
		raise ValueError("A variavel AZURE_OPENAI_ENDPOINT nao foi definida no .env")

	print("Variaveis de configuracao:")
	print(f"AZURE_OPENAI_ENDPOINT={azure_openai_endpoint}")
	print(f"AZURE_OPENAI_DEPLOYMENT={deployment_name}")

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

	# Cria um vector store no Foundry para indexar o arquivo CSV de vendas.
	vector_store = client.vector_stores.create(name="vendas-loja-store")
	print(f"\nVector store criado: {vector_store.id}")

	csv_path = Path(__file__).resolve().parent / "dados_vendas_loja.txt"
	if not csv_path.exists():
		raise FileNotFoundError(f"Arquivo nao encontrado: {csv_path}")

	# Faz upload do CSV e aguarda a indexacao para uso no file_search.
	with csv_path.open("rb") as f:
		batch = client.vector_stores.file_batches.upload_and_poll(
			vector_store_id=vector_store.id,
			files=[f],
		)

	print("Arquivo indexado no vector store.")
	print(f"Status do batch: {getattr(batch, 'status', '(sem status)')}")

	# Configura a tool file_search apontando para o vector store criado.
	tools = [{"type": "file_search", "vector_store_ids": [vector_store.id]}]

	# Imprime os dados da chamada da tool antes da execucao.
	print("\nChamada da tool (payload):")
	print(
		json.dumps(
			{
				"tool": "file_search",
				"vector_store_ids": [vector_store.id],
				"arquivo_indexado": str(csv_path.name),
			},
			indent=2,
			ensure_ascii=False,
		)
	)

	prompt_1 = (
		"Usando file_search no TXT indexado, calcule o faturamento total por canal "
		"(Loja Fisica, E-commerce e Marketplace) e responda em portugues."
	)
	print(f"\nUsuario (1): {prompt_1}")
	response_1 = client.responses.create(
		model=deployment_name,
		input=prompt_1,
		tools=tools,
	)
	print_tool_outputs(response_1, "1")
	print(f"Assistente (1): {get_text(response_1)}")

	prompt_2 = "Agora diga qual vendedor teve maior faturamento total no periodo."
	print(f"\nUsuario (2): {prompt_2}")
	response_2 = client.responses.create(
		model=deployment_name,
		input=prompt_2,
		previous_response_id=response_1.id,
		tools=tools,
	)
	print_tool_outputs(response_2, "2")
	print(f"Assistente (2): {get_text(response_2)}")


if __name__ == "__main__":
	main()
