import json
import requests
from flask import current_app
from app.utils.crypto import decrypt_api_key


class OpenRouterService:
    """Wrapper around the OpenRouter API for chat and vision completions."""

    def __init__(self, user=None):
        self.base_url = current_app.config["OPENROUTER_BASE_URL"]
        self.user = user
        self._resolve_api_key()

    def _resolve_api_key(self):
        """Pick user's own key if available, else admin's."""
        if self.user and self.user.has_own_api_key():
            self.api_key = decrypt_api_key(self.user.openrouter_api_key_enc)
            self.has_own_key = True
        else:
            self.api_key = current_app.config["OPENROUTER_API_KEY"]
            self.has_own_key = False

    def get_available_models(self, model_type="chat"):
        """Return models the current user is allowed to use."""
        if self.has_own_key:
            if model_type == "vision":
                return current_app.config["VISION_MODELS"]
            return current_app.config["CHAT_MODELS"]
        return current_app.config["LIMITED_MODELS"]

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://error-notebook.local",
            "X-Title": "Digital Error Notebook",
        }

    def chat_completion(self, messages, model=None, temperature=0.7, max_tokens=4096):
        """Non-streaming chat completion."""
        if not model:
            model = current_app.config["DEFAULT_CHAT_MODEL"]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_completion_stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
        """Streaming chat completion — yields content chunks."""
        if not model:
            model = current_app.config["DEFAULT_CHAT_MODEL"]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def vision_completion(self, images_b64, prompt, model=None, temperature=0.3, max_tokens=8192):
        """
        Send images + prompt to a vision model.
        images_b64: list of base64-encoded image strings
        Returns: model text response
        """
        if not model:
            model = current_app.config["DEFAULT_VISION_MODEL"]

        content = [{"type": "text", "text": prompt}]
        for img_b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        messages = [{"role": "user", "content": content}]
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
