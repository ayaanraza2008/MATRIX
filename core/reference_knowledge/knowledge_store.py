"""MATRIX Reference Knowledge Base.
Extracts, structures, and indexes actionable tools, prompts, tutorials, and APIs
from the 6 reference repositories:
1. jixserver/free-for-dev
2. mnfst/awesome-free-llm-apis
3. codecrafters-io/build-your-own-x
4. SailikNanda/ERA-System-Prompts
5. ai-boost/awesome-harness-engineering
6. public-apis/public-apis
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from config.logging_config import get_logger

logger = get_logger("core.reference_knowledge")


class KnowledgeEntry(BaseModel):
    entry_id: str
    source_repo: str
    category: str
    title: str
    description: str
    tags: List[str] = Field(default_factory=list)
    content: Dict[str, Any] = Field(default_factory=dict)
    link: Optional[str] = None


class ReferenceKnowledgeStore:
    """In-memory structured repository knowledge index."""

    def __init__(self):
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._build_knowledge_base()

    def _build_knowledge_base(self):
        """Populate verified domain knowledge from the 6 reference catalogs."""
        
        # 1. free-for-dev (Developer free tiers for SaaS, PaaS, IaaS)
        free_dev_items = [
            ("dev_hosting_vercel", "Hosting & PaaS", "Vercel Free Tier", "Deploy modern web applications, serverless functions with automatic SSL and global CDN.", ["hosting", "web", "serverless", "frontend"], "https://vercel.com"),
            ("dev_hosting_render", "Hosting & PaaS", "Render Cloud Free", "Free tier for web services, static sites, PostgreSQL database, and Redis cache.", ["hosting", "backend", "database", "redis"], "https://render.com"),
            ("dev_db_supabase", "Databases & BaaS", "Supabase Free Tier", "Hosted PostgreSQL database with instant REST/GraphQL APIs, Auth, and Storage.", ["postgres", "database", "auth", "storage"], "https://supabase.com"),
            ("dev_db_neon", "Databases & BaaS", "Neon Serverless Postgres", "Serverless PostgreSQL with instant autoscaling, branching, and generous free compute.", ["postgres", "serverless", "sql"], "https://neon.tech"),
            ("dev_monitoring_sentry", "Monitoring & Logs", "Sentry Developer", "Application performance monitoring, crash diagnostics, and error tracking.", ["monitoring", "error_tracking", "apm"], "https://sentry.io"),
            ("dev_ci_github_actions", "CI/CD & DevOps", "GitHub Actions Free", "2,000 monthly automation minutes for Linux, macOS, and Windows runners.", ["cicd", "devops", "automation"], "https://github.com/features/actions"),
            ("dev_dns_cloudflare", "Network & CDN", "Cloudflare DNS & CDN", "Fast authoritative DNS, DDoS mitigation, free SSL/TLS, and global content caching.", ["dns", "cdn", "security", "ssl"], "https://cloudflare.com")
        ]
        for eid, cat, title, desc, tags, link in free_dev_items:
            self._add_entry(eid, "jixserver/free-for-dev", cat, title, desc, tags, {"tier": "Free", "url": link}, link)

        # 2. awesome-free-llm-apis (Free public LLM providers)
        free_llm_items = [
            ("llm_groq_free", "Free LLM Providers", "Groq Cloud LPU", "Ultra-fast inference on Llama 3.3 70B, Mixtral, and Gemma models via OpenAI-compatible API.", ["groq", "llama3", "fast_inference", "free_api"], "https://groq.com"),
            ("llm_gemini_free", "Free LLM Providers", "Google Gemini Free Tier", "Free access to Gemini 1.5 Flash and Gemini 1.5 Pro up to 15 RPM.", ["gemini", "google", "multimodal", "free_api"], "https://aistudio.google.com"),
            ("llm_together_free", "Free LLM Providers", "Together AI Trial", "Open source model inference credits with extensive model catalog.", ["together", "mistral", "llama", "api"], "https://together.ai"),
            ("llm_openrouter_free", "Free LLM Providers", "OpenRouter Free Models", "Aggregator providing free endpoints for open-weight models including DeepSeek-R1 and Qwen.", ["openrouter", "deepseek", "qwen", "free_endpoints"], "https://openrouter.ai"),
            ("llm_github_models", "Free LLM Providers", "GitHub Models Marketplace", "Free playground and API access to GPT-4o, Phi-3, and Llama-3 for authenticated developers.", ["github", "gpt4o", "phi3", "free_quota"], "https://github.com/marketplace/models")
        ]
        for eid, cat, title, desc, tags, link in free_llm_items:
            self._add_entry(eid, "mnfst/awesome-free-llm-apis", cat, title, desc, tags, {"provider": title, "free_quota": True}, link)

        # 3. build-your-own-x (Recreating favorite technologies from scratch)
        byox_items = [
            ("byox_git", "Architecture Blueprints", "Build Your Own Git", "Implement a content-addressable filesystem, SHA-1 object hashes, trees, commits, and refs in Python.", ["git", "vcs", "data_structures", "storage"], "https://github.com/codecrafters-io/build-your-own-x#build-your-own-git"),
            ("byox_sqlite", "Architecture Blueprints", "Build Your Own SQLite", "Implement a B-tree indexed SQL database engine, pager, parser, and query execution engine.", ["database", "sqlite", "btree", "sql"], "https://github.com/codecrafters-io/build-your-own-x#build-your-own-sqlite"),
            ("byox_docker", "Architecture Blueprints", "Build Your Own Docker", "Create process isolation, cgroups, Linux namespaces, and chroot environments from scratch.", ["docker", "containers", "namespaces", "cgroups"], "https://github.com/codecrafters-io/build-your-own-x#build-your-own-docker"),
            ("byox_compiler", "Architecture Blueprints", "Build Your Own Compiler / Interpreter", "Build lexer, recursive-descent AST parser, symbol table, semantic analysis, and bytecode generator.", ["compiler", "ast", "lexer", "interpreter"], "https://github.com/codecrafters-io/build-your-own-x#build-your-own-programming-language"),
            ("byox_neural_net", "Architecture Blueprints", "Build Your Own Neural Network", "Implement forward-pass matrix multiplication, backpropagation gradients, and Adam optimizer in raw NumPy.", ["neural_network", "deep_learning", "numpy", "backpropagation"], "https://github.com/codecrafters-io/build-your-own-x#build-your-own-neural-network")
        ]
        for eid, cat, title, desc, tags, link in byox_items:
            self._add_entry(eid, "codecrafters-io/build-your-own-x", cat, title, desc, tags, {"difficulty": "Advanced", "language": "Multi-language"}, link)

        # 4. ERA-System-Prompts (Curated AI behavioral system prompts)
        era_prompts = [
            ("prompt_jarvis_executive", "System Prompts", "JARVIS Executive Operating Persona", "Precision-engineered system prompt enforcing concise, action-first tone, structured output, and proactive execution verification.", ["jarvis", "executive", "system_prompt", "persona"], None),
            ("prompt_deep_code_architect", "System Prompts", "Deep Code Architect", "Forces AI model to inspect AST structures, verify file paths, plan diffs, execute tests, and avoid hallucinations.", ["coding", "architecture", "diff", "verification"], None),
            ("prompt_cybersecurity_auditor", "System Prompts", "Offensive & Defensive Security Specialist", "Rigorous security evaluation prompt analyzing MITRE ATT&CK vectors, input validation flaws, and permission bounds.", ["security", "audit", "mitre", "cybersecurity"], None),
            ("prompt_research_analyst", "System Prompts", "Rigorous Intelligence Researcher", "Enforces multi-source triangulation, citation verification, factual neutrality, and executive briefing formats.", ["research", "citations", "analysis", "intelligence"], None)
        ]
        for eid, cat, title, desc, tags, link in era_prompts:
            self._add_entry(eid, "SailikNanda/ERA-System-Prompts", cat, title, desc, tags, {"type": "System Prompt Template"}, link)

        # 5. awesome-harness-engineering (AI agent harness patterns & evals)
        harness_items = [
            ("harness_mcp_bridge", "Agent Harness Engineering", "Model Context Protocol (MCP) Standard", "Standardized JSON-RPC protocol connecting local LLMs to secure desktop tools, file systems, and external services.", ["mcp", "agent_tools", "json_rpc", "harness"], "https://modelcontextprotocol.io"),
            ("harness_eval_benchmarks", "Agent Harness Engineering", "Agentic Evaluation & Grading Framework", "Automated unit and regression harnesses measuring tool call accuracy, plan completion, and error recovery rates.", ["evals", "benchmarks", "regression", "metrics"], None),
            ("harness_context_compaction", "Agent Harness Engineering", "Context Window Compaction & Sliding Memory", "Token-efficient sliding window summarization preserving crucial system instructions and historical tool state.", ["context", "token_optimization", "sliding_window"], None),
            ("harness_autonomy_gate", "Agent Harness Engineering", "3-Tier Policy Boundary & Guardrails", "Multi-layered permission validation preventing unsafe file deletions, network exfiltration, or privileged execution.", ["policy_gate", "guardrails", "permissions", "safety"], None)
        ]
        for eid, cat, title, desc, tags, link in harness_items:
            self._add_entry(eid, "ai-boost/awesome-harness-engineering", cat, title, desc, tags, {"standard": "Agentic Architecture"}, link)

        # 6. public-apis (Curated directory of public REST endpoints)
        public_api_items = [
            ("api_open_meteo", "Public REST APIs", "Open-Meteo Weather API", "Free open-source weather forecasting and historical climate API requiring no API key.", ["weather", "forecast", "climate", "no_key"], "https://open-meteo.com"),
            ("api_rest_countries", "Public REST APIs", "REST Countries API", "Get information about world countries: currencies, languages, capitals, population, and borders.", ["countries", "geography", "demographics", "no_key"], "https://restcountries.com"),
            ("api_exchange_rates", "Public REST APIs", "Frankfurter Currency Exchange API", "Open API tracking European Central Bank foreign exchange rates and currency conversion.", ["currency", "finance", "exchange_rates", "ecb"], "https://api.frankfurter.app"),
            ("api_wikipedia_summary", "Public REST APIs", "Wikimedia REST API", "Instant encyclopedic summary, lead paragraphs, and thumbnails for verified knowledge retrieval.", ["wikipedia", "encyclopedia", "facts", "knowledge"], "https://en.wikipedia.org/api/rest_v1/"),
            ("api_usaspending", "Public REST APIs", "USA Spending Open Data", "Official US government open spending data, contract awards, federal grants, and public allocations.", ["government", "finance", "open_data", "public"], "https://api.usaspending.gov")
        ]
        for eid, cat, title, desc, tags, link in public_api_items:
            self._add_entry(eid, "public-apis/public-apis", cat, title, desc, tags, {"auth_required": False, "endpoint": link}, link)

        logger.info(f"Initialized Reference Knowledge Base with {len(self._entries)} verified actionable entries.")

    def _add_entry(
        self,
        entry_id: str,
        source_repo: str,
        category: str,
        title: str,
        description: str,
        tags: List[str],
        content: Dict[str, Any],
        link: Optional[str] = None
    ):
        entry = KnowledgeEntry(
            entry_id=entry_id,
            source_repo=source_repo,
            category=category,
            title=title,
            description=description,
            tags=tags,
            content=content,
            link=link
        )
        self._entries[entry_id] = entry

    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[KnowledgeEntry]:
        """Search knowledge base using keyword matching across titles, descriptions, and tags."""
        q_tokens = query.lower().split()
        scores: List[tuple[int, KnowledgeEntry]] = []

        for entry in self._entries.values():
            if category and entry.category.lower() != category.lower() and category.lower() not in entry.source_repo.lower():
                continue

            score = 0
            text_corpus = f"{entry.title} {entry.description} {' '.join(entry.tags)} {entry.source_repo}".lower()

            for token in q_tokens:
                if token in entry.title.lower():
                    score += 5
                elif token in entry.tags:
                    score += 3
                elif token in text_corpus:
                    score += 1

            if score > 0:
                scores.append((score, entry))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scores[:limit]]

    def get_by_id(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self._entries.get(entry_id)

    def list_all(self) -> List[KnowledgeEntry]:
        return list(self._entries.values())

    def list_categories(self) -> List[str]:
        return sorted(list(set(e.category for e in self._entries.values())))


# Global singleton
reference_knowledge = ReferenceKnowledgeStore()
