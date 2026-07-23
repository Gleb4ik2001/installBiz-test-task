import asyncio

import httpx

from app.config import settings


class APIClient:
    def __init__(self, download_state: dict):
        self.download_state = download_state
        self.headers = {}
        if settings.CANDIDATE_ID:
            self.headers["X-Candidate-Id"] = settings.CANDIDATE_ID

    async def safe_request(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs
    ):
        while True:
            try:
                response = await client.request(
                    method, url, headers=self.headers, **kwargs
                )

                if response.status_code in (429, 403):
                    retry_header = response.headers.get("Retry-After", "5")
                    try:
                        retry_seconds = int(retry_header)
                    except ValueError:
                        retry_seconds = 5

                    self.download_state["retry_after"] = retry_seconds
                    if response.status_code == 403:
                        self.download_state["status_message"] = (
                            f"Заблокирован. Ожидание {retry_seconds} сек..."
                        )
                    else:
                        self.download_state["status_message"] = (
                            f"Превышен лимит частоты. Пауза {retry_seconds} сек..."
                        )

                    await asyncio.sleep(retry_seconds)
                    self.download_state["retry_after"] = 0
                    continue

                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                self.download_state["error_message"] = (
                    f"HTTP ошибка {exc.response.status_code}: {exc.response.text}"
                )
                raise exc
            except Exception as exc:
                self.download_state["error_message"] = f"Сетевая ошибка: {str(exc)}"
                raise exc
