#!/usr/bin/env python3
"""Generate and optionally schedule SignPlease social campaigns via Buffer.

Default behavior is dry-run: generate campaign assets and Buffer payloads under
output/ without publishing. To publish, set DRY_RUN=false and pass --publish.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
import textwrap
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "context.md"
OUTPUT_ROOT = ROOT / "output"
BUFFER_ENDPOINT = "https://api.buffer.com"


FORBIDDEN_PHRASES = [
    "무조건 벌금을 막아",
    "벌금 100% 방지",
    "노무 분쟁 100% 예방",
    "법적으로 완벽",
    "가장 안전한 전자계약",
    "노무사 없이 완벽",
    "변호사 없이 완벽",
]


ANGLES = [
    {
        "name": "근로계약서 미루는 습관 바꾸기",
        "pain": "알바를 뽑고도 근로계약서 작성을 나중으로 미루는 습관",
        "myth": "알바니까 구두로 정해도 괜찮다는 생각",
        "shift": "근로계약서는 벌금 회피용 서류가 아니라 사장님을 지키는 기본 기록",
        "cta": "오늘 알바를 뽑았다면, 출근 전 계약서부터 보내세요.",
    },
    {
        "name": "초보 사장님 첫 근로계약",
        "pain": "근로계약서 양식을 봐도 무엇을 채워야 할지 모르는 막막함",
        "myth": "법률 문서는 어렵고 오래 걸린다는 생각",
        "shift": "질문에 답하면 필요한 항목을 하나씩 정리할 수 있음",
        "cta": "싸인해주세요에서 무료로 첫 근로계약서를 만들어보세요.",
    },
    {
        "name": "종이 없는 알바 계약",
        "pain": "출력, 도장, 스캔, 사진 보관이 번거로운 종이 계약",
        "myth": "계약서는 꼭 종이로 만나서 써야 한다는 생각",
        "shift": "모바일 전자서명으로 출근 전에도 계약을 끝낼 수 있음",
        "cta": "알림톡으로 보내고 모바일로 서명받으세요.",
    },
    {
        "name": "사업주 보호 기록",
        "pain": "임금, 근무시간, 업무 범위가 나중에 다르게 기억되는 문제",
        "myth": "계약서는 근로자만 보호하는 문서라는 생각",
        "shift": "명확한 근로조건 기록은 사장님도 보호함",
        "cta": "사장님을 지키는 첫 기록을 무료로 남겨보세요.",
    },
    {
        "name": "카페/식당 피크타임 전 계약",
        "pain": "바쁜 매장 운영 때문에 서류 작업이 계속 밀리는 문제",
        "myth": "출근하고 시간 날 때 계약서를 쓰면 된다는 생각",
        "shift": "출근 전 모바일로 보내면 피크타임 전에 계약을 끝낼 수 있음",
        "cta": "알바 첫 출근 전, 계약서부터 보내는 습관을 만드세요.",
    },
]


@dataclass(frozen=True)
class Slot:
    local_dt: datetime

    @property
    def due_at_utc(self) -> str:
        return self.local_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @property
    def label(self) -> str:
        return self.local_dt.strftime("%Y-%m-%d %H:%M")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or os.environ[key] == ""):
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and schedule social campaigns.")
    parser.add_argument("--days", type=int, default=int(os.getenv("CAMPAIGN_DAYS", "7")))
    parser.add_argument("--publish", action="store_true", help="Actually call Buffer API.")
    parser.add_argument("--list-channels", action="store_true", help="List Buffer channel IDs and exit.")
    parser.add_argument("--context", default=str(CONTEXT_PATH))
    return parser.parse_args()


def parse_post_times(value: str) -> list[time]:
    result: list[time] = []
    for part in value.split(","):
        hour, minute = part.strip().split(":", 1)
        result.append(time(hour=int(hour), minute=int(minute)))
    return result


def build_slots(days: int, tz_name: str, post_times: list[time]) -> list[Slot]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    slots: list[Slot] = []
    day = now.date()

    while len(slots) < days * len(post_times):
        for post_time in post_times:
            candidate = datetime.combine(day, post_time, tz)
            if candidate > now + timedelta(minutes=5):
                slots.append(Slot(candidate))
                if len(slots) >= days * len(post_times):
                    break
        day += timedelta(days=1)

    return slots


def read_context(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"context file not found: {path}")
    return path.read_text(encoding="utf-8")


def wrap_korean(text: str, width: int = 18) -> list[str]:
    wrapped: list[str] = []
    for paragraph in text.split("\n"):
        wrapped.extend(textwrap.wrap(paragraph, width=width) or [""])
    return wrapped


def make_item(index: int, slot: Slot) -> dict[str, Any]:
    angle = ANGLES[index % len(ANGLES)]
    day_part = "오전" if slot.local_dt.hour < 12 else "오후"

    instagram_slides = [
        {
            "title": "알바 뽑았는데",
            "body": "근로계약서, 또 나중으로 미루고 있나요?",
        },
        {
            "title": "진짜 문제는 비용보다 습관",
            "body": angle["pain"],
        },
        {
            "title": "계약서는 사장님도 지킵니다",
            "body": angle["shift"],
        },
        {
            "title": "싸인해주세요로 쉽게",
            "body": "질문에 답하면 AI가 근로계약서를 만들고, 알림톡으로 서명 요청까지 보낼 수 있어요.",
        },
        {
            "title": "오늘부터 무료로",
            "body": angle["cta"],
        },
    ]

    instagram_caption = (
        f"{angle['name']}\n\n"
        "근로계약서는 벌금을 피하기 위한 서류이기도 하지만, "
        "무엇보다 사장님의 사업장을 지키는 기록입니다.\n\n"
        "싸인해주세요는 알바 근로계약서 작성부터 알림톡 서명 요청, "
        "PDF 보관까지 쉽게 이어지도록 돕습니다.\n\n"
        "무료로 시작하고, 알바를 뽑을 때마다 계약서부터 보내는 습관을 만들어보세요.\n\n"
        "#싸인해주세요 #근로계약서 #알바근로계약서 #소상공인 #자영업자 #전자서명"
    )

    threads_text = (
        f"알바 근로계약서가 계속 미뤄지는 이유는 사장님이 몰라서라기보다 "
        f"바쁘고 귀찮고 어렵게 느껴지기 때문일 때가 많습니다.\n\n"
        f"근로계약서는 벌금 회피용 서류를 넘어, 임금·근무시간·업무 범위를 남겨 "
        f"사장님을 지키는 기록이기도 해요.\n\n"
        f"{angle['cta']}\n싸인해주세요는 무료로 시작할 수 있습니다."
    )

    x_text = (
        "알바 근로계약서, 미루는 습관부터 바꿔야 합니다. "
        "근로계약은 벌금 회피용 서류가 아니라 사장님을 지키는 기록입니다. "
        "싸인해주세요에서 무료로 만들고, 알림톡으로 바로 서명받으세요."
    )

    return {
        "slot": slot.label,
        "dueAt": slot.due_at_utc,
        "dayPart": day_part,
        "angle": angle,
        "instagram": {
            "caption": instagram_caption,
            "slides": instagram_slides,
        },
        "threads": {
            "text": threads_text,
        },
        "x": {
            "text": x_text,
        },
    }


def make_svg(slide: dict[str, str], footer: str) -> str:
    title_lines = wrap_korean(slide["title"], width=14)
    body_lines = wrap_korean(slide["body"], width=19)

    def text_block(lines: list[str], x: int, y: int, size: int, weight: int, color: str) -> str:
        nodes = []
        for i, line in enumerate(lines):
            nodes.append(
                f'<text x="{x}" y="{y + i * int(size * 1.35)}" '
                f'font-size="{size}" font-weight="{weight}" fill="{color}">'
                f"{html.escape(line)}</text>"
            )
        return "\n".join(nodes)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <rect width="1080" height="1350" fill="#FFF7EA"/>
  <rect x="72" y="72" width="936" height="1206" rx="48" fill="#FFFFFF" stroke="#111827" stroke-width="4"/>
  <circle cx="890" cy="180" r="72" fill="#FFE08A"/>
  <circle cx="190" cy="1160" r="92" fill="#D7F5E8"/>
  <text x="96" y="150" font-size="34" font-weight="700" fill="#F97316">싸인해주세요</text>
  {text_block(title_lines, 96, 390, 82, 900, "#111827")}
  {text_block(body_lines, 96, 650, 46, 600, "#374151")}
  <text x="96" y="1180" font-size="34" font-weight="700" fill="#111827">{html.escape(footer)}</text>
</svg>
"""


def write_cards(item: dict[str, Any], item_dir: Path) -> list[str]:
    card_dir = item_dir / "cards"
    card_dir.mkdir(parents=True, exist_ok=True)
    local_paths: list[str] = []
    for idx, slide in enumerate(item["instagram"]["slides"], start=1):
        path = card_dir / f"slide-{idx:02d}.svg"
        path.write_text(make_svg(slide, "무료로 근로계약서 시작하기"), encoding="utf-8")
        local_paths.append(str(path.relative_to(ROOT)))
    return local_paths


def convert_svg_to_png(svg_path: Path, png_path: Path) -> bool:
    png_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("rsvg-convert"):
        command = ["rsvg-convert", "-w", "1080", "-h", "1350", "-o", str(png_path), str(svg_path)]
    elif shutil.which("magick"):
        command = ["magick", str(svg_path), "-background", "white", str(png_path)]
    elif shutil.which("convert"):
        command = ["convert", str(svg_path), "-background", "white", str(png_path)]
    elif shutil.which("qlmanage"):
        temp_dir = png_path.parent / ".qlmanage"
        temp_dir.mkdir(parents=True, exist_ok=True)
        command = ["qlmanage", "-t", "-s", "1080", "-o", str(temp_dir), str(svg_path)]
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return False

        generated = temp_dir / f"{svg_path.name}.png"
        if not generated.exists():
            return False
        shutil.move(str(generated), str(png_path))
        shutil.rmtree(temp_dir, ignore_errors=True)
        return png_path.exists()
    else:
        return False

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return False

    return png_path.exists()


def export_public_assets(card_paths: list[str]) -> dict[str, Any]:
    export_root = ROOT / os.getenv("ASSET_EXPORT_DIR", "docs")
    (export_root / ".nojekyll").write_text("", encoding="utf-8")

    exported_paths: list[str] = []
    conversion_warnings: list[str] = []

    for card_path in card_paths:
        source = ROOT / card_path
        try:
            relative_to_output = source.relative_to(OUTPUT_ROOT)
        except ValueError:
            relative_to_output = Path(card_path)

        export_relative = Path("assets") / relative_to_output.with_suffix(".png")
        target = export_root / export_relative

        if convert_svg_to_png(source, target):
            exported_paths.append(str(export_relative))
        else:
            fallback_relative = export_relative.with_suffix(".svg")
            fallback_target = export_root / fallback_relative
            fallback_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, fallback_target)
            exported_paths.append(str(fallback_relative))
            conversion_warnings.append(f"PNG 변환 실패, SVG로 export됨: {fallback_relative}")

    return {
        "exportRoot": str(export_root.relative_to(ROOT)),
        "exportedPaths": exported_paths,
        "warnings": conversion_warnings,
    }


def public_asset_urls(exported_paths: list[str]) -> list[str]:
    base = os.getenv("PUBLIC_ASSET_BASE_URL", "").rstrip("/")
    if not base:
        return []
    return [f"{base}/{path}" for path in exported_paths]


def review_item(
    item: dict[str, Any],
    card_paths: list[str],
    asset_urls: list[str],
    export_result: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    all_text = "\n".join(
        [
            item["instagram"]["caption"],
            item["threads"]["text"],
            item["x"]["text"],
            *[slide["title"] + " " + slide["body"] for slide in item["instagram"]["slides"]],
        ]
    )

    for phrase in FORBIDDEN_PHRASES:
        if phrase in all_text:
            issues.append(f"금지 표현 포함: {phrase}")

    if len(item["x"]["text"]) > 280:
        issues.append(f"X 글자 수 초과: {len(item['x']['text'])}자")

    if "무료" not in all_text:
        issues.append("현재 무료 서비스 전략이 반영되지 않음")

    if len(item["instagram"]["slides"]) < 4:
        issues.append("Instagram 카드뉴스 장수가 부족함")

    if not card_paths:
        issues.append("Instagram 카드뉴스 파일이 생성되지 않음")

    warnings: list[str] = []
    if not asset_urls:
        warnings.append("PUBLIC_ASSET_BASE_URL이 없어 Instagram Buffer 페이로드에는 이미지가 첨부되지 않음")
    warnings.extend(export_result.get("warnings", []))

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "xLength": len(item["x"]["text"]),
    }


def build_buffer_payloads(item: dict[str, Any], asset_urls: list[str]) -> list[dict[str, Any]]:
    channel_map = {
        "instagram": os.getenv("BUFFER_CHANNEL_INSTAGRAM", ""),
        "threads": os.getenv("BUFFER_CHANNEL_THREADS", ""),
        "x": os.getenv("BUFFER_CHANNEL_X", ""),
    }

    payloads: list[dict[str, Any]] = []
    for platform, channel_id in channel_map.items():
        if not channel_id:
            continue

        if platform == "instagram":
            text = item["instagram"]["caption"]
            assets = [{"image": {"url": url}} for url in asset_urls]
        elif platform == "threads":
            text = item["threads"]["text"]
            assets = []
        else:
            text = item["x"]["text"]
            assets = []

        input_data: dict[str, Any] = {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": item["dueAt"],
            "aiAssisted": True,
            "source": "signplease-marketing-agent",
        }
        if assets:
            input_data["assets"] = assets

        payloads.append({"platform": platform, "input": input_data})

    return payloads


def graphql_request(api_key: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        BUFFER_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "error": "http_error",
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace"),
        }
    except urllib.error.URLError as exc:
        return {"error": "url_error", "reason": str(exc.reason)}


def call_buffer(api_key: str, input_data: dict[str, Any]) -> dict[str, Any]:
    query = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post {
        id
        text
        status
        dueAt
      }
    }
    ... on MutationError {
      message
    }
  }
}
"""
    return graphql_request(api_key, query, {"input": input_data})


def list_buffer_channels(api_key: str) -> dict[str, Any]:
    organizations_query = """
query GetOrganizations {
  account {
    organizations {
      id
      name
    }
  }
}
"""
    organizations_response = graphql_request(api_key, organizations_query)
    organizations = (
        organizations_response.get("data", {})
        .get("account", {})
        .get("organizations", [])
    )

    results: list[dict[str, Any]] = []
    channels_query = """
query GetChannels($input: ChannelsInput!) {
  channels(input: $input) {
    id
    displayName
    name
    service
    descriptor
    isDisconnected
    isLocked
    organizationId
  }
}
"""
    for organization in organizations:
        channels_response = graphql_request(
            api_key,
            channels_query,
            {"input": {"organizationId": organization["id"]}},
        )
        results.append(
            {
                "organization": organization,
                "channels": channels_response.get("data", {}).get("channels", []),
                "raw": channels_response if "data" not in channels_response else None,
            }
        )

    return {
        "organizationsResponse": organizations_response if "data" not in organizations_response else None,
        "results": results,
    }


def git_commit_and_push_assets(run_id: str) -> dict[str, Any]:
    export_dir = os.getenv("ASSET_EXPORT_DIR", "docs")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", export_dir],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        return {"ok": False, "skipped": True, "reason": "git 저장소가 아니거나 상태 확인 실패", "stderr": status.stderr}

    if not status.stdout.strip():
        return {"ok": True, "skipped": True, "reason": "push할 새 asset 변경 없음"}

    steps = [
        ["git", "add", export_dir],
        ["git", "commit", "-m", f"Add campaign assets {run_id}"],
        ["git", "push", "origin", "HEAD"],
    ]
    outputs: list[dict[str, Any]] = []
    for command in steps:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        outputs.append(
            {
                "command": " ".join(command),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        if result.returncode != 0:
            return {"ok": False, "skipped": False, "outputs": outputs}

    return {"ok": True, "skipped": False, "outputs": outputs}


def main() -> int:
    load_env_file(ROOT / ".env")
    args = parse_args()

    context = read_context(Path(args.context))
    if "무료 서비스" not in context and "무료 전략" not in context:
        print("context.md에 무료 전략이 명확하지 않습니다. 먼저 context.md를 업데이트하세요.", file=sys.stderr)
        return 2

    tz_name = os.getenv("TIMEZONE", "Asia/Seoul")
    post_times = parse_post_times(os.getenv("POST_TIMES", "09:00,21:00"))
    dry_run = os.getenv("DRY_RUN", "true").lower() != "false"
    should_publish = args.publish and not dry_run
    api_key = os.getenv("BUFFER_API_KEY", "")

    if args.list_channels:
        if not api_key:
            print("BUFFER_API_KEY가 필요합니다. .env에 키를 넣고 다시 실행하세요.", file=sys.stderr)
            return 2
        print(json.dumps(list_buffer_channels(api_key), ensure_ascii=False, indent=2))
        return 0

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = OUTPUT_ROOT / "campaigns" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    slots = build_slots(args.days, tz_name, post_times)
    campaign_items: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    publish_results: list[dict[str, Any]] = []
    asset_push_result: dict[str, Any] | None = None

    for index, slot in enumerate(slots):
        item = make_item(index, slot)
        item_dir = run_dir / f"{index + 1:02d}-{slot.local_dt.strftime('%Y%m%d-%H%M')}"
        item_dir.mkdir(parents=True, exist_ok=True)

        card_paths = write_cards(item, item_dir)
        export_result = export_public_assets(card_paths)
        asset_urls = public_asset_urls(export_result["exportedPaths"])
        review = review_item(item, card_paths, asset_urls, export_result)
        item_payloads = build_buffer_payloads(item, asset_urls) if review["passed"] else []

        item["cardPaths"] = card_paths
        item["publicAssetExport"] = export_result
        item["assetUrls"] = asset_urls
        item["review"] = review
        item["bufferPayloads"] = item_payloads

        (item_dir / "content.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        campaign_items.append(item)
        reviews.append({"slot": item["slot"], **review})
        payloads.extend(item_payloads)

    if should_publish:
        if not api_key:
            print("BUFFER_API_KEY가 없어 실제 업로드를 중단합니다.", file=sys.stderr)
            should_publish = False
        else:
            push_assets = os.getenv("PUSH_ASSETS_BEFORE_PUBLISH", "true").lower() == "true"
            if push_assets and os.getenv("PUBLIC_ASSET_BASE_URL", "").strip():
                asset_push_result = git_commit_and_push_assets(run_id)
                if not asset_push_result.get("ok"):
                    print("GitHub Pages asset push 실패로 실제 업로드를 중단합니다.", file=sys.stderr)
                    print(json.dumps(asset_push_result, ensure_ascii=False, indent=2), file=sys.stderr)
                    should_publish = False

            for payload in payloads:
                if should_publish:
                    result = call_buffer(api_key, payload["input"])
                    publish_results.append({"platform": payload["platform"], "result": result})

    summary = {
        "runId": run_id,
        "timezone": tz_name,
        "postTimes": [slot.label for slot in slots],
        "dryRun": not should_publish,
        "published": should_publish,
        "items": len(campaign_items),
        "payloads": len(payloads),
        "missingChannels": [
            name
            for name, env_key in {
                "instagram": "BUFFER_CHANNEL_INSTAGRAM",
                "threads": "BUFFER_CHANNEL_THREADS",
                "x": "BUFFER_CHANNEL_X",
            }.items()
            if not os.getenv(env_key, "")
        ],
        "reviews": reviews,
        "assetPushResult": asset_push_result,
        "publishResults": publish_results,
    }

    (run_dir / "campaign.json").write_text(
        json.dumps(campaign_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "buffer_payloads.json").write_text(
        json.dumps(payloads, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "review.json").write_text(
        json.dumps(reviews, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n결과 폴더: {run_dir.relative_to(ROOT)}")
    if not should_publish:
        print("실제 Buffer 업로드는 하지 않았습니다. DRY_RUN=false 와 --publish가 모두 필요합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
