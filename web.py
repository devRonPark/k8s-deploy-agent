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
    ("app_name", "애플리케이션 이름", "payments-api"),
    ("environment", "환경", "dev"),
    ("target_namespace", "대상 namespace", "payments-dev"),
    ("source_repo_url", "Source repository URL", "internal source repository"),
    ("source_branch", "Source branch", "main"),
    ("source_credential_id", "Source credential ID", "credential ID만 입력"),
    ("source_access_token_env", "Source access token env", "K8S_DEPLOY_AGENT_SOURCE_TOKEN"),
    ("gitops_repo_url", "GitOps repository URL", "internal GitOps repository"),
    ("gitops_branch", "GitOps branch", "main"),
    ("gitops_path", "GitOps path", "apps/payments-api"),
    ("gitops_credential_id", "GitOps credential ID", "credential ID만 입력"),
    ("registry_url", "Registry URL", "registry.internal/acme"),
    ("registry_project", "Registry project", "payments"),
    ("registry_credential_id", "Registry credential ID", "credential ID만 입력"),
    ("registry_ca_cert_credential_id", "Registry CA credential ID", "credential ID만 입력"),
)
FORM_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "작업 대상",
        "application 이름, 환경, namespace를 먼저 고정합니다.",
        ("app_name", "environment", "target_namespace"),
    ),
    (
        "Source repository",
        "clone 또는 서버 local path 중 하나로 분석 대상을 선택합니다.",
        ("source_repo_url", "source_branch", "source_credential_id", "source_access_token_env"),
    ),
    (
        "GitOps target",
        "Rancher Fleet 산출물이 놓일 내부 GitOps repository 위치입니다.",
        ("gitops_repo_url", "gitops_branch", "gitops_path", "gitops_credential_id"),
    ),
    (
        "Private registry",
        "이미지 이름 생성에 사용할 내부 registry 정보입니다.",
        ("registry_url", "registry_project", "registry_credential_id", "registry_ca_cert_credential_id"),
    ),
)
FORM_FIELD_LOOKUP = {name: (label, placeholder) for name, label, placeholder in FORM_FIELDS}

ENV_VAR_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SOURCE_INPUT_MODES = {"clone", "local"}
DEFAULT_SOURCE_INPUT_MODE = "clone"
LOCAL_SOURCE_REPO_PATH_FIELD = "local_source_repo_path"
SOURCE_INPUT_MODE_FIELD = "source_input_mode"


@dataclass(frozen=True)
class ConsoleValidationResult:
    ok: bool
    messages: tuple[str, ...]
    config: DemoConfig | None = None

    @property
    def status_label(self) -> str:
        return "검증 완료" if self.ok else "검토 필요"


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
    source_input_mode = _source_input_mode(values)
    local_source_repo_path = str(values.get(LOCAL_SOURCE_REPO_PATH_FIELD, "")).strip()
    messages: list[str] = []
    config: DemoConfig | None = None

    source_env = payload.get("source_access_token_env", "")
    if source_env and not ENV_VAR_NAME_RE.fullmatch(source_env):
        if source_input_mode == "clone":
            messages.append(
                "source_access_token_env는 대문자 환경변수 이름이어야 합니다"
            )

    if source_input_mode not in SOURCE_INPUT_MODES:
        messages.append("source_input_mode는 clone 또는 local이어야 합니다")
    elif source_input_mode == "local":
        local_repo_path, local_path_errors = _resolve_local_source_repo_path(local_source_repo_path)
        messages.extend(local_path_errors)
        if local_repo_path is not None:
            local_source_repo_path = str(local_repo_path)
            payload = {
                **payload,
                "source_repo_url": local_source_repo_path,
                "source_branch": "local",
                "source_credential_id": "local-source",
                "source_access_token_env": "",
            }

    try:
        config = DemoConfig.from_mapping(payload)
    except ValueError as error:
        messages.append(str(error))

    redaction_values = {field: str(values.get(field, "")).strip() for field, _, _ in FORM_FIELDS}
    if source_input_mode == "local":
        for field in ("source_repo_url", "source_branch", "source_credential_id", "source_access_token_env"):
            redaction_values[field] = ""
    redaction_values.update(
        {
            SOURCE_INPUT_MODE_FIELD: source_input_mode,
            LOCAL_SOURCE_REPO_PATH_FIELD: local_source_repo_path,
        }
    )
    redaction_probe = "\n".join(
        f"{field}: {value}"
        for field, value in redaction_values.items()
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
    source_input_mode = _source_input_mode(values)
    repo_path: str | None = None
    if source_input_mode == "local":
        local_repo_path, local_path_errors = _resolve_local_source_repo_path(
            str(values.get(LOCAL_SOURCE_REPO_PATH_FIELD, "")).strip()
        )
        if local_path_errors or local_repo_path is None:
            return ConsoleDryRunResult(
                ok=False,
                messages=tuple(local_path_errors),
                config=validation.config,
                validation=validation,
                output_dir=output_dir,
            )
        repo_path = str(local_repo_path)
    elif source_input_mode != "clone":
        return ConsoleDryRunResult(
            ok=False,
            messages=("source_input_mode는 clone 또는 local이어야 합니다",),
            config=validation.config,
            validation=validation,
            output_dir=output_dir,
        )

    try:
        from k8s_deploy_agent.cli import run_dry_run_with_config

        generated_paths = run_dry_run_with_config(validation.config, repo_path, output_dir)
    except (ValueError, OSError, PermissionError) as error:
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
    form_values: Mapping[str, str] | None = None,
) -> str:
    validation_html = _render_validation_result(validation)
    dry_run_html = _render_dry_run_result(dry_run)
    preview_html = _render_generated_asset_preview(dry_run)
    checklist_html = _render_validation_checklist(dry_run)
    stepper_html = _render_workflow_stepper(validation, dry_run)
    summary_html = _render_run_summary(validation, dry_run)
    status_class = "warn"
    status_label = "입력 대기"
    if dry_run is not None:
        status_class = "ok" if dry_run.ok else "blocked"
        status_label = "dry-run 완료" if dry_run.ok else "dry-run 차단"
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
    .workflow {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .step {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 72px;
      padding: 10px 12px;
    }
    .step strong {
      display: block;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .step span {
      color: var(--muted);
      display: block;
      font-size: 12px;
      margin-top: 4px;
    }
    .step.ok {
      border-color: #a9dfc7;
      background: #f4fbf8;
    }
    .step.blocked {
      border-color: #f1b8b2;
      background: #fff8f7;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .summary-item {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 72px;
      padding: 12px;
    }
    .summary-item span {
      color: var(--muted);
      display: block;
      font-size: 12px;
      margin-bottom: 6px;
    }
    .summary-item strong {
      display: block;
      font-size: 17px;
      overflow-wrap: anywhere;
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
    fieldset {
      display: grid;
      gap: 10px;
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
    }
    fieldset.form-group {
      padding: 12px;
    }
    legend {
      color: var(--ink);
      font-size: 12px;
      font-weight: 700;
      padding: 0 4px;
    }
    .radio-row {
      display: grid;
      gap: 8px;
    }
    .radio-option {
      align-items: center;
      display: flex;
      gap: 8px;
      min-height: 24px;
    }
    .field-grid {
      display: grid;
      gap: 10px;
    }
    form:has(input[name="source_input_mode"][value="clone"]:checked) .local-source-fields {
      display: none;
    }
    form:has(input[name="source_input_mode"][value="local"]:checked) .clone-source-fields {
      display: none;
    }
    .group-note {
      color: var(--muted);
      font-size: 12px;
      margin: 0;
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
    input[type="radio"] {
      width: 16px;
      min-height: 16px;
      padding: 0;
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
    .future-panel {
      display: grid;
      gap: 10px;
    }
    .future-row {
      border: 1px dashed var(--line);
      border-radius: 7px;
      padding: 10px 12px;
    }
    .future-row p {
      color: var(--muted);
      margin: 4px 0 0;
      font-size: 13px;
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
    .asset-groups {
      display: grid;
      gap: 12px;
    }
    .asset-group {
      border: 1px solid var(--line);
      border-radius: 7px;
      overflow: hidden;
    }
    .asset-group-title {
      align-items: center;
      background: #fbfcfe;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
    }
    .artifact {
      padding: 12px;
    }
    .artifact + .artifact {
      border-top: 1px solid var(--line);
    }
    pre {
      background: #101828;
      border-radius: 6px;
      color: #f8fafc;
      font-size: 12px;
      margin: 10px 0 0;
      max-height: 220px;
      overflow: auto;
      padding: 10px;
      white-space: pre-wrap;
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
      .layout, .cards, .workflow, .summary-grid {
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
        <span>온프레미스 Kubernetes migration 준비를 위한 local web UI</span>
      </div>
      <div class="status">offline-first · loopback server</div>
    </div>
  </header>
  <main class="wrap">
    __WORKFLOW_STEPPER__
    __RUN_SUMMARY__
    <div class="layout">
      <section>
        <div class="section-head">
          <h2>1. 입력</h2>
          <span class="pill warn">입력 form</span>
        </div>
        <div class="panel-body">
            <form class="form-grid" method="post" action="/validate">
            __FORM_INPUTS__
            <div class="button-row">
              <button type="submit">입력 검증</button>
              <button type="submit" formaction="/dry-run">dry-run 실행</button>
              <button type="reset" class="secondary">초기화</button>
            </div>
          </form>
        </div>
      </section>
      <div class="stack">
        <section>
          <div class="section-head">
            <h2>2. 검증</h2>
            <span class="pill __STATUS_CLASS__">__STATUS_LABEL__</span>
          </div>
          <div class="panel-body result">
            __VALIDATION_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>3. dry-run</h2>
            <span class="pill __DRY_RUN_CLASS__">__DRY_RUN_LABEL__</span>
          </div>
          <div class="panel-body result">
            __DRY_RUN_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>4. 분석 / 산출물 리뷰</h2>
            <span class="pill __PREVIEW_CLASS__">__PREVIEW_LABEL__</span>
          </div>
          <div class="panel-body result">
            __PREVIEW_HTML__
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>향후 확장</h2>
            <span class="pill warn">비활성</span>
          </div>
          <div class="panel-body future-panel">
            <div class="future-row">
              <h3>On-prem LLM review</h3>
              <p>이번 개편에서는 recommendation panel을 실행하지 않습니다. dry-run 흐름은 LLM 없이 완료됩니다.</p>
            </div>
            <div class="future-row">
              <h3>Write-back preparation</h3>
              <p>source/GitOps repository 변경은 validation gate 이후 별도 작업으로 유지합니다.</p>
            </div>
          </div>
        </section>
        <section>
          <div class="section-head">
            <h2>5. 검증 checklist</h2>
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
        template.replace("__FORM_INPUTS__", _form_inputs(form_values))
        .replace("__WORKFLOW_STEPPER__", stepper_html)
        .replace("__RUN_SUMMARY__", summary_html)
        .replace("__STATUS_CLASS__", status_class)
        .replace("__STATUS_LABEL__", status_label)
        .replace("__VALIDATION_HTML__", validation_html)
        .replace("__DRY_RUN_CLASS__", "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn"))
        .replace(
            "__DRY_RUN_LABEL__",
            "완료" if dry_run and dry_run.ok else ("검토 필요" if dry_run else "실행 대기"),
        )
        .replace("__DRY_RUN_HTML__", dry_run_html)
        .replace("__PREVIEW_CLASS__", "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn"))
        .replace(
            "__PREVIEW_LABEL__",
            "준비 완료" if dry_run and dry_run.ok else ("차단" if dry_run else "실행 대기"),
        )
        .replace("__PREVIEW_HTML__", preview_html)
        .replace("__CHECKLIST_CLASS__", "ok" if dry_run and dry_run.ok else ("warn" if dry_run else "blocked"))
        .replace(
            "__CHECKLIST_LABEL__",
            "통과" if dry_run and dry_run.ok else ("대기" if dry_run is None else "차단"),
        )
        .replace("__CHECKLIST_HTML__", checklist_html)
    )


def _render_workflow_stepper(
    validation: ConsoleValidationResult | None,
    dry_run: ConsoleDryRunResult | None,
) -> str:
    validation_status = "ok" if validation and validation.ok else ("blocked" if validation else "warn")
    dry_run_status = "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn")
    review_status = "ok" if dry_run and dry_run.ok else ("blocked" if dry_run else "warn")
    checklist_status = "ok" if dry_run and dry_run.ok else ("blocked" if dry_run and not dry_run.ok else "warn")
    steps = (
        ("1", "입력", "대상과 내부 시스템 참조 입력", "ok"),
        ("2", "검증", "필수값과 secret-like 값 차단", validation_status),
        ("3", "dry-run", "기존 CLI pipeline 실행", dry_run_status),
        ("4", "리뷰", "분석 결과와 생성 파일 확인", review_status),
        ("5", "checklist", "write-back 전 blocking 조건 확인", checklist_status),
    )
    items = "\n".join(
        f"""<div class="step {escape(status)}">
          <strong>{escape(number)}. {escape(title)}</strong>
          <span>{escape(description)}</span>
        </div>"""
        for number, title, description, status in steps
    )
    return f'<div class="workflow" aria-label="operator workflow">{items}</div>'


def _render_run_summary(
    validation: ConsoleValidationResult | None,
    dry_run: ConsoleDryRunResult | None,
) -> str:
    config = dry_run.config if dry_run and dry_run.config else validation.config if validation else None
    app_name = config.app_name if config else "-"
    namespace = config.namespace if config else "-"
    generated_count = str(len(dry_run.generated_paths)) if dry_run and dry_run.ok else "0"
    if dry_run is None:
        run_state = "실행 대기"
    elif dry_run.ok:
        run_state = "dry-run 완료"
    else:
        run_state = "차단"
    output_dir = dry_run.output_dir if dry_run and dry_run.output_dir else "-"
    items = (
        ("Application", app_name),
        ("Namespace", namespace),
        ("Run state", run_state),
        ("Generated files", generated_count),
    )
    summary_items = "\n".join(
        f"""<div class="summary-item">
          <span>{escape(label)}</span>
          <strong>{escape(value)}</strong>
        </div>"""
        for label, value in items
    )
    return f"""<div class="summary-grid" aria-label="run summary">
      {summary_items}
      <div class="summary-item">
        <span>Output dir</span>
        <strong>{escape(output_dir)}</strong>
      </div>
    </div>"""


def _render_validation_result(result: ConsoleValidationResult | None) -> str:
    if result is None:
        return (
            '<p class="result-note">검증 대기 중입니다. '
            "이 console은 `DemoConfig` 호환 payload를 받고 raw secret 유사 값을 차단합니다.</p>"
        )

    if result.ok and result.config is not None:
        items = [
            ("애플리케이션", result.config.app_name),
            ("환경", result.config.environment),
            ("Namespace", result.config.namespace),
            ("Source repo", result.config.source_repo_url),
            ("GitOps repo", result.config.gitops_repo_url),
        ]
        details = "".join(
            f"<li><strong>{escape(label)}</strong>: <code>{escape(value)}</code></li>" for label, value in items
        )
        return f"""
<span class="pill ok">검증 완료</span>
<p class="result-note">Payload가 승인되었습니다. 이 console은 config를 기존 dry-run pipeline에 전달할 수 있습니다.</p>
<ul class="result-list">{details}</ul>
"""

    messages = "".join(f"<li>{escape(message)}</li>" for message in result.messages)
    return f"""
<span class="pill blocked">차단</span>
<p class="result-note">Payload가 거부되었습니다. dry-run 또는 export 준비 전에 아래 오류를 검토하세요.</p>
<ul class="result-list">{messages}</ul>
"""


def _render_dry_run_result(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return '<p class="result-note"><code>dry-run 실행</code>으로 form을 제출하면 local output directory에 asset을 생성합니다.</p>'

    if result.ok and result.config is not None and result.output_dir is not None:
        items = [
            ("Output dir", result.output_dir),
            ("생성 파일", ", ".join(result.generated_paths) if result.generated_paths else "-"),
            ("Namespace", result.config.namespace),
        ]
        details = "".join(
            f"<li><strong>{escape(label)}</strong>: <code>{escape(value)}</code></li>" for label, value in items
        )
        return f"""
<span class="pill ok">완료</span>
<p class="result-note">dry-run이 기존 pipeline을 재사용해 검토용 local asset을 작성했습니다.</p>
<ul class="result-list">{details}</ul>
"""

    messages = "".join(f"<li>{escape(message)}</li>" for message in result.messages)
    return f"""
<span class="pill blocked">차단</span>
<p class="result-note">dry-run이 완료되지 않았습니다. 차단 원인을 수정한 뒤 다시 실행하세요.</p>
<ul class="result-list">{messages}</ul>
"""


def _render_generated_asset_preview(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return '<p class="result-note">생성 파일을 local output directory에서 확인하려면 dry-run을 실행하세요.</p>'

    if not result.ok or result.output_dir is None:
        return '<p class="result-note">dry-run이 성공적으로 완료될 때까지 생성 asset preview를 사용할 수 없습니다.</p>'

    output_dir = Path(result.output_dir)
    preview_groups = (
        ("Repository analysis", (".agent/reports/repository-analysis.md",)),
        ("CI pipeline", ("Jenkinsfile",)),
        ("GitOps base", ("gitops/fleet.yaml", "gitops/base/namespace.yaml")),
        (
            "Service manifests",
            tuple(path for path in result.generated_paths if path.startswith("gitops/apps/")),
        ),
        (
            "Dockerfile proposals",
            tuple(path for path in result.generated_paths if path.startswith("dockerfile-proposals/")),
        ),
    )
    groups = []
    for title, relative_paths in preview_groups:
        artifacts = []
        for relative_path in relative_paths:
            file_path = output_dir / relative_path
            if not file_path.is_file():
                continue
            snippet = "\n".join(file_path.read_text(encoding="utf-8").splitlines()[:8])
            artifacts.append(
                f"""<details class="artifact">
                  <summary><strong>{escape(relative_path)}</strong></summary>
                  <pre>{escape(snippet)}</pre>
                </details>"""
            )
        if artifacts:
            groups.append(
                f"""<div class="asset-group">
                  <div class="asset-group-title">
                    <h3>{escape(title)}</h3>
                    <span class="pill">{len(artifacts)}개</span>
                  </div>
                  {''.join(artifacts)}
                </div>"""
            )

    if not groups:
        return '<p class="result-note">local output directory에서 preview 가능한 파일을 찾지 못했습니다.</p>'

    return f'<div class="asset-groups">{"".join(groups)}</div>'


def _render_validation_checklist(result: ConsoleDryRunResult | None) -> str:
    if result is None:
        return """
<div class="panel-body checklist">
  <div class="check">
    <div>
      <h3>Secret redaction</h3>
      <p>write-back 준비 전에 <code>assert_no_secret_values</code>가 통과해야 합니다.</p>
    </div>
    <span class="pill warn">대기</span>
  </div>
  <div class="check">
    <div>
      <h3>생성 assets</h3>
      <p>Report, Jenkinsfile, Fleet config, Namespace, Deployment, Service, ConfigMap이 존재해야 합니다.</p>
    </div>
    <span class="pill warn">대기</span>
  </div>
  <div class="check">
    <div>
      <h3>On-prem LLM</h3>
      <p>추천 내용은 선택 검토 텍스트이며 생성 파일을 자동 변경하지 않습니다.</p>
    </div>
    <span class="pill ok">선택</span>
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
      <p>write-back 준비 전에 검증이 차단되었습니다.</p>
    </div>
    <span class="pill blocked">차단</span>
  </div>
  <div class="check">
    <div>
      <h3>생성 assets</h3>
      <p>dry-run이 성공할 때까지 preview와 manifest 검사를 사용할 수 없습니다.</p>
    </div>
    <span class="pill blocked">차단</span>
  </div>
  <div class="check">
    <div>
      <h3>dry-run 오류</h3>
      <ul class="result-list">{messages}</ul>
    </div>
    <span class="pill blocked">차단</span>
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
            "생성 assets에서 assert_no_secret_values가 통과했습니다.",
            "ok" if secret_ok else "blocked",
        ),
        (
            "생성 assets",
            "Report, Jenkinsfile, Fleet config, namespace manifest가 존재합니다." if generated_ok else f"누락: {', '.join(missing)}",
            "ok" if generated_ok else "blocked",
        ),
        (
            "Namespace 정합성",
            f"Namespace manifest에 {result.config.namespace}가 포함되어 있습니다." if namespace_matches else "Namespace manifest가 대상 namespace와 일치하지 않습니다.",
            "ok" if namespace_matches else "blocked",
        ),
        (
            "Dockerfile proposals",
            "Dockerfile/.dockerignore proposals가 review-only validation을 통과했습니다."
            if dockerfile_validation_ok
            else "Dockerfile proposal validation이 없거나 차단되었습니다.",
            "ok" if dockerfile_validation_ok else "blocked",
        ),
        (
            "On-prem LLM",
            "추천 내용은 review-only로 유지되며 자동 적용되지 않습니다.",
            "ok",
        ),
    ]
    status_labels = {"ok": "통과", "blocked": "차단", "warn": "대기"}
    items = "\n".join(
        f"""<div class="check">
      <div>
        <h3>{escape(title)}</h3>
        <p>{escape(description)}</p>
      </div>
      <span class="pill {escape(status)}">{escape(status_labels.get(status, status))}</span>
    </div>"""
        for title, description, status in checklist
    )
    return f'<div class="panel-body checklist">{items}</div>'


def _source_input_mode(values: Mapping[str, str]) -> str:
    mode = str(values.get(SOURCE_INPUT_MODE_FIELD, "")).strip()
    return mode or DEFAULT_SOURCE_INPUT_MODE


def _resolve_local_source_repo_path(raw_path: str) -> tuple[Path | None, tuple[str, ...]]:
    if not raw_path:
        return None, ("source_input_mode가 local이면 local_source_repo_path가 필요합니다",)

    try:
        path = Path(raw_path).expanduser().resolve()
    except (OSError, RuntimeError) as error:
        return None, (f"local_source_repo_path를 해석할 수 없습니다: {error}",)

    try:
        if not path.exists():
            return None, (f"local_source_repo_path가 존재하지 않습니다: {path}",)
        if not path.is_dir():
            return None, (f"local_source_repo_path가 directory가 아닙니다: {path}",)
    except (OSError, PermissionError) as error:
        return None, (f"local_source_repo_path를 검사할 수 없습니다: {error}",)

    return path, ()


def _form_inputs(values: Mapping[str, str] | None = None) -> str:
    form_values = values or {}
    selected_mode = _source_input_mode(form_values)
    mode_options = []
    for mode, label in (("clone", "source repository URL clone"), ("local", "서버 local path 분석")):
        checked = " checked" if selected_mode == mode else ""
        mode_options.append(
            f"""<label class="radio-option">
                <input type="radio" name="{escape(SOURCE_INPUT_MODE_FIELD)}" value="{escape(mode)}"{checked}>
                <span>{escape(label)}</span>
              </label>"""
        )
    groups = []
    source_mode_controls = f"""<fieldset class="source-mode">
          <legend>source 입력 mode</legend>
          <div class="radio-row">{''.join(mode_options)}</div>
        </fieldset>"""
    for title, note, field_names in FORM_GROUPS:
        controls = []
        if title == "Source repository":
            controls.append(source_mode_controls)
            controls.append(_source_repository_mode_fields(form_values))
        else:
            for name in field_names:
                label, placeholder = FORM_FIELD_LOOKUP[name]
                value = str(form_values.get(name, "")).strip()
                controls.append(
                    f"""<label>{escape(label)}
                      <input name="{escape(name)}" value="{escape(value)}" placeholder="{escape(placeholder)}">
                    </label>"""
                )
        groups.append(
            f"""<fieldset class="form-group">
              <legend>{escape(title)}</legend>
              <p class="group-note">{escape(note)}</p>
              <div class="field-grid">{''.join(controls)}</div>
            </fieldset>"""
        )
    return "\n".join(groups)


def _source_repository_mode_fields(form_values: Mapping[str, str]) -> str:
    clone_fields = []
    for name in ("source_repo_url", "source_branch", "source_credential_id", "source_access_token_env"):
        label, placeholder = FORM_FIELD_LOOKUP[name]
        if name == "source_credential_id":
            label = "Source credential ID (Private repo only)"
        value = str(form_values.get(name, "")).strip()
        clone_fields.append(
            f"""<label>{escape(label)}
              <input name="{escape(name)}" value="{escape(value)}" placeholder="{escape(placeholder)}">
            </label>"""
        )
    local_path_value = str(form_values.get(LOCAL_SOURCE_REPO_PATH_FIELD, "")).strip()
    local_fields = f"""<label>local source repository path (absolute path)
      <input name="{escape(LOCAL_SOURCE_REPO_PATH_FIELD)}" value="{escape(local_path_value)}" placeholder="/srv/repos/payments-api">
    </label>"""
    return f"""<fieldset class="clone-source-fields">
          <legend>source repository URL clone</legend>
          <div class="field-grid">{''.join(clone_fields)}</div>
        </fieldset>
        <fieldset class="local-source-fields">
          <legend>서버 local path</legend>
          <div class="field-grid">{local_fields}</div>
        </fieldset>"""


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
            body = render_operator_console(validation=validation, form_values=payload).encode("utf-8")
        else:
            dry_run = run_console_dry_run(payload)
            body = render_operator_console(validation=dry_run.validation, dry_run=dry_run, form_values=payload).encode("utf-8")

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
