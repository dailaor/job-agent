/* Synthetic demonstration data only; no user profile, credentials or backend required. */
window.FrontendDemoData = {
  "config": {
    "candidate": {
      "name": "演示候选人",
      "headline": "",
      "years_experience": 2,
      "education": "本科",
      "skills": [
        "SQL",
        "Python",
        "需求分析",
        "数据分析"
      ],
      "resume_path": "示例简历.pdf",
      "resume_filename": "示例简历.pdf",
      "resume_text_path": "",
      "profile_source": "manual"
    },
    "preferences": {
      "boss_keywords": [],
      "official_keywords": [],
      "target_titles": [],
      "excluded_keywords": [],
      "locations": [
        "北京",
        "杭州"
      ],
      "employment_types": [],
      "work_modes": [],
      "workload_preference": "balanced",
      "role_boundary_preference": "no_preference",
      "growth_priority": "medium",
      "stability_priority": "medium",
      "culture_preferences": [],
      "community_risk_avoidances": [],
      "minimum_salary": 18000,
      "max_experience_gap": 2,
      "published_within_days": null,
      "unknown_field_policy": "keep",
      "blacklisted_companies": [],
      "company_tiers": {},
      "boss_daily_limit": 20,
      "official_daily_limit": 10,
      "strategy_mix": {
        "冲高": 0.25,
        "持平": 0.5,
        "保底": 0.25
      },
      "strategy_mode": "balanced",
      "channel_priority": [
        "official",
        "boss"
      ],
      "max_overqualification_years": 3,
      "auto_send_resume_after_reply": false
    },
    "greetings": {
      "default": "演示配置，无真实投递"
    },
    "fixed_answers": {},
    "boss": {},
    "official_sites": [],
    "mail": {},
    "knowledge": {
      "enabled": true,
      "allowed_sources": [
        "nowcoder",
        "xiaohongshu",
        "manual"
      ],
      "company_aliases": {
        "示例科技": [
          "示例科技"
        ],
        "示例云": [
          "示例云"
        ]
      },
      "role_families": {
        "product": [
          "产品经理",
          "ai产品",
          "大模型产品",
          "智能体产品",
          "数据产品",
          "策略产品",
          "增长产品",
          "平台产品",
          "b端产品",
          "用户产品",
          "产品策划",
          "产品岗"
        ],
        "data": [
          "数据分析",
          "数分",
          "商业分析",
          "商分",
          "经营分析",
          "策略分析",
          "数据科学",
          "数据运营",
          "数据研发",
          "数据工程",
          "大数据开发",
          "数仓"
        ],
        "algorithm": [
          "算法工程师",
          "算法岗",
          "大模型算法",
          "ai算法",
          "机器学习",
          "llm",
          "nlp",
          "推荐算法",
          "搜索算法",
          "推理算法",
          "算法实习"
        ],
        "backend": [
          "后端开发",
          "后端研发",
          "后端岗",
          "服务端开发",
          "java开发",
          "go开发",
          "golang"
        ]
      },
      "min_document_chars": 120,
      "max_document_chars": 20000,
      "max_age_days": 730,
      "retain_full_text": false,
      "embedding_provider": "hashing",
      "embedding_dimensions": 384,
      "retrieval_top_k": 12,
      "max_chunks_per_document": 2,
      "public_fetch_min_interval_seconds": 5
    },
    "scoring": {
      "provider": "rule",
      "model": "deepseek-v4-flash",
      "base_url": "https://api.deepseek.com",
      "api_key_env": "DEEPSEEK_API_KEY",
      "timeout_seconds": 90,
      "max_tokens": 2400,
      "temperature": 0,
      "thinking": false
    }
  },
  "dashboard": {
    "jobs": {
      "可投": 4
    },
    "applications": {
      "已发开场白": 1,
      "需要人工处理": 2
    },
    "strategies": {
      "持平": 4
    },
    "events": [
      {
        "id": 21,
        "entity_type": "application",
        "entity_id": "14",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:28:49.002372+00:00"
      },
      {
        "id": 20,
        "entity_type": "application",
        "entity_id": "13",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:28:48.994012+00:00"
      },
      {
        "id": 19,
        "entity_type": "application",
        "entity_id": "12",
        "event_type": "已发开场白",
        "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
        "occurred_at": "2026-10-12T15:28:48.960676+00:00"
      },
      {
        "id": 18,
        "entity_type": "application",
        "entity_id": "11",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:17:08.633244+00:00"
      },
      {
        "id": 17,
        "entity_type": "application",
        "entity_id": "10",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:17:08.626268+00:00"
      },
      {
        "id": 16,
        "entity_type": "application",
        "entity_id": "9",
        "event_type": "已发开场白",
        "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
        "occurred_at": "2026-10-12T15:17:08.592166+00:00"
      },
      {
        "id": 15,
        "entity_type": "application",
        "entity_id": "8",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:16:04.487679+00:00"
      },
      {
        "id": 14,
        "entity_type": "application",
        "entity_id": "7",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T15:16:04.480136+00:00"
      },
      {
        "id": 13,
        "entity_type": "job",
        "entity_id": "1",
        "event_type": "evaluated",
        "payload_json": "{\"job_id\": 1, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"SQL\", \"数据分析\", \"需求分析\"], \"missing_capabilities\": [], \"hard_reasons\": [], \"match_score\": 100.0, \"need_score\": 78.9, \"company_score\": 50.0, \"overall_score\": 89.45, \"confidence\": 0.87, \"reason\": \"能力关系：基本持平；技能覆盖 4/4；岗位满足度 79；公司档位：未知。\"}",
        "occurred_at": "2026-10-12T15:16:04.471208+00:00"
      },
      {
        "id": 12,
        "entity_type": "job",
        "entity_id": "2",
        "event_type": "evaluated",
        "payload_json": "{\"job_id\": 2, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"数据分析\", \"需求分析\"], \"missing_capabilities\": [], \"hard_reasons\": [], \"match_score\": 100.0, \"need_score\": 72.95, \"company_score\": 50.0, \"overall_score\": 86.47, \"confidence\": 0.79, \"reason\": \"能力关系：基本持平；技能覆盖 3/3；岗位满足度 73；公司档位：未知。\"}",
        "occurred_at": "2026-10-12T15:16:04.457328+00:00"
      },
      {
        "id": 11,
        "entity_type": "job",
        "entity_id": "3",
        "event_type": "evaluated",
        "payload_json": "{\"job_id\": 3, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"需求分析\"], \"missing_capabilities\": [], \"hard_reasons\": [], \"match_score\": 100.0, \"need_score\": 73.75, \"company_score\": 50.0, \"overall_score\": 86.88, \"confidence\": 0.71, \"reason\": \"能力关系：基本持平；技能覆盖 2/2；岗位满足度 74；公司档位：未知。\"}",
        "occurred_at": "2026-10-12T15:16:04.443236+00:00"
      },
      {
        "id": 10,
        "entity_type": "job",
        "entity_id": "4",
        "event_type": "evaluated",
        "payload_json": "{\"job_id\": 4, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"SQL\", \"数据分析\", \"需求分析\"], \"missing_capabilities\": [\"增长\"], \"hard_reasons\": [], \"match_score\": 90.0, \"need_score\": 78.1, \"company_score\": 50.0, \"overall_score\": 84.05, \"confidence\": 0.95, \"reason\": \"能力关系：基本持平；技能覆盖 4/5；岗位满足度 78；公司档位：未知。\"}",
        "occurred_at": "2026-10-12T15:16:04.430024+00:00"
      },
      {
        "id": 9,
        "entity_type": "application",
        "entity_id": "6",
        "event_type": "已发开场白",
        "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
        "occurred_at": "2026-10-12T15:16:04.392256+00:00"
      },
      {
        "id": 8,
        "entity_type": "application",
        "entity_id": "3",
        "event_type": "application_progress_updated",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": false}",
        "occurred_at": "2026-10-12T14:55:45.862744+00:00"
      },
      {
        "id": 7,
        "entity_type": "application",
        "entity_id": "5",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T14:55:45.736116+00:00"
      },
      {
        "id": 6,
        "entity_type": "application",
        "entity_id": "4",
        "event_type": "application_progress_updated",
        "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T14:55:44.817385+00:00"
      },
      {
        "id": 5,
        "entity_type": "application",
        "entity_id": "4",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T14:55:44.707467+00:00"
      },
      {
        "id": 4,
        "entity_type": "application",
        "entity_id": "3",
        "event_type": "已发开场白",
        "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
        "occurred_at": "2026-10-12T14:55:40.119268+00:00"
      },
      {
        "id": 3,
        "entity_type": "application",
        "entity_id": "2",
        "event_type": "application_progress_updated",
        "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T14:55:22.813780+00:00"
      },
      {
        "id": 2,
        "entity_type": "application",
        "entity_id": "2",
        "event_type": "manual_application_recorded",
        "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
        "occurred_at": "2026-10-12T14:55:22.707863+00:00"
      }
    ],
    "sources": [],
    "channels": [
      {
        "id": "demo",
        "name": "合成演示岗位库",
        "type": "official",
        "enabled": true,
        "ready": true,
        "keywords": [
          "产品经理"
        ],
        "strategy": "json_api",
        "url": "https://example.com",
        "health": "api_fetched",
        "health_label": "演示已就绪",
        "missing": [],
        "capabilities": {
          "discovery": "available",
          "autofill_status": "not_planned"
        }
      }
    ],
    "knowledge": {
      "enabled": true,
      "sources": [
        "nowcoder",
        "xiaohongshu"
      ],
      "embedding_provider": "hashing-v1",
      "raw_text_retained": false,
      "documents": {
        "accepted": 1
      },
      "chunks": 4,
      "scopes": [
        {
          "company": "示例科技",
          "role_family": "product",
          "employment_type": "full_time",
          "documents": 1
        }
      ]
    }
  },
  "jobs": [
    {
      "id": 1,
      "fingerprint": "245360a756527aee02a25b23",
      "source": "demo",
      "source_id": "decision-good",
      "title": "数据产品经理（演示）",
      "company": "示例科技",
      "location": "北京",
      "url": "https://example.com/jobs/data-product",
      "apply_url": null,
      "description": "本科及以上，2 年经验。负责数据产品需求分析与指标体系，使用 SQL、Python、数据分析协作。固定工资 20–26K/月，13 薪。常规工作时间 9:30–18:30，双休。提供导师反馈和内部培训。",
      "salary_min": 20000,
      "salary_max": 26000,
      "experience_min": null,
      "experience_max": null,
      "education": "本科及以上",
      "published_at": "2026-10-10T15:28:48.929611+00:00",
      "deadline": null,
      "recruiter_name": null,
      "recruiter_activity": null,
      "metadata_json": "{\"is_demo\": true, \"employment_type\": \"full_time\", \"salary_unit\": \"month\", \"business_unit\": \"数据平台\"}",
      "status": "可投",
      "first_seen_at": "2026-10-11T16:38:12.382573+00:00",
      "last_seen_at": "2026-10-12T15:28:48.929611+00:00",
      "strategy": "持平",
      "ability_relation": "基本持平",
      "match_score": 100,
      "need_score": 78.9,
      "company_score": 50,
      "overall_score": 89.45,
      "evaluation_reason": "能力关系：基本持平；技能覆盖 4/4；岗位满足度 79；公司档位：未知。",
      "hard_reasons_json": "[]",
      "application_status": "需要人工处理",
      "application_id": 13
    },
    {
      "id": 3,
      "fingerprint": "1d1e28c50e784cac14f35ef8",
      "source": "demo",
      "source_id": "decision-education",
      "title": "算法产品经理（演示·门槛不符）",
      "company": "示例科技",
      "location": "北京",
      "url": "https://example.com/jobs/algorithm-product",
      "apply_url": null,
      "description": "硕士及以上学历，负责需求分析，熟悉 Python。",
      "salary_min": null,
      "salary_max": null,
      "experience_min": null,
      "experience_max": null,
      "education": "硕士及以上",
      "published_at": "2026-10-12T15:28:48.929611+00:00",
      "deadline": null,
      "recruiter_name": null,
      "recruiter_activity": null,
      "metadata_json": "{\"is_demo\": true, \"employment_type\": \"full_time\"}",
      "status": "可投",
      "first_seen_at": "2026-10-11T16:38:12.390665+00:00",
      "last_seen_at": "2026-10-12T15:28:48.942300+00:00",
      "strategy": "持平",
      "ability_relation": "基本持平",
      "match_score": 100,
      "need_score": 73.75,
      "company_score": 50,
      "overall_score": 86.88,
      "evaluation_reason": "能力关系：基本持平；技能覆盖 2/2；岗位满足度 74；公司档位：未知。",
      "hard_reasons_json": "[]",
      "application_status": null,
      "application_id": null
    },
    {
      "id": 2,
      "fingerprint": "164f1d6d64a5aa518a3fb4e8",
      "source": "demo",
      "source_id": "decision-unknown",
      "title": "AI 产品经理（演示）",
      "company": "示例云",
      "location": "杭州",
      "url": "https://example.com/jobs/ai-product",
      "apply_url": null,
      "description": "本科，负责 AI 产品需求分析及用户反馈分析。熟悉 Python 与数据分析，推动产品迭代。薪资与具体工作安排面议。",
      "salary_min": null,
      "salary_max": null,
      "experience_min": null,
      "experience_max": null,
      "education": "本科",
      "published_at": "2026-10-11T15:28:48.929611+00:00",
      "deadline": null,
      "recruiter_name": null,
      "recruiter_activity": null,
      "metadata_json": "{\"is_demo\": true, \"employment_type\": \"full_time\"}",
      "status": "可投",
      "first_seen_at": "2026-10-11T16:38:12.386512+00:00",
      "last_seen_at": "2026-10-12T15:28:48.937774+00:00",
      "strategy": "持平",
      "ability_relation": "基本持平",
      "match_score": 100,
      "need_score": 72.95,
      "company_score": 50,
      "overall_score": 86.47,
      "evaluation_reason": "能力关系：基本持平；技能覆盖 3/3；岗位满足度 73；公司档位：未知。",
      "hard_reasons_json": "[]",
      "application_status": "已发开场白",
      "application_id": 12
    },
    {
      "id": 4,
      "fingerprint": "c5538657cb24cb72cf453353",
      "source": "demo",
      "source_id": "decision-good-growth",
      "title": "增长数据产品经理（演示）",
      "company": "示例科技",
      "location": "杭州",
      "url": "https://example.com/jobs/growth-product",
      "apply_url": null,
      "description": "本科及以上，2 年经验。负责增长数据产品需求分析与指标体系，使用 SQL、Python 和数据分析支持产品迭代。固定工资 19–24K/月，13 薪。常规工作时间 9:30–18:30，周末双休。提供内部培训和导师反馈。",
      "salary_min": 19000,
      "salary_max": 24000,
      "experience_min": null,
      "experience_max": null,
      "education": "本科及以上",
      "published_at": "2026-10-09T15:28:48.929611+00:00",
      "deadline": null,
      "recruiter_name": null,
      "recruiter_activity": null,
      "metadata_json": "{\"is_demo\": true, \"employment_type\": \"full_time\", \"salary_unit\": \"month\", \"business_unit\": \"增长分析\"}",
      "status": "可投",
      "first_seen_at": "2026-10-12T14:55:18.252220+00:00",
      "last_seen_at": "2026-10-12T15:28:48.933934+00:00",
      "strategy": "持平",
      "ability_relation": "基本持平",
      "match_score": 90,
      "need_score": 78.1,
      "company_score": 50,
      "overall_score": 84.05,
      "evaluation_reason": "能力关系：基本持平；技能覆盖 4/5；岗位满足度 78；公司档位：未知。",
      "hard_reasons_json": "[]",
      "application_status": "需要人工处理",
      "application_id": 14
    }
  ],
  "recommendations": {
    "items": [
      {
        "job_id": 1,
        "title": "数据产品经理（演示）",
        "company": "示例科技",
        "location": "北京",
        "source": "demo",
        "url": "https://example.com/jobs/data-product",
        "apply_url": "https://example.com/jobs/data-product",
        "is_demo": true,
        "job_status": "可投",
        "decision": {
          "status": "recommend",
          "label": "优先了解",
          "summary": "已知条件与偏好有证据支撑，确认实际待遇和提交资格后可推进"
        },
        "eligibility": {
          "status": "eligible",
          "label": "已知门槛通过",
          "reasons": [],
          "unknowns": [
            "专业及毕业时间要求需要核对",
            "ATS 表单与提交资格尚未验证"
          ]
        },
        "ability": {
          "label": "已知技能较匹配",
          "matched": [
            "Python",
            "SQL",
            "数据分析",
            "需求分析"
          ],
          "missing": [],
          "score": 100,
          "summary": "仅按当前档案与 JD 技能线索核对，不代表面试或录用概率"
        },
        "compensation": {
          "label": "20,000–26,000元/月",
          "status": "known",
          "unit": "month",
          "fields": [
            {
              "key": "fixed_salary",
              "label": "固定薪资",
              "value": "20,000–26,000元/月",
              "status": "known",
              "evidence_ids": [
                "jd:1:5"
              ]
            },
            {
              "key": "salary_months",
              "label": "发薪月数",
              "value": "固定工资 20–26K/月，13 薪",
              "status": "partial",
              "evidence_ids": [
                "jd:1:8"
              ]
            },
            {
              "key": "bonus",
              "label": "奖金与年终奖",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "equity",
              "label": "股票、期权与归属",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "benefits",
              "label": "补贴与福利",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "insurance",
              "label": "五险一金基数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "probation",
              "label": "试用期薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "overtime",
              "label": "加班费或调休",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "signing_bonus",
              "label": "签字费",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "annual_cash",
              "label": "保底年现金收入",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "total_package",
              "label": "预期总包",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "effective_hourly",
              "label": "有效时薪",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            }
          ]
        },
        "experience": [
          {
            "key": "time",
            "label": "时间负担",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：常规工作时间 9:30–18:30，双休",
                "evidence_ids": [
                  "jd:1:6"
                ]
              }
            ],
            "unknowns": [
              "常规上下班时间待确认",
              "周末加班频率待确认",
              "值班、出差与通勤待确认"
            ]
          },
          {
            "key": "pace",
            "label": "工作节奏",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "需求变化与紧急任务比例待确认",
              "交付周期待确认",
              "会议负担与人手配置待确认"
            ]
          },
          {
            "key": "responsibility",
            "label": "职责质量",
            "status": "partial",
            "summary": "有 3 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：负责数据产品需求分析与指标体系，使用 SQL、Python、数据分析协作",
                "evidence_ids": [
                  "jd:1:2"
                ]
              },
              {
                "text": "同作用域社区样本：实际待遇、业务安排、团队变化应当向 HR 和直属负责人核实，此处只演示证据如何被引用与展示。",
                "evidence_ids": [
                  "community:68"
                ]
              },
              {
                "text": "同作用域社区样本：负责人每周安排导师反馈，入职后有培训和内部学习机会。",
                "evidence_ids": [
                  "community:67"
                ]
              }
            ],
            "unknowns": [
              "核心业务与实际职责待确认",
              "决策权与自主空间待确认",
              "重复执行工作占比待确认"
            ]
          },
          {
            "key": "culture",
            "label": "管理文化",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "直属领导与沟通方式待确认",
              "绩效透明度待确认",
              "团队协作与心理安全待确认"
            ]
          },
          {
            "key": "growth",
            "label": "成长性",
            "status": "partial",
            "summary": "有 2 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：提供导师反馈和内部培训",
                "evidence_ids": [
                  "jd:1:7"
                ]
              },
              {
                "text": "同作用域社区样本：负责人每周安排导师反馈，入职后有培训和内部学习机会。",
                "evidence_ids": [
                  "community:67"
                ]
              }
            ],
            "unknowns": [
              "导师与培训待确认",
              "晋升与内部转岗路径待确认",
              "能力可迁移性待确认"
            ]
          },
          {
            "key": "stability",
            "label": "稳定性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "团队流动与业务变化待确认",
              "HC 与用工合同待确认",
              "裁员、续签或转正情况待确认"
            ]
          }
        ],
        "reasons": [
          {
            "text": "学历符合 JD 已披露的本科门槛",
            "evidence_ids": [
              "jd:1:1"
            ]
          },
          {
            "text": "当前档案覆盖 4/4 项 JD 技能线索：Python、SQL、数据分析、需求分析",
            "evidence_ids": [
              "jd:1:2"
            ]
          },
          {
            "text": "披露的固定月薪下限达到你的 18,000 元最低期望",
            "evidence_ids": [
              "jd:1:5"
            ]
          },
          {
            "text": "工作地点 北京 符合你的城市选择",
            "evidence_ids": [
              "jd:1:9"
            ]
          }
        ],
        "risks": [
          {
            "text": "以下体验尚无本岗位可信事实：工作节奏、管理文化、稳定性",
            "evidence_ids": []
          }
        ],
        "questions": [
          "这个岗位所属团队、用工类型、专业和毕业时间的硬要求是什么？",
          "实际平均下班时间、周末加班频率以及值班安排如何？",
          "发薪月数、奖金兑现、五险一金基数和试用期待遇分别是什么？"
        ],
        "evidence": [
          {
            "id": "jd:1:1",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "本科及以上",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          },
          {
            "id": "jd:1:2",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "负责数据产品需求分析与指标体系，使用 SQL、Python、数据分析协作",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "ability",
              "responsibility"
            ]
          },
          {
            "id": "community:68",
            "type": "community",
            "source": "manual",
            "source_label": "手动导入",
            "url": "https://example.com/experience/data-team",
            "title": "示例科技数据平台体验（合成演示，不是真实经历）",
            "date": "2026-09-27T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "实际待遇、业务安排、团队变化应当向 HR 和直属负责人核实，此处只演示证据如何被引用与展示。",
            "relevance": "direct",
            "limitations": [
              "社区个人样本，未经该岗位 HR 确认，不代表团队所有人"
            ],
            "dimensions": [
              "responsibility"
            ],
            "document_id": 1
          },
          {
            "id": "community:67",
            "type": "community",
            "source": "manual",
            "source_label": "手动导入",
            "url": "https://example.com/experience/data-team",
            "title": "示例科技数据平台体验（合成演示，不是真实经历）",
            "date": "2026-09-27T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "负责人每周安排导师反馈，入职后有培训和内部学习机会。",
            "relevance": "direct",
            "limitations": [
              "社区个人样本，未经该岗位 HR 确认，不代表团队所有人"
            ],
            "dimensions": [
              "responsibility",
              "growth"
            ],
            "document_id": 1
          },
          {
            "id": "jd:1:5",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "招聘页薪资字段：下限 20000，上限 26000；单位 month",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "compensation"
            ]
          },
          {
            "id": "jd:1:6",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "常规工作时间 9:30–18:30，双休",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "time"
            ]
          },
          {
            "id": "jd:1:7",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "提供导师反馈和内部培训",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "growth"
            ]
          },
          {
            "id": "jd:1:8",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "固定工资 20–26K/月，13 薪",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "compensation"
            ]
          },
          {
            "id": "jd:1:9",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/data-product",
            "title": "数据产品经理（演示）",
            "date": "2026-10-10T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "工作地点：北京",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          }
        ],
        "evidence_summary": {
          "direct": 9,
          "context": 0,
          "uncertain": 0,
          "documents": 1,
          "experience_direct": 2,
          "label": "有同作用域社区样本",
          "unknown_dimensions": [
            "工作节奏",
            "管理文化",
            "稳定性"
          ]
        },
        "ranking_basis": {
          "preference_supports": 2,
          "experience_direct": 2,
          "unknown_fields": 3
        },
        "default_visible": true
      },
      {
        "job_id": 4,
        "title": "增长数据产品经理（演示）",
        "company": "示例科技",
        "location": "杭州",
        "source": "demo",
        "url": "https://example.com/jobs/growth-product",
        "apply_url": "https://example.com/jobs/growth-product",
        "is_demo": true,
        "job_status": "可投",
        "decision": {
          "status": "recommend",
          "label": "优先了解",
          "summary": "已知条件与偏好有证据支撑，确认实际待遇和提交资格后可推进"
        },
        "eligibility": {
          "status": "eligible",
          "label": "已知门槛通过",
          "reasons": [],
          "unknowns": [
            "专业及毕业时间要求需要核对",
            "ATS 表单与提交资格尚未验证"
          ]
        },
        "ability": {
          "label": "已知技能较匹配",
          "matched": [
            "Python",
            "SQL",
            "数据分析",
            "需求分析"
          ],
          "missing": [
            "增长"
          ],
          "score": 80,
          "summary": "仅按当前档案与 JD 技能线索核对，不代表面试或录用概率"
        },
        "compensation": {
          "label": "19,000–24,000元/月",
          "status": "known",
          "unit": "month",
          "fields": [
            {
              "key": "fixed_salary",
              "label": "固定薪资",
              "value": "19,000–24,000元/月",
              "status": "known",
              "evidence_ids": [
                "jd:4:3"
              ]
            },
            {
              "key": "salary_months",
              "label": "发薪月数",
              "value": "固定工资 19–24K/月，13 薪",
              "status": "partial",
              "evidence_ids": [
                "jd:4:6"
              ]
            },
            {
              "key": "bonus",
              "label": "奖金与年终奖",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "equity",
              "label": "股票、期权与归属",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "benefits",
              "label": "补贴与福利",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "insurance",
              "label": "五险一金基数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "probation",
              "label": "试用期薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "overtime",
              "label": "加班费或调休",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "signing_bonus",
              "label": "签字费",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "annual_cash",
              "label": "保底年现金收入",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "total_package",
              "label": "预期总包",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "effective_hourly",
              "label": "有效时薪",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            }
          ]
        },
        "experience": [
          {
            "key": "time",
            "label": "时间负担",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：常规工作时间 9:30–18:30，周末双休",
                "evidence_ids": [
                  "jd:4:4"
                ]
              }
            ],
            "unknowns": [
              "常规上下班时间待确认",
              "周末加班频率待确认",
              "值班、出差与通勤待确认"
            ]
          },
          {
            "key": "pace",
            "label": "工作节奏",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "需求变化与紧急任务比例待确认",
              "交付周期待确认",
              "会议负担与人手配置待确认"
            ]
          },
          {
            "key": "responsibility",
            "label": "职责质量",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：负责增长数据产品需求分析与指标体系，使用 SQL、Python 和数据分析支持产品迭代",
                "evidence_ids": [
                  "jd:4:2"
                ]
              }
            ],
            "unknowns": [
              "核心业务与实际职责待确认",
              "决策权与自主空间待确认",
              "重复执行工作占比待确认"
            ]
          },
          {
            "key": "culture",
            "label": "管理文化",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "直属领导与沟通方式待确认",
              "绩效透明度待确认",
              "团队协作与心理安全待确认"
            ]
          },
          {
            "key": "growth",
            "label": "成长性",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：提供内部培训和导师反馈",
                "evidence_ids": [
                  "jd:4:5"
                ]
              }
            ],
            "unknowns": [
              "导师与培训待确认",
              "晋升与内部转岗路径待确认",
              "能力可迁移性待确认"
            ]
          },
          {
            "key": "stability",
            "label": "稳定性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "团队流动与业务变化待确认",
              "HC 与用工合同待确认",
              "裁员、续签或转正情况待确认"
            ]
          }
        ],
        "reasons": [
          {
            "text": "学历符合 JD 已披露的本科门槛",
            "evidence_ids": [
              "jd:4:1"
            ]
          },
          {
            "text": "当前档案覆盖 4/5 项 JD 技能线索：Python、SQL、数据分析、需求分析",
            "evidence_ids": [
              "jd:4:2"
            ]
          },
          {
            "text": "披露的固定月薪下限达到你的 18,000 元最低期望",
            "evidence_ids": [
              "jd:4:3"
            ]
          },
          {
            "text": "工作地点 杭州 符合你的城市选择",
            "evidence_ids": [
              "jd:4:7"
            ]
          }
        ],
        "risks": [
          {
            "text": "档案尚未体现：增长；需核实是否必需及可用项目弥补",
            "evidence_ids": [
              "jd:4:2"
            ]
          },
          {
            "text": "以下体验尚无本岗位可信事实：工作节奏、管理文化、稳定性",
            "evidence_ids": []
          }
        ],
        "questions": [
          "这个岗位所属团队、用工类型、专业和毕业时间的硬要求是什么？",
          "实际平均下班时间、周末加班频率以及值班安排如何？",
          "发薪月数、奖金兑现、五险一金基数和试用期待遇分别是什么？"
        ],
        "evidence": [
          {
            "id": "jd:4:1",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "本科及以上",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          },
          {
            "id": "jd:4:2",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "负责增长数据产品需求分析与指标体系，使用 SQL、Python 和数据分析支持产品迭代",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "ability",
              "responsibility"
            ]
          },
          {
            "id": "jd:4:3",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "招聘页薪资字段：下限 19000，上限 24000；单位 month",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "compensation"
            ]
          },
          {
            "id": "jd:4:4",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "常规工作时间 9:30–18:30，周末双休",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "time"
            ]
          },
          {
            "id": "jd:4:5",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "提供内部培训和导师反馈",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "growth"
            ]
          },
          {
            "id": "jd:4:6",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "固定工资 19–24K/月，13 薪",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "compensation"
            ]
          },
          {
            "id": "jd:4:7",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/growth-product",
            "title": "增长数据产品经理（演示）",
            "date": "2026-10-09T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "增长分析",
              "city": "杭州"
            },
            "excerpt": "工作地点：杭州",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          }
        ],
        "evidence_summary": {
          "direct": 7,
          "context": 0,
          "uncertain": 0,
          "documents": 0,
          "experience_direct": 0,
          "label": "仅 JD 与背景，体验待核实",
          "unknown_dimensions": [
            "工作节奏",
            "管理文化",
            "稳定性"
          ]
        },
        "ranking_basis": {
          "preference_supports": 2,
          "experience_direct": 0,
          "unknown_fields": 3
        },
        "default_visible": true
      },
      {
        "job_id": 2,
        "title": "AI 产品经理（演示）",
        "company": "示例云",
        "location": "杭州",
        "source": "demo",
        "url": "https://example.com/jobs/ai-product",
        "apply_url": "https://example.com/jobs/ai-product",
        "is_demo": true,
        "job_status": "可投",
        "decision": {
          "status": "verify",
          "label": "核实后再投",
          "summary": "已有部分匹配线索，关键待遇、门槛或体验仍待确认"
        },
        "eligibility": {
          "status": "eligible",
          "label": "已知门槛通过",
          "reasons": [],
          "unknowns": [
            "专业及毕业时间要求需要核对",
            "ATS 表单与提交资格尚未验证"
          ]
        },
        "ability": {
          "label": "已知技能较匹配",
          "matched": [
            "Python",
            "数据分析",
            "需求分析"
          ],
          "missing": [],
          "score": 100,
          "summary": "仅按当前档案与 JD 技能线索核对，不代表面试或录用概率"
        },
        "compensation": {
          "label": "薪资未披露",
          "status": "unknown",
          "unit": "unknown",
          "fields": [
            {
              "key": "fixed_salary",
              "label": "固定薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "salary_months",
              "label": "发薪月数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "bonus",
              "label": "奖金与年终奖",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "equity",
              "label": "股票、期权与归属",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "benefits",
              "label": "补贴与福利",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "insurance",
              "label": "五险一金基数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "probation",
              "label": "试用期薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "overtime",
              "label": "加班费或调休",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "signing_bonus",
              "label": "签字费",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "annual_cash",
              "label": "保底年现金收入",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "total_package",
              "label": "预期总包",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "effective_hourly",
              "label": "有效时薪",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            }
          ]
        },
        "experience": [
          {
            "key": "time",
            "label": "时间负担",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "常规上下班时间待确认",
              "周末加班频率待确认",
              "值班、出差与通勤待确认"
            ]
          },
          {
            "key": "pace",
            "label": "工作节奏",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "需求变化与紧急任务比例待确认",
              "交付周期待确认",
              "会议负担与人手配置待确认"
            ]
          },
          {
            "key": "responsibility",
            "label": "职责质量",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：本科，负责 AI 产品需求分析及用户反馈分析",
                "evidence_ids": [
                  "jd:2:2"
                ]
              }
            ],
            "unknowns": [
              "核心业务与实际职责待确认",
              "决策权与自主空间待确认",
              "重复执行工作占比待确认"
            ]
          },
          {
            "key": "culture",
            "label": "管理文化",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "直属领导与沟通方式待确认",
              "绩效透明度待确认",
              "团队协作与心理安全待确认"
            ]
          },
          {
            "key": "growth",
            "label": "成长性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "导师与培训待确认",
              "晋升与内部转岗路径待确认",
              "能力可迁移性待确认"
            ]
          },
          {
            "key": "stability",
            "label": "稳定性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "团队流动与业务变化待确认",
              "HC 与用工合同待确认",
              "裁员、续签或转正情况待确认"
            ]
          }
        ],
        "reasons": [
          {
            "text": "学历符合 JD 已披露的本科门槛",
            "evidence_ids": [
              "jd:2:1"
            ]
          },
          {
            "text": "当前档案覆盖 3/3 项 JD 技能线索：Python、数据分析、需求分析",
            "evidence_ids": [
              "jd:2:2",
              "jd:2:3"
            ]
          },
          {
            "text": "工作地点 杭州 符合你的城市选择",
            "evidence_ids": [
              "jd:2:4"
            ]
          }
        ],
        "risks": [
          {
            "text": "月薪口径未确认，不能判断是否达到你的最低薪资期望",
            "evidence_ids": []
          },
          {
            "text": "以下体验尚无本岗位可信事实：时间负担、工作节奏、管理文化、成长性、稳定性",
            "evidence_ids": []
          },
          {
            "text": "薪资未披露，不能估算年现金收入、总包或有效时薪",
            "evidence_ids": []
          }
        ],
        "questions": [
          "这个岗位固定薪资区间及计薪口径是什么？",
          "固定月薪保底能否达到 18,000 元？实习如按日计薪，请确认每月计薪天数。",
          "这个岗位所属团队、用工类型、专业和毕业时间的硬要求是什么？",
          "实际平均下班时间、周末加班频率以及值班安排如何？",
          "发薪月数、奖金兑现、五险一金基数和试用期待遇分别是什么？"
        ],
        "evidence": [
          {
            "id": "jd:2:1",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/ai-product",
            "title": "AI 产品经理（演示）",
            "date": "2026-10-11T15:28:48.929611+00:00",
            "scope": {
              "company": "示例云",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "杭州"
            },
            "excerpt": "本科",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          },
          {
            "id": "jd:2:2",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/ai-product",
            "title": "AI 产品经理（演示）",
            "date": "2026-10-11T15:28:48.929611+00:00",
            "scope": {
              "company": "示例云",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "杭州"
            },
            "excerpt": "本科，负责 AI 产品需求分析及用户反馈分析",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "ability",
              "responsibility"
            ]
          },
          {
            "id": "jd:2:3",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/ai-product",
            "title": "AI 产品经理（演示）",
            "date": "2026-10-11T15:28:48.929611+00:00",
            "scope": {
              "company": "示例云",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "杭州"
            },
            "excerpt": "熟悉 Python 与数据分析，推动产品迭代",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "ability"
            ]
          },
          {
            "id": "jd:2:4",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/ai-product",
            "title": "AI 产品经理（演示）",
            "date": "2026-10-11T15:28:48.929611+00:00",
            "scope": {
              "company": "示例云",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "杭州"
            },
            "excerpt": "工作地点：杭州",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          }
        ],
        "evidence_summary": {
          "direct": 4,
          "context": 0,
          "uncertain": 0,
          "documents": 0,
          "experience_direct": 0,
          "label": "仅 JD 与背景，体验待核实",
          "unknown_dimensions": [
            "时间负担",
            "工作节奏",
            "管理文化",
            "成长性",
            "稳定性"
          ]
        },
        "ranking_basis": {
          "preference_supports": 1,
          "experience_direct": 0,
          "unknown_fields": 6
        },
        "default_visible": true
      },
      {
        "job_id": 3,
        "title": "算法产品经理（演示·门槛不符）",
        "company": "示例科技",
        "location": "北京",
        "source": "demo",
        "url": "https://example.com/jobs/algorithm-product",
        "apply_url": "https://example.com/jobs/algorithm-product",
        "is_demo": true,
        "job_status": "可投",
        "decision": {
          "status": "not_recommended",
          "label": "暂不推荐",
          "summary": "存在明确门槛或岗位池过滤状态，保留原因供核对"
        },
        "eligibility": {
          "status": "blocked",
          "label": "已知条件不通过",
          "reasons": [
            "学历硬条件不满足：要求硕士，当前档案为本科"
          ],
          "unknowns": [
            "专业及毕业时间要求需要核对",
            "ATS 表单与提交资格尚未验证"
          ]
        },
        "ability": {
          "label": "已知技能较匹配",
          "matched": [
            "Python",
            "需求分析"
          ],
          "missing": [],
          "score": 100,
          "summary": "仅按当前档案与 JD 技能线索核对，不代表面试或录用概率"
        },
        "compensation": {
          "label": "薪资未披露",
          "status": "unknown",
          "unit": "unknown",
          "fields": [
            {
              "key": "fixed_salary",
              "label": "固定薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "salary_months",
              "label": "发薪月数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "bonus",
              "label": "奖金与年终奖",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "equity",
              "label": "股票、期权与归属",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "benefits",
              "label": "补贴与福利",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "insurance",
              "label": "五险一金基数",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "probation",
              "label": "试用期薪资",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "overtime",
              "label": "加班费或调休",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "signing_bonus",
              "label": "签字费",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "annual_cash",
              "label": "保底年现金收入",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "total_package",
              "label": "预期总包",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            },
            {
              "key": "effective_hourly",
              "label": "有效时薪",
              "value": "未披露",
              "status": "unknown",
              "evidence_ids": []
            }
          ]
        },
        "experience": [
          {
            "key": "time",
            "label": "时间负担",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "常规上下班时间待确认",
              "周末加班频率待确认",
              "值班、出差与通勤待确认"
            ]
          },
          {
            "key": "pace",
            "label": "工作节奏",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "需求变化与紧急任务比例待确认",
              "交付周期待确认",
              "会议负担与人手配置待确认"
            ]
          },
          {
            "key": "responsibility",
            "label": "职责质量",
            "status": "partial",
            "summary": "有 1 条披露/样本，实际情况待确认",
            "facts": [
              {
                "text": "JD 披露：硕士及以上学历，负责需求分析，熟悉 Python",
                "evidence_ids": [
                  "jd:3:2"
                ]
              }
            ],
            "unknowns": [
              "核心业务与实际职责待确认",
              "决策权与自主空间待确认",
              "重复执行工作占比待确认"
            ]
          },
          {
            "key": "culture",
            "label": "管理文化",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "直属领导与沟通方式待确认",
              "绩效透明度待确认",
              "团队协作与心理安全待确认"
            ]
          },
          {
            "key": "growth",
            "label": "成长性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "导师与培训待确认",
              "晋升与内部转岗路径待确认",
              "能力可迁移性待确认"
            ]
          },
          {
            "key": "stability",
            "label": "稳定性",
            "status": "unknown",
            "summary": "暂无本岗位可信事实",
            "facts": [],
            "unknowns": [
              "团队流动与业务变化待确认",
              "HC 与用工合同待确认",
              "裁员、续签或转正情况待确认"
            ]
          }
        ],
        "reasons": [
          {
            "text": "当前档案覆盖 2/2 项 JD 技能线索：Python、需求分析",
            "evidence_ids": [
              "jd:3:2"
            ]
          },
          {
            "text": "工作地点 北京 符合你的城市选择",
            "evidence_ids": [
              "jd:3:5"
            ]
          }
        ],
        "risks": [
          {
            "text": "学历硬条件不满足：要求硕士，当前档案为本科",
            "evidence_ids": [
              "jd:3:1"
            ]
          },
          {
            "text": "月薪口径未确认，不能判断是否达到你的最低薪资期望",
            "evidence_ids": []
          },
          {
            "text": "以下体验尚无本岗位可信事实：时间负担、工作节奏、管理文化、成长性、稳定性",
            "evidence_ids": []
          },
          {
            "text": "薪资未披露，不能估算年现金收入、总包或有效时薪",
            "evidence_ids": []
          }
        ],
        "questions": [
          "这个岗位固定薪资区间及计薪口径是什么？",
          "固定月薪保底能否达到 18,000 元？实习如按日计薪，请确认每月计薪天数。",
          "这个岗位所属团队、用工类型、专业和毕业时间的硬要求是什么？",
          "实际平均下班时间、周末加班频率以及值班安排如何？",
          "发薪月数、奖金兑现、五险一金基数和试用期待遇分别是什么？"
        ],
        "evidence": [
          {
            "id": "jd:3:1",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/algorithm-product",
            "title": "算法产品经理（演示·门槛不符）",
            "date": "2026-10-12T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "北京"
            },
            "excerpt": "硕士及以上",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          },
          {
            "id": "jd:3:2",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/algorithm-product",
            "title": "算法产品经理（演示·门槛不符）",
            "date": "2026-10-12T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "北京"
            },
            "excerpt": "硕士及以上学历，负责需求分析，熟悉 Python",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "ability",
              "responsibility"
            ]
          },
          {
            "id": "community:68",
            "type": "community",
            "source": "manual",
            "source_label": "手动导入",
            "url": "https://example.com/experience/data-team",
            "title": "示例科技数据平台体验（合成演示，不是真实经历）",
            "date": "2026-09-27T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "实际待遇、业务安排、团队变化应当向 HR 和直属负责人核实，此处只演示证据如何被引用与展示。",
            "relevance": "context",
            "limitations": [
              "社区个人样本，未经该岗位 HR 确认，不代表团队所有人",
              "团队或城市未完整对齐，仅作背景，不能当作本岗位事实"
            ],
            "dimensions": [
              "responsibility"
            ],
            "document_id": 1
          },
          {
            "id": "community:67",
            "type": "community",
            "source": "manual",
            "source_label": "手动导入",
            "url": "https://example.com/experience/data-team",
            "title": "示例科技数据平台体验（合成演示，不是真实经历）",
            "date": "2026-09-27T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "数据平台",
              "city": "北京"
            },
            "excerpt": "负责人每周安排导师反馈，入职后有培训和内部学习机会。",
            "relevance": "context",
            "limitations": [
              "社区个人样本，未经该岗位 HR 确认，不代表团队所有人",
              "团队或城市未完整对齐，仅作背景，不能当作本岗位事实"
            ],
            "dimensions": [
              "responsibility",
              "growth"
            ],
            "document_id": 1
          },
          {
            "id": "jd:3:5",
            "type": "jd",
            "source": "demo",
            "source_label": "招聘页 / JD",
            "inference": false,
            "url": "https://example.com/jobs/algorithm-product",
            "title": "算法产品经理（演示·门槛不符）",
            "date": "2026-10-12T15:28:48.929611+00:00",
            "scope": {
              "company": "示例科技",
              "role_family": "product",
              "employment_type": "full_time",
              "business_unit": "",
              "city": "北京"
            },
            "excerpt": "工作地点：北京",
            "relevance": "direct",
            "limitations": [
              "招聘页披露，实际执行情况仍需确认"
            ],
            "dimensions": [
              "eligibility"
            ]
          }
        ],
        "evidence_summary": {
          "direct": 3,
          "context": 2,
          "uncertain": 0,
          "documents": 1,
          "experience_direct": 0,
          "label": "仅 JD 与背景，体验待核实",
          "unknown_dimensions": [
            "时间负担",
            "工作节奏",
            "管理文化",
            "成长性",
            "稳定性"
          ]
        },
        "ranking_basis": {
          "preference_supports": 1,
          "experience_direct": 0,
          "unknown_fields": 6
        },
        "default_visible": false
      }
    ],
    "summary": {
      "total": 4,
      "recommended": 2,
      "verify": 1,
      "excluded": 1,
      "evidence_supported": 1
    },
    "generated_at": "2026-10-12T15:28:49.039293+00:00",
    "method": "local_rules",
    "policy": {
      "read_only": true,
      "paid_model_called": false,
      "unknown_is_not_positive": true,
      "context_is_not_job_fact": true,
      "ranking_uses_company_prestige": false
    }
  },
  "applications": [
    {
      "id": 14,
      "job_id": 4,
      "channel": "demo",
      "status": "需要人工处理",
      "greeting": null,
      "external_id": null,
      "evidence": null,
      "error": null,
      "created_at": "2026-10-12T15:28:49.002372+00:00",
      "updated_at": "2026-10-12T15:28:49.002372+00:00",
      "recruitment_stage": "面试",
      "progress_note": "演示：周五一面，确认团队工作时长",
      "progress_source": "manual",
      "progress_updated_at": "2026-10-12T15:28:49.002372+00:00",
      "title": "增长数据产品经理（演示）",
      "company": "示例科技",
      "location": "杭州",
      "url": "https://example.com/jobs/growth-product",
      "apply_url": null,
      "source": "demo",
      "strategy": "持平",
      "overall_score": 84.05
    },
    {
      "id": 13,
      "job_id": 1,
      "channel": "demo",
      "status": "需要人工处理",
      "greeting": null,
      "external_id": null,
      "evidence": null,
      "error": null,
      "created_at": "2026-10-12T15:28:48.994012+00:00",
      "updated_at": "2026-10-12T15:28:48.994012+00:00",
      "recruitment_stage": "已投递",
      "progress_note": "演示：已在官网提交，等待后续沟通",
      "progress_source": "manual",
      "progress_updated_at": "2026-10-12T15:28:48.994012+00:00",
      "title": "数据产品经理（演示）",
      "company": "示例科技",
      "location": "北京",
      "url": "https://example.com/jobs/data-product",
      "apply_url": null,
      "source": "demo",
      "strategy": "持平",
      "overall_score": 89.45
    },
    {
      "id": 12,
      "job_id": 2,
      "channel": "demo",
      "status": "已发开场白",
      "greeting": "合成演示开场白，无真实发送",
      "external_id": "synthetic-thread-001",
      "evidence": "合成演示回执，无真实平台操作",
      "error": null,
      "created_at": "2026-10-12T15:28:48.951334+00:00",
      "updated_at": "2026-10-12T15:28:48.955917+00:00",
      "recruitment_stage": "沟通中",
      "progress_note": "",
      "progress_source": "legacy_status",
      "progress_updated_at": "2026-10-12T15:28:48.955917+00:00",
      "title": "AI 产品经理（演示）",
      "company": "示例云",
      "location": "杭州",
      "url": "https://example.com/jobs/ai-product",
      "apply_url": null,
      "source": "demo",
      "strategy": "持平",
      "overall_score": 86.47
    }
  ],
  "events": [
    {
      "id": 21,
      "entity_type": "application",
      "entity_id": "14",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:28:49.002372+00:00"
    },
    {
      "id": 20,
      "entity_type": "application",
      "entity_id": "13",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:28:48.994012+00:00"
    },
    {
      "id": 19,
      "entity_type": "application",
      "entity_id": "12",
      "event_type": "已发开场白",
      "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
      "occurred_at": "2026-10-12T15:28:48.960676+00:00"
    },
    {
      "id": 18,
      "entity_type": "application",
      "entity_id": "11",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:17:08.633244+00:00"
    },
    {
      "id": 17,
      "entity_type": "application",
      "entity_id": "10",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:17:08.626268+00:00"
    },
    {
      "id": 16,
      "entity_type": "application",
      "entity_id": "9",
      "event_type": "已发开场白",
      "payload_json": "{\"evidence\": \"合成演示回执，无真实平台操作\", \"error\": null}",
      "occurred_at": "2026-10-12T15:17:08.592166+00:00"
    },
    {
      "id": 15,
      "entity_type": "application",
      "entity_id": "8",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"面试\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:16:04.487679+00:00"
    },
    {
      "id": 14,
      "entity_type": "application",
      "entity_id": "7",
      "event_type": "manual_application_recorded",
      "payload_json": "{\"stage\": \"已投递\", \"source\": \"manual\", \"has_note\": true}",
      "occurred_at": "2026-10-12T15:16:04.480136+00:00"
    },
    {
      "id": 13,
      "entity_type": "job",
      "entity_id": "1",
      "event_type": "evaluated",
      "payload_json": "{\"job_id\": 1, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"SQL\", \"数据分析\", \"需求分析\"], \"missing_capabilities\": [], \"hard_reasons\": [], \"match_score\": 100.0, \"need_score\": 78.9, \"company_score\": 50.0, \"overall_score\": 89.45, \"confidence\": 0.87, \"reason\": \"能力关系：基本持平；技能覆盖 4/4；岗位满足度 79；公司档位：未知。\"}",
      "occurred_at": "2026-10-12T15:16:04.471208+00:00"
    },
    {
      "id": 12,
      "entity_type": "job",
      "entity_id": "2",
      "event_type": "evaluated",
      "payload_json": "{\"job_id\": 2, \"hard_pass\": true, \"strategy\": \"持平\", \"ability_relation\": \"基本持平\", \"matched_capabilities\": [\"Python\", \"数据分析\", \"需求分析\"], \"missing_capabilities\": [], \"hard_reasons\": [], \"match_score\": 100.0, \"need_score\": 72.95, \"company_score\": 50.0, \"overall_score\": 86.47, \"confidence\": 0.79, \"reason\": \"能力关系：基本持平；技能覆盖 3/3；岗位满足度 73；公司档位：未知。\"}",
      "occurred_at": "2026-10-12T15:16:04.457328+00:00"
    }
  ],
  "knowledgeStatus": {
    "enabled": true,
    "sources": [
      "nowcoder",
      "xiaohongshu"
    ],
    "embedding_provider": "hashing-v1",
    "raw_text_retained": false,
    "documents": {
      "accepted": 1
    },
    "chunks": 4,
    "scopes": [
      {
        "company": "示例科技",
        "role_family": "product",
        "employment_type": "full_time",
        "documents": 1
      }
    ]
  },
  "knowledgeDocuments": [
    {
      "id": 1,
      "source": "manual",
      "source_url": "https://example.com/experience/data-team",
      "url_hash": "003896f4c0d59715e3e6f5fe63df689b0cd141b22edfb7c9754ffb6c4c0134a0",
      "title": "示例科技数据平台体验（合成演示，不是真实经历）",
      "company": "示例科技",
      "role_family": "product",
      "employment_type": "full_time",
      "business_unit": "数据平台",
      "city": "北京",
      "seniority": "",
      "published_at": "2026-09-27T15:28:48.929611+00:00",
      "collected_at": "2026-10-12T15:28:48.967967+00:00",
      "collection_method": "manual_import",
      "source_status": "imported",
      "policy_status": "accepted",
      "quality_score": 0.873,
      "content_hash": "dc5788446e267df06e7d5263072b0fc8278d4853ffcd8e2dcc398270e9b8b008",
      "author_hash": "",
      "duplicate_of_document_id": null,
      "chunk_count": 4,
      "policy_reasons": [],
      "topics": [
        "duties",
        "workload",
        "culture",
        "growth"
      ],
      "metadata": {}
    }
  ],
  "resume": {
    "configured": true,
    "available": true,
    "filename": "示例简历.pdf",
    "path": "演示简历（仅用于交互，不含真实文件）",
    "profile_source": "manual",
    "text_available": false
  },
  "channels": [
    {
      "id": "demo",
      "name": "合成演示岗位库",
      "type": "official",
      "enabled": true,
      "ready": true,
      "keywords": [
        "产品经理"
      ],
      "strategy": "json_api",
      "url": "https://example.com",
      "health": "api_fetched",
      "health_label": "演示已就绪",
      "missing": [],
      "capabilities": {
        "discovery": "available",
        "autofill_status": "not_planned"
      }
    }
  ]
};
