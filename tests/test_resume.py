from __future__ import annotations

import unittest

from job_agent.resume import infer_resume_profile


class ResumeProfileTests(unittest.TestCase):
    def test_short_latin_skills_use_token_boundaries(self) -> None:
        profile = infer_resume_profile("Built JavaScript services for Google products; 熟悉需求分析")
        self.assertIn("JavaScript", profile.skills)
        self.assertIn("需求分析", profile.skills)
        self.assertNotIn("Java", profile.skills)
        self.assertNotIn("Go", profile.skills)


if __name__ == "__main__":
    unittest.main()
