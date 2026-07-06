from __future__ import annotations

from html import escape

from k8s_deploy_agent.analyzer import RepositoryAnalysis, ServiceCandidate
from k8s_deploy_agent.config import DemoConfig


def render_dry_run_dashboard(
    config: DemoConfig,
    analysis: RepositoryAnalysis,
    generated_paths: list[str],
    image_tag: str,
) -> str:
    deployable_services = [
        service for service in analysis.services if service.dockerfile and service.stack != "unsupported"
    ]
    skipped_services = [
        service for service in analysis.services if not service.dockerfile or service.stack == "unsupported"
    ]

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(config.app_name)} 배포 미리보기</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --ink: #18212f;
      --muted: #657286;
      --line: #d8dee8;
      --accent: #246bfe;
      --accent-soft: #eaf1ff;
      --ok: #0f8f61;
      --warn: #a15d00;
      --shadow: 0 12px 32px rgba(24, 33, 47, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    .wrap {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      min-height: 64px;
    }}
    .brand {{
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }}
    .brand strong {{
      overflow-wrap: anywhere;
      font-size: 18px;
    }}
    .brand span, .meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    main {{
      padding: 28px 0 40px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .metric {{
      padding: 16px;
      min-height: 88px;
    }}
    .metric span {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      margin-bottom: 8px;
    }}
    .metric strong {{
      display: block;
      font-size: 24px;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.8fr);
      gap: 16px;
      align-items: start;
    }}
    section {{
      overflow: hidden;
    }}
    .section-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1, h2 {{
      margin: 0;
      letter-spacing: 0;
    }}
    h1 {{ font-size: 22px; }}
    h2 {{ font-size: 15px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px 18px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      background: #fbfcfe;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    code {{
      background: #f0f3f7;
      border: 1px solid #e1e6ee;
      border-radius: 5px;
      padding: 2px 5px;
      overflow-wrap: anywhere;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 2px 9px;
      font-size: 12px;
      font-weight: 600;
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .pill.ok {{
      background: #e7f8f1;
      color: var(--ok);
    }}
    .pill.warn {{
      background: #fff3df;
      color: var(--warn);
    }}
    .list {{
      display: grid;
      gap: 10px;
      padding: 16px 18px 18px;
    }}
    .artifact {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px 12px;
      min-width: 0;
    }}
    .artifact a {{
      color: var(--ink);
      text-decoration: none;
      overflow-wrap: anywhere;
    }}
    .artifact a:hover {{ color: var(--accent); }}
    .empty {{
      color: var(--muted);
      padding: 18px;
    }}
    @media (max-width: 860px) {{
      .topbar {{
        align-items: flex-start;
        flex-direction: column;
        padding: 14px 0;
      }}
      .summary, .grid {{
        grid-template-columns: 1fr;
      }}
      th, td {{
        padding: 10px 12px;
      }}
      table {{
        min-width: 680px;
      }}
      .table-scroll {{
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <strong>{escape(config.app_name)} 배포 미리보기</strong>
        <span>{escape(config.source_repo_url)} · {escape(config.source_branch)}</span>
      </div>
      <div class="meta">{escape(config.environment)} / {escape(config.namespace)}</div>
    </div>
  </header>
  <main class="wrap">
    <div class="summary">
      <div class="metric"><span>감지된 서비스</span><strong>{len(analysis.services)}</strong></div>
      <div class="metric"><span>배포 가능 서비스</span><strong>{len(deployable_services)}</strong></div>
      <div class="metric"><span>스캔한 파일</span><strong>{len(analysis.file_tree)}</strong></div>
      <div class="metric"><span>Image tag</span><strong>{escape(image_tag)}</strong></div>
    </div>
    <div class="grid">
      <section>
        <div class="section-head">
          <h2>서비스 준비 상태</h2>
          <span class="pill ok">{len(deployable_services)} 준비 완료</span>
        </div>
        <div class="table-scroll">
          {_service_table(config, analysis)}
        </div>
      </section>
      <section>
        <div class="section-head">
          <h2>생성된 산출물</h2>
          <span class="pill">{len(generated_paths)}개 파일</span>
        </div>
        {_artifact_list(generated_paths)}
      </section>
    </div>
    {_skipped_services(skipped_services)}
  </main>
</body>
</html>
"""


def _service_table(config: DemoConfig, analysis: RepositoryAnalysis) -> str:
    if not analysis.services:
        return '<div class="empty">감지된 서비스 후보가 없습니다.</div>'

    rows = "\n".join(_service_row(config, analysis, service) for service in analysis.services)
    return f"""<table>
  <thead>
    <tr>
      <th>서비스</th>
      <th>스택</th>
      <th>경로</th>
      <th>Dockerfile</th>
      <th>Image</th>
      <th>상태</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def _service_row(config: DemoConfig, analysis: RepositoryAnalysis, service: ServiceCandidate) -> str:
    service_path = service.path.relative_to(analysis.root).as_posix()
    dockerfile = "-"
    if service.dockerfile:
        dockerfile = service.dockerfile.relative_to(analysis.root).as_posix()
    ready = service.stack != "unsupported" and service.dockerfile is not None
    status_class = "ok" if ready else "warn"
    status_text = "준비 완료" if ready else "검토 필요"
    image = config.image_for(service.name, "${BUILD_NUMBER}" if ready else "n/a")
    return f"""<tr>
      <td><strong>{escape(service.name)}</strong></td>
      <td>{escape(service.stack)}</td>
      <td><code>{escape(service_path)}</code></td>
      <td><code>{escape(dockerfile)}</code></td>
      <td><code>{escape(image)}</code></td>
      <td><span class="pill {status_class}">{status_text}</span></td>
    </tr>"""


def _artifact_list(generated_paths: list[str]) -> str:
    items = "\n".join(
        f"""<div class="artifact">
          <a href="{escape(path)}">{escape(path)}</a>
          <span class="pill">열기</span>
        </div>"""
        for path in generated_paths
        if path != "index.html"
    )
    if not items:
        return '<div class="empty">생성된 산출물이 없습니다.</div>'
    return f'<div class="list">{items}</div>'


def _skipped_services(services: list[ServiceCandidate]) -> str:
    if not services:
        return ""
    items = "\n".join(
        f"<li><strong>{escape(service.name)}</strong>: {escape(service.reason)}</li>"
        for service in services
    )
    return f"""<section style="margin-top: 16px;">
      <div class="section-head">
        <h2>검토 필요 항목</h2>
        <span class="pill warn">{len(services)}개 서비스</span>
      </div>
      <div class="list">
        <ul style="margin: 0; padding-left: 18px;">{items}</ul>
      </div>
    </section>"""
