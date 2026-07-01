import asyncio
import json
import os
import re
from typing import Any

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _get_required_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise ValueError(f"A variavel {name} nao foi definida no arquivo .env")
	return value


def _build_remote_headers() -> dict[str, str]:
	headers_json = os.getenv("FOUNDRY_REMOTE_MCP_HEADERS_JSON", "{}")
	headers: dict[str, str] = json.loads(headers_json)

	bearer_token = os.getenv("FOUNDRY_REMOTE_MCP_BEARER_TOKEN")
	if bearer_token:
		headers["Authorization"] = f"Bearer {bearer_token}"
		return headers

	# Usa identidade Azure (CLI) para obter token quando nao houver bearer no .env.
	credential = DefaultAzureCredential(
		exclude_environment_credential=True,
		exclude_managed_identity_credential=True,
		exclude_shared_token_cache_credential=True,
		exclude_visual_studio_code_credential=True,
		exclude_powershell_credential=True,
		exclude_developer_cli_credential=False,
		exclude_interactive_browser_credential=True,
	)
	token = credential.get_token("https://ai.azure.com/.default")
	headers["Authorization"] = f"Bearer {token.token}"

	return headers


def _normalize_tool_name(name: str) -> str:
	return name.strip().lower().replace("_", "-")


def _select_pii_tool_name(available_tools: list[str]) -> str:
	preferred_tools = [
		"redact_pii_from_text",
		"redact_pii_from_document",
	]
	for preferred_tool in preferred_tools:
		if preferred_tool in available_tools:
			return preferred_tool

	for tool in available_tools:
		normalized = _normalize_tool_name(tool)
		if re.search(r"(pii|personally-identifiable|redact)", normalized):
			return tool

	raise ValueError(
		"Nao foi possivel detectar automaticamente uma ferramenta de PII. "
		"Verifique as ferramentas MCP disponiveis no endpoint remoto."
	)


def _extract_text_from_result(tool_result: Any) -> str:
	content = getattr(tool_result, "content", None)
	if not content:
		return str(tool_result)

	parts: list[str] = []
	for item in content:
		text_value = getattr(item, "text", None)
		if text_value:
			parts.append(text_value)

	return "\n".join(parts) if parts else str(tool_result)


def _parse_payload(raw_text: str) -> Any:
	try:
		return json.loads(raw_text)
	except json.JSONDecodeError:
		if raw_text.strip().lower().startswith("an error occurred invoking"):
			raise ValueError(f"Falha na invocacao da tool MCP: {raw_text}")

		start = raw_text.find("{")
		end = raw_text.rfind("}")
		if start != -1 and end != -1 and end > start:
			return json.loads(raw_text[start : end + 1])

		start = raw_text.find("[")
		end = raw_text.rfind("]")
		if start != -1 and end != -1 and end > start:
			return json.loads(raw_text[start : end + 1])

	raise ValueError(
		"Nao foi possivel interpretar o retorno em JSON. Retorno bruto:\n"
		f"{raw_text}"
	)


async def _run_language_pii_tool(texto: str) -> Any:
	mcp_url = _get_required_env("FOUNDRY_REMOTE_MCP_URL")
	headers = _build_remote_headers()

	# Payload padrao para cenarios comuns de PII. Caso sua ferramenta use
	# um contrato diferente, sobrescreva com FOUNDRY_LANGUAGE_PII_ARGUMENTS_JSON.
	default_arguments = {
		"message": texto,
		"language": "pt",
	}

	arguments_from_env = os.getenv("FOUNDRY_LANGUAGE_PII_ARGUMENTS_JSON")
	if arguments_from_env:
		tool_arguments = json.loads(arguments_from_env)
	else:
		tool_arguments = default_arguments

	# Conecta somente em MCP remoto no Microsoft Foundry (sem servidor local).
	async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
		async with ClientSession(read_stream, write_stream) as session:
			await session.initialize()

			tools_response = await session.list_tools()
			available_tools = [tool.name for tool in tools_response.tools]
			selected_tool = _select_pii_tool_name(available_tools)

			print("Ferramentas MCP disponiveis:")
			for name in available_tools:
				print(f"- {name}")
			print(f"\nFerramenta de PII selecionada: {selected_tool}")

			result = await session.call_tool(selected_tool, arguments=tool_arguments)
			raw_output = _extract_text_from_result(result)
			return _parse_payload(raw_output)


def main() -> None:
	# Carrega as variaveis de ambiente do arquivo .env na raiz do projeto.
	load_dotenv()

	texto = (
		"Meu nome e Carlos Silva. Meu CPF e 123.456.789-09, "
		"meu e-mail e carlos.silva@contoso.com e meu telefone e +55 11 91234-5678."
	)

	print("Executando extracao de PII com Azure Language in Foundry Tools via MCP...")
	resultado = asyncio.run(_run_language_pii_tool(texto))

	print("\nTexto original:")
	print(texto)
	print("\nResultado (JSON):")
	print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
	main()
