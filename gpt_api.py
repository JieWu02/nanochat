#!/usr/bin/env python3
"""
Minimal GPT calling API extracted from the original script.

- Azure OpenAI client with Azure AD auth (az cli)
- Global semaphore for concurrency control
- call_o3() with retry, rate-limit/backoff, timeout handling
"""

import os
import re
import time
import threading
from typing import Optional, Tuple, Dict, Any

from openai import AzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider

# ----------------- Global concurrency & monitoring -----------------

# Limit concurrent API calls (same逻辑：100个并发)
API_SEMAPHORE = threading.Semaphore(100)

# Track recent success/fail for monitoring
API_SUCCESS_WINDOW = []
API_SUCCESS_LOCK = threading.Lock()


def record_api_result(success: bool) -> None:
    """Record API call result for monitoring (keeps last 50 results)."""
    global API_SUCCESS_WINDOW
    with API_SUCCESS_LOCK:
        API_SUCCESS_WINDOW.append(success)
        if len(API_SUCCESS_WINDOW) > 50:
            API_SUCCESS_WINDOW.pop(0)


# ----------------- GPT Client 封装 -----------------

class GPTClient:
    """
    Thin wrapper around Azure OpenAI `o3-mini` with:
    - Azure AD auth via `az login`
    - Global semaphore concurrency control
    - Retries for 429 / timeout
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: str = "o3-mini",
        api_version: str = "2025-01-01-preview",
    ) -> None:
        """
        Args:
            endpoint_url: Azure OpenAI endpoint. If None, read from ENDPOINT_URL
                          or fallback to the default in the original script.
            model_name:   Model name / deployment name, default "o3-mini".
            api_version:  API version.
        """
        self.model_name = model_name
        self.client = self._setup_azure_client(endpoint_url, api_version)

    @staticmethod
    def _setup_azure_client(
        endpoint_url: Optional[str],
        api_version: str,
    ) -> AzureOpenAI:
        """Setup Azure OpenAI client with Azure AD token provider."""
        endpoint_url = endpoint_url or os.getenv(
            "ENDPOINT_URL",
            "https://aims-oai-research-inference-uks.openai.azure.com/",
        )

        # 使用 AzureCliCredential + bearer token provider
        token_provider = get_bearer_token_provider(
            AzureCliCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

        return AzureOpenAI(
            azure_endpoint=endpoint_url,
            azure_ad_token_provider=token_provider,
            api_version=api_version,
        )

    def call_o3(
        self,
        prompt: str,
        max_completion_tokens: int = 32768,
        timeout: int = 300,
        reasoning_effort: str = "high",
        max_retries: int = 5,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Call o3-mini with retry & rate-limit handling.

        Args:
            prompt:              User prompt.
            max_completion_tokens: Max completion tokens.
            timeout:            Request timeout (seconds).
            reasoning_effort:   "low" | "medium" | "high".
            max_retries:        Max retry attempts.

        Returns:
            (content, usage) where:
              - content: str | None  (model输出文本)
              - usage:   dict | None (OpenAI usage，对应 response.usage)
        """
        for attempt in range(max_retries):
            # 控制并发
            with API_SEMAPHORE:
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "user", "content": prompt},
                        ],
                        reasoning_effort=reasoning_effort,
                        max_completion_tokens=max_completion_tokens,
                        timeout=timeout,  # SDK 内部处理超时
                    )

                    if response and response.choices:
                        record_api_result(True)
                        print("✅ API call successful")
                        return response.choices[0].message.content, response.usage
                    else:
                        record_api_result(False)
                        print("❌ API call returned no response")
                        return None, None

                except Exception as e:
                    error_msg = str(e)

                    # ----- 429 / rate limit -----
                    if "429" in error_msg or "rate limit" in error_msg.lower():
                        record_api_result(False)
                        # 从报错里抽取 "Try again in X seconds"
                        wait_match = re.search(r"Try again in (\d+) seconds", error_msg)
                        if wait_match:
                            wait_time = float(wait_match.group(1))
                        else:
                            # 0.5, 1, 2, 4... 最多 10s（和原脚本一致）
                            wait_time = min(0.5 * (2 ** attempt), 10)

                        if attempt < max_retries - 1:
                            print(
                                f"⏳ Rate limit, retry in {wait_time:.1f}s "
                                f"(attempt {attempt + 2}/{max_retries})"
                            )
                            time.sleep(wait_time)
                            continue
                        else:
                            print(
                                f"❌ API call failed after {max_retries} attempts: {e}"
                            )
                            return None, None

                    # ----- timeout -----
                    elif "timeout" in error_msg.lower():
                        if attempt < max_retries - 1:
                            print(
                                f"⏰ Timeout, retrying {attempt + 2}/{max_retries}..."
                            )
                            time.sleep(2)
                            continue
                        else:
                            print(
                                f"⏰ API call timed out after {max_retries} attempts"
                            )
                            return None, None

                    # ----- 其它错误 -----
                    else:
                        print(f"❌ API call failed: {e}")
                        return None, None

        # 理论上不会走到这里
        return None, None


# 你在其它脚本里可以这样用：
#
# from gpt_api import GPTClient
#
# gpt = GPTClient()
# content, usage = gpt.call_o3("Your prompt here")
# print(content)
