from __future__ import annotations

import base64
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from job_agent.config import config_from_dict
from job_agent.connectors.campus import CampusPortalConnector
from job_agent.connectors.registry import build_channel_registry
from job_agent.models import normalize_url


ROOT = Path(__file__).resolve().parents[1]


def _site(adapter: str, host: str = "careers.example.com", **extra: object) -> dict:
    return {
        "id": f"{adapter}-campus",
        "name": adapter,
        "strategy": "campus_api",
        "adapter": adapter,
        "list_url": f"https://{host}/jobs",
        "allowed_hosts": [host],
        "autofill": {"status": "planned", "profile": f"{adapter}-v1"},
        **extra,
    }


class CampusConnectorTests(unittest.TestCase):
    def test_spa_detail_fragments_are_preserved(self) -> None:
        value = "https://campus.example.com/e/#/job/42?code=abc"
        self.assertEqual(normalize_url(value), value)

    def test_moka_aes_envelope_is_decrypted(self) -> None:
        key = b"0123456789abcdef"
        iv = "fedcba9876543210"
        clear = json.dumps({"success": True, "data": {"jobs": [{"id": "one"}]}}, ensure_ascii=False).encode()
        padder = PKCS7(128).padder()
        padded = padder.update(clear) + padder.finalize()
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv.encode())).encryptor()
        cipher = encryptor.update(padded) + encryptor.finalize()
        decoded = CampusPortalConnector._decrypt_moka_response({
            "necromancer": key.decode(),
            "data": base64.b64encode(cipher).decode(),
        }, iv)
        self.assertTrue(decoded["success"])
        self.assertEqual(decoded["data"]["jobs"][0]["id"], "one")

    def test_meituan_mapping_includes_full_jd_and_future_autofill_profile(self) -> None:
        connector = CampusPortalConnector(_site("meituan", "zhaopin.meituan.com"))
        job = connector._meituan_job({
            "jobUnionId": "42",
            "name": "AI 产品经理",
            "jobType": "1",
            "cityList": [{"name": "北京"}],
            "department": [{"name": "核心业务"}],
            "jobDuty": "负责 Agent 产品",
            "jobRequirement": "熟悉大模型",
            "refreshTime": 1_787_000_000_000,
        })
        self.assertIn("负责 Agent 产品", job.description)
        self.assertEqual(job.metadata["employment_type"], ["全职", "校招"])
        self.assertEqual(job.metadata["autofill_profile"], "meituan-v1")
        self.assertIn("jobUnionId=42", job.url)

    def test_each_portal_maps_to_a_stable_job_detail(self) -> None:
        didi = CampusPortalConnector(_site("didi_moka", "app.mokahr.com"))
        didi_job = didi._didi_job({
            "id": "uuid-one",
            "title": "产品经理",
            "locations": [{"cityName": "北京"}],
            "commitment": "全职",
            "jobDescription": "岗位描述",
        }, "REF")
        self.assertIn("#/job/uuid-one", didi_job.url)

        kuaishou = CampusPortalConnector(_site(
            "kuaishou",
            "campus.kuaishou.cn",
            share_code="share",
        ))
        kuaishou_job = kuaishou._kuaishou_job({
            "id": 7,
            "name": "平台产品经理",
            "positionNatureCode": "fulltime",
            "workLocationDicts": [{"name": "杭州"}],
            "description": "岗位职责",
            "positionDemand": "岗位要求",
        }, ["project"])
        self.assertIn("#/campus/job-info/7", kuaishou_job.url)

        tencent = CampusPortalConnector(_site("tencent", "join.qq.com"))
        tencent_job = tencent._tencent_job({
            "postId": "99",
            "positionTitle": "技术产品经理",
            "workCities": "深圳 北京",
            "recruitLabelName": "应届毕业生",
        })
        self.assertEqual(tencent_job.url, "https://join.qq.com/post_detail.html?postid=99")

        jd = CampusPortalConnector(_site("jd", "campus.jd.com", referral_erp="ERP"))
        jd_job = jd._jd_job({
            "publishId": 88,
            "positionName": "金融产品经理",
            "workContent": "岗位职责",
            "qualification": "岗位要求",
            "requirementVoList": [
                {"reqId": 1, "workCity": "北京", "positionBg": "京东科技"},
                {"reqId": 1, "workCity": "北京", "positionBg": "京东科技"},
            ],
        })
        self.assertIn("#/details?id=88&codeValueErp=ERP", jd_job.url)
        self.assertEqual(jd_job.location, "北京")
        self.assertEqual(jd_job.metadata["business_units"], ["京东科技"])

    def test_default_detail_urls_do_not_expose_referral_identifiers(self) -> None:
        didi = CampusPortalConnector(_site("didi_moka", "app.mokahr.com"))
        didi_job = didi._didi_job({"id": "uuid-two", "title": "产品经理"}, "")
        self.assertEqual(
            didi_job.url,
            "https://app.mokahr.com/campus_apply/didiglobal/96064#/job/uuid-two",
        )

        jd = CampusPortalConnector(_site("jd", "campus.jd.com"))
        jd_job = jd._jd_job({"publishId": 89, "positionName": "产品经理"})
        self.assertEqual(
            jd_job.url,
            "https://campus.jd.com/api/wx/position/index#/details?id=89",
        )

    def test_example_config_registers_five_ready_campus_channels(self) -> None:
        data = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        registry = build_channel_registry(config_from_dict(data), load_entry_points=False)
        campus = [item for item in registry.all() if item.strategy == "campus_api"]
        self.assertEqual(len(campus), 5)
        self.assertTrue(all(item.ready for item in campus))
        self.assertTrue(all(item.capabilities["autofill_status"] == "planned" for item in campus))


if __name__ == "__main__":
    unittest.main()
