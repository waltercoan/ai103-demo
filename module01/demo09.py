import json
import os
import platform
import ctypes

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


def get_total_memory_gb() -> float:
	# Obtem memoria total instalada em GB no Windows via API nativa.
	class MEMORYSTATUSEX(ctypes.Structure):
		_fields_ = [
			("dwLength", ctypes.c_ulong),
			("dwMemoryLoad", ctypes.c_ulong),
			("ullTotalPhys", ctypes.c_ulonglong),
			("ullAvailPhys", ctypes.c_ulonglong),
			("ullTotalPageFile", ctypes.c_ulonglong),
			("ullAvailPageFile", ctypes.c_ulonglong),
			("ullTotalVirtual", ctypes.c_ulonglong),
			("ullAvailVirtual", ctypes.c_ulonglong),
			("sullAvailExtendedVirtual", ctypes.c_ulonglong),
		]

	mem = MEMORYSTATUSEX()
	mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

	if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
		return 0.0

	return round(mem.ullTotalPhys / (1024**3), 2)


def get_hardware_info() -> dict:
	# Funcao local exposta como Function Tool para o modelo.
	return {
		"hostname": platform.node(),
		"os": platform.platform(),
		"architecture": platform.machine(),
		"processor": platform.processor(),
		"cpu_logical_cores": os.cpu_count(),
		"total_memory_gb": get_total_memory_gb(),
	}


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

	# Define a Function Tool que o modelo pode chamar.
	tools = [
		{
			"type": "function",
			"name": "get_hardware_info",
			"description": "Retorna as configuracoes de hardware do computador local.",
			"parameters": {"type": "object", "properties": {}, "required": []},
		},
	]

	prompt = (
		"Use a function get_hardware_info para obter os dados do computador e "
		"resuma em portugues as configuracoes principais."
	)

	print("\nChamada da tool (definicao enviada ao modelo):")
	print(json.dumps(tools, indent=2, ensure_ascii=False))
	print(f"\nUsuario: {prompt}")

	# Primeiro request: o modelo decide se chama a function tool.
	response = client.responses.create(
		model=deployment_name,
		input=prompt,
		tools=tools,
	)

	# Procura chamadas de funcao retornadas pelo modelo.
	function_calls = []
	for item in (getattr(response, "output", None) or []):
		if getattr(item, "type", "") == "function_call":
			function_calls.append(item)

	if not function_calls:
		print("\nNenhuma chamada de function tool foi retornada pelo modelo.")
		print(f"Assistente: {get_text(response)}")
		return

	# Executa a function local e devolve o resultado ao modelo.
	for call in function_calls:
		call_name = getattr(call, "name", "")
		call_id = getattr(call, "call_id", "")
		arguments = getattr(call, "arguments", "{}")

		print("\nChamada da tool (retornada pelo modelo):")
		print(
			json.dumps(
				{
					"name": call_name,
					"call_id": call_id,
					"arguments": arguments,
				},
				indent=2,
				ensure_ascii=False,
			)
		)

		if call_name != "get_hardware_info":
			tool_result = {"error": f"Funcao nao suportada: {call_name}"}
		else:
			tool_result = get_hardware_info()

		print("Retorno da tool (executada localmente):")
		print(json.dumps(tool_result, indent=2, ensure_ascii=False))

		response = client.responses.create(
			model=deployment_name,
			previous_response_id=response.id,
			input=[
				{
					"type": "function_call_output",
					"call_id": call_id,
					"output": json.dumps(tool_result, ensure_ascii=False),
				}
			],
			tools=tools,
		)

	print("\nResposta final do assistente:")
	print(get_text(response))


if __name__ == "__main__":
	main()
