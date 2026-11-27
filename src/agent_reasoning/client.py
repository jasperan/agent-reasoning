import json
import sys

import requests
from requests.adapters import HTTPAdapter

# One pooled session for every client: agents create a fresh OllamaClient per
# request and multi-call strategies hit Ollama many times per query, so reusing
# keep-alive connections avoids a TCP handshake on every LLM call. The pool is
# sized for arena mode, which runs all agents concurrently.
_SESSION = requests.Session()
_SESSION.mount("http://", HTTPAdapter(pool_connections=4, pool_maxsize=32))
_SESSION.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=32))


class OllamaClient:
    def __init__(self, model="gemma3:latest", base_url=None, think=None):
        if base_url is None:
            from agent_reasoning.config import get_ollama_host

            base_url = get_ollama_host()
        self.model = model
        self.base_url = base_url
        self.think = think  # None = model default, False = disable thinking

    def generate(
        self,
        prompt,
        system=None,
        stream=True,
        temperature=0.7,
        top_k=40,
        top_p=0.9,
        num_predict=2048,
        stop=None,
        timeout=120,
    ):
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            # Ollama only honours sampling parameters (and stop sequences)
            # inside "options"; top-level copies are silently ignored.
            "options": {
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "num_predict": num_predict,
            },
        }
        if stop:
            data["options"]["stop"] = stop
        if system:
            data["system"] = system
        if self.think is not None:
            data["think"] = self.think

        try:
            response = _SESSION.post(url, json=data, stream=stream, timeout=timeout)
            try:
                response.raise_for_status()

                if stream:
                    lines = response.iter_lines()
                    for line in lines:
                        if line:
                            body = json.loads(line)
                            if "response" in body:
                                yield body["response"]
                            if body.get("done", False):
                                # Read to the end of the chunked body so the
                                # connection goes back to the pool for reuse.
                                for _ in lines:
                                    pass
                                break
                else:
                    body = response.json()
                    yield body.get("response", "")
            finally:
                # Release the connection even when the caller stops iterating early.
                response.close()

        except requests.exceptions.RequestException as e:
            error_msg = f"[OllamaClient] Error communicating with Ollama (model={self.model}): {e}"
            print(error_msg, file=sys.stderr)
            yield (
                f"Error: Could not reach Ollama model '{self.model}'. "
                "Please check the model is available (ollama list)."
            )
