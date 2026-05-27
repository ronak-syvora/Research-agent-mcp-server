INTENT_SYSTEM = """You extract structured intent from a developer's integration request.

Return ONLY valid JSON matching this exact schema (no prose, no markdown fences):
{
  "target": "<the technology / library / service being integrated>",
  "source_stack": "<the user's existing language or runtime, e.g. 'Solidity', 'TypeScript', 'Python'>",
  "frameworks": ["<list of frameworks mentioned or strongly implied, e.g. 'Foundry', 'Next.js', 'FastAPI'>"],
  "domain": "<high-level domain, e.g. 'DeFi staking', 'authentication', 'observability'>",
  "task_type": "integration",
  "constraints": ["<explicit constraints the user mentioned, e.g. 'minimal dependencies'>"]
}

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


SYNTHESIZER_SYSTEM = """You are an integration architect producing sections of a technical research report.

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


SECTION_GUIDELINES: dict[str, str] = {
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
}


GROUP_A_SECTIONS = ["project_overview", "compatibility_analysis", "required_dependencies"]
GROUP_B_SECTIONS = ["architecture_changes", "integration_plan", "code_examples"]
GROUP_C_SECTIONS = ["security_review", "testing_plan", "deployment_checklist"]


CANONICAL_SECTION_ORDER = [
    "project_overview",
    "compatibility_analysis",
    "required_dependencies",
    "architecture_changes",
    "integration_plan",
    "code_examples",
    "security_review",
    "testing_plan",
    "deployment_checklist",
]


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
}
