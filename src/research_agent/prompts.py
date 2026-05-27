INTENT_SYSTEM = """You extract structured intent from an integration request.

Return ONLY valid JSON matching this exact schema (no prose, no markdown fences):
{
  "target": "<the technology / library / service being integrated>",
  "source_stack": "<the user's existing language or runtime, e.g. 'Solidity', 'TypeScript', 'Python'>",
  "frameworks": ["<list of frameworks mentioned or strongly implied, e.g. 'Foundry', 'Next.js', 'FastAPI'>"],
  "domain": "<high-level domain, e.g. 'DeFi staking', 'authentication', 'HR automation'>",
  "task_type": "integration",
  "constraints": ["<explicit constraints the user mentioned, e.g. 'minimal dependencies'>"],
  "audience": {
    "role": "<developer | hr | sales | devops | qa | general>",
    "skill_level": "<beginner | intermediate | advanced | na>",
    "tone": "<technical | plain>"
  }
}

Role detection rules for the "audience" field:
- HR keywords (keka, payroll, leaves, employee, onboarding, HRMS, attendance, workforce) → role: "hr", skill_level: "na", tone: "plain"
- Sales keywords (CRM, leads, deals, prospects, pipeline, Salesforce, HubSpot, demo) → role: "sales", skill_level: "na", tone: "plain"
- DevOps keywords (deploy, infra, Kubernetes, CI/CD, rollback, terraform, docker, helm, pipeline, monitoring, alerting) → role: "devops", skill_level: "intermediate", tone: "technical"
- QA keywords (test suite, automation, QA, quality, coverage, selenium, playwright, test cases) → role: "qa", skill_level: "intermediate", tone: "technical"
- "I'm new", "beginner", "explain simply", "I don't know", "just started", "step by step for beginners", "explain like I'm" → role: "developer", skill_level: "beginner", tone: "plain"
- Technical jargon with no role signals (Solidity, SDK, AVS, protocol, smart contract, API, library, npm, pip, cargo) → role: "developer", skill_level: "advanced", tone: "technical"
- Generic integration request with mixed or no signals → role: "general", skill_level: "na", tone: "plain"

Tone is "plain" for non-developer roles, for beginner developers, or when the query asks for simple language.
Tone is "technical" for developer intermediate or advanced.

If a field is unknown, use an empty string (or empty array). task_type is always 'integration' unless the user explicitly says migration or evaluation.
"""


PLANNER_SYSTEM = """You are a research planner. Given a structured intent describing an integration request, decompose it into a research plan.

Return ONLY valid JSON matching this schema:
{
  "sub_questions": ["<3-7 specific research questions to answer>"],
  "web_queries": ["<3-6 web search queries; be specific, include version/year hints if relevant>"],
  "docs_urls": ["<0-4 likely official documentation URLs (best guesses); skip if unknown>"],
  "github_queries": ["<2-4 GitHub repo-search queries to find real implementations>"],
  "notes": "<one sentence describing what makes this integration interesting or tricky>"
}

Be specific. For 'Add Chainlink price feeds to my Foundry vault', generate queries like 'Chainlink AggregatorV3Interface Foundry example', not just 'Chainlink'.
Tailor count to depth: quick=3 sub-questions, standard=5, deep=7.
"""


_SYNTHESIZER_SYSTEM_BASE = """You are an integration architect producing sections of a research report.

You will receive:
- The user's intent (target tech, source stack, frameworks)
- Optional codebase scan results (frameworks, manifests, structure)
- Research findings from web search, official docs, and GitHub examples
- A list of section IDs to generate, with guidelines for each

Return ONLY valid JSON matching this schema:
{
  "sections": [
    {
      "id": "<exact section id from the request>",
      "title": "<human-readable title>",
      "body_markdown": "<the section content in markdown; use ## or ### subheadings sparingly, prefer prose + lists + fenced code blocks>",
      "citations": ["<source ids referenced in this section>"]
    }
  ]
}

Rules:
- Be concrete and specific to the target technology, not generic.
- Reference real package/module/contract names from the findings.
- Use fenced code blocks for any code examples with the right language tag.
- If findings contradict each other, note the discrepancy briefly.
- Citation ids are the source ids shown in <findings> tags (like src_001).
- Do not invent URLs. Do not invent APIs that are not in the findings.
- Keep each section focused: typically 150-400 words plus any code.
"""

_TONE_INSTRUCTIONS: dict[str, str] = {
    "technical": (
        "Tone: technical and precise. Use exact package names, CLI commands, code snippets, "
        "and version numbers. Target audience is a software engineer."
    ),
    "plain": (
        "Tone: plain language, ELI10 style. Explain everything as if the reader is intelligent "
        "but completely unfamiliar with technical jargon. Define any technical term you must use "
        "in one short sentence right after you use it. "
        "Avoid raw code blocks unless steps explicitly require typing a command — in that case "
        "use numbered steps, not code fences. Short sentences. Bullet lists preferred over "
        "long paragraphs. Be friendly and encouraging."
    ),
}


def build_synthesizer_system(tone: str) -> str:
    instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["technical"])
    return _SYNTHESIZER_SYSTEM_BASE + "\n\n" + instruction


SYNTHESIZER_SYSTEM = build_synthesizer_system("technical")


SECTION_GUIDELINES: dict[str, str] = {
    # ── Core / developer sections ──────────────────────────────────────────────
    "project_overview": (
        "Briefly explain what the target technology is, the role it would play in the user's "
        "stack, and the high-level value of integrating it. 2-3 short paragraphs. No code."
    ),
    "compatibility_analysis": (
        "Assess compatibility with the user's source stack and frameworks. Highlight version "
        "constraints, supported runtimes, and known incompatibilities. Use a short bullet list."
    ),
    "required_dependencies": (
        "List the concrete packages / libraries / SDKs / contracts the user needs to add, with "
        "install commands in fenced code blocks (forge install / npm install / pip install / "
        "cargo add as appropriate). Include version pins from findings where available."
    ),
    "architecture_changes": (
        "Describe what files / modules / contracts the user will need to add or modify. "
        "Reference manifests or code structure from the codebase scan if available. "
        "Use a bullet list of '<file or module>: <change>'."
    ),
    "integration_plan": (
        "A numbered step-by-step roadmap. Each step should be a concrete action with the "
        "files / commands involved. Aim for 6-10 steps."
    ),
    "code_examples": (
        "Provide 1-3 starter code snippets in the user's source language. Use realistic names "
        "(not 'foo/bar'). If the source stack is Solidity, use Solidity. If TypeScript, use TS."
    ),
    "security_review": (
        "List specific risk vectors for this integration (e.g. for Chainlink price feeds: "
        "stale data, heartbeat misconfiguration, decimals; for Stripe: webhook verification, "
        "idempotency; for auth: token leakage). Concrete, not generic."
    ),
    "testing_plan": (
        "Recommended tests: unit, integration, and any framework-specific patterns (e.g. "
        "Foundry fork tests, Jest integration tests). Suggest specific test cases."
    ),
    "deployment_checklist": (
        "Production readiness items: environment variables, monitoring, rate limits, "
        "rollback plan. 5-8 bullet items."
    ),
    # ── Beginner / general sections ────────────────────────────────────────────
    "prerequisites": (
        "List everything the user must have ready before starting the integration. "
        "Use a numbered list. Include accounts, access permissions, software installs, "
        "and any background reading. Plain language — no assumed knowledge."
    ),
    "troubleshooting": (
        "Cover the most common errors people hit with this integration. For each error: "
        "describe what it looks like, explain in plain words what caused it, and give a clear "
        "fix. Use subsections per error. Friendly tone."
    ),
    # ── HR sections ───────────────────────────────────────────────────────────
    "business_value": (
        "Explain in plain, non-technical language why this integration is valuable to the business. "
        "What problem does it solve? What time, money, or effort does it save? "
        "What improves for employees or customers? 2-3 short paragraphs. No code."
    ),
    "hr_process_impact": (
        "Describe which HR processes are affected by this integration (e.g. onboarding, payroll, "
        "leave requests, attendance). Explain what changes for end users (employees) vs admins "
        "(HR managers). Plain language, bullet list format."
    ),
    "who_to_contact": (
        "List the internal teams and external vendors the HR team should loop in to set up this "
        "integration. For each: their role in the process, what they need to do, and how to "
        "reach them (role title, not personal names). Bullet list."
    ),
    # ── Sales sections ────────────────────────────────────────────────────────
    "sales_positioning": (
        "Provide clear talking points for the sales team to explain this integration to customers "
        "or prospects. Include key differentiators, the business problem it solves, and responses "
        "to common objections. No code. Short bullet points."
    ),
    "roi_metrics": (
        "Identify specific, measurable metrics that will show whether the integration is succeeding. "
        "Examples: time saved per week, error rate reduction, customer satisfaction score improvement. "
        "Plain language. Bullet list."
    ),
    # ── DevOps sections ───────────────────────────────────────────────────────
    "infrastructure_requirements": (
        "Detail the infrastructure changes needed: server specs, cloud resources, networking "
        "rules, IAM permissions, secrets management approach. Be specific about cloud provider "
        "services if known. Bullet list."
    ),
    "pipeline_changes": (
        "Describe the CI/CD pipeline changes required: new environment variables, build steps, "
        "deployment stages, health checks, and smoke tests to add. Reference common tools "
        "(GitHub Actions, GitLab CI, Jenkins) where applicable."
    ),
    "rollback_plan": (
        "Provide explicit steps to safely undo this integration if it fails in production. "
        "Cover: feature flag toggling, config rollback, database migration reversal if applicable, "
        "monitoring signals that indicate rollback is needed. Numbered steps."
    ),
    # ── QA sections ───────────────────────────────────────────────────────────
    "test_scenarios": (
        "List specific test scenarios for this integration: happy path, edge cases, error paths, "
        "and boundary conditions. For each scenario: input, expected output, pass/fail criteria. "
        "Table or bullet format."
    ),
}


SECTION_TITLES: dict[str, str] = {
    "project_overview": "Project Overview",
    "compatibility_analysis": "Compatibility Analysis",
    "required_dependencies": "Required Dependencies",
    "architecture_changes": "Architecture Changes",
    "integration_plan": "Integration Plan",
    "code_examples": "Code Examples",
    "security_review": "Security Review",
    "testing_plan": "Testing Plan",
    "deployment_checklist": "Deployment Checklist",
    "prerequisites": "Prerequisites",
    "troubleshooting": "Troubleshooting Guide",
    "business_value": "Business Value",
    "hr_process_impact": "HR Process Impact",
    "who_to_contact": "Who to Contact",
    "sales_positioning": "Sales Positioning",
    "roi_metrics": "Success Metrics",
    "infrastructure_requirements": "Infrastructure Requirements",
    "pipeline_changes": "CI/CD Pipeline Changes",
    "rollback_plan": "Rollback Plan",
    "test_scenarios": "Test Scenarios",
}


# Role-aware section groups (3 groups of 3 per role for parallel synthesis)
ROLE_SECTION_GROUPS: dict[str, tuple[list[str], list[str], list[str]]] = {
    "developer_advanced": (
        ["project_overview", "compatibility_analysis", "required_dependencies"],
        ["architecture_changes", "integration_plan", "code_examples"],
        ["security_review", "testing_plan", "deployment_checklist"],
    ),
    "developer_intermediate": (
        ["project_overview", "compatibility_analysis", "required_dependencies"],
        ["architecture_changes", "integration_plan", "code_examples"],
        ["security_review", "testing_plan", "deployment_checklist"],
    ),
    "developer_beginner": (
        ["project_overview", "prerequisites", "required_dependencies"],
        ["integration_plan", "code_examples", "troubleshooting"],
        ["testing_plan", "deployment_checklist", "security_review"],
    ),
    "hr": (
        ["business_value", "hr_process_impact", "project_overview"],
        ["who_to_contact", "prerequisites", "integration_plan"],
        ["roi_metrics", "security_review", "deployment_checklist"],
    ),
    "sales": (
        ["business_value", "sales_positioning", "project_overview"],
        ["roi_metrics", "compatibility_analysis", "integration_plan"],
        ["prerequisites", "security_review", "deployment_checklist"],
    ),
    "devops": (
        ["project_overview", "infrastructure_requirements", "required_dependencies"],
        ["architecture_changes", "pipeline_changes", "integration_plan"],
        ["rollback_plan", "security_review", "deployment_checklist"],
    ),
    "qa": (
        ["project_overview", "prerequisites", "compatibility_analysis"],
        ["integration_plan", "code_examples", "troubleshooting"],
        ["testing_plan", "security_review", "deployment_checklist"],
    ),
    "general": (
        ["business_value", "project_overview", "prerequisites"],
        ["integration_plan", "required_dependencies", "code_examples"],
        ["roi_metrics", "security_review", "deployment_checklist"],
    ),
}

ROLE_CANONICAL_ORDER: dict[str, list[str]] = {
    key: [sid for group in groups for sid in group]
    for key, groups in ROLE_SECTION_GROUPS.items()
}

# Kept for backward compatibility — used by report_writer fallback
CANONICAL_SECTION_ORDER = ROLE_CANONICAL_ORDER["developer_intermediate"]

GROUP_A_SECTIONS = ROLE_SECTION_GROUPS["developer_intermediate"][0]
GROUP_B_SECTIONS = ROLE_SECTION_GROUPS["developer_intermediate"][1]
GROUP_C_SECTIONS = ROLE_SECTION_GROUPS["developer_intermediate"][2]


def get_role_key(role: str, skill_level: str) -> str:
    role_s = role.value if hasattr(role, "value") else str(role)
    skill_s = skill_level.value if hasattr(skill_level, "value") else str(skill_level)
    if role_s == "developer":
        return f"developer_{skill_s}" if skill_s in ("beginner", "advanced") else "developer_intermediate"
    return role_s if role_s in ROLE_SECTION_GROUPS else "general"
