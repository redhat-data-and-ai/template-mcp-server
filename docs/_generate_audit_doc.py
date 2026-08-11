"""Generate MCP SEP Audit Report as .docx file."""

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def add_bookmark(paragraph, bookmark_name):
    """Add a bookmark to a paragraph element."""
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    tag = run._r
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(hash(bookmark_name) % 100000))
    start.set(qn("w:name"), bookmark_name)
    tag.addprevious(start)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), start.get(qn("w:id")))
    tag.addnext(end)


def add_internal_hyperlink(paragraph, bookmark_name, text):
    """Add an internal hyperlink (to a bookmark) inside a paragraph."""
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), bookmark_name)
    run_elem = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F3864")
    rPr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "22")
    rPr.append(sz)
    run_elem.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run_elem.append(t)
    hyperlink.append(run_elem)
    paragraph._p.append(hyperlink)


def set_cell_shading(cell, color_hex):
    """Apply background shading to a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shd = shading.makeelement(
        qn("w:shd"),
        {
            qn("w:fill"): color_hex,
            qn("w:val"): "clear",
        },
    )
    shading.append(shd)


def add_table(doc, headers, rows, col_widths=None):
    """Add a formatted table to the document."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
        set_cell_shading(cell, "D9E2F3")

    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)

    return table


def add_code_block(doc, code_text, label=None):
    """Add a monospace code block to the document."""
    if label:
        p = doc.add_paragraph()
        run = p.add_run(label)
        run.bold = True
        run.font.size = Pt(9)

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    return p


def build_document():
    """Build the full audit DOCX document."""
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for level in range(1, 4):
        hs = doc.styles[f"Heading {level}"]
        hs.font.name = "Calibri"
        hs.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    # ── Title ──
    title = doc.add_heading(
        "MCP SEP Implementation — Comprehensive Audit Report", level=0
    )
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Date: 2026-08-10  |  Codebase: template-mcp-server  |  Branch: feat/new-sep-updates"
    )
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("Test Results: 710 passed, 0 failed  |  Overall Coverage: 100%")
    run2.bold = True
    run2.font.size = Pt(11)
    run2.font.color.rgb = RGBColor(0x00, 0x70, 0x30)

    doc.add_page_break()

    # ── Table of Contents with hyperlinks ──
    doc.add_heading("Table of Contents", level=1)
    toc_entries = [
        ("1. SEP Implementation Status", "section_1"),
        ("2. Deprecated Task Removal Verification", "section_2"),
        ("3. Duplicate Code Audit & Fixes Applied", "section_3"),
        ("4. Hardcoded Values Audit & Fixes Applied", "section_4"),
        ("5. Duplicate Test Case Audit", "section_5"),
        ("6. Test Coverage Analysis", "section_6"),
        ("7. Local & Kubernetes Compatibility", "section_7"),
        ("8. Detailed SEP Code Changes", "section_8"),
        ("9. Testing Guide — How to Verify Each SEP", "section_9"),
        ("10. Code Breakage Analysis", "section_10"),
    ]
    for label, bookmark in toc_entries:
        p = doc.add_paragraph(style="List Number")
        add_internal_hyperlink(p, bookmark, label)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1: SEP Implementation Status
    # ══════════════════════════════════════════════════════════════════════
    h1 = doc.add_heading("1. SEP Implementation Status", level=1)
    add_bookmark(h1, "section_1")
    doc.add_paragraph(
        "All 19 SEPs from the 2026-07-28 sprint roadmap are fully implemented."
    )

    sep_rows = [
        (
            "1",
            "SEP-414",
            "W3C Trace Context (traceparent, tracestate, baggage)",
            "Done",
        ),
        ("2", "SEP-837", "application_type in DCR", "Done"),
        ("3", "SEP-991", "CIMD endpoint + DCR deprecation header", "Done"),
        (
            "4",
            "SEP-2106",
            "JSON Schema 2020-12 (outputSchema, composition keywords)",
            "Done",
        ),
        ("5", "SEP-2133", "Extensions framework (extensions in capabilities)", "Done"),
        ("6", "SEP-2207", "OIDC offline_access exclusion", "Done"),
        ("7", "SEP-2243", "Mcp-Method / Mcp-Name header validation", "Done"),
        ("8", "SEP-2260", "Server request association (no standalone pushes)", "Done"),
        (
            "9",
            "SEP-2322",
            "Multi Round-Trip Requests (resultType on tools/call)",
            "Done",
        ),
        ("10", "SEP-2352", "Client Credential Binding (Issuer Identifier)", "Done"),
        ("11", "SEP-2468", "iss in Authorization Responses (RFC 9207)", "Done"),
        (
            "12",
            "SEP-2549",
            "Deterministic tools/list ordering + TTL/Cache Scope",
            "Done",
        ),
        (
            "13",
            "SEP-2567",
            "Session removal (stateless HTTP, no Mcp-Session-Id)",
            "Done",
        ),
        (
            "14",
            "SEP-2575",
            "Stateless MCP (server/discover, removed methods, _meta)",
            "Done",
        ),
        ("15", "SEP-2577", "Deprecate Roots, Sampling, Logging", "Done"),
        ("16", "SEP-2596", "Feature lifecycle / deprecation policy", "Done"),
        ("17", "SEP-1865", "MCP Apps extension (io.modelcontextprotocol/ui)", "Done"),
        ("18", "SEP-2663", "Tasks extension (io.modelcontextprotocol/tasks)", "Done"),
        ("19", "Error codes", "Allocation policy + renumbering", "Done"),
    ]
    add_table(
        doc, ["#", "SEP", "Implementation", "Status"], sep_rows, [0.3, 0.8, 4.0, 0.6]
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2: Deprecated Task Removal
    # ══════════════════════════════════════════════════════════════════════
    h2 = doc.add_heading("2. Deprecated Task Removal Verification", level=1)
    add_bookmark(h2, "section_2")
    doc.add_paragraph(
        "All deprecated/removed features from the 2026-07-28 spec are properly handled:"
    )

    dep_rows = [
        (
            "Sessions (Mcp-Session-Id)",
            "Removed",
            "Yes",
            "stateless_http=True in mcp.py (SEP-2567)",
        ),
        (
            "Initialize handshake",
            "Removed",
            "Yes",
            "server/discover RPC in middleware (SEP-2575)",
        ),
        ("ping", "Removed", "Yes", "Rejected with -32023 in _REMOVED_METHODS"),
        (
            "logging/setLevel",
            "Removed",
            "Yes",
            "Rejected with -32023; per-request _meta.logLevel supported",
        ),
        ("notifications/roots/list_changed", "Removed", "Yes", "Rejected with -32023"),
        (
            "SSE resumability",
            "Removed",
            "Yes",
            "stateless_http=True disables Last-Event-ID",
        ),
        (
            "elicitation/create",
            "Superseded",
            "Yes",
            "Registered as removed in deprecation_registry; MRTR replaces it",
        ),
        (
            "elicitation notification",
            "Removed",
            "Yes",
            "Registered as removed in deprecation_registry",
        ),
        ("tasks/list", "Removed", "Yes", "In _REMOVED_METHODS, rejected with -32023"),
        (
            "DCR (POST /auth/register)",
            "Deprecated",
            "Yes",
            "Returns Deprecation: true header; CIMD endpoint available",
        ),
        (
            "HTTP+SSE transport",
            "Deprecated",
            "N/A",
            "Server uses Streamable HTTP; never had HTTP+SSE",
        ),
        (
            "Roots",
            "Deprecated",
            "Yes",
            "Registered in deprecation_registry with migration guidance",
        ),
        (
            "Sampling",
            "Deprecated",
            "Yes",
            "Registered in deprecation_registry with migration guidance",
        ),
        (
            "Logging",
            "Deprecated",
            "Yes",
            "Registered in deprecation_registry with migration guidance",
        ),
        (
            "includeContext",
            "Deprecated",
            "N/A",
            "Server never used includeContext; registered in registry",
        ),
    ]
    add_table(
        doc, ["Feature", "Spec State", "Impl?", "How"], dep_rows, [1.8, 0.8, 0.5, 3.0]
    )

    p = doc.add_paragraph()
    run = p.add_run("Verification method: ")
    run.bold = True
    p.add_run(
        "deprecation_registry in deprecation.py has 15 entries total (9 removed + 6 deprecated). "
        "The _REMOVED_METHODS frozenset in api.py blocks 4 methods at the middleware level."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3: Duplicate Code
    # ══════════════════════════════════════════════════════════════════════
    h3 = doc.add_heading("3. Duplicate Code Audit & Fixes Applied", level=1)
    add_bookmark(h3, "section_3")

    doc.add_heading("Fixed: Duplicate trace extraction in api.py", level=2)
    doc.add_paragraph(
        "Before: _bind_trace_context() and _trace_response_headers() both contained identical "
        "6-line blocks extracting trace context from HTTP headers and _meta fields."
    )
    doc.add_paragraph(
        "After: Extracted shared logic into _extract_trace_context() static method. Both methods "
        "now call this single helper."
    )
    doc.add_paragraph("File: template_mcp_server/src/api.py")

    doc.add_heading("Verified: No other duplicate code", level=2)
    doc.add_paragraph(
        "Files analyzed for duplication patterns:\n"
        "- tracing.py: extract_trace_from_headers() and extract_trace_from_meta() handle different "
        "data sources (HTTP headers vs MCP _meta dict) — not true duplicates.\n"
        "- schema.py: validate_input_schema() and validate_output_schema() share _validate_refs() "
        "via helper — already factored.\n"
        "- extensions.py and deprecation.py: Both are registry patterns but serve different domains.\n"
        "- oauth/controller.py: Grant type handlers share structure but have distinct business logic."
    )

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 4: Hardcoded Values
    # ══════════════════════════════════════════════════════════════════════
    h4 = doc.add_heading("4. Hardcoded Values Audit & Fixes Applied", level=1)
    add_bookmark(h4, "section_4")

    doc.add_heading('Fixed: "template-mcp-server" repeated 4 times in api.py', level=2)
    doc.add_paragraph(
        'Before: The string "template-mcp-server" appeared in SCOPES_SUPPORTED, _get_version(), '
        "get_server_discover_result(), and health_check()."
    )
    doc.add_paragraph(
        'After: Extracted to _SERVER_NAME = "template-mcp-server" constant. All 4 usages reference the constant.'
    )
    doc.add_paragraph("File: template_mcp_server/src/api.py")

    doc.add_heading('Fixed: "2026-07-28" hardcoded in error message', level=2)
    doc.add_paragraph(
        'Before: api.py had: f"...removed in 2026-07-28 spec".\n'
        'After: Changed to f"...removed in {settings.MCP_PROTOCOL_VERSION} spec" — uses the configurable setting.'
    )
    doc.add_paragraph("File: template_mcp_server/src/api.py")

    doc.add_heading('Fixed: "2026-07-28" repeated 14 times in deprecation.py', level=2)
    doc.add_paragraph(
        'Before: Every DeprecationEntry had removed_in="2026-07-28" or deprecated_since="2026-07-28" as raw strings.\n'
        'After: Extracted to _SPEC_VERSION = "2026-07-28" and _PREV_SPEC_VERSION = "2025-11-05" constants.'
    )
    doc.add_paragraph("File: template_mcp_server/src/deprecation.py")

    doc.add_heading("Fixed: MCP_TRANSPORT_PROTOCOL in Kubernetes ConfigMaps", level=2)
    doc.add_paragraph(
        "Before: Both deployment/kind/configmap.yaml and deployment/openshift/configmap.yaml had "
        'MCP_TRANSPORT_PROTOCOL: "http" — an invalid value that would fail settings validation.\n'
        'After: Changed to "streamable-http" in both files. Also added missing SEP settings '
        "(MCP_STATELESS_HTTP, MCP_PROTOCOL_VERSION, MCP_TRACE_CONTEXT_ENABLED, MCP_EXTENSIONS_ENABLED)."
    )

    doc.add_heading("Remaining hardcoded values (correct by design)", level=2)
    hc_rows = [
        (
            '"0.0.0-dev"',
            "api.py:_get_version()",
            "Fallback when package not installed — intentional sentinel",
        ),
        (
            '"localhost"',
            "settings.py defaults",
            "Pydantic default values — overridable via env vars",
        ),
        (
            "5001",
            "settings.py MCP_PORT default",
            "Pydantic default — overridable via env vars",
        ),
        (
            '"http://localhost:5001"',
            "service.py:_ISSUER_SAFE_DEFAULT",
            "Safe fallback for local dev only",
        ),
        (
            "Error codes (-32020 to -32602)",
            "errors.py",
            "Protocol-defined constants from JSON-RPC / MCP spec",
        ),
        (
            '"io.modelcontextprotocol/..."',
            "tracing.py, extensions.py",
            "Protocol-defined reverse-DNS identifiers",
        ),
    ]
    add_table(doc, ["Value", "Location", "Why it's correct"], hc_rows, [1.8, 1.8, 2.8])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 5: Duplicate Tests
    # ══════════════════════════════════════════════════════════════════════
    h5 = doc.add_heading("5. Duplicate Test Case Audit", level=1)
    add_bookmark(h5, "section_5")

    doc.add_heading("Fixed: Duplicate DCR deprecation test", level=2)
    doc.add_paragraph(
        "TestSEP991DCRDeprecation.test_register_endpoint_returns_deprecation_header was a pure "
        "duplicate of TestRegisterEndpointRoute.test_register_endpoint_returns_model_dump_with_deprecation "
        "(identical mock setup, same assertions, same endpoint)."
    )
    doc.add_paragraph(
        "Action: Removed TestSEP991DCRDeprecation class entirely. The original test in "
        "TestRegisterEndpointRoute covers the same scenario plus verifies model_dump() was called."
    )

    doc.add_heading("Same-named tests in different classes (not duplicates)", level=2)
    doc.add_paragraph(
        "test_public_path_passes_through exists in both TestAuthorizationMiddleware and "
        "TestLocalDevelopmentAuthorizationMiddleware. These test different middleware classes — distinct, valid tests."
    )

    doc.add_heading("Verified: No other duplicate tests", level=2)
    doc.add_paragraph(
        "All 710 tests across 24 test files have unique scenarios. Cross-file checks confirmed "
        "test_deprecation.py, test_extensions.py, and test_tracing.py test different layers than test_api.py."
    )

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 6: Test Coverage
    # ══════════════════════════════════════════════════════════════════════
    h6 = doc.add_heading("6. Test Coverage Analysis", level=1)
    add_bookmark(h6, "section_6")
    doc.add_paragraph(
        "Overall: 100% (1821 statements, 0 missed) — 710 tests across 24 test files."
    )

    cov_rows = [
        (
            "api.py",
            "100%",
            "324 stmts",
            "All middleware paths, trace context, MRTR, removed methods, apps/tasks RPCs",
        ),
        (
            "apps.py",
            "100%",
            "35 stmts",
            "AppEntry model, AppRegistry CRUD, get_extension_config",
        ),
        (
            "deprecation.py",
            "100%",
            "43 stmts",
            "Registry, lifecycle states, to_dict/to_list",
        ),
        (
            "errors.py",
            "100%",
            "27 stmts",
            "Error codes, exception classes, range constants",
        ),
        ("extensions.py", "100%", "20 stmts", "Registry CRUD, capabilities, singleton"),
        (
            "main.py",
            "100%",
            "66 stmts",
            "validate_config, handle_startup_error, main, run, SSL config",
        ),
        (
            "mcp.py",
            "100%",
            "47 stmts",
            "Init, tool registration, schema validation, deterministic order",
        ),
        (
            "oauth/controller.py",
            "100%",
            "222 stmts",
            "All grant types, callback, introspect, CIMD, issuer verification",
        ),
        (
            "oauth/handler.py",
            "100%",
            "64 stmts",
            "Session management, PKCE, state generation",
        ),
        (
            "oauth/models.py",
            "100%",
            "45 stmts",
            "Pydantic models, application_type, CIMD response",
        ),
        (
            "oauth/routes.py",
            "100%",
            "50 stmts",
            "All 6 route endpoints, not-initialized guards, register_oauth_routes",
        ),
        (
            "oauth/service.py",
            "100%",
            "137 stmts",
            "Client registration, token management, issuer binding",
        ),
        (
            "schema.py",
            "100%",
            "60 stmts",
            "Input/output schema validation, $ref resolution, 2020-12 keywords",
        ),
        (
            "settings.py",
            "100%",
            "71 stmts",
            "All Pydantic Settings fields and validators",
        ),
        (
            "storage_service.py",
            "100%",
            "206 stmts",
            "PostgreSQL CRUD, table creation, token storage",
        ),
        (
            "tasks.py",
            "100%",
            "73 stmts",
            "TaskEntry model, TaskStore CRUD, cancel, active_tasks, status validation",
        ),
        (
            "tools/bmi_tool.py",
            "100%",
            "41 stmts",
            "BMI calculation, all 4 WHO categories, input validation",
        ),
        (
            "tools/email_tool.py",
            "100%",
            "47 stmts",
            "Resend API, import guard, sync/async wrappers",
        ),
        (
            "tools/validate_email_tool.py",
            "100%",
            "42 stmts",
            "Email validation regex, DNS check mock paths",
        ),
        (
            "tools/web_search_tool.py",
            "100%",
            "96 stmts",
            "Tavily API, retry logic, dedup, truncation, import guard",
        ),
        (
            "tracing.py",
            "100%",
            "60 stmts",
            "W3C parsing, span/trace generation, structlog processor",
        ),
        (
            "pylogger.py",
            "100%",
            "44 stmts",
            "Structured logging, contextvars, uvicorn config",
        ),
    ]
    add_table(
        doc,
        ["File", "Coverage", "Statements", "What's Tested"],
        cov_rows,
        [1.5, 0.6, 0.8, 3.5],
    )

    doc.add_heading("Tests added to achieve 100% coverage", level=2)
    new_test_rows = [
        (
            "tests/test_bmi_tool.py",
            "16",
            "All WHO categories, boundary values, invalid inputs (non-numeric, None, out-of-range)",
        ),
        (
            "tests/test_email_tool.py",
            "9",
            "API key missing, resend not installed, from_email missing, success, exception, async wrapper, import guard",
        ),
        (
            "tests/test_web_search_tool.py",
            "12",
            "Retry logic, timeout handling, snippet truncation, dedup, tavily not installed, import guard",
        ),
        (
            "tests/test_oauth_routes.py",
            "15",
            "All 6 endpoints (initialized + not-initialized), model_dump vs dict responses, deprecation header",
        ),
        (
            "tests/test_main.py",
            "12",
            "validate_config (empty host, AttributeError), handle_startup_error (all 5 error types), main (SSL, KeyboardInterrupt), run()",
        ),
        ("tests/test_mcp.py", "+1", "outputSchema validation failure branch"),
        (
            "tests/test_api.py",
            "+3",
            "Missing method passthrough, trace disabled branches, structlog import exception",
        ),
        (
            "tests/test_apps.py",
            "13",
            "AppEntry to_dict (minimal/full), defaults, AppRegistry register/get/unregister/list/count/config, module singleton",
        ),
        (
            "tests/test_tasks.py",
            "22",
            "TaskEntry defaults/to_dict/is_terminal for all 5 statuses, TaskStore CRUD/update/cancel/active_tasks/progress clamp/terminal rejection",
        ),
    ]
    add_table(
        doc,
        ["Test File", "New Tests", "Scenarios Covered"],
        new_test_rows,
        [1.8, 0.6, 4.0],
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 7: K8s Compatibility
    # ══════════════════════════════════════════════════════════════════════
    h7 = doc.add_heading("7. Local & Kubernetes Compatibility", level=1)
    add_bookmark(h7, "section_7")

    doc.add_heading("Local Development", level=2)
    local_rows = [
        (
            "Local server startup",
            "Works",
            "uv run template-mcp-server or python -m template_mcp_server.src.main",
        ),
        (
            "Local Postgres",
            "Works",
            "docker compose up postgres starts Postgres on port 5433",
        ),
        ("Auth disabled mode", "Works", "ENABLE_AUTH=false allows running without SSO"),
        (
            "STDIO transport",
            "Works",
            "MCP_TRANSPORT_PROTOCOL=stdio for local MCP client testing",
        ),
        (
            "Tests without infra",
            "Works",
            "All 710 tests pass without any external services",
        ),
        (".env file support", "Works", "python-dotenv loads .env automatically"),
    ]
    add_table(doc, ["Aspect", "Status", "Details"], local_rows, [1.5, 0.6, 4.2])

    doc.add_heading("Kubernetes Compatibility", level=2)
    k8s_rows = [
        (
            "Kind cluster",
            "Works",
            "deployment/kind/ has Deployment, Service, ConfigMap, Secret, Kustomization",
        ),
        (
            "OpenShift cluster",
            "Works",
            "deployment/openshift/ has full resource set including Route and BuildConfig",
        ),
        (
            "Container image",
            "Works",
            "Containerfile uses ubi9/python-312, installs via uv pip install",
        ),
        (
            "Health probes",
            "Works",
            "Liveness and readiness probes configured on /health:5001",
        ),
        ("Resource limits", "Works", "Requests: 256Mi/100m, Limits: 512Mi/500m"),
        ("Env from ConfigMap", "Works", "All settings sourced from ConfigMap + Secret"),
        (
            "Non-root execution",
            "Works",
            "Containerfile uses USER default (UID 1001 on UBI)",
        ),
        ("Postgres connectivity", "Works", "POSTGRES_HOST configurable via ConfigMap"),
        (
            "Graceful shutdown",
            "Works",
            "restartPolicy: Always, lifespan handler cleans up storage connections",
        ),
    ]
    add_table(doc, ["Aspect", "Status", "Details"], k8s_rows, [1.5, 0.6, 4.2])

    doc.add_heading("Fixes Applied for K8s Compatibility", level=2)
    doc.add_paragraph(
        '1. MCP_TRANSPORT_PROTOCOL: "http" changed to "streamable-http" in both Kind and OpenShift configmaps. '
        "The old value is not in the valid enum and would cause startup validation failure.\n\n"
        "2. Added missing SEP settings (MCP_STATELESS_HTTP, MCP_PROTOCOL_VERSION, MCP_TRACE_CONTEXT_ENABLED, "
        "MCP_EXTENSIONS_ENABLED) to both ConfigMaps for self-documenting deployment configs."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 8: Detailed SEP Code Changes
    # ══════════════════════════════════════════════════════════════════════
    h8 = doc.add_heading("8. Detailed SEP Code Changes", level=1)
    add_bookmark(h8, "section_8")

    # SEP-414
    doc.add_heading("SEP-414: W3C Trace Context Propagation", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/tracing.py (60 statements, 100% covered)"
    )

    t414_rows = [
        (
            "parse_traceparent(value)",
            "Parses W3C traceparent header into {version, trace_id, parent_id, trace_flags}. Rejects all-zero IDs.",
        ),
        (
            "generate_span_id()",
            "Generates random 16-hex-char span ID via os.urandom(8).hex()",
        ),
        (
            "generate_trace_id()",
            "Generates random 32-hex-char trace ID via os.urandom(16).hex()",
        ),
        (
            "build_traceparent(trace_id, span_id, flags)",
            "Builds {version}-{trace_id}-{span_id}-{flags} string",
        ),
        (
            "extract_trace_from_meta(meta)",
            "Extracts trace from MCP _meta fields using io.modelcontextprotocol/traceparent keys",
        ),
        (
            "extract_trace_from_headers(headers)",
            "Extracts trace from HTTP traceparent, tracestate, baggage headers",
        ),
        (
            "trace_context_processor(logger, method, event_dict)",
            "Structlog processor that injects trace_id/span_id from contextvars into log entries",
        ),
    ]
    add_table(doc, ["Function", "Purpose"], t414_rows, [2.8, 3.8])

    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: Incoming MCP requests may carry W3C trace context in HTTP headers (traceparent, tracestate, baggage) "
        "or in the MCP _meta field. The server must propagate the trace_id across log entries and return a new "
        "server-generated span_id in the response traceparent header for distributed tracing."
    )
    add_code_block(
        doc,
        (
            "# New static method — merges trace from HTTP headers and MCP _meta\n"
            "@staticmethod\n"
            "def _extract_trace_context(request: Request, body: dict) -> dict:\n"
            "    trace_ctx = extract_trace_from_headers(request.headers)\n"
            "    params = body.get('params', {})\n"
            "    meta = params.get('_meta', {}) if isinstance(params, dict) else {}\n"
            "    if isinstance(meta, dict):\n"
            "        meta_trace = extract_trace_from_meta(meta)\n"
            "        if meta_trace and 'traceparent' not in trace_ctx:\n"
            "            trace_ctx.update(meta_trace)\n"
            "    return trace_ctx\n\n"
            "# _bind_trace_context() — binds trace_id + server span_id to structlog\n"
            "def _bind_trace_context(self, request, body):\n"
            "    if not settings.MCP_TRACE_CONTEXT_ENABLED: return\n"
            "    trace_ctx = self._extract_trace_context(request, body)\n"
            "    if 'traceparent' in trace_ctx:\n"
            "        server_span = generate_span_id()\n"
            "        structlog.contextvars.bind_contextvars(\n"
            "            trace_id=trace_ctx['traceparent']['trace_id'],\n"
            "            span_id=server_span)\n\n"
            "# _trace_response_headers() — builds response headers with new span_id\n"
            "def _trace_response_headers(self, request, body) -> dict:\n"
            "    if not settings.MCP_TRACE_CONTEXT_ENABLED: return {}\n"
            "    trace_ctx = self._extract_trace_context(request, body)\n"
            "    if 'traceparent' in trace_ctx:\n"
            "        tp = trace_ctx['traceparent']\n"
            "        new_span = generate_span_id()\n"
            "        headers['traceparent'] = build_traceparent(\n"
            "            tp['trace_id'], new_span, tp['trace_flags'])\n"
            "    return headers"
        ),
        "Code added to McpProtocolMiddleware:",
    )

    doc.add_paragraph(
        "Modified file: template_mcp_server/utils/pylogger.py\n"
        "- Added structlog.contextvars.merge_contextvars as the first processor in the structlog chain "
        "so that trace_id and span_id bound in middleware appear in every log entry.\n\n"
        "Modified file: template_mcp_server/src/settings.py\n"
        "- Added MCP_TRACE_CONTEXT_ENABLED: bool = Field(default=True) — allows disabling trace propagation.\n\n"
        "Test files: tests/test_tracing.py (30 tests), tests/test_api.py::TestSEP414TraceContext (7 tests)"
    )

    # SEP-837
    doc.add_heading("SEP-837: application_type in Dynamic Client Registration", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/oauth/service.py")
    doc.add_paragraph(
        "Why: RFC 7591 defines application_type to distinguish 'native' apps (loopback/custom-scheme redirect URIs) "
        "from 'web' apps. The server must infer this when not explicitly provided."
    )
    add_code_block(
        doc,
        (
            "def _infer_application_type(redirect_uris: list[str]) -> str:\n"
            "    for uri in redirect_uris:\n"
            "        parsed = urlparse(uri)\n"
            "        if parsed.hostname in ('localhost', '127.0.0.1', '[::1]'):\n"
            "            return 'native'\n"
            "        if parsed.scheme not in ('http', 'https'):\n"
            "            return 'native'  # custom scheme = native app\n"
            "    return 'web'\n\n"
            "# In register_client():\n"
            "app_type = request.application_type or _infer_application_type(request.redirect_uris)"
        ),
        "Code added:",
    )

    doc.add_paragraph(
        "Modified file: template_mcp_server/src/oauth/models.py\n"
        "- ClientRegistrationRequest.application_type: Optional[str] = None\n"
        "- ClientRegistrationResponse.application_type: str — always present in response.\n"
        "- ClientMetadataResponse.application_type: str — present in CIMD responses.\n\n"
        "Modified file: template_mcp_server/src/storage/storage_service.py\n"
        "- Added application_type VARCHAR(50) column to oauth_clients table."
    )

    # SEP-991
    doc.add_heading("SEP-991 / PR-2858: CIMD Endpoint + DCR Deprecation", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/oauth/routes.py")
    doc.add_paragraph(
        "Why: Dynamic Client Registration (POST /auth/register) is deprecated in favor of the Client ID Metadata "
        "Document (CIMD) endpoint. The existing register endpoint now returns a Deprecation header."
    )
    add_code_block(
        doc,
        (
            "# POST /auth/register — existing endpoint, now returns deprecation header\n"
            "@oauth_router.post('/auth/register')\n"
            "async def register_endpoint(request: Request):\n"
            "    result = await controller.handle_register(request, oauth_service)\n"
            "    return JSONResponse(\n"
            "        content=result.model_dump(),\n"
            "        headers={'Deprecation': 'true'},  # <-- NEW\n"
            "    )\n\n"
            "# GET /auth/client-metadata/{client_id} — NEW CIMD endpoint\n"
            "@oauth_router.get('/auth/client-metadata/{client_id}')\n"
            "async def client_metadata_endpoint(request: Request, client_id: str):\n"
            "    result = await controller.handle_client_metadata(client_id, oauth_service)\n"
            "    return result.model_dump()"
        ),
        "Code changes:",
    )

    doc.add_paragraph(
        "Modified file: template_mcp_server/src/oauth/controller.py\n"
        "- handle_client_metadata(client_id, oauth_service) — Retrieves client metadata or returns 404.\n\n"
        "Modified file: template_mcp_server/src/api.py\n"
        "- PUBLIC_PATH_PREFIXES includes /auth/client-metadata/ — CIMD paths bypass auth.\n"
        "- Well-known endpoints include registration_endpoint_is_deprecated: true and client_metadata_endpoint."
    )

    # SEP-2106
    doc.add_heading("SEP-2106: JSON Schema 2020-12", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/schema.py (60 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: MCP 2026-07-28 requires JSON Schema 2020-12 for tool schemas. inputSchema must have type:'object' "
        "at root. outputSchema is optional but validated when present. $ref must resolve within $defs."
    )
    add_code_block(
        doc,
        (
            "def validate_input_schema(schema: dict | None) -> list[str]:\n"
            "    errors = []\n"
            "    if schema and schema.get('type') != 'object':\n"
            "        errors.append('inputSchema root must have type: object')\n"
            "    errors.extend(_validate_refs(schema))\n"
            "    return errors\n\n"
            "def _validate_refs(schema: dict | None) -> list[str]:\n"
            "    if not schema: return []\n"
            "    refs = _collect_refs(schema)\n"
            "    defs = set(schema.get('$defs', {}).keys())\n"
            "    return [f'$ref {r} does not resolve' for r in refs\n"
            "            if r.startswith('#/$defs/') and r[8:] not in defs]\n\n"
            "# In mcp.py — TemplateMCPServer._validate_tool_schemas():\n"
            "for key, tool in components.items():\n"
            "    if not key.startswith('tool:'): continue\n"
            "    input_errors = validate_input_schema(tool.parameters)\n"
            "    output_errors = validate_output_schema(tool.output_schema)\n"
            "    if input_errors or output_errors: raise ValueError(...)"
        ),
        "Key code:",
    )

    doc.add_paragraph(
        "Modified files: template_mcp_server/src/tools/{bmi,email,validate_email,web_search}_tool.py\n"
        "- Each tool defines an OUTPUT_SCHEMA dict with type, properties, and required fields."
    )

    # SEP-2133
    doc.add_heading("SEP-2133: Extensions Framework", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/extensions.py (20 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: MCP extensions use reverse-DNS identifiers in capabilities. The server needs a registry "
        "to manage extension lifecycle and advertise capabilities in server/discover."
    )
    add_code_block(
        doc,
        (
            "class ExtensionRegistry:\n"
            "    def __init__(self): self._extensions = {}\n"
            "    def register(self, ext_id: str, config: dict): ...\n"
            "    def unregister(self, ext_id: str): ...\n"
            "    def get_capabilities(self) -> dict:  # returns all registered\n"
            "        return dict(self._extensions)\n\n"
            "EXTENSION_APPS = 'io.modelcontextprotocol/ui'\n"
            "EXTENSION_TASKS = 'io.modelcontextprotocol/tasks'\n"
            "extension_registry = ExtensionRegistry()  # module-level singleton\n\n"
            "# In api.py — module-level registration:\n"
            "if settings.MCP_EXTENSIONS_ENABLED:\n"
            "    extension_registry.register(\n"
            "        EXTENSION_APPS, app_registry.get_extension_config())\n"
            "    extension_registry.register(EXTENSION_TASKS, {\n"
            "        'methods': ['tasks/get', 'tasks/update', 'tasks/cancel'],\n"
            "        'activeTaskCount': task_store.count})"
        ),
        "Code structure:",
    )

    # SEP-2207
    doc.add_heading("SEP-2207: OIDC Refresh Token Guidance", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: OIDC spec says offline_access must not appear in scopes_supported for MCP servers. "
        "Refresh tokens are controlled via grant_types_supported instead."
    )
    add_code_block(
        doc,
        (
            "SCOPES_SUPPORTED = [_SERVER_NAME]  # NO offline_access\n\n"
            "def _validate_scopes_no_offline_access(scopes: list[str]):\n"
            "    if 'offline_access' in scopes:\n"
            "        raise ValueError(\n"
            "            'offline_access must not be in scopes_supported (SEP-2207)')\n\n"
            "_validate_scopes_no_offline_access(SCOPES_SUPPORTED)  # runs at import"
        ),
        "Code added:",
    )

    # SEP-2243
    doc.add_heading("SEP-2243: Mcp-Method / Mcp-Name Header Validation", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: Clients may send Mcp-Method and Mcp-Name headers for routing/logging. "
        "The server must validate these match the JSON-RPC body to prevent header injection."
    )
    add_code_block(
        doc,
        (
            "# In McpProtocolMiddleware.dispatch():\n"
            "header_method = request.headers.get('mcp-method')\n"
            "if header_method is not None and header_method != rpc_method:\n"
            "    return _jsonrpc_error(request_id, HEADER_MISMATCH,\n"
            "        f\"Mcp-Method '{header_method}' != JSON-RPC '{rpc_method}'\")\n\n"
            "# For tools/call — also validate Mcp-Name:\n"
            "if rpc_method == 'tools/call':\n"
            "    tool_name = body.get('params', {}).get('name')\n"
            "    header_name = request.headers.get('mcp-name')\n"
            "    if header_name is not None and tool_name and header_name != tool_name:\n"
            "        return _jsonrpc_error(request_id, HEADER_MISMATCH, ...)\n\n"
            "# Response headers:\n"
            "response.headers['x-mcp-method'] = rpc_method\n"
            "if tool_name: response.headers['x-mcp-name'] = tool_name"
        ),
        "Code added to dispatch():",
    )

    # SEP-2260
    doc.add_heading("SEP-2260: Server Request Association", level=2)
    doc.add_paragraph(
        "Verified structurally — No code changes needed.\n"
        "Why: SEP-2260 requires servers not to send standalone pushes (notifications without a pending client request). "
        "This server uses tools-first architecture: no resources, no prompts, no subscriptions. "
        "Therefore it never initiates server-to-client messages.\n"
        "Verified in TestSEP2260ServerRequestAssociation: no resource: or prompt: keys in components."
    )

    # SEP-2322
    doc.add_heading("SEP-2322: Multi Round-Trip Requests (MRTR)", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: Every tools/call response must include a resultType field. For simple tools that complete "
        "in one call, the value is 'complete'. The middleware post-processes the response to inject this field."
    )
    add_code_block(
        doc,
        (
            "async def _inject_result_type(self, response: Response) -> Response:\n"
            "    # Consume Starlette's one-use body_iterator\n"
            "    body_bytes = b''.join([chunk async for chunk in response.body_iterator])\n"
            "    if not body_bytes: return response\n"
            "    try:\n"
            "        data = json.loads(body_bytes)\n"
            "        if 'result' in data and isinstance(data['result'], dict):\n"
            "            data['result'].setdefault('resultType', 'complete')\n"
            "        new_body = json.dumps(data).encode()\n"
            "        # Reconstruct response — remove stale content-length\n"
            "        new_headers = {k: v for k, v in response.headers.items()\n"
            "                       if k.lower() != 'content-length'}\n"
            "        return Response(content=new_body, status_code=response.status_code,\n"
            "                        headers=new_headers, media_type=response.media_type)\n"
            "    except Exception:\n"
            "        return Response(content=body_bytes, ...)  # fallback\n\n"
            "# In dispatch() — called only for tools/call:\n"
            "if rpc_method == 'tools/call':\n"
            "    response = await self._inject_result_type(response)"
        ),
        "Code added:",
    )

    # SEP-2352
    doc.add_heading("SEP-2352: Client Credential Binding (Issuer Identifier)", level=2)
    doc.add_paragraph(
        "Modified files: oauth/service.py, oauth/controller.py, storage/storage_service.py"
    )
    doc.add_paragraph(
        "Why: Multi-issuer environments need tokens bound to a specific issuer. Authorization codes, "
        "access tokens, and refresh tokens are tagged with the issuer, and grant handlers verify the issuer matches."
    )
    add_code_block(
        doc,
        (
            "# oauth/service.py:\n"
            "class OAuthService:\n"
            "    def __init__(self, storage_service, issuer: str):\n"
            "        self.issuer = issuer\n"
            "    def create_authorization_code(self, ...):\n"
            "        code_data['issuer'] = self.issuer  # tag code with issuer\n"
            "    def store_access_token(self, ...):\n"
            "        token_data['issuer'] = self.issuer\n\n"
            "# oauth/controller.py — issuer verification:\n"
            "async def handle_authorization_code_grant(request, oauth_service):\n"
            "    code_data = await oauth_service.get_authorization_code(code)\n"
            "    if code_data['issuer'] != oauth_service.issuer:\n"
            "        raise ValueError('Issuer mismatch')\n\n"
            "# storage_service.py:\n"
            "# oauth_clients PRIMARY KEY changed to (issuer, client_id)"
        ),
        "Key code changes:",
    )

    # SEP-2468
    doc.add_heading("SEP-2468: iss in Authorization Responses", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/oauth/controller.py")
    doc.add_paragraph(
        "Why: RFC 9207 requires the authorization response to include the issuer identifier (iss parameter) "
        "so clients can verify they received the response from the expected authorization server."
    )
    add_code_block(
        doc,
        (
            "# In handle_callback():\n"
            "redirect_params = {\n"
            "    'code': authorization_code,\n"
            "    'state': state,\n"
            "    'iss': get_current_issuer(),  # <-- NEW per RFC 9207\n"
            "}\n\n"
            "# In api.py well-known metadata:\n"
            "'authorization_response_iss_parameter_supported': True"
        ),
        "Code added:",
    )

    # SEP-2549
    doc.add_heading(
        "SEP-2549: Deterministic tools/list Ordering + Cache Metadata", level=2
    )
    doc.add_paragraph("Modified file: template_mcp_server/src/mcp.py")
    doc.add_paragraph(
        "Why: Deterministic tool ordering enables client-side caching and LLM prompt cache hits. "
        "Without sorting, tool order can vary between restarts, invalidating cached prompts."
    )
    add_code_block(
        doc,
        (
            "def _ensure_deterministic_tool_order(self):\n"
            "    original_list_tools = self.mcp.list_tools\n"
            "    async def sorted_list_tools(**kwargs):\n"
            "        tools = await original_list_tools(**kwargs)\n"
            "        return sorted(tools, key=lambda t: t.name)\n"
            "    self.mcp.list_tools = sorted_list_tools\n\n"
            "def _get_cache_meta(self) -> dict:\n"
            "    return {\n"
            "        'ttlMs': settings.TOOL_CACHE_TTL_MS,     # default 300000 (5 min)\n"
            "        'cacheScope': settings.TOOL_CACHE_SCOPE,  # default 'public'\n"
            "    }\n\n"
            "# Each tool registered with:\n"
            "self.mcp.tool(output_schema=SCHEMA, meta=cache_meta)(tool_func)"
        ),
        "Code added:",
    )

    # SEP-2567
    doc.add_heading("SEP-2567: Session Removal", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: MCP 2026-07-28 removes sessions. The server runs in stateless HTTP mode — "
        "no Mcp-Session-Id header, no session tracking, no Last-Event-ID resumability."
    )
    add_code_block(
        doc,
        (
            "# In api.py — app construction:\n"
            "mcp_app = server.mcp.http_app(\n"
            "    path='/mcp',\n"
            "    stateless_http=settings.MCP_STATELESS_HTTP  # default: True\n"
            ")\n\n"
            "# settings.py:\n"
            "MCP_STATELESS_HTTP: bool = Field(default=True)"
        ),
        "Code changed:",
    )

    # SEP-2575
    doc.add_heading("SEP-2575: Stateless MCP", level=2)
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    doc.add_paragraph(
        "Why: Replaces initialize handshake with server/discover. Removed methods return -32023 errors. "
        "Per-request log level via _meta.logLevel replaces logging/setLevel."
    )
    add_code_block(
        doc,
        (
            "_REMOVED_METHODS = frozenset({\n"
            "    'ping', 'logging/setLevel',\n"
            "    'notifications/roots/list_changed', 'tasks/list',\n"
            "})\n\n"
            "def get_server_discover_result() -> dict:\n"
            "    return {\n"
            "        'protocolVersion': settings.MCP_PROTOCOL_VERSION,\n"
            "        'serverInfo': {'name': _SERVER_NAME, 'version': _get_version()},\n"
            "        'capabilities': {\n"
            "            'tools': {'listChanged': False},\n"
            "            'extensions': extension_registry.get_capabilities(),\n"
            "        },\n"
            "        'deprecations': deprecation_registry.to_list(),\n"
            "    }\n\n"
            "# In dispatch():\n"
            "if rpc_method == 'server/discover':\n"
            "    return _jsonrpc_success(request_id, get_server_discover_result())\n"
            "if rpc_method in _REMOVED_METHODS:\n"
            "    return _jsonrpc_error(request_id, METHOD_NOT_SUPPORTED,\n"
            "        f\"Method '{rpc_method}' is not supported\")\n\n"
            "# Per-request log level from _meta:\n"
            "meta_log_level = meta.get('logLevel') if isinstance(meta, dict) else None\n"
            "if meta_log_level: logger.setLevel(meta_log_level.upper())"
        ),
        "Key code:",
    )

    # SEP-2577
    doc.add_heading("SEP-2577: Deprecate Roots, Sampling, Logging", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/deprecation.py (43 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: Roots, sampling, and logging capabilities are deprecated in the 2026-07-28 spec. "
        "The server must advertise migration guidance in server/discover."
    )
    add_code_block(
        doc,
        (
            "# Pre-registered deprecation entries:\n"
            "deprecation_registry.register(DeprecationEntry(\n"
            "    feature='roots',\n"
            "    lifecycle=LIFECYCLE_DEPRECATED,\n"
            "    deprecated_since=_SPEC_VERSION,\n"
            "    replacement='Server-managed resource discovery',\n"
            "    migration='Remove roots/list_changed notifications',\n"
            "))\n"
            "# Similar entries for 'sampling' and 'logging'\n"
            "# (sampling -> MRTR, logging -> per-request _meta.logLevel)"
        ),
        "Code added:",
    )

    # SEP-2596
    doc.add_heading("SEP-2596: Feature Lifecycle / Deprecation Policy", level=2)
    doc.add_paragraph("New file: template_mcp_server/src/deprecation.py")
    doc.add_paragraph(
        "Why: Provides a structured registry for tracking feature lifecycle states (active -> deprecated -> removed) "
        "with migration guidance, enabling clients to adapt proactively."
    )
    add_code_block(
        doc,
        (
            "LIFECYCLE_ACTIVE = 'active'\n"
            "LIFECYCLE_DEPRECATED = 'deprecated'\n"
            "LIFECYCLE_REMOVED = 'removed'\n\n"
            "_SPEC_VERSION = '2026-07-28'      # constants, not hardcoded\n"
            "_PREV_SPEC_VERSION = '2025-11-05'\n\n"
            "class DeprecationEntry:\n"
            "    feature: str\n"
            "    lifecycle: str  # active | deprecated | removed\n"
            "    deprecated_since: str | None\n"
            "    removed_in: str | None\n"
            "    replacement: str | None\n"
            "    migration: str | None\n\n"
            "    def to_dict(self) -> dict:  # camelCase output\n"
            "        return {'feature': ..., 'deprecatedSince': ..., 'removedIn': ...}\n\n"
            "class DeprecationRegistry:\n"
            "    def register(self, entry: DeprecationEntry): ...\n"
            "    def get_by_lifecycle(self, lifecycle: str) -> list: ...\n"
            "    def to_list(self) -> list[dict]: ..."
        ),
        "Code structure:",
    )

    # SEP-1865
    doc.add_heading("SEP-1865: MCP Apps Extension", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/apps.py (35 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: MCP Apps allow servers to declare UI-capable applications that clients can discover and render. "
        "The server registers apps with metadata (appId, name, description, uiType, url) and serves them "
        "via apps/list and apps/get RPC methods."
    )
    add_code_block(
        doc,
        (
            "# apps.py — App model and registry:\n"
            "class AppEntry:\n"
            "    def __init__(self, app_id, name, *, description=None,\n"
            "                 ui_type='iframe', url=None, metadata=None): ...\n"
            "    def to_dict(self) -> dict:\n"
            "        return {'appId': ..., 'name': ..., 'uiType': ..., ...}\n\n"
            "class AppRegistry:\n"
            "    def register(self, entry: AppEntry): ...\n"
            "    def unregister(self, app_id: str) -> bool: ...\n"
            "    def get(self, app_id: str) -> AppEntry | None: ...\n"
            "    def list_apps(self) -> list[dict]: ...\n"
            "    def get_extension_config(self) -> dict:\n"
            "        return {'appCount': self.count, 'apps': self.list_apps()}\n\n"
            "app_registry = AppRegistry()  # module-level singleton"
        ),
        "Code structure:",
    )
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    add_code_block(
        doc,
        (
            "# Default app registration:\n"
            "app_registry.register(AppEntry(\n"
            "    app_id='health-dashboard',\n"
            "    name='Health Dashboard',\n"
            "    description='Server health and diagnostics',\n"
            "    ui_type='iframe', url='/health',\n"
            "))\n\n"
            "# Extension config uses live data:\n"
            "extension_registry.register(\n"
            "    EXTENSION_APPS, app_registry.get_extension_config())\n\n"
            "# RPC handlers in McpProtocolMiddleware:\n"
            "_APPS_METHODS = frozenset({'apps/list', 'apps/get'})\n\n"
            "def _handle_apps_rpc(self, rpc_method, request_id, body):\n"
            "    if rpc_method == 'apps/list':\n"
            "        return JSONResponse(content={'jsonrpc': '2.0', 'id': request_id,\n"
            "            'result': {'apps': app_registry.list_apps()}})\n"
            "    if rpc_method == 'apps/get':\n"
            "        app_id = params.get('appId')\n"
            "        entry = app_registry.get(app_id)\n"
            "        if entry is None: return error(...)\n"
            "        return JSONResponse(content={..., 'result': entry.to_dict()})"
        ),
        "Code added:",
    )

    # SEP-2663
    doc.add_heading("SEP-2663: Tasks Extension", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/tasks.py (73 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: Tasks represent long-running operations. The server needs a task store to track "
        "task lifecycle (pending -> running -> completed/failed/cancelled). tasks/list is removed "
        "per SEP-2575; tasks/get, tasks/update, tasks/cancel are fully implemented."
    )
    add_code_block(
        doc,
        (
            "# tasks.py — Task model and store:\n"
            "STATUS_PENDING = 'pending'\n"
            "STATUS_RUNNING = 'running'\n"
            "STATUS_COMPLETED = 'completed'\n"
            "STATUS_FAILED = 'failed'\n"
            "STATUS_CANCELLED = 'cancelled'\n\n"
            "class TaskEntry:\n"
            "    def __init__(self, task_id, method, *, status='pending',\n"
            "                 progress=None, message=None, result=None): ...\n"
            "    @property\n"
            "    def is_terminal(self) -> bool:\n"
            "        return self.status in {completed, failed, cancelled}\n\n"
            "class TaskStore:\n"
            "    def create(self, task_id, method, **kw) -> TaskEntry: ...\n"
            "    def get(self, task_id) -> TaskEntry | None: ...\n"
            "    def update(self, task_id, *, status=None, progress=None,\n"
            "              message=None, result=None) -> TaskEntry | None:\n"
            "        # Returns None if terminal or missing\n"
            "        # Clamps progress to [0.0, 1.0]\n"
            "        # Validates status against allowed set\n"
            "    def cancel(self, task_id) -> TaskEntry | None: ...\n"
            "    def active_tasks(self) -> list[TaskEntry]: ..."
        ),
        "Code structure:",
    )
    doc.add_paragraph("Modified file: template_mcp_server/src/api.py")
    add_code_block(
        doc,
        (
            "# Extension config uses live task count:\n"
            "extension_registry.register(EXTENSION_TASKS, {\n"
            "    'methods': ['tasks/get', 'tasks/update', 'tasks/cancel'],\n"
            "    'activeTaskCount': len(task_store.active_tasks()),\n"
            "})\n\n"
            "# Full RPC handler in McpProtocolMiddleware:\n"
            "def _handle_task_rpc(self, rpc_method, request_id, body):\n"
            "    task_id = params.get('taskId')\n"
            "    if rpc_method == 'tasks/get':\n"
            "        entry = task_store.get(task_id)\n"
            "        if entry: return success(entry.to_dict())\n"
            "    if rpc_method == 'tasks/cancel':\n"
            "        entry = task_store.cancel(task_id)  # None if terminal\n"
            "    if rpc_method == 'tasks/update':\n"
            "        # Extracts status, progress, message, result from params\n"
            "        entry = task_store.update(task_id, **fields)\n\n"
            "# tasks/list in _REMOVED_METHODS -> returns -32023"
        ),
        "Code added:",
    )

    # Error Codes
    doc.add_heading("Error Codes: Allocation Policy + Renumbering", level=2)
    doc.add_paragraph(
        "New file: template_mcp_server/src/errors.py (27 statements, 100% covered)"
    )
    doc.add_paragraph(
        "Why: MCP defines error code ranges. Implementation-defined codes are -32000 to -32099, "
        "MCP-reserved codes are -32600 to -32699. Each error has a named constant and exception class."
    )
    add_code_block(
        doc,
        (
            "# Range constants:\n"
            "IMPL_DEFINED_RANGE_MIN = -32099\n"
            "IMPL_DEFINED_RANGE_MAX = -32000\n"
            "MCP_RESERVED_RANGE_MIN = -32699\n"
            "MCP_RESERVED_RANGE_MAX = -32600\n\n"
            "# Error codes:\n"
            "HEADER_MISMATCH = -32020\n"
            "MISSING_REQUIRED_CLIENT_CAPABILITY = -32021\n"
            "UNSUPPORTED_PROTOCOL_VERSION = -32022\n"
            "METHOD_NOT_SUPPORTED = -32023\n"
            "RESOURCE_NOT_FOUND = -32602\n\n"
            "# Each has an exception class extending McpError:\n"
            "class HeaderMismatchError(McpError): code = HEADER_MISMATCH\n"
            "class MethodNotSupportedError(McpError): code = METHOD_NOT_SUPPORTED\n"
            "# etc."
        ),
        "Code structure:",
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 9: Testing Guide
    # ══════════════════════════════════════════════════════════════════════
    h9 = doc.add_heading("9. Testing Guide — How to Verify Each SEP", level=1)
    add_bookmark(h9, "section_9")

    doc.add_heading("Prerequisites", level=2)
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    run = p.add_run(
        "# Install dependencies\n"
        "uv sync --all-extras\n\n"
        "# Start local Postgres (only needed for OAuth integration tests)\n"
        "docker compose up -d postgres\n\n"
        "# Run all tests\n"
        "uv run pytest tests/ -v"
    )
    run.font.name = "Consolas"
    run.font.size = Pt(9)

    test_commands = [
        (
            "SEP-414: W3C Trace Context",
            [
                "uv run pytest tests/test_tracing.py -v",
                "uv run pytest tests/test_api.py::TestSEP414TraceContext -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-H "traceparent: 00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\' -v\n'
            "# Verify response includes traceparent with same trace_id but new span_id",
        ),
        (
            "SEP-837: application_type",
            [
                'uv run pytest tests/test_oauth_service.py -k "application_type" -v',
            ],
            None,
        ),
        (
            "SEP-991: CIMD + DCR Deprecation",
            [
                "uv run pytest tests/test_api.py::TestRegisterEndpointRoute -v",
                "uv run pytest tests/test_api.py::TestWellKnownEndpoints -v",
            ],
            'curl -X POST http://localhost:5001/auth/register -H "Content-Type: application/json" '
            '-d \'{"client_name":"test","redirect_uris":["http://localhost:3000/cb"]}\' -v\n'
            "# Look for: Deprecation: true header",
        ),
        (
            "SEP-2106: JSON Schema 2020-12",
            [
                "uv run pytest tests/test_schema.py -v",
                'uv run pytest tests/test_mcp.py -k "schema" -v',
            ],
            None,
        ),
        (
            "SEP-2133: Extensions Framework",
            [
                "uv run pytest tests/test_extensions.py -v",
                "uv run pytest tests/test_api.py::TestSEP2133Extensions -v",
            ],
            None,
        ),
        (
            "SEP-2207: offline_access Exclusion",
            [
                "uv run pytest tests/test_api.py::TestSEP2207OfflineAccessExclusion -v",
            ],
            "curl http://localhost:5001/.well-known/oauth-protected-resource | jq .scopes_supported\n"
            '# Should NOT contain "offline_access"',
        ),
        (
            "SEP-2243: Mcp-Method / Mcp-Name Headers",
            [
                "uv run pytest tests/test_api.py::TestSEP2243McpHeaderValidation -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-H "mcp-method: tools/list" -d \'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\' -v\n'
            "# Response includes: x-mcp-method: tools/list",
        ),
        (
            "SEP-2260: No Standalone Server Pushes",
            [
                "uv run pytest tests/test_api.py::TestSEP2260ServerRequestAssociation -v",
            ],
            None,
        ),
        (
            "SEP-2322: MRTR (resultType)",
            [
                "uv run pytest tests/test_api.py::TestSEP2322MRTR -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"calculate_bmi","arguments":{"height":"175","weight":"70"}}}\'\n'
            '# Response result should include: "resultType": "complete"',
        ),
        (
            "SEP-2352: Issuer Identifier",
            [
                'uv run pytest tests/test_oauth_controller.py -k "issuer" -v',
                'uv run pytest tests/test_oauth_service.py -k "issuer" -v',
            ],
            None,
        ),
        (
            "SEP-2468: iss in Auth Responses",
            [
                'uv run pytest tests/test_oauth_controller.py -k "iss" -v',
            ],
            None,
        ),
        (
            "SEP-2549: Deterministic Tool Order",
            [
                "uv run pytest tests/test_mcp.py -v",
            ],
            None,
        ),
        (
            "SEP-2567: Session Removal",
            [
                "uv run pytest tests/test_api.py::TestSEP2567SessionRemoval -v",
            ],
            None,
        ),
        (
            "SEP-2575: Stateless MCP",
            [
                "uv run pytest tests/test_api.py::TestSEP2575StatelessMcp -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"server/discover"}\'\n\n'
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"ping"}\'\n'
            "# Returns error code -32023",
        ),
        (
            "SEP-2577: Deprecate Roots/Sampling/Logging",
            [
                "uv run pytest tests/test_deprecation.py -v",
                "uv run pytest tests/test_api.py::TestSEP2577DeprecateRootsSamplingLogging -v",
            ],
            None,
        ),
        (
            "SEP-2596: Feature Lifecycle",
            [
                "uv run pytest tests/test_deprecation.py -v",
                "uv run pytest tests/test_api.py::TestSEP2596DeprecationMetadata -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"server/discover"}\' | jq .result.deprecations\n'
            "# Should list 15 entries",
        ),
        (
            "SEP-1865: Apps Extension",
            [
                "uv run pytest tests/test_apps.py -v",
                "uv run pytest tests/test_api.py::TestSEP1865AppsExtension -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"apps/list"}\'\n'
            "# Returns list of registered apps including health-dashboard",
        ),
        (
            "SEP-2663: Tasks Extension",
            [
                "uv run pytest tests/test_tasks.py -v",
                "uv run pytest tests/test_api.py::TestSEP2663Tasks -v",
            ],
            'curl -X POST http://localhost:5001/mcp -H "Content-Type: application/json" '
            '-d \'{"jsonrpc":"2.0","id":1,"method":"tasks/list"}\'\n'
            "# Returns -32023 (METHOD_NOT_SUPPORTED)",
        ),
        (
            "Error Codes",
            [
                "uv run pytest tests/test_errors.py -v",
            ],
            None,
        ),
    ]

    for sep_name, commands, manual in test_commands:
        doc.add_heading(sep_name, level=3)

        p = doc.add_paragraph()
        run = p.add_run("Automated tests:")
        run.bold = True

        for cmd in commands:
            p = doc.add_paragraph()
            run = p.add_run(cmd)
            run.font.name = "Consolas"
            run.font.size = Pt(9)

        if manual:
            p = doc.add_paragraph()
            run = p.add_run("Manual verification:")
            run.bold = True

            p = doc.add_paragraph()
            run = p.add_run(manual)
            run.font.name = "Consolas"
            run.font.size = Pt(9)

    doc.add_heading("Run All Tests At Once", level=3)
    p = doc.add_paragraph()
    run = p.add_run(
        "# Full suite with coverage\n"
        "uv run pytest tests/ --cov=template_mcp_server --cov-report=term-missing -v\n\n"
        "# Quick pass/fail\n"
        "uv run pytest tests/ -q"
    )
    run.font.name = "Consolas"
    run.font.size = Pt(9)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 10: Code Breakage Analysis
    # ══════════════════════════════════════════════════════════════════════
    h10 = doc.add_heading("10. Code Breakage Analysis", level=1)
    add_bookmark(h10, "section_10")

    doc.add_heading("Current Status: No breakage detected", level=2)
    doc.add_paragraph(
        "710 tests pass with 0 failures, 0 errors.\n"
        "100% test coverage across all 28 source files.\n"
        "All imports resolve correctly.\n"
        "No circular dependencies detected.\n"
        "All module-level code executes without errors."
    )

    doc.add_heading("Potential Risk Areas", level=2)
    risk_rows = [
        (
            "conftest.py mocks structlog/fastmcp",
            "Tests don't exercise real structlog or FastMCP paths",
            "trace_context_processor tests use patch.dict('sys.modules') to inject mock structlog properly",
        ),
        (
            "_inject_result_type consumes body_iterator",
            "One-use iterator — if consumed but exception occurs, must reconstruct response",
            "except block reconstructs Response from consumed body bytes — tested",
        ),
        (
            "Module-level extension registration",
            "Runs at import time based on settings",
            "Setting is True by default; toggling uses mocked settings",
        ),
        (
            "_get_session_secret() in production",
            "Raises ValueError if SESSION_SECRET not set",
            "Tested in TestGetSessionSecret.test_production_without_secret_raises",
        ),
        (
            "McpProtocolMiddleware reads body twice",
            "Could cause issues if body not cached",
            "request.body() caches internally in Starlette — verified by middleware tests",
        ),
    ]
    add_table(doc, ["Area", "Risk", "Mitigation"], risk_rows, [2.0, 2.0, 2.5])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════
    # Summary of Changes
    # ══════════════════════════════════════════════════════════════════════
    doc.add_heading("Summary of Code Changes Made During This Audit", level=1)

    changes_rows = [
        (
            "Extract _extract_trace_context() to eliminate duplication",
            "api.py",
            "Reduced 12 lines of duplicate code",
        ),
        (
            "Extract _SERVER_NAME constant",
            "api.py",
            "4 usages consolidated to 1 constant",
        ),
        (
            "Use settings.MCP_PROTOCOL_VERSION in error message",
            "api.py",
            "Removed hardcoded spec version",
        ),
        (
            "Extract _SPEC_VERSION and _PREV_SPEC_VERSION constants",
            "deprecation.py",
            "14 hardcoded date strings consolidated",
        ),
        (
            'Fix MCP_TRANSPORT_PROTOCOL: "http" to "streamable-http"',
            "kind + openshift configmap.yaml",
            "Fixed startup validation failure in K8s",
        ),
        (
            "Add SEP settings to ConfigMaps",
            "Both configmap.yaml files",
            "Self-documenting deployment configs",
        ),
        (
            "Remove duplicate TestSEP991DCRDeprecation test class",
            "tests/test_api.py",
            "Eliminated 1 duplicate test",
        ),
        (
            "Add BMI tool tests (16 tests)",
            "tests/test_bmi_tool.py (NEW)",
            "100% coverage: all WHO categories, validation",
        ),
        (
            "Add email tool tests (9 tests)",
            "tests/test_email_tool.py (NEW)",
            "100% coverage: API key, import guard, async",
        ),
        (
            "Add web search tests (12 tests)",
            "tests/test_web_search_tool.py (EXPANDED)",
            "100% coverage: retry, timeout, dedup, truncation",
        ),
        (
            "Add OAuth routes tests (15 tests)",
            "tests/test_oauth_routes.py (NEW)",
            "100% coverage: all 6 endpoints, init guards",
        ),
        (
            "Expand main.py tests (12 total)",
            "tests/test_main.py (EXPANDED)",
            "100% coverage: SSL, handle_startup_error, run()",
        ),
        (
            "Add outputSchema validation test",
            "tests/test_mcp.py (+1 test)",
            "100% coverage: line 107 branch",
        ),
        (
            "Add api.py edge case tests",
            "tests/test_api.py (+3 tests)",
            "100% coverage: missing method, trace disabled",
        ),
        (
            "Implement MCP Apps extension (SEP-1865)",
            "apps.py (NEW), api.py",
            "Full AppEntry/AppRegistry with apps/list and apps/get RPC handlers",
        ),
        (
            "Implement Tasks extension (SEP-2663)",
            "tasks.py (NEW), api.py",
            "Full TaskEntry/TaskStore with tasks/get/update/cancel RPC handlers",
        ),
        (
            "Add apps extension tests (13 tests)",
            "tests/test_apps.py (NEW)",
            "100% coverage: AppEntry, AppRegistry, module singleton",
        ),
        (
            "Add tasks extension tests (22 tests)",
            "tests/test_tasks.py (NEW)",
            "100% coverage: TaskEntry, TaskStore, all lifecycle states",
        ),
        (
            "Update SEP-1865 + SEP-2663 API tests",
            "tests/test_api.py (EXPANDED)",
            "6 apps tests + 12 tasks tests replacing stubs",
        ),
    ]
    add_table(doc, ["Change", "File(s)", "Impact"], changes_rows, [2.8, 1.8, 2.0])

    return doc


if __name__ == "__main__":
    doc = build_document()
    output_path = (
        "/Users/pratisin/ai_factory/template-mcp-server/docs/MCP_SEP_AUDIT_REPORT.docx"
    )
    doc.save(output_path)
    print(f"Document saved to: {output_path}")
