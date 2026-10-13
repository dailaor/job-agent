"""Isolated, clearly synthetic recommendation fixtures; never reads the user's profile."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from job_agent.config import AgentConfig, KnowledgeSettings, Preferences, save_config
from job_agent.database import Database
from job_agent.knowledge.service import KnowledgeService
from job_agent.models import ApplicationStatus, Candidate, Job
from job_agent.service import AgentService
from job_agent.web import serve


def prepare() -> AgentService:
    root = Path(__file__).resolve().parents[1] / "work" / "recommendation-preview"
    root.mkdir(parents=True, exist_ok=True)
    knowledge = KnowledgeSettings(company_aliases={"示例科技": ["示例科技"], "示例云": ["示例云"]})
    config = AgentConfig(
        candidate=Candidate("演示候选人", education="本科", skills=["SQL", "Python", "需求分析", "数据分析"], years_experience=2),
        preferences=Preferences(locations=["北京", "杭州"], minimum_salary=18000, published_within_days=None),
        greetings={"default": "演示配置，无真实投递"}, knowledge=knowledge,
    )
    save_config(config, root / "config.json")
    db = Database(root / "preview.sqlite3")
    now = datetime.now(timezone.utc)
    fixture_ids: dict[str, int] = {}
    for job in [
        Job(source="demo", source_id="decision-good", title="数据产品经理（演示）", company="示例科技", location="北京", url="https://example.com/jobs/data-product", education="本科及以上", salary_min=20000, salary_max=26000,
            published_at=(now - timedelta(days=2)).isoformat(),
            description="本科及以上，2 年经验。负责数据产品需求分析与指标体系，使用 SQL、Python、数据分析协作。固定工资 20–26K/月，13 薪。常规工作时间 9:30–18:30，双休。提供导师反馈和内部培训。",
            metadata={"is_demo": True, "employment_type": "full_time", "salary_unit": "month", "business_unit": "数据平台"}),
        Job(source="demo", source_id="decision-good-growth", title="增长数据产品经理（演示）", company="示例科技", location="杭州", url="https://example.com/jobs/growth-product", education="本科及以上", salary_min=19000, salary_max=24000,
            published_at=(now - timedelta(days=3)).isoformat(),
            description="本科及以上，2 年经验。负责增长数据产品需求分析与指标体系，使用 SQL、Python 和数据分析支持产品迭代。固定工资 19–24K/月，13 薪。常规工作时间 9:30–18:30，周末双休。提供内部培训和导师反馈。",
            metadata={"is_demo": True, "employment_type": "full_time", "salary_unit": "month", "business_unit": "增长分析"}),
        Job(source="demo", source_id="decision-unknown", title="AI 产品经理（演示）", company="示例云", location="杭州", url="https://example.com/jobs/ai-product", education="本科", published_at=(now - timedelta(days=1)).isoformat(),
            description="本科，负责 AI 产品需求分析及用户反馈分析。熟悉 Python 与数据分析，推动产品迭代。薪资与具体工作安排面议。",
            metadata={"is_demo": True, "employment_type": "full_time"}),
        Job(source="demo", source_id="decision-education", title="算法产品经理（演示·门槛不符）", company="示例科技", location="北京", url="https://example.com/jobs/algorithm-product", education="硕士及以上", published_at=now.isoformat(),
            description="硕士及以上学历，负责需求分析，熟悉 Python。",
            metadata={"is_demo": True, "employment_type": "full_time"}),
    ]:
        fixture_ids[job.source_id] = db.upsert_job(job)[0]
    # Reset only these synthetic fixture records so repeated UI runs are deterministic.
    with db.connect() as connection:
        marks = ",".join("?" for _ in fixture_ids)
        connection.execute(f"DELETE FROM applications WHERE job_id IN ({marks})", tuple(fixture_ids.values()))
    legacy_id = db.create_application(fixture_ids["decision-unknown"], "demo", "合成演示开场白，无真实发送")
    db.update_application(legacy_id, ApplicationStatus.GREETING_SENT,
                          evidence="合成演示回执，无真实平台操作", external_id="synthetic-thread-001")
    service = KnowledgeService(knowledge, db)
    service.import_payload({
        "source": "manual", "url": "https://example.com/experience/data-team", "title": "示例科技数据平台体验（合成演示，不是真实经历）",
        "company": "示例科技", "role_family": "product", "employment_type": "full_time", "business_unit": "数据平台", "city": "北京",
        "published_at": (now - timedelta(days=15)).isoformat(),
        "content": "这是一条用于界面验收的合成演示，不能作为真实公司情况。示例科技北京数据平台产品岗位平时九点半上班，通常十八点半下班，周末双休，发布周偶尔加班。团队按双周迭代周期交付，每周两次会议，需求变更会共同确认优先级。负责人每周安排导师反馈，入职后有培训和内部学习机会。实际待遇、业务安排、团队变化应当向 HR 和直属负责人核实，此处只演示证据如何被引用与展示。",
    })
    return AgentService(root / "config.json", root / "preview.sqlite3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    service = prepare()
    if args.prepare_only:
        print(f"Synthetic preview prepared: {service.database_path}")
    else:
        serve(service, port=args.port)
