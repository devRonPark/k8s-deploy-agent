from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
import re
import tempfile
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, urlparse

from k8s_deploy_agent.config import DemoConfig
from k8s_deploy_agent.redaction import assert_no_secret_values


FORM_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("app_name", "Application name", "payments-api"),
    ("environment", "Environment", "dev"),
    ("target_namespace", "Target namespace", "payments-dev"),
    ("source_repo_url", "Source repository URL", "internal source repository"),
    ("source_branch", "Source branch", "main"),
    ("source_credential_id", "Source credential ID", "credential ID only"),
    ("source_access_token_env", "Source access token env", "K8S_DEPLOY_AGENT_SOURCE_TOKEN"),
    ("gitops_repo_url", "GitOps repository URL", "internal GitOps repository"),
    ("gitops_branch", "GitOps branch", "main"),
    ("gitops_path", "GitOps path", "apps/payments-api"),
    ("gitops_credential_id", "GitOps credential ID", "credential ID only"),
    ("registry_url", "Registry URL", "registry.internal/acme"),
    ("registry_project", "Registry project", "payments"),
    ("registry_credential_id", "Registry credential ID", "credential ID only"),
    ("registry_ca_cert_credential_id", "Registry CA credential ID", "credential ID only"),
)

ENV_VAR_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


@dataclass(frozen=True)
class ConsoleValidationResult:
    ok: bool
    messages: tuple[str, ...]
    config: DemoConfig | None = None

    @property
    def status_label(self) -> str:
        return "valid" if self.ok else "needs review"


@dataclass(frozen=True)
class ConsoleDryRunResult:
    ok: bool
    messages: tuple[str, ...]
    config: DemoConfig | None = None
    validation: ConsoleValidationResult | None = None
    output_dir: str | None = None
    generated_paths: tuple[str, ...] = ()


def validate_console_payload(values: Mapping[str, str]) -> ConsoleValidationResult:
    payload = {field: str(values.get(field, "")).strip() for field, _, _ in FORM_FIELDS}
    messages: list[str] = []
    config: DemoConfig | None = None

    try:
        config = DemoConfig.from_mapping(payload)
    except ValueError as error:
        messages.append(str(error))

    source_env = payload.get("source_access_token_env", "")
    if source_env and not ENV_VAR_NAME_RE.fullmatch(source_env):
        messages.append(
            "source_access_token_env must be an uppercase environment variable name"
        )

    redaction_probe = "\n".join(
        f"{field}: {value}"
        for field, value in payload.items()
        if value and field != "source_access_token_env"
    )
    if redaction_probe:
        try:
            assert_no_secret_values({"console-form": redaction_probe})
        except ValueError as error:
            messages.append(str(error))

    return ConsoleValidationResult(ok=not messages and config is not None, messages=tuple(messages), config=config)


def run_console_dry_run(values: Mapping[str, str]) -> ConsoleDryRunResult:
    validation = validate_console_payload(values)
    if not validation.ok or validation.config is None:
        return ConsoleDryRunResult(
            ok=False,
            messages=validation.messages,
            config=validation.config,
            validation=validation,
        )

    output_dir = tempfile.mkdtemp(prefix="k8s-deploy-agent-web-")
    try:
        from k8s_deploy_agent.cli import run_dry_run_with_config

        generated_paths = run_dry_run_with_config(validation.config, None, output_dir)
    except ValueError as error:
        return ConsoleDryRunResult(
            ok=False,
            messages=(str(error),),
            config=validation.config,
            validation=validation,
            output_dir=output_dir,
        )

    return ConsoleDryRunResult(
        ok=True,
        messages=(),
        config=validation.config,
        validation=validation,
        output_dir=output_dir,
        generated_paths=tuple(generated_paths),
    )


def render_operator_console(
    validation: ConsoleValidationResult | None = None,
    dry_run: ConsoleDryRunResult | None = None,
) -> str:
    validation_html = _render_validation_result(validation)
    dry_run_html = _render_dry_run_result(dry_run)
    preview_html = _render_generated_asset_preview(dry_run)
    checklist_html = _render_validation_checklist(dry_run)
    status_class = "warn"
    status_label = "awaiting input"
    if dry_run is not None:
        status_class = "ok" if dry_run.ok else "blocked"
        status_label = "dry-run complete" if dry_run.ok else "dry-run blocked"
    elif validation is not None:
        status_class = "ok" if validation.ok else "blocked"
        status_label = validation.status_label

    template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>k8s-deploy-agent operator console</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #657184;
      --line: #d9e0ea;
      --accent: #1264d8;
      --accent-soft: #e7f0ff;
      --ok: #0e7a55;
      --warn: #946200;
      --blocked: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      min-height: 64px;
      padding: 10px 0;
    }
    .brand {
      min-width: 0;
    }
    .brand strong {
      display: block;
      font-size: 18px;
      overflow-wrap: anywhere;
    }
    .brand span, .status {
      color: var(--muted);
      font-size: 13px;
    }
    main {
      padding: 24px 0 40px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    h1, h2, h3 {
      margin: 0;
      letter-spacing: 0;
    }
    h1 { font-size: 22px; }
    h2 { font-size: 15px; }
    h3 { font-size: 14px; }
    .panel-body {
      padding: 16px;
    }
    .form-grid {
      display: grid;
      gap: 12px;
    }
    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    input {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      font: inherit;
      padding: 7px 9px;
    }
    input:disabled {
      background: #f2f5f9;
      color: #526071;
    }
    .button-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 4px;
    }
    button {
      min-height: 36px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: var(--accent);
      color: #ffffff;
      font: inherit;
      font-weight: 650;
      padding: 7px 12px;
    }
    button.secondary {
      background: #ffffff;
      color: var(--accent);
    }
    button:disabled {
      border-color: var(--line);
      background: #edf1f6;
      color: #758294;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 7px;
      min-height: 106px;
      padding: 12px;
    }
    .card span {
      color: var(--muted);
      display: block;
      font-size: 12px;
      margin-top: 8px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 2px 9px;
      font-size: 12px;
      font-weight: 650;
      background: var(--accent-soft);
      color: var(--accent);
    }
    .pill.ok {
      background: #e6f6ef;
      color: var(--ok);
    }
    .pill.warn {
      background: #fff4d7;
      color: var(--warn);
    }
    .pill.blocked {
      background: #fde8e6;
      color: var(--blocked);
    }
    .stack {
      display: grid;
      gap: 16px;
    }
    .checklist {
      display: grid;
      gap: 10px;
    }
    .check {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px 12px;
    }
    .check p {
      margin: 2px 0 0;
      color: var(--muted);
      font-size: 13px;
    }
    .result {
      display: grid;
      gap: 10px;
    }
    .result-note {
      color: var(--muted);
      font-size: 13px;
      margin: 0;
    }
    .result-list {
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
    }
    .result-list li + li {
      margin-top: 6px;
    }
    code {
      background: #eef2f7;
      border: 1px solid #dfe5ee;
      border-radius: 5px;
      padding: 2px 5px;
      overflow-wrap: anywhere;
    }
    @media (max-width: 900px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }
      .layout, .cards {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <strong>k8s-deploy-agent operator console</strong>
        <span>Local web UI for on-premise Kubernetes migration preparation</span>
      </div>
      <div class="status">offline-first · loopback server</div>
    </div>
  </header>
  <main class="wrap">
    <div class="layout">
      <section>
        <div class="section-head">
          <h2>Project Onboarding</h2>
          <span class="pill warn">form shell</span>
        </div>
        <div class="panel-body">
            <form class="form-grid" method="post" action="/validate">
            __FORM_INPUTS__
            <div class="button-row">
              <button type="submit">Validate payload</button>
              <button type="submit" formaction="/dry-run">Run dry-run</button>
              <button type="reset" class="secondary">Clear</button>
            </div>
          </form>
        </div>
      </section>
      <div class="stack">
        <section>
          <div class="section-head">
            <h2>Validation Result</h2>
            <span class="pill __STATUS_CLASS__">__STATUS_LABEL__</span>
          </div>
          <div class="panel-body result">
            __VALIDATION_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>Dry-run Execution</h2>
            <span class="pill __DRY_RUN_CLASS__">__DRY_RUN_LABEL__</span>
          </div>
          <div class="panel-body result">
            __DRY_RUN_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>Generated Asset Preview</h2>
            <span class="pill __PREVIEW_CLASS__">__PREVIEW_LABEL__</span>
          </div>
          <div class="panel-body result">
            __PREVIEW_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>Workflow</h2>
            <span class="pill ok">local</span>
          </div>
          <div class="panel-body cards">
            <div class="card">
              <h3>1. Validate Inputs</h3>
              <span>Collect credential IDs and environment variable names. Raw secret values stay out of UI state.</span>
            </div>
            <div class="card">
              <h3>2. Run Dry-run</h3>
              <span>Reuse the existing analyzer, renderers, and redaction guard from the CLI pipeline.</span>
            </div>
            <div class="card">
              <h3>3. Review Assets</h3>
              <span>Preview report, Jenkinsfile, Fleet config, and Kubernetes manifests before export.</span>
            </div>
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>Validation Checklist</h2>
            <span class="pill __CHECKLIST_CLASS__">__CHECKLIST_LABEL__</span>
          </div>
          __CHECKLIST_HTML__
        </section>
      </div>
    </div>
  </main>
</body>
</html>
"""
    return (
        template.replace("__FORM_INPUTS__", _form_inputs())
        .replace("__STATUS_CLASS__", status_class)
        .replace("__STATUS_LABEL__", status_label)
        .replace("__VALIDATION_HTML__", validation_html)
        .replace("__DRY_RUN_CLASS__", "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn"))
        .replace(
            "__DRY_RUN_LABEL__",
            "completed" if dry_run and dry_run.ok else ("needs review" if dry_run else "awaiting run"),
        )
        .replace("__DRY_RUN_HTML__", dry_run_html)
        .replace("__PREVIEW_CLASS__", "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn"))
        .replace(
            "__PREVIEW_LABEL__",
            "ready" if dry_run and dry_run.ok else ("blocked" if dry_run else "awaiting run"),
        )
        .replace("__PREVIEW_HTML__", preview_html)
        .replace("__CHECKLIST_CLASS__", "ok" if dry_run and dry_run.ok else ("warn" if dry_run else "blocked"))
        .replace(
            "__CHECKLIST_LABEL__",
            "pass" if dry_run and dry_run.ok else ("pending" if dry_run is None else "blocked"),
        )
        .replace("__CHECKLIST_HTML__", checklist_html)
    )


def _render_validation_result(result: ConsoleValidationResult | None) -> str:
    if result is None:
        return (
            '<p class="result-note">Awaiting validation. '
            "The console accepts `DemoConfig` compatible payloads and blocks raw secret-like values.</p>"
        )

    if result.ok and result.config is not None:
        items = [
            ("Application", result.config.app_name),
            ("Environment", result.config.environment),
            ("Namespace", result.config.namespace),
            ("Source repo", result.config.source_repo_url),
            ("GitOps repo", result.config.gitops_repo_url),
        ]
        details = "".join(
            f"<li><strong>{escape(label)}</strong>: <code>{escape(value)}</code></li>" for label, value in items
        )
        return f"""
<span class="pill ok">validated</span>
<p class="result-note">Payload accepted. The console can hand the config to the existing dry-run pipeline.</p>
<ul class="result-list">{details}</ul>
"""

    messages = "".join(f"<li>{escape(message)}</li>" for message in result.messages)
    return f"""
<span class="pill blocked">blocked</span>
<p class="result-note">Payload rejected. Review the errors below before running dry-run or export preparation.</p>
<ul class="result-list">{messages}</ul>
"""


def _render_dry_run_result(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return '<p class="result-note">Submit the form with <code>Run dry-run</code> to generate assets in a local output directory.</p>'

    if result.ok and result.config is not None and result.output_dir is not None:
        items = [
            ("Output dir", result.output_dir),
            ("Generated files", ", ".join(result.generated_paths) if result.generated_paths else "-"),
            ("Namespace", result.config.namespace),
        ]
        details = "".join(
            f"<li><strong>{escape(label)}</strong>: <code>{escape(value)}</code></li>" for label, value in items
        )
        return f"""
<span class="pill ok">completed</span>
<p class="result-note">Dry-run reused the existing pipeline and wrote local assets for review.</p>
<ul class="result-list">{details}</ul>
"""

    messages = "".join(f"<li>{escape(message)}</li>" for message in result.messages)
    return f"""
<span class="pill blocked">blocked</span>
<p class="result-note">Dry-run did not complete. Fix the blocking issue and rerun.</p>
<ul class="result-list">{messages}</ul>
"""


def _render_generated_asset_preview(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return '<p class="result-note">Run dry-run to inspect generated files from the local output directory.</p>'

    if not result.ok or result.output_dir is None:
        return '<p class="result-note">Generated asset preview is unavailable until dry-run completes successfully.</p>'

    output_dir = Path(result.output_dir)
    preview_paths = (
        ".agent/reports/repository-analysis.md",
        "dockerfile-proposals/VALIDATION.md",
        "Jenkinsfile",
        "gitops/fleet.yaml",
        "gitops/base/namespace.yaml",
    )
    items = []
    for relative_path in preview_paths:
        file_path = output_dir / relative_path
        if not file_path.is_file():
            continue
        snippet = "\n".join(file_path.read_text(encoding="utf-8").splitlines()[:8])
        items.append(
            f"""<details class="artifact" open>
              <summary><strong>{escape(relative_path)}</strong></summary>
              <pre style="margin: 10px 0 0; white-space: pre-wrap;">{escape(snippet)}</pre>
            </details>"""
        )

    if not items:
        return '<p class="result-note">No previewable files were found in the local output directory.</p>'

    return "".join(items)


def _render_validation_checklist(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return """
<div class="panel-body checklist">
  <div class="check">
    <div>
      <h3>Secret redaction</h3>
      <p><code>assert_no_secret_values</code> must pass before write-back preparation.</p>
    </div>
    <span class="pill warn">pending</span>
  </div>
  <div class="check">
    <div>
      <h3>Generated assets</h3>
      <p>Report, Jenkinsfile, Fleet config, Namespace, Deployment, Service, and ConfigMap must exist.</p>
    </div>
    <span class="pill warn">pending</span>
  </div>
  <div class="check">
    <div>
      <h3>On-prem LLM</h3>
      <p>Recommendations are optional review text and never mutate generated files automatically.</p>
    </div>
    <span class="pill ok">optional</span>
  </div>
</div>
"""

    if not result.ok or result.output_dir is None or result.config is None:
        messages = "".join(f"<li>{escape(message)}</li>" for message in result.messages)
        return f"""
<div class="panel-body checklist">
  <div class="check">
    <div>
      <h3>Secret redaction</h3>
      <p>Validation blocked before write-back preparation.</p>
    </div>
    <span class="pill blocked">blocked</span>
  </div>
  <div class="check">
    <div>
      <h3>Generated assets</h3>
      <p>Preview and manifest checks are unavailable until dry-run succeeds.</p>
    </div>
    <span class="pill blocked">blocked</span>
  </div>
  <div class="check">
    <div>
      <h3>Dry-run errors</h3>
      <ul class="result-list">{messages}</ul>
    </div>
    <span class="pill blocked">blocked</span>
  </div>
</div>
"""

    output_dir = Path(result.output_dir)
    required_files = {
        ".agent/reports/repository-analysis.md",
        "Jenkinsfile",
        "gitops/fleet.yaml",
        "gitops/base/namespace.yaml",
    }
    missing = sorted(path for path in required_files if not (output_dir / path).is_file())
    namespace_file = output_dir / "gitops/base/namespace.yaml"
    namespace_matches = result.config.namespace in namespace_file.read_text(encoding="utf-8") if namespace_file.is_file() else False
    generated_ok = not missing
    secret_ok = result.ok
    dockerfile_validation = output_dir / "dockerfile-proposals/VALIDATION.md"
    dockerfile_validation_ok = dockerfile_validation.is_file() and "blocked" not in dockerfile_validation.read_text(
        encoding="utf-8"
    )
    checklist = [
        (
            "Secret redaction",
            "assert_no_secret_values passed on generated assets.",
            "ok" if secret_ok else "blocked",
        ),
        (
            "Generated assets",
            "Report, Jenkinsfile, Fleet config, and namespace manifest exist." if generated_ok else f"Missing: {', '.join(missing)}",
            "ok" if generated_ok else "blocked",
        ),
        (
            "Namespace alignment",
            f"Namespace manifest includes {result.config.namespace}." if namespace_matches else "Namespace manifest does not match the target namespace.",
            "ok" if namespace_matches else "blocked",
        ),
        (
            "Dockerfile proposals",
            "Dockerfile/.dockerignore proposals passed review-only validation."
            if dockerfile_validation_ok
            else "Dockerfile proposal validation is missing or blocked.",
            "ok" if dockerfile_validation_ok else "blocked",
        ),
        (
            "On-prem LLM",
            "Recommendations remain review-only and are not auto-applied.",
            "ok",
        ),
    ]
    items = "\n".join(
        f"""<div class="check">
      <div>
        <h3>{escape(title)}</h3>
        <p>{escape(description)}</p>
      </div>
      <span class="pill {escape(status)}">{escape(status)}</span>
    </div>"""
        for title, description, status in checklist
    )
    return f'<div class="panel-body checklist">{items}</div>'


def _form_inputs() -> str:
    fields = []
    for name, label, placeholder in FORM_FIELDS:
        fields.append(
            f"""<label>{escape(label)}
              <input name="{escape(name)}" placeholder="{escape(placeholder)}">
            </label>"""
        )
    return "\n".join(fields)


class OperatorConsoleHandler(BaseHTTPRequestHandler):
    server_version = "k8s-deploy-agent-web/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        body = render_operator_console().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/validate", "/dry-run"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8")
        payload = {key: values[-1] for key, values in parse_qs(raw_body, keep_blank_values=True).items()}
        if path == "/validate":
            validation = validate_console_payload(payload)
            body = render_operator_console(validation=validation).encode("utf-8")
        else:
            dry_run = run_console_dry_run(payload)
            body = render_operator_console(validation=dry_run.validation, dry_run=dry_run).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_web_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), OperatorConsoleHandler)
    print(f"operator console listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("operator console stopped")
    finally:
        server.server_close()
