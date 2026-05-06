"""OpenRouter API client for making LLM requests."""

import httpx
from typing import List, Dict, Any
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


def _extract_error_message(response: httpx.Response) -> str:
    """Pull the human-readable error message out of an OpenRouter response."""
    try:
        body = response.json()
        err = body.get('error')
        if isinstance(err, dict):
            msg = err.get('message')
            if msg:
                return msg
        if isinstance(err, str):
            return err
    except Exception:
        pass
    text = response.text or ''
    return text[:500] if text else f'HTTP {response.status_code}'


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Dict[str, Any]:
    """
    Query a single model via OpenRouter API.

    Returns a dict with either ('content', 'reasoning_details') on success
    or ('content': None, 'error': str) on failure.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )

            if response.status_code >= 400:
                err_msg = f"HTTP {response.status_code}: {_extract_error_message(response)}"
                print(f"Error querying model {model}: {err_msg}")
                return {'content': None, 'error': err_msg}

            data = response.json()

            # OpenRouter sometimes returns 200 with an error body and no choices
            if not data.get('choices'):
                err_msg = _extract_error_message(response)
                print(f"Error querying model {model}: {err_msg}")
                return {'content': None, 'error': err_msg}

            message = data['choices'][0]['message']
            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                'error': None,
            }

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        print(f"Error querying model {model}: {err_msg}")
        return {'content': None, 'error': err_msg}


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Dict[str, Any]]:
    """Query multiple models in parallel. Each value is a dict from `query_model`."""
    import asyncio

    tasks = [query_model(model, messages) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
