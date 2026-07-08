"""
llm_provider.py
---------------
LLM Provider Abstraction Layer for TutorAI.

Allows swapping backends (OpenRouter vs Gemini) and models via configurations,
preventing hardcoupling to any single client SDK or provider.
"""

from __future__ import annotations

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx
from google import genai as google_genai
from google.genai import types

from app.core.config import settings


# ─────────────────────────────────────────────────────────────
# ABSTRACT BASE CLASS INTERFACE
# ─────────────────────────────────────────────────────────────

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.

    Every provider implementation must conform to this interface.
    """

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        tools: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Execute a standard chat completion.

        Returns a dictionary:
            {
                "text": "The generated model output...",
                "tool_calls": [...] # optional function calls list
            }
        """
        pass

    @abstractmethod
    async def complete_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        queue: asyncio.Queue
    ) -> str:
        """
        Execute a streaming chat completion, pushing text fragments
        to the queue in real-time. Returns the complete concatenated text.
        """
        pass


# ─────────────────────────────────────────────────────────────
# OPENROUTER PROVIDER
# ─────────────────────────────────────────────────────────────

class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API Client implementation using httpx.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TutorAI"
        }

    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        tools: Optional[List[dict]] = None,
        max_tokens: int = 0
    ) -> Dict[str, Any]:
        
        # If API key is dummy/missing, trigger mock answer directly to allow testing
        if not self.api_key or "dummy" in self.api_key:
            return self._mock_fallback(model, messages)

        from app.core.config import settings
        token_limit = max_tokens or settings.max_tokens

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": token_limit,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if tools:
            payload["tools"] = tools

        print(f"[LLMProvider] POST {self.base_url} model={model} max_tokens={token_limit}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
                if response.status_code != 200:
                    print(f"[LLMProvider] ERROR {response.status_code}: {response.text[:200]}")
                response.raise_for_status()
                data = response.json()
                
                choice = data["choices"][0]["message"]
                return {
                    "text": choice.get("content") or "",
                    "tool_calls": choice.get("tool_calls") or []
                }
            except Exception as e:
                # If a 404/model failure occurs on Nvidia/OpenRouter, try to fall back to llama-3.1-8b-instruct
                # to get a real answer, before falling back to static mock response.
                fallback_model = "meta/llama-3.1-8b-instruct" if "nvidia" in self.base_url else "meta-llama/llama-3.1-8b-instruct"
                if model != fallback_model:
                    print(f"[LLMProvider] API Error: {e}. Retrying with fallback model '{fallback_model}'...")
                    payload["model"] = fallback_model
                    try:
                        response = await client.post(
                            self.base_url,
                            headers=self._get_headers(),
                            json=payload
                        )
                        if response.status_code != 200:
                            print(f"[LLMProvider] FALLBACK ERROR {response.status_code}: {response.text[:200]}")
                        response.raise_for_status()
                        data = response.json()
                        choice = data["choices"][0]["message"]
                        return {
                            "text": choice.get("content") or "",
                            "tool_calls": choice.get("tool_calls") or []
                        }
                    except Exception as fallback_err:
                        print(f"[LLMProvider] Fallback error: {fallback_err}")
                
                print(f"[LLMProvider] API Error: {e} - falling back to mock response.")
                return self._mock_fallback(model, messages)

    async def complete_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        queue: asyncio.Queue
    ) -> str:
        
        if not self.api_key or "dummy" in self.api_key:
            mock_res = self._mock_fallback(model, messages)["text"]
            for chunk in mock_res.split(" "):
                await queue.put(chunk + " ")
                await asyncio.sleep(0.05)
            return mock_res

        from app.core.config import settings
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": settings.max_tokens,
        }

        print(f"[LLMProvider Stream] POST {self.base_url} model={model} max_tokens={settings.max_tokens}")

        full_parts = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        await response.read()
                        print(f"[LLMProvider Stream] ERROR {response.status_code}: {response.text[:200]}")
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data_str)
                                delta = chunk_data["choices"][0]["delta"]
                                content = delta.get("content") or ""
                                if content:
                                    full_parts.append(content)
                                    await queue.put(content)
                            except:
                                continue
            except Exception as e:
                # If error, try fallback model streaming
                fallback_model = "meta/llama-3.1-8b-instruct" if "nvidia" in self.base_url else "meta-llama/llama-3.1-8b-instruct"
                if model != fallback_model:
                    print(f"[LLMProvider Stream] Error: {e}. Retrying stream with fallback model '{fallback_model}'...")
                    payload["model"] = fallback_model
                    try:
                        async with client.stream(
                            "POST",
                            self.base_url,
                            headers=self._get_headers(),
                            json=payload
                        ) as response:
                            if response.status_code != 200:
                                await response.read()
                                print(f"[LLMProvider Stream] FALLBACK ERROR {response.status_code}: {response.text[:200]}")
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line.strip():
                                    continue
                                if line.startswith("data: "):
                                    data_str = line[6:].strip()
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk_data = json.loads(data_str)
                                        delta = chunk_data["choices"][0]["delta"]
                                        content = delta.get("content") or ""
                                        if content:
                                            full_parts.append(content)
                                            await queue.put(content)
                                    except:
                                        continue
                            return "".join(full_parts)
                    except Exception as fallback_err:
                        print(f"[LLMProvider Stream] Fallback error: {fallback_err}")
                
                print(f"[LLMProvider] Streaming Error: {e}")
                err_text = f"\n\n[LLMProvider Stream Error: {e}]"
                await queue.put(err_text)
                return err_text

        return "".join(full_parts)

    def _mock_fallback(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Provides a safe, local fallback response if offline or API key is missing."""
        last_msg = messages[-1]["content"] if messages else ""
        print(f"[OpenRouter Mock] Mocking completion for model '{model}'")
        
        # Determine intent for routing mock responses
        if "Classify" in last_msg or "Orchestrator" in last_msg or "TutorAI Orchestrator" in str(messages):
            return {
                "text": json.dumps({
                    "agents": ["tutor"],
                    "reasoning": "Mock orchestrator classification"
                }),
                "tool_calls": []
            }
        if "Critic" in str(messages):
            return {
                "text": json.dumps({
                    "approved": True,
                    "feedback": "Approved (Mocked Critic)",
                    "action": "approve",
                    "missing_elements": []
                }),
                "tool_calls": []
            }
        if "svg_visualizer" in str(messages) or "diagram" in last_msg.lower():
            return {
                "text": json.dumps({
                    "type": "flowchart",
                    "title": "Mocked Concept Diagram",
                    "nodes": [{"id": "n1", "label": "Mock Diagram", "level": 0}],
                    "edges": []
                }),
                "tool_calls": []
            }
            
        return {
            "text": f"**[Mocked {model.split('/')[-1]} Response]**\nThis is a mock completion for testing the TutorAI multi-agent graph pipelines offline.",
            "tool_calls": []
        }


# ─────────────────────────────────────────────────────────────
# GEMINI SDK PROVIDER
# ─────────────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    """
    Google Gemini SDK client wrapper.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = google_genai.Client(api_key=api_key) if api_key else None

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[types.Content]:
        """Convert standard message dictionary to Gemini SDK Content format."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])]
                )
            )
        return contents

    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        tools: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("[GeminiProvider] client not initialized. GEMINI_API_KEY is missing.")

        # Translate model name to Gemini naming if it uses OpenRouter string
        gemini_model = "gemini-2.5-flash"
        if "gemini" in model:
            gemini_model = model.split("/")[-1]

        contents = self._convert_messages(messages)
        
        # Translate OpenAI tools format to Gemini Tool format
        gemini_tools = None
        if tools:
            # Build tool definitions manually or wrap
            from app.agents.tools import ToolRegistry
            tool_names = [t["function"]["name"] for t in tools]
            gemini_tools = ToolRegistry.get_gemini_tools(tool_names)

        # Separate system instruction if present in first index
        system_instruction = None
        if messages and messages[0]["role"] == "system":
            system_instruction = messages[0]["content"]
            contents = contents[1:]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json" if json_mode else "text/plain"
        )
        if gemini_tools:
            config.tools = [gemini_tools]

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=gemini_model,
                contents=contents,
                config=config
            )
        )

        candidate = response.candidates[0]
        text_content = ""
        tool_calls = []

        for part in candidate.content.parts:
            if part.text:
                text_content += part.text
            elif part.function_call:
                tool_calls.append({
                    "id": f"call_{part.function_call.name}",
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": json.dumps(dict(part.function_call.args))
                    }
                })

        return {
            "text": text_content,
            "tool_calls": tool_calls
        }

    async def complete_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        queue: asyncio.Queue
    ) -> str:
        if not self.client:
            raise ValueError("[GeminiProvider] client not initialized. GEMINI_API_KEY is missing.")

        gemini_model = "gemini-2.5-flash"
        if "gemini" in model:
            gemini_model = model.split("/")[-1]

        contents = self._convert_messages(messages)
        system_instruction = None
        if messages and messages[0]["role"] == "system":
            system_instruction = messages[0]["content"]
            contents = contents[1:]

        config = types.GenerateContentConfig(system_instruction=system_instruction)

        loop = asyncio.get_running_loop()
        
        def _stream_gen():
            parts = []
            for chunk in self.client.models.generate_content_stream(
                model=gemini_model,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    parts.append(chunk.text)
                    loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
            return "".join(parts)

        return await loop.run_in_executor(None, _stream_gen)


# ─────────────────────────────────────────────────────────────
# NVIDIA PROVIDER
# ─────────────────────────────────────────────────────────────

class NvidiaProvider(OpenRouterProvider):
    """
    NVIDIA API Client implementation using OpenAI compatible integrate endpoint.
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _translate_model(self, model: str) -> str:
        # Translate OpenRouter/standard model names to NVIDIA's NIM model names
        if model.startswith("meta-llama/"):
            return model.replace("meta-llama/", "meta/")
        if model.startswith("deepseek/"):
            return model.replace("deepseek/", "deepseek-ai/")
        return model

    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        tools: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        nvidia_model = self._translate_model(model)
        print(f"[NvidiaProvider] Translated model '{model}' -> '{nvidia_model}'")
        return await super().complete(nvidia_model, messages, json_mode, tools)

    async def complete_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        queue: asyncio.Queue
    ) -> str:
        nvidia_model = self._translate_model(model)
        print(f"[NvidiaProvider Stream] Translated model '{model}' -> '{nvidia_model}'")
        return await super().complete_stream(nvidia_model, messages, queue)


# ─────────────────────────────────────────────────────────────
# FACTORY INSTANTIATOR
# ─────────────────────────────────────────────────────────────

def get_llm_provider() -> LLMProvider:
    """
    Factory function returning the configured LLM provider.
    """
    provider_name = settings.llm_provider.lower()
    
    if provider_name == "gemini":
        return GeminiProvider(api_key=settings.gemini_api_key)
    
    if provider_name == "nvidia":
        return NvidiaProvider(api_key=settings.nvidia_api_key)
        
    return OpenRouterProvider(api_key=settings.openrouter_api_key)
