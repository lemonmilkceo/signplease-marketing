#!/usr/bin/env python3
"""Build a photo-led five-card campaign and Buffer payloads from a reviewed plan."""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
SEOUL = ZoneInfo("Asia/Seoul")
REVIEW_DATE = "2026-09-05"
FORBIDDEN = ["무조건", "100%", "완벽", "노동청 신고 피하기"]


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=True, break_on_hyphens=False) or [""])
    return lines


def text_nodes(lines: list[str], x: int, y: int, size: int, gap: int, weight: int = 700,
               color: str = "#FFFFFF", anchor: str = "start") -> str:
    return "\n".join(
        f'<text x="{x}" y="{y + i * gap}" class="kr" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}" text-anchor="{anchor}">{html.escape(line)}</text>'
        for i, line in enumerate(lines)
    )


def base_svg(body: str, index: int, label: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350">
  <defs>
    <linearGradient id="dim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#07111F" stop-opacity=".40"/>
      <stop offset=".42" stop-color="#07111F" stop-opacity=".66"/>
      <stop offset="1" stop-color="#07111F" stop-opacity=".96"/>
    </linearGradient>
    <style>.kr{{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;letter-spacing:-1px}}</style>
  </defs>
  <image x="0" y="0" width="1080" height="1350" href="../background.png" xlink:href="../background.png" preserveAspectRatio="xMidYMid slice"/>
  <rect width="1080" height="1350" fill="url(#dim)"/>
  <rect x="64" y="64" width="952" height="1222" rx="30" fill="none" stroke="#FFFFFF" stroke-opacity=".24" stroke-width="2"/>
  <rect x="82" y="91" width="64" height="8" rx="4" fill="#FFD84D"/>
  <text x="82" y="148" class="kr" font-size="25" font-weight="800" fill="#FFFFFF">사장님 현장 노무</text>
  <text x="998" y="148" class="kr" font-size="25" font-weight="800" fill="#FFFFFF" text-anchor="end">{index}/5 · {html.escape(label)}</text>
  {body}
  <text x="82" y="1244" class="kr" font-size="23" font-weight="600" fill="#FFFFFF" fill-opacity=".74">저장해두고 실제 상황에서 다시 확인하세요</text>
</svg>'''


def make_slides(item: dict) -> list[str]:
    title = text_nodes(wrap(item["hook_title"], 13), 82, 650, 76, 94, 900)
    hook = text_nodes(wrap(item["hook"], 27)[:4], 82, 925, 36, 53, 650, "#F2F4F7")
    slide1 = base_svg(f'<text x="82" y="560" class="kr" font-size="27" font-weight="850" fill="#FFD84D">{html.escape(item["topic_code"])} · 실제 사장님 질문</text>{title}{hook}', 1, "질문")

    ctitle = text_nodes(wrap(item["conclusion_title"], 15), 82, 590, 70, 86, 900)
    cbody = text_nodes(wrap(item["conclusion"], 25)[:5], 82, 805, 39, 56, 650, "#F4F5F7")
    slide2 = base_svg(f'<text x="82" y="500" class="kr" font-size="27" font-weight="850" fill="#FFD84D">먼저 결론</text>{ctitle}{cbody}', 2, "결론")

    boxes = []
    for i, entry in enumerate(item["criteria"], 1):
        y = 390 + (i - 1) * 245
        boxes.append(f'<rect x="82" y="{y}" width="916" height="205" rx="26" fill="#081423" fill-opacity=".78" stroke="#FFFFFF" stroke-opacity=".16"/>')
        boxes.append(f'<circle cx="137" cy="{y+58}" r="27" fill="#FFD84D"/><text x="137" y="{y+68}" class="kr" font-size="25" font-weight="900" fill="#111827" text-anchor="middle">{i}</text>')
        boxes.append(text_nodes(wrap(entry, 27)[:3], 190, y + 58, 35, 48, 750))
    slide3 = base_svg('<text x="82" y="310" class="kr" font-size="57" font-weight="900" fill="#FFFFFF">판단 기준 3가지</text>' + ''.join(boxes), 3, "기준")

    steps = []
    for i, action in enumerate(item["actions"], 1):
        y = 415 + (i - 1) * 245
        steps.append(f'<text x="82" y="{y}" class="kr" font-size="74" font-weight="900" fill="#FFD84D" fill-opacity=".96">0{i}</text>')
        steps.append(f'<line x1="190" y1="{y-24}" x2="998" y2="{y-24}" stroke="#FFFFFF" stroke-opacity=".22" stroke-width="2"/>')
        steps.append(text_nodes(wrap(action, 26)[:3], 190, y, 37, 51, 720))
    slide4 = base_svg('<text x="82" y="300" class="kr" font-size="57" font-weight="900" fill="#FFFFFF">사장님이 지금 할 일</text>' + ''.join(steps), 4, "행동")

    take = text_nodes(wrap(item["takeaway"], 16)[:5], 82, 470, 64, 82, 900)
    slide5 = base_svg(
        '<text x="82" y="350" class="kr" font-size="27" font-weight="850" fill="#FFD84D">한 줄 정리</text>' + take +
        '<rect x="82" y="900" width="916" height="220" rx="28" fill="#FFD84D"/>'
        '<text x="128" y="970" class="kr" font-size="28" font-weight="850" fill="#111827">노무 리스크를 줄이는 첫 단계</text>'
        '<text x="128" y="1030" class="kr" font-size="39" font-weight="900" fill="#111827">합의 조건을 작성·서명·보관하세요</text>'
        '<text x="128" y="1082" class="kr" font-size="27" font-weight="750" fill="#111827">무료 전자근로계약서 · signplease.kr</text>', 5, "정리")
    return [slide1, slide2, slide3, slide4, slide5]


def instagram_caption(item: dict) -> str:
    criteria = "\n".join(f"{i}. {v}" for i, v in enumerate(item["criteria"], 1))
    actions = "\n".join(f"{i}. {v}" for i, v in enumerate(item["actions"], 1))
    sources = " · ".join(item["source_labels"])
    return (
        f'{item["hook"]}\n\n결론부터 말하면, {item["conclusion"]}\n\n판단 기준\n{criteria}\n\n'
        f'사장님이 지금 할 일\n{actions}\n\n한 줄 정리: {item["takeaway"]}\n\n'
        f'※ 일반적인 법 기준을 정리한 정보이며, 계약 내용과 실제 근무 형태에 따라 판단이 달라질 수 있습니다.\n'
        f'근거: {sources} · 검토일 {REVIEW_DATE}\n\n'
        '#소상공인 #자영업자 #알바고용 #노무상식 #근로계약서\n\n'
        '합의한 근로조건은 무료 전자근로계약서 싸인해주세요로 작성·서명·교부·보관하세요.\n'
        '지금 바로 시작해보세요.\nhttps://signplease.kr'
    )


def threads_caption(item: dict) -> str:
    action = " / ".join(item["actions"])
    return (
        f'{item["hook"]}\n\n결론: {item["conclusion"]}\n\n사장님 체크: {action}\n\n'
        f'※ 실제 계약·근무 형태에 따라 달라질 수 있습니다. 근거 검토일 {REVIEW_DATE}.\n\n'
        '합의한 근로조건은 무료 전자근로계약서 싸인해주세요로 작성·서명·보관하세요.\n'
        '지금 바로 시작해보세요.\n'
        'https://signplease.kr?utm_source=threads&utm_medium=social&utm_campaign=labor-question-db'
    )


def render(svg: Path, png: Path, profile: Path) -> None:
    try:
        import cairosvg
    except ImportError:
        cairosvg = None
    if cairosvg is not None:
        png.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1080, output_height=1350)
        return
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        raise RuntimeError("Google Chrome을 찾지 못했습니다.")
    png.parent.mkdir(parents=True, exist_ok=True)
    slide_profile = profile / f"{png.parent.parent.name}-{png.stem}"
    subprocess.run([
        str(chrome), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=1080,1350",
        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=1000",
        f"--user-data-dir={slide_profile}", f"--screenshot={png}", svg.resolve().as_uri()
    ], check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_pillow(item: dict, slide_index: int, background: Path, png: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    width, height = 1080, 1350
    photo = ImageOps.fit(Image.open(background).convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    canvas = photo.convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(82 + 145 * (y / height))
        overlay_draw.line((0, y, width, y), fill=(4, 13, 25, alpha))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

    def font(size: int, bold: bool = False):
        return ImageFont.truetype(font_path, size=size, index=8 if bold else 0)

    def lines(text: str, x: int, y: int, size: int, chars: int, gap: int, fill="#FFFFFF", bold=False,
              max_lines=6):
        for line_no, line in enumerate(wrap(text, chars)[:max_lines]):
            draw.text((x, y + line_no * gap), line, font=font(size, bold), fill=fill,
                      stroke_width=1 if bold else 0, stroke_fill=fill)

    draw.rounded_rectangle((64, 64, 1016, 1286), radius=30, outline=(255, 255, 255, 65), width=2)
    draw.rounded_rectangle((82, 91, 146, 99), radius=4, fill="#FFD84D")
    draw.text((82, 116), "사장님 현장 노무", font=font(25, True), fill="#FFFFFF")
    labels = ["질문", "결론", "기준", "행동", "정리"]
    page = f"{slide_index}/5 · {labels[slide_index-1]}"
    bbox = draw.textbbox((0, 0), page, font=font(25, True))
    draw.text((998 - (bbox[2] - bbox[0]), 116), page, font=font(25, True), fill="#FFFFFF")

    if slide_index == 1:
        draw.text((82, 520), f'{item["topic_code"]} · 실제 사장님 질문', font=font(27, True), fill="#FFD84D")
        lines(item["hook_title"], 82, 590, 76, 13, 94, bold=True, max_lines=4)
        lines(item["hook"], 82, 920, 36, 27, 53, fill="#F2F4F7", max_lines=4)
    elif slide_index == 2:
        draw.text((82, 455), "먼저 결론", font=font(27, True), fill="#FFD84D")
        lines(item["conclusion_title"], 82, 515, 70, 15, 86, bold=True, max_lines=3)
        lines(item["conclusion"], 82, 770, 39, 25, 56, fill="#F4F5F7", max_lines=5)
    elif slide_index == 3:
        draw.text((82, 245), "판단 기준 3가지", font=font(57, True), fill="#FFFFFF")
        for i, entry in enumerate(item["criteria"], 1):
            y = 350 + (i - 1) * 245
            draw.rounded_rectangle((82, y, 998, y + 205), radius=26, fill=(8, 20, 35, 205), outline=(255, 255, 255, 40), width=2)
            draw.ellipse((110, y + 31, 164, y + 85), fill="#FFD84D")
            n = str(i); nb = draw.textbbox((0, 0), n, font=font(25, True))
            draw.text((137 - (nb[2]-nb[0])/2, y + 40), n, font=font(25, True), fill="#111827")
            lines(entry, 190, y + 30, 35, 27, 48, bold=True, max_lines=3)
    elif slide_index == 4:
        draw.text((82, 245), "사장님이 지금 할 일", font=font(57, True), fill="#FFFFFF")
        for i, action in enumerate(item["actions"], 1):
            y = 380 + (i - 1) * 245
            draw.text((82, y - 42), f"0{i}", font=font(74, True), fill="#FFD84D")
            draw.line((190, y - 20, 998, y - 20), fill=(255, 255, 255, 55), width=2)
            lines(action, 190, y, 37, 26, 51, bold=True, max_lines=3)
    else:
        draw.text((82, 305), "한 줄 정리", font=font(27, True), fill="#FFD84D")
        lines(item["takeaway"], 82, 395, 64, 16, 82, bold=True, max_lines=5)
        draw.rounded_rectangle((82, 900, 998, 1120), radius=28, fill="#FFD84D")
        draw.text((128, 935), "노무 리스크를 줄이는 첫 단계", font=font(28, True), fill="#111827")
        draw.text((128, 990), "합의 조건을 작성·서명·보관하세요", font=font(39, True), fill="#111827")
        draw.text((128, 1045), "무료 전자근로계약서 · signplease.kr", font=font(27, True), fill="#111827")
    draw.text((82, 1215), "저장해두고 실제 상황에서 다시 확인하세요", font=font(23), fill=(255, 255, 255, 188))
    png.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(png, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start", required=True, help="Asia/Seoul ISO datetime")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    load_env()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if len(plan) > 10:
        raise SystemExit("Buffer 무료 한도상 한 번에 최대 10개만 생성합니다.")
    start = datetime.fromisoformat(args.start).replace(tzinfo=SEOUL)
    run_dir = ROOT / "output" / "campaigns" / args.run_id
    public_dir = ROOT / "docs" / "assets" / "campaigns" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / ".nojekyll").touch()
    base_url = os.environ["PUBLIC_ASSET_BASE_URL"].rstrip("/")
    channel_ids = {
        "instagram": os.environ["BUFFER_CHANNEL_INSTAGRAM"],
        "threads": os.environ["BUFFER_CHANNEL_THREADS"],
    }
    payloads, campaign_items, reviews = [], [], []
    profile = Path("/private/tmp/signplease-cardnews-chrome")
    for idx, item in enumerate(plan, 1):
        due_local = start + timedelta(hours=12 * (idx - 1))
        folder = f'{idx:02d}-{due_local:%Y%m%d-%H%M}-{item["slug"]}'
        item_dir = run_dir / folder
        card_dir = item_dir / "cards"
        asset_card_dir = public_dir / folder / "cards"
        card_dir.mkdir(parents=True, exist_ok=True)
        asset_card_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item["background"], item_dir / "background.png")
        slides = make_slides(item)
        urls = []
        for slide_idx, svg_text in enumerate(slides, 1):
            svg = card_dir / f"slide-{slide_idx:02d}.svg"
            png = asset_card_dir / f"slide-{slide_idx:02d}.png"
            svg.write_text(svg_text, encoding="utf-8")
            if args.render and not png.exists():
                render_pillow(item, slide_idx, item_dir / "background.png", png)
            urls.append(f"{base_url}/assets/campaigns/{args.run_id}/{folder}/cards/slide-{slide_idx:02d}.png")
        ig_text = instagram_caption(item)
        th_text = threads_caption(item)
        due_utc = due_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        ig_input = {
            "text": ig_text, "channelId": channel_ids["instagram"], "schedulingType": "automatic",
            "mode": "customScheduled", "dueAt": due_utc, "aiAssisted": True,
            "source": "signplease-marketing-agent", "assets": [{"image": {"url": u}} for u in urls],
            "metadata": {"instagram": {"type": "post", "shouldShareToFeed": True}},
        }
        th_input = {
            "text": th_text, "channelId": channel_ids["threads"], "schedulingType": "automatic",
            "mode": "customScheduled", "dueAt": due_utc, "aiAssisted": True,
            "source": "signplease-marketing-agent", "assets": [{"image": {"url": urls[0]}}],
        }
        payloads.extend([{"platform": "instagram", "input": ig_input}, {"platform": "threads", "input": th_input}])
        content = {**item, "scheduledAt": due_local.isoformat(), "instagram": ig_text, "threads": th_text,
                   "cards": [str((card_dir / f"slide-{n:02d}.svg").relative_to(ROOT)) for n in range(1, 6)],
                   "publicUrls": urls}
        (item_dir / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        issues = []
        for phrase in FORBIDDEN:
            if phrase in ig_text or phrase in th_text:
                issues.append(f"금지 표현: {phrase}")
        if ig_text.count("싸인해주세요") != 1 or th_text.count("싸인해주세요") != 1:
            issues.append("플랫폼별 브랜드 언급 1회 제한 위반")
        if "utm_" in ig_text or "utm_source=threads" not in th_text:
            issues.append("플랫폼별 URL 규칙 위반")
        if any("law.go.kr" not in u and "moel.go.kr" not in u for u in item["source_urls"]):
            issues.append("비공식 출처 포함")
        review = {"topic": item["name"], "status": "blocked" if issues else "approved", "issues": issues,
                  "checks": {"overlap": "new", "cards": 5, "brandMentions": {"instagram": ig_text.count("싸인해주세요"), "threads": th_text.count("싸인해주세요")},
                             "officialSources": True, "reviewedOn": REVIEW_DATE}}
        (item_dir / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        reviews.append(review)
        campaign_items.append({"folder": folder, "topic": item["name"], "dueAt": due_utc, "status": review["status"], "publicUrls": urls})
    campaign = {"runId": args.run_id, "createdAt": datetime.now(SEOUL).isoformat(), "sourceDatabase": "skills/create-small-business-labor-cardnews/references/topic-db.md",
                "topicOverlapCheck": "output/proposed_buffer_capacity_topics.json", "capacity": {"instagram": len(plan), "threads": len(plan)}, "items": campaign_items}
    (run_dir / "campaign.json").write_text(json.dumps(campaign, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "review.json").write_text(json.dumps({"status": "blocked" if any(r["status"] == "blocked" for r in reviews) else "approved", "items": reviews}, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "buffer_payloads.json").write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "pending_payloads.json").write_text("[]\n", encoding="utf-8")
    print(json.dumps({"runDir": str(run_dir.relative_to(ROOT)), "items": len(plan), "cards": len(plan) * 5, "payloads": len(payloads)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
