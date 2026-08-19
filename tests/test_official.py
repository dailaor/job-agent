from __future__ import annotations

import json
import unittest
from io import BytesIO
from unittest.mock import patch

from job_agent.connectors.official import OfficialSiteConnector


class _Response(BytesIO):
    def __init__(self, payload: dict, url: str) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))
        self._url = url

    def geturl(self) -> str:
        return self._url


class _Opener:
    def __init__(self, response: _Response) -> None:
        self.response = response

    def open(self, request: object, timeout: int) -> _Response:
        return self.response


def _definition() -> dict:
    return {
        "id": "example",
        "name": "示例招聘",
        "strategy": "json_api",
        "list_url": "https://careers.example.com/api/jobs",
        "allowed_hosts": ["careers.example.com"],
        "records_path": "data.jobs",
        "mapping": {
            "id": "id",
            "title": "title",
            "company": "company",
            "location": "location",
            "description": "description",
            "url": "url",
            "apply_url": "apply_url",
            "salary_min": "salary_min",
            "salary_max": "salary_max",
            "experience_min": "experience_min",
            "experience_max": "experience_max",
            "employment_type": "employment_type",
            "work_mode": "work_mode",
        },
    }


class OfficialConnectorTests(unittest.TestCase):
    def test_json_mapping_populates_hard_filter_fields(self) -> None:
        payload = {"data": {"jobs": [{
            "id": "one",
            "title": "产品经理",
            "company": "示例公司",
            "location": "上海",
            "description": "负责产品规划",
            "url": "/jobs/one",
            "apply_url": "/jobs/one/apply",
            "salary_min": "20,000",
            "salary_max": 30000,
            "experience_min": "2",
            "experience_max": 5,
            "employment_type": "全职",
            "work_mode": ["混合"],
        }]}}
        response = _Response(payload, "https://careers.example.com/api/jobs")
        with patch("job_agent.connectors.official.build_opener", return_value=_Opener(response)):
            jobs = OfficialSiteConnector(_definition())._discover_json(["产品经理"])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].salary_min, 20000)
        self.assertEqual(jobs[0].salary_max, 30000)
        self.assertEqual(jobs[0].experience_min, 2)
        self.assertEqual(jobs[0].metadata["employment_type"], "全职")
        self.assertEqual(jobs[0].metadata["work_mode"], ["混合"])

    def test_json_redirect_to_unlisted_host_is_rejected(self) -> None:
        response = _Response({"data": {"jobs": []}}, "https://evil.example.net/jobs")
        with patch("job_agent.connectors.official.build_opener", return_value=_Opener(response)):
            with self.assertRaisesRegex(ValueError, "outside configured hosts"):
                OfficialSiteConnector(_definition())._discover_json([])


if __name__ == "__main__":
    unittest.main()
