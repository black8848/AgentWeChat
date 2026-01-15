import os
import base64

import requests


class BaiduOCR:
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"

    def __init__(self, api_key: str, secret_key: str):
        self._api_key = api_key
        self._secret_key = secret_key
        self._access_token = None

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": self._api_key,
            "client_secret": self._secret_key,
        }
        resp = requests.post(self.TOKEN_URL, params=params)
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    def recognize(self, image_path: str) -> list[dict]:
        """识别图片中的文字，返回带位置信息的结果"""
        token = self._get_access_token()

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        resp = requests.post(
            f"{self.OCR_URL}?access_token={token}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"image": image_data},
        )
        resp.raise_for_status()
        result = resp.json()

        if "error_code" in result:
            raise Exception(f"OCR错误: {result['error_msg']}")

        return result.get("words_result", [])
