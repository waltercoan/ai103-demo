import json
import os
from pathlib import Path
from typing import Any

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import (
	ContentAnalyzer,
	ContentFieldDefinition,
	ContentFieldSchema,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def _create_client() -> ContentUnderstandingClient:
	# Carrega as variaveis de ambiente do arquivo .env na raiz do projeto.
	load_dotenv()

	# Le endpoint do recurso de Content Understanding.
	content_endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
	if not content_endpoint:
		raise ValueError(
			"A variavel CONTENTUNDERSTANDING_ENDPOINT nao foi definida no arquivo .env"
		)

	# Se existir chave no .env, usa autenticacao por chave.
	# Caso contrario, usa identidade Azure (CLI) no mesmo padrao dos demos anteriores.
	content_key = os.getenv("CONTENTUNDERSTANDING_KEY")
	if content_key:
		credential: Any = AzureKeyCredential(content_key)
	else:
		credential = DefaultAzureCredential(
			exclude_environment_credential=True,
			exclude_managed_identity_credential=False,
			exclude_shared_token_cache_credential=True,
			exclude_visual_studio_code_credential=True,
			exclude_powershell_credential=True,
			exclude_developer_cli_credential=False,
			exclude_interactive_browser_credential=True,
		)

	return ContentUnderstandingClient(
		endpoint=content_endpoint,
		credential=credential,
	)


def _resolve_image_path() -> Path:
	image_path_env = os.getenv("CONTENTUNDERSTANDING_IMAGE_PATH")
	if image_path_env:
		image_path = Path(image_path_env)
		if not image_path.is_absolute():
			image_path = (Path.cwd() / image_path).resolve()
	else:
		# Usa o arquivo solicitado no enunciado como padrao.
		image_path = Path(__file__).resolve().with_name("cardapio.jpg")

	if not image_path.exists():
		raise FileNotFoundError(f"Imagem nao encontrada: {image_path}")

	if image_path.suffix.lower() not in {".jpg", ".jpeg"}:
		raise ValueError("A imagem deve estar no formato JPG/JPEG.")

	return image_path


def _extract_summary(result: Any) -> str:
	# O schema pode variar por analyzer/versao; tentamos caminhos comuns.
	if isinstance(result, dict):
		possible_paths = [
			("summary",),
			("result", "summary"),
			("result", "contents", 0, "summary"),
			("contents", 0, "summary"),
			("contents", 0, "markdown"),
		]
		for path in possible_paths:
			cursor: Any = result
			ok = True
			for key in path:
				if isinstance(key, int):
					if isinstance(cursor, list) and len(cursor) > key:
						cursor = cursor[key]
					else:
						ok = False
						break
				else:
					if isinstance(cursor, dict) and key in cursor:
						cursor = cursor[key]
					else:
						ok = False
						break
			if ok and isinstance(cursor, str) and cursor.strip():
				return cursor

	return "(resumo nao encontrado no payload; veja JSON completo abaixo)"


def _get_contents(result_dict: dict[str, Any]) -> list[dict[str, Any]]:
	contents = result_dict.get("contents")
	if isinstance(contents, list):
		return [item for item in contents if isinstance(item, dict)]

	result_obj = result_dict.get("result")
	if isinstance(result_obj, dict):
		nested_contents = result_obj.get("contents")
		if isinstance(nested_contents, list):
			return [item for item in nested_contents if isinstance(item, dict)]

	return []


def _get_fields_from_content(content: dict[str, Any]) -> dict[str, Any]:
	fields = content.get("fields")
	if isinstance(fields, dict):
		return fields

	# Alguns schemas retornam campos dentro de "result" no item de conteudo.
	content_result = content.get("result")
	if isinstance(content_result, dict):
		nested_fields = content_result.get("fields")
		if isinstance(nested_fields, dict):
			return nested_fields

	return {}


def _extract_field_value(field: Any) -> Any:
	if not isinstance(field, dict):
		return field

	# Prioriza chaves tipadas mais comuns da API.
	for key in (
		"valueString",
		"valueNumber",
		"valueInteger",
		"valueBoolean",
		"valueDate",
		"valueTime",
		"valueArray",
		"valueObject",
		"valueJson",
	):
		if key in field:
			return field[key]

	# Fallback para nomenclatura snake_case.
	for key in (
		"value_string",
		"value_number",
		"value_integer",
		"value_boolean",
		"value_date",
		"value_time",
		"value_array",
		"value_object",
		"value_json",
	):
		if key in field:
			return field[key]

	# Se nao houver valor tipado, retorna o proprio objeto para depuracao.
	return field


def _print_analysis_results(result_dict: dict[str, Any]) -> None:
	contents = _get_contents(result_dict)

	print("\nResultados da analise de conteudo:")
	if not contents:
		print("- Nenhum item em contents foi retornado.")
		return

	for idx, content in enumerate(contents, start=1):
		content_type = content.get("contentType") or content.get("content_type") or "(desconhecido)"
		print(f"\nConteudo {idx}:")
		print(f"- Tipo: {content_type}")

		summary = content.get("summary")
		if isinstance(summary, str) and summary.strip():
			print(f"- Summary: {summary}")

		fields = _get_fields_from_content(content)
		if not fields:
			print("- Campos extraidos: (nenhum)")
			continue

		print("- Campos extraidos:")
		for field_name, field_value in fields.items():
			parsed_value = _extract_field_value(field_value)
			if isinstance(parsed_value, (dict, list)):
				formatted = json.dumps(parsed_value, ensure_ascii=False)
			else:
				formatted = str(parsed_value)
			print(f"  - {field_name}: {formatted}")


def _to_result_dict(result: Any) -> dict[str, Any]:
	if hasattr(result, "as_dict"):
		return result.as_dict()
	if hasattr(result, "to_dict"):
		return result.to_dict()
	if hasattr(result, "model_dump"):
		return result.model_dump()
	return {"raw_result": str(result)}


def _has_content(result_dict: dict[str, Any]) -> bool:
	contents = result_dict.get("contents")
	if isinstance(contents, list) and len(contents) > 0:
		return True

	result_obj = result_dict.get("result")
	if isinstance(result_obj, dict):
		nested_contents = result_obj.get("contents")
		if isinstance(nested_contents, list) and len(nested_contents) > 0:
			return True

	return False


def _analyze_with_fallback(
	client: ContentUnderstandingClient, image_bytes: bytes, analyzer_id: str
) -> tuple[str, dict[str, Any]]:
	poller = client.begin_analyze_binary(
		analyzer_id=analyzer_id,
		binary_input=image_bytes,
		content_type="image/jpeg",
	)
	result_dict = _to_result_dict(poller.result())

	if _has_content(result_dict):
		return analyzer_id, result_dict

	if analyzer_id != "prebuilt-document":
		print(
			"Nenhum conteudo retornado com o analyzer atual. "
			"Tentando fallback para prebuilt-document..."
		)
		poller = client.begin_analyze_binary(
			analyzer_id="prebuilt-document",
			binary_input=image_bytes,
			content_type="image/jpeg",
		)
		fallback_result_dict = _to_result_dict(poller.result())
		return "prebuilt-document", fallback_result_dict

	return analyzer_id, result_dict


def _build_field_schema() -> ContentFieldSchema:
	return ContentFieldSchema(
		description="Schema para analise de imagem com descricao e tags",
		fields={
			"descricao": ContentFieldDefinition(
				type="string",
				description="Descricao textual objetiva do conteudo principal da imagem.",
				method="generate",
			),
			"tags": ContentFieldDefinition(
				type="array",
				description="Lista curta de tags semanticas da imagem.",
				method="generate",
				item_definition=ContentFieldDefinition(type="string"),
			),
		},
	)


def _ensure_custom_analyzer(client: ContentUnderstandingClient, analyzer_id: str) -> None:
	base_analyzer_id = os.getenv(
		"CONTENTUNDERSTANDING_BASE_ANALYZER_ID", "prebuilt-image"
	)

	resource = ContentAnalyzer(
		description="Analyzer customizado para retornar descricao e tags de imagem.",
		tags={
			"scenario": "image-understanding",
			"module": "module04",
			"purpose": "descricao-e-tags",
		},
		base_analyzer_id=base_analyzer_id,
		field_schema=_build_field_schema(),
	)

	print("\nGarantindo analyzer custom com schema (descricao/tags)...")
	print(f"Base analyzer: {base_analyzer_id}")
	poller = client.begin_create_analyzer(
		analyzer_id=analyzer_id,
		resource=resource,
		allow_replace=True,
	)
	poller.result()


def _normalize_custom_analyzer_id(analyzer_id: str) -> str:
	# IDs prebuilt devem ser preservados exatamente como fornecidos pelo servico.
	if analyzer_id.startswith("prebuilt-"):
		return analyzer_id

	# Para analyzer custom, evita caracteres invalidos no ID.
	normalized = analyzer_id.replace("-", "_")
	if not normalized:
		normalized = "demo19_image_schema"
	return normalized


def main() -> None:
	client = _create_client()

	raw_analyzer_id = os.getenv("CONTENTUNDERSTANDING_ANALYZER_ID", "prebuilt-document")
	analyzer_id = _normalize_custom_analyzer_id(raw_analyzer_id)
	image_path = _resolve_image_path()

	print("Configuracao:")
	print(f"CONTENTUNDERSTANDING_ENDPOINT={os.getenv('CONTENTUNDERSTANDING_ENDPOINT')}")
	print(f"CONTENTUNDERSTANDING_ANALYZER_ID={analyzer_id}")
	print(f"CONTENTUNDERSTANDING_IMAGE_PATH={image_path}")
	if raw_analyzer_id != analyzer_id:
		print(
			"Observacao: analyzer_id custom foi normalizado para evitar caracteres invalidos. "
			f"Original='{raw_analyzer_id}', usado='{analyzer_id}'."
		)

	with image_path.open("rb") as image_file:
		image_bytes = image_file.read()

	if not analyzer_id.startswith("prebuilt-"):
		try:
			_ensure_custom_analyzer(client, analyzer_id)
		except Exception as exc:
			print(
				"Aviso: nao foi possivel criar/atualizar analyzer custom. "
				"Sera usado prebuilt-document para evitar analise vazia."
			)
			print(f"Motivo: {exc}")
			analyzer_id = "prebuilt-document"

	print("\nEnviando imagem para Content Understanding...")
	used_analyzer_id, result_dict = _analyze_with_fallback(client, image_bytes, analyzer_id)
	print(f"Analyzer utilizado: {used_analyzer_id}")

	print("\nResumo da analise:")
	print(_extract_summary(result_dict))
	_print_analysis_results(result_dict)

	if not _has_content(result_dict):
		print(
			"\nAviso: a API retornou sem conteudo estruturado. "
			"Verifique se os model deployments padrao do Content Understanding estao configurados no recurso."
		)

	print("\nResultado completo (JSON):")
	print(json.dumps(result_dict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
	main()
