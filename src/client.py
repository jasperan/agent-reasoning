import json
import requests
import sys

class OllamaClient:
    def __init__(self, model="gemma3:270m", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, system=None, stream=True):
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        if system:
            data["system"] = system

        try:
            response = requests.post(url, json=data, stream=stream)
            response.raise_for_status()

            full_response = ""
            if stream:
                for line in response.iter_lines():
                    if line:
                        body = json.loads(line)
                        if "response" in body:
                            content = body["response"]
                            yield content
                            full_response += content
                        if body.get("done", False):
                            break
            else:
                body = response.json()
                yield body.get("response", "")

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Ollama: {e}", file=sys.stderr)
            yield ""
