# Architecture

## System Architecture

```mermaid
graph TB
    subgraph "External Clients"
        A[Claude Code/LLM Client]
        B[Custom MCP Client]
        C[Development Tools]
    end

    subgraph "Network Layer"
        D[Load Balancer/Proxy]
        E[SSL Termination]
    end

    subgraph "Template MCP Server"
        subgraph "Application Layer"
            F[FastAPI Application<br/>api.py]
            G[Health Check Endpoint<br/>/health]
            H[MCP Protocol Handler<br/>/mcp]
        end

        subgraph "MCP Core"
            I[TemplateMCPServer<br/>mcp.py]
            J[FastMCP Instance<br/>Protocol Implementation]
            K[Tool Registry<br/>Dynamic Registration]
        end

        subgraph "Tool Layer"
            L[Mathematical Tools<br/>multiply_numbers]
            M[Logo Tool<br/>get_redhat_logo]
            N[Code Review Tool<br/>generate_code_review_prompt]
            O[Custom Tools<br/>Extensible]
        end

        subgraph "Infrastructure Layer"
            P[Configuration Management<br/>settings.py]
            Q[Structured Logging<br/>pylogger.py]
            R[Error Handling<br/>Exception Management]
            S[Asset Management<br/>Static Resources]
        end

        subgraph "Transport Layer"
            T[HTTP Transport]
            U[SSE Transport]
            V[Streamable HTTP Transport]
        end
    end

    subgraph "External Dependencies"
        W[Environment Variables<br/>.env]
        X[SSL Certificates<br/>TLS/HTTPS]
        Y[Static Assets<br/>Images/Files]
        Z[Container Runtime<br/>Docker/Podman]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    H --> I
    I --> J
    J --> K
    K --> L
    K --> M
    K --> N
    K --> O
    I --> P
    I --> Q
    I --> R
    M --> S
    F --> T
    F --> U
    F --> V
    P --> W
    E --> X
    S --> Y
    Z --> F

    classDef client fill:#e3f2fd
    classDef network fill:#f3e5f5
    classDef application fill:#e8f5e8
    classDef core fill:#fff3e0
    classDef tools fill:#fce4ec
    classDef infrastructure fill:#f1f8e9
    classDef transport fill:#fef7e0
    classDef external fill:#f5f5f5

    class A,B,C client
    class D,E network
    class F,G,H application
    class I,J,K core
    class L,M,N,O tools
    class P,Q,R,S infrastructure
    class T,U,V transport
    class W,X,Y,Z external
```

## Control Flow

```mermaid
flowchart TD
    A[MCP Client Request] --> B{Transport Protocol?}

    B -->|HTTP/Streamable-HTTP| C[FastAPI App<br/>api.py]
    B -->|SSE| D[SSE App<br/>create_sse_app]

    C --> E[Health Check?]
    D --> E

    E -->|/health| F[Health Endpoint<br/>Return Status]
    E -->|/mcp| G[MCP Request Handler<br/>FastMCP Instance]

    G --> H{MCP Method Type?}

    H -->|tools/list| I[List Available Tools<br/>Return tool definitions]
    H -->|tools/call| J[Tool Execution Router<br/>mcp.py]

    J --> K{Which Tool?}

    K -->|multiply_numbers| L[Multiply Tool<br/>multiply_tool.py]
    K -->|get_redhat_logo| M[Logo Tool<br/>redhat_logo_tool.py]
    K -->|generate_code_review_prompt| N[Code Review Tool<br/>code_review_tool.py]

    L --> O[Validate Input<br/>Check numeric types]
    M --> P[Read Asset File<br/>Base64 encode PNG]
    N --> Q[Generate Prompt<br/>Format code review template]

    O --> R[Perform Calculation<br/>a * b]
    P --> S[Return Image Data<br/>MIME type + base64]
    Q --> T[Return Prompt Array<br/>Structured messages]

    R --> U[Log Result<br/>Structured logging]
    S --> U
    T --> U

    U --> V[Return Success Response<br/>JSON format]

    V --> W[Send to MCP Client<br/>Complete request cycle]

    F --> W
    I --> W

    X[Configuration Loading<br/>settings.py] --> Y[Environment Variables<br/>.env file]
    Y --> Z[Pydantic Validation<br/>Type checking & defaults]
    Z --> AA[Server Startup<br/>main.py]
    AA --> C
    AA --> D

    BB[Error Handling] --> CC[Structured Logging<br/>pylogger.py]
    CC --> DD[JSON Output<br/>Timestamp + Context]

    O --> BB
    P --> BB
    Q --> BB

    classDef request fill:#e3f2fd
    classDef routing fill:#f3e5f5
    classDef tools fill:#e8f5e8
    classDef config fill:#fff3e0
    classDef logging fill:#fce4ec

    class A,B,E,H,K request
    class C,D,G,J routing
    class L,M,N,O,P,Q,R,S,T tools
    class X,Y,Z,AA config
    class BB,CC,DD logging
```

## Code Structure

```
template-mcp-server/
├── template_mcp_server/           # Main package directory
│   ├── __init__.py
│   ├── src/                       # Core source code
│   │   ├── __init__.py
│   │   ├── main.py               # Application entry point & startup logic
│   │   ├── api.py                # FastAPI application & transport setup
│   │   ├── mcp.py                # MCP server implementation & tool registration
│   │   ├── settings.py           # Pydantic-based configuration management
│   │   ├── assets/               # Static resource files
│   │   │   └── redhat.png        # Example image asset
│   │   ├── oauth/                # OAuth integration
│   │   │   ├── __init__.py
│   │   │   ├── controller.py     # OAuth controller logic
│   │   │   ├── handler.py        # OAuth request handlers
│   │   │   ├── models.py         # OAuth data models
│   │   │   ├── routes.py         # OAuth route definitions
│   │   │   └── service.py        # OAuth service layer
│   │   ├── storage/              # Persistent storage
│   │   │   ├── __init__.py
│   │   │   └── storage_service.py # PostgreSQL token storage
│   │   └── tools/                # MCP tool implementations
│   │       ├── __init__.py
│   │       ├── multiply_tool.py          # Mathematical operations tool
│   │       ├── code_review_tool.py       # Code review prompt generator
│   │       └── redhat_logo_tool.py       # Base64 image resource handler
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       └── pylogger.py          # Structured logging with structlog
├── tests/                        # Comprehensive test suite
│   ├── conftest.py              # Pytest fixtures and configuration
│   ├── test_api.py              # API endpoint tests
│   ├── test_basic.py            # Basic integration tests
│   ├── test_main.py             # Entry point tests
│   ├── test_mcp.py              # MCP server tests
│   ├── test_oauth_controller.py # OAuth controller tests
│   ├── test_oauth_handler.py    # OAuth handler tests
│   ├── test_oauth_service.py    # OAuth service tests
│   ├── test_settings.py         # Configuration tests
│   ├── test_storage_init.py     # Storage init tests
│   ├── test_storage_service.py  # Storage service tests
│   ├── test_tools.py            # Tool unit tests
│   └── test_utils.py            # Utility tests
├── examples/                     # Client examples
│   ├── fastmcp_client.py        # FastMCP client example
│   └── langgraph_client.py      # LangGraph client example
├── deployment/                   # Deployment configurations
│   └── openshift/               # OpenShift manifests
├── .github/                      # GitHub configuration
│   ├── ISSUE_TEMPLATE/          # Issue templates
│   ├── PULL_REQUEST_TEMPLATE.md # PR template
│   ├── dependabot.yml           # Dependency automation
│   ├── labeler.yml              # Auto-labeling rules
│   └── workflows/               # CI/CD workflows
├── pyproject.toml               # Project metadata & dependencies
├── Makefile                     # Development commands
├── Containerfile                # Red Hat UBI-based container build
├── compose.yaml                 # Podman/Docker Compose orchestration
├── CONTRIBUTING.md              # Contribution guide
├── SECURITY.md                  # Security policy
├── CHANGELOG.md                 # Release history
├── LICENSE                      # Apache 2.0
└── README.md                    # Project documentation
```

## Key Components

- **`main.py`**: Application entry point with configuration validation, error handling, and uvicorn server startup
- **`api.py`**: FastAPI application setup with transport protocol selection (HTTP/SSE/streamable-HTTP) and health endpoints
- **`mcp.py`**: Core MCP server class that registers tools using FastMCP decorators
- **`settings.py`**: Environment-based configuration using Pydantic BaseSettings with validation
- **`tools/`**: MCP tool implementations demonstrating arithmetic, prompts, and resource access patterns
- **`utils/pylogger.py`**: Structured JSON logging using structlog with comprehensive processors

## Current MCP Tools

1. **`multiply_numbers`**: Demonstrates basic arithmetic operations with error handling
2. **`get_redhat_logo`**: Shows resource access patterns with base64 encoding
3. **`generate_code_review_prompt`**: Illustrates prompt generation for code analysis
