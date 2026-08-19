from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..models import Job


def demo_jobs() -> list[Job]:
    now = datetime.now(timezone.utc)
    return [
        Job(
            source="boss",
            source_id="demo-boss-1",
            title="AI 产品经理",
            company="示例大厂",
            location="北京",
            url="https://www.zhipin.com/job_detail/demo-boss-1.html",
            description="负责大模型产品规划和需求分析，要求 3-5 年经验，熟悉 SQL、A/B测试和用户研究。",
            experience_min=3,
            experience_max=5,
            published_at=now.isoformat(),
            metadata={"required_skills": ["需求分析", "SQL", "A/B测试", "用户研究", "LLM"], "demo": True, "detail_loaded": True},
        ),
        Job(
            source="boss",
            source_id="demo-boss-2",
            title="数据产品经理",
            company="示例成长公司",
            location="上海",
            url="https://www.zhipin.com/job_detail/demo-boss-2.html",
            description="负责指标体系和数据平台，要求 2-4 年经验，熟悉 SQL、Python 和数据分析。",
            experience_min=2,
            experience_max=4,
            published_at=(now - timedelta(days=1)).isoformat(),
            metadata={"required_skills": ["SQL", "Python", "数据分析", "需求分析"], "demo": True, "detail_loaded": True},
        ),
        Job(
            source="official:demo-ats",
            source_id="demo-official-1",
            title="高级 AI 产品负责人",
            company="目标科技",
            location="北京",
            url="https://careers.example.com/jobs/demo-official-1",
            apply_url="https://careers.example.com/jobs/demo-official-1/apply",
            description="负责 AI 平台业务，要求 4 年以上经验，熟悉产品设计、LLM、SQL、项目管理。",
            experience_min=4,
            published_at=(now - timedelta(days=2)).isoformat(),
            deadline=(now + timedelta(days=20)).isoformat(),
            metadata={"required_skills": ["SQL", "数据分析", "LLM"], "demo": True},
        ),
        Job(
            source="official:demo-ats",
            source_id="demo-official-2",
            title="产品经理（销售方向）",
            company="示例保险",
            location="北京",
            url="https://careers.example.com/jobs/demo-official-2",
            description="销售支持与培训。",
            published_at=now.isoformat(),
            metadata={"required_skills": ["销售"], "demo": True},
        ),
    ]
