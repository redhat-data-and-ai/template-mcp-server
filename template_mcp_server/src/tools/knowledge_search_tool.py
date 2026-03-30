"""Knowledge search tool for deep research testing.

This tool provides a sample knowledge base that the deep research pipeline
can query. It simulates a real knowledge retrieval system by searching
through an in-memory collection of articles and returning relevant results.
"""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

_KNOWLEDGE_BASE: list[Dict[str, Any]] = [
    {
        "id": "kb-001",
        "title": "Introduction to Machine Learning",
        "content": (
            "Machine learning is a subset of artificial intelligence that enables "
            "systems to learn from data and improve from experience without being "
            "explicitly programmed. Key techniques include supervised learning "
            "(classification, regression), unsupervised learning (clustering, "
            "dimensionality reduction), and reinforcement learning. Common "
            "algorithms include linear regression, decision trees, random forests, "
            "support vector machines, and neural networks. The field has seen "
            "rapid growth with deep learning achieving state-of-the-art results "
            "in computer vision, natural language processing, and speech recognition."
        ),
        "category": "technology",
        "tags": ["machine learning", "AI", "deep learning", "algorithms"],
    },
    {
        "id": "kb-002",
        "title": "Cloud Computing Overview",
        "content": (
            "Cloud computing delivers computing services over the internet, "
            "including servers, storage, databases, networking, software, and "
            "analytics. The three main service models are Infrastructure as a "
            "Service (IaaS), Platform as a Service (PaaS), and Software as a "
            "Service (SaaS). Major providers include AWS, Google Cloud, and "
            "Microsoft Azure. Benefits include cost efficiency, scalability, "
            "reliability, and global reach. Challenges include security concerns, "
            "compliance requirements, and vendor lock-in."
        ),
        "category": "technology",
        "tags": ["cloud", "infrastructure", "SaaS", "AWS", "Azure"],
    },
    {
        "id": "kb-003",
        "title": "Agile Software Development Methodology",
        "content": (
            "Agile is an iterative approach to software development that "
            "emphasizes flexibility, collaboration, and customer feedback. "
            "Key frameworks include Scrum (sprints, daily standups, retrospectives), "
            "Kanban (visual boards, WIP limits), and Extreme Programming (pair "
            "programming, test-driven development). Agile promotes adaptive planning, "
            "evolutionary development, early delivery, and continual improvement. "
            "Teams typically work in 2-4 week sprints, delivering incremental "
            "features. The Agile Manifesto values individuals and interactions, "
            "working software, customer collaboration, and responding to change."
        ),
        "category": "methodology",
        "tags": ["agile", "scrum", "kanban", "development", "methodology"],
    },
    {
        "id": "kb-004",
        "title": "Data Engineering Best Practices",
        "content": (
            "Data engineering involves designing and building systems for "
            "collecting, storing, and analyzing data at scale. Key practices "
            "include building reliable data pipelines with tools like Apache "
            "Airflow, Apache Spark, and dbt. Data quality is ensured through "
            "validation, testing, and monitoring. Modern data architectures "
            "include data lakes, data warehouses, and the lakehouse paradigm. "
            "Important concepts include ETL/ELT processes, data modeling "
            "(star schema, snowflake schema), and data governance. "
            "Metrics: average pipeline latency is 15 minutes, data freshness "
            "SLA is 99.5%, and typical data volume is 50TB per day."
        ),
        "category": "data",
        "tags": ["data engineering", "pipelines", "ETL", "data lake", "Spark"],
    },
    {
        "id": "kb-005",
        "title": "Cybersecurity Fundamentals",
        "content": (
            "Cybersecurity protects systems, networks, and programs from digital "
            "attacks. Key areas include network security (firewalls, IDS/IPS), "
            "application security (OWASP Top 10, secure coding), identity and "
            "access management (IAM, MFA, SSO), and data protection (encryption, "
            "DLP). Common threats include phishing (accounting for 36% of breaches), "
            "ransomware (average cost $4.5M per incident), and insider threats. "
            "Security frameworks include NIST, ISO 27001, and CIS Controls. "
            "Organizations should implement defense in depth, zero trust "
            "architecture, and regular security assessments."
        ),
        "category": "security",
        "tags": ["cybersecurity", "security", "encryption", "compliance"],
    },
    {
        "id": "kb-006",
        "title": "Kubernetes Container Orchestration",
        "content": (
            "Kubernetes (K8s) is an open-source container orchestration platform "
            "that automates deployment, scaling, and management of containerized "
            "applications. Key concepts include Pods (smallest deployable unit), "
            "Services (networking abstraction), Deployments (declarative updates), "
            "and ConfigMaps/Secrets (configuration management). Kubernetes supports "
            "horizontal pod autoscaling, rolling updates, and self-healing. "
            "The ecosystem includes Helm for package management, Istio for service "
            "mesh, and Prometheus/Grafana for monitoring. Enterprise adoption rate "
            "is 78% among organizations running containers."
        ),
        "category": "technology",
        "tags": ["kubernetes", "containers", "docker", "orchestration", "DevOps"],
    },
    {
        "id": "kb-007",
        "title": "Project Management Metrics and KPIs",
        "content": (
            "Effective project management relies on tracking key metrics. "
            "Schedule Performance Index (SPI) measures schedule efficiency, "
            "with SPI > 1.0 indicating ahead of schedule. Cost Performance "
            "Index (CPI) measures cost efficiency. Velocity in Agile tracks "
            "story points completed per sprint (average 40-60 points). "
            "Lead time measures end-to-end delivery (average 14 days). "
            "Cycle time measures active development time (average 5 days). "
            "Defect density tracks bugs per 1000 lines of code (target < 5). "
            "Customer satisfaction (CSAT) score averages 4.2/5.0 across teams."
        ),
        "category": "management",
        "tags": ["project management", "KPIs", "metrics", "velocity", "agile"],
    },
    {
        "id": "kb-008",
        "title": "API Design and RESTful Services",
        "content": (
            "RESTful API design follows principles of statelessness, resource-based "
            "URLs, and standard HTTP methods (GET, POST, PUT, DELETE). Best "
            "practices include versioning (v1/v2), pagination for large datasets, "
            "proper error handling with standard HTTP status codes, and rate "
            "limiting. Modern alternatives include GraphQL (flexible queries) "
            "and gRPC (high performance). API documentation standards include "
            "OpenAPI/Swagger. Key metrics: average API response time should be "
            "< 200ms for reads and < 500ms for writes. API uptime target is 99.9%."
        ),
        "category": "technology",
        "tags": ["API", "REST", "GraphQL", "design", "microservices"],
    },
]


def _score_match(article: Dict[str, Any], query: str) -> float:
    """Score how well an article matches a search query."""
    query_lower = query.lower()
    terms = query_lower.split()

    score = 0.0
    title_lower = article["title"].lower()
    content_lower = article["content"].lower()
    tags = [t.lower() for t in article.get("tags", [])]

    for term in terms:
        if term in title_lower:
            score += 3.0
        if term in content_lower:
            score += 1.0
        if any(term in tag for tag in tags):
            score += 2.0

    return score


def knowledge_search(
    query: str,
    category: str | None = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search the knowledge base for relevant articles.

    TOOL_NAME=knowledge_search
    DISPLAY_NAME=Knowledge Base Search
    USECASE=Search through a knowledge base of articles on technology, methodology, and management topics
    INSTRUCTIONS=1. Provide a search query, 2. Optionally filter by category, 3. Receive matching articles
    INPUT_DESCRIPTION=query (required): search terms. category (optional): filter by "technology", "methodology", "data", "security", "management". max_results (optional, default 5): limit results.
    OUTPUT_DESCRIPTION=Dictionary with status, query, results count, and list of matching articles with title, content, category, tags, and relevance score
    EXAMPLES=knowledge_search("machine learning"), knowledge_search("kubernetes", category="technology"), knowledge_search("project metrics", max_results=3)
    PREREQUISITES=None
    RELATED_TOOLS=None

    Searches an in-memory knowledge base and returns relevant articles
    ranked by relevance score.

    Args:
        query: The search query string.
        category: Optional category filter.
        max_results: Maximum number of results to return (default: 5).

    Returns:
        Dictionary containing search results with relevance scores.
    """
    try:
        logger.info(f"Knowledge search: query='{query}', category={category}")

        candidates = _KNOWLEDGE_BASE
        if category:
            candidates = [a for a in candidates if a["category"] == category.lower()]

        scored = []
        for article in candidates:
            score = _score_match(article, query)
            if score > 0:
                scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_results = scored[:max_results]

        results = []
        for score, article in top_results:
            results.append(
                {
                    "id": article["id"],
                    "title": article["title"],
                    "content": article["content"],
                    "category": article["category"],
                    "tags": article["tags"],
                    "relevance_score": round(score, 2),
                }
            )

        logger.info(f"Knowledge search returned {len(results)} results for '{query}'")

        return {
            "status": "success",
            "query": query,
            "category_filter": category,
            "total_results": len(results),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in knowledge search: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "results": [],
        }
