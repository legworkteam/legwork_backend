from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from fastapi.routing import APIRoute
from PIL import Image, ImageDraw, ImageFont

from app.main import app

OUTPUT_PATH = Path(__file__).resolve().parent / "docs" / "endpoint_inventory_report.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\NanumGothic.ttf")
TITLE_FONT_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")

PAGE_WIDTH = 2480
PAGE_HEIGHT = 1754
MARGIN_X = 70
MARGIN_Y = 60
TABLE_TOP_GAP = 26
ROW_PADDING_X = 12
ROW_PADDING_Y = 10


@dataclass(frozen=True)
class EndpointNote:
    group: str
    auth: str
    returns: str
    fallback: str
    notes: str


NOTES: dict[tuple[str, str], EndpointNote] = {
    ("POST", "/api/v1/auth/signup"): EndpointNote(
        "Auth",
        "Public",
        "실제 DB에 로컬 회원 생성, JWT 발급 준비",
        "-",
        "LOCAL 계정 생성",
    ),
    ("POST", "/api/v1/auth/login"): EndpointNote(
        "Auth",
        "Public",
        "실제 DB 조회 + JWT/refresh 발급",
        "-",
        "실패 횟수/잠금도 실제 저장",
    ),
    ("POST", "/api/v1/auth/social"): EndpointNote(
        "Auth",
        "Public",
        "사용자 생성/조회와 토큰 발급은 실제 DB/JWT",
        "Google/Kakao 프로필 fetch는 mock",
        "authorization code를 해시해 deterministic 프로필 생성",
    ),
    ("POST", "/api/v1/auth/refresh"): EndpointNote(
        "Auth",
        "Public",
        "실제 refresh token rotation",
        "-",
        "refresh token hash를 DB에 저장/폐기",
    ),
    ("POST", "/api/v1/auth/logout"): EndpointNote(
        "Auth",
        "Member",
        "실제 refresh token revoke",
        "-",
        "토큰 무효화만 수행",
    ),
    ("POST", "/api/v1/auth/claim"): EndpointNote(
        "Auth",
        "Member + guest token",
        "실제 DB에서 guest recent-products를 member로 이전",
        "Avatar/Try-on/Coordi claim 미구현",
        "현재는 RecentProduct만 claim",
    ),
    ("POST", "/api/v1/guest-sessions"): EndpointNote(
        "Guest",
        "Public",
        "실제 guest session 생성 + guest JWT 발급",
        "-",
        "만료 규칙은 KST 기준",
    ),
    ("GET", "/api/v1/me"): EndpointNote(
        "Users",
        "Member",
        "실제 회원 프로필 반환",
        "-",
        "avatar 존재 여부도 함께 계산",
    ),
    ("PATCH", "/api/v1/me"): EndpointNote(
        "Users",
        "Member",
        "실제 회원 프로필 수정",
        "-",
        "DB 직접 업데이트",
    ),
    ("PATCH", "/api/v1/me/password"): EndpointNote(
        "Users",
        "Member",
        "실제 비밀번호 변경",
        "-",
        "password hash 갱신",
    ),
    ("GET", "/api/v1/products/{product_id}"): EndpointNote(
        "Products",
        "Guest or Member",
        "실제 DB 상품 상세 반환",
        "라이브 커머스 API 없음",
        "seed 카탈로그 기반, recent-products 기록",
    ),
    ("GET", "/api/v1/products/{product_id}/variants"): EndpointNote(
        "Products",
        "Guest or Member",
        "실제 DB 옵션 반환",
        "-",
        "활성/재고 기준으로 정리",
    ),
    ("GET", "/api/v1/recent-products"): EndpointNote(
        "Products",
        "Guest or Member",
        "실제 DB 최근 본 상품 반환",
        "-",
        "owner별 커서 페이지네이션",
    ),
    ("POST", "/api/v1/cart/items"): EndpointNote(
        "Cart",
        "Member",
        "실제 DB 장바구니 항목 추가 후 전체 cart 반환",
        "-",
        "재고/variant 검증 포함",
    ),
    ("GET", "/api/v1/cart"): EndpointNote(
        "Cart",
        "Member",
        "실제 DB 장바구니 조회",
        "-",
        "cart aggregate 응답",
    ),
    ("PATCH", "/api/v1/cart/items/{cart_item_id}"): EndpointNote(
        "Cart",
        "Member",
        "실제 DB 장바구니 수정",
        "-",
        "수량 변경",
    ),
    ("DELETE", "/api/v1/cart/items/{cart_item_id}"): EndpointNote(
        "Cart",
        "Member",
        "실제 DB 장바구니 삭제",
        "-",
        "삭제 후 전체 cart 반환",
    ),
    ("POST", "/api/v1/orders"): EndpointNote(
        "Orders",
        "Member",
        "주문/주문항목/재고 차감은 실제 DB",
        "결제 승인만 MockPayment",
        "paymentMethod 기본값도 mock",
    ),
    ("GET", "/api/v1/me/orders"): EndpointNote(
        "Orders",
        "Member",
        "실제 DB 주문 목록 반환",
        "-",
        "커서 페이지네이션",
    ),
    ("GET", "/api/v1/me/orders/{order_id}"): EndpointNote(
        "Orders",
        "Member",
        "실제 DB 주문 상세 반환",
        "-",
        "주문항목 포함",
    ),
    ("POST", "/api/v1/me/products"): EndpointNote(
        "Owned Products",
        "Member",
        "실제 등록상품 생성",
        "-",
        "serial/product code 매칭 기반",
    ),
    ("GET", "/api/v1/me/products"): EndpointNote(
        "Owned Products",
        "Member",
        "실제 내 등록상품/구매상품 목록 반환",
        "-",
        "커서 페이지네이션",
    ),
    ("GET", "/api/v1/me/products/{registration_id}"): EndpointNote(
        "Owned Products",
        "Member",
        "실제 등록상품 상세 반환",
        "-",
        "product 정보 조인",
    ),
    ("GET", "/api/v1/me/products/{registration_id}/care-guide"): EndpointNote(
        "Owned Products",
        "Member",
        "실제 care guide 반환",
        "-",
        "상품 care guide를 조회",
    ),
    ("GET", "/api/v1/stores"): EndpointNote(
        "Stores",
        "Member",
        "실제 DB 매장 + 예약 가능 슬롯 반환",
        "슬롯 자체는 business-hours 계산값",
        "확정 예약과 충돌하는 슬롯만 제외",
    ),
    ("GET", "/api/v1/health"): EndpointNote(
        "Health",
        "Public",
        "앱 상태/환경/시간 반환",
        "-",
        "DB 의존 없이 동작",
    ),
    ("POST", "/api/v1/product-recognitions"): EndpointNote(
        "OCR",
        "Guest or Member",
        "실제 PaddleOCR 실행 후 DB 상품코드 매칭",
        "1차 OCR 실패 시 2차 전처리 재시도",
        "mock 아님, OCR 결과는 DB 카탈로그에 의존",
    ),
    ("GET", "/api/v1/jobs/{jobId}"): EndpointNote(
        "Jobs",
        "Owner only",
        "실제 DB job 상태 반환",
        "-",
        "try-on/diagnosis 비동기 추적",
    ),
    ("GET", "/api/v1/files/{fileId}"): EndpointNote(
        "Files",
        "Owner or public file",
        "실제 로컬 스토리지 파일 반환",
        "-",
        "private/public visibility 검사",
    ),
    ("POST", "/api/v1/me/avatar"): EndpointNote(
        "Avatar",
        "Member",
        "실제 avatar 파라미터 생성",
        "-",
        "DB 저장",
    ),
    ("GET", "/api/v1/me/avatar"): EndpointNote(
        "Avatar",
        "Member",
        "실제 avatar 파라미터 조회",
        "-",
        "DB 조회",
    ),
    ("PUT", "/api/v1/me/avatar"): EndpointNote(
        "Avatar",
        "Member",
        "실제 avatar 생성/수정",
        "-",
        "upsert",
    ),
    ("PUT", "/api/v1/guest-sessions/me/avatar-parameters"): EndpointNote(
        "Avatar",
        "Guest",
        "실제 guest avatar 파라미터 저장",
        "-",
        "guest session row 업데이트",
    ),
    ("POST", "/api/v1/avatar-try-ons"): EndpointNote(
        "Try-on",
        "Guest or Member",
        "job/file/DB 흐름은 실제 구현",
        "provider는 기본 mock, openai 설정이어도 avatar 요청은 mock fallback",
        "source photo가 없어서 OpenAI provider가 내부적으로 mock 위임",
    ),
    ("POST", "/api/v1/try-ons"): EndpointNote(
        "Try-on",
        "Guest or Member",
        "job/file/DB 흐름은 실제 구현",
        "기본 mock, TRY_ON_PROVIDER=openai면 photo try-on만 실제 OpenAI 사용 가능",
        "guest는 호출 횟수 제한, fullCoordi는 member only",
    ),
    ("POST", "/api/v1/try-ons/{tryOnId}/save"): EndpointNote(
        "Try-on",
        "Member",
        "실제 try-on 결과 영구 저장",
        "-",
        "TTL 제거",
    ),
    ("GET", "/api/v1/me/try-ons"): EndpointNote(
        "Try-on",
        "Member",
        "실제 저장된 try-on 목록 반환",
        "-",
        "saved 결과만 노출",
    ),
    ("DELETE", "/api/v1/me/try-ons/{tryOnId}"): EndpointNote(
        "Try-on",
        "Member",
        "실제 saved try-on row와 파일 삭제",
        "-",
        "스토리지 파일도 함께 제거",
    ),
    ("GET", "/api/v1/products/{productId}/recommendations"): EndpointNote(
        "Recommendations",
        "Guest or Member",
        "실제 rule-based 추천 계산",
        "ML/외부 추천 API 없음",
        "상품/태그/재고 기준 정렬",
    ),
    ("POST", "/api/v1/me/coordis"): EndpointNote(
        "Coordi",
        "Member",
        "실제 saved coordi 생성",
        "-",
        "item rows 포함 저장",
    ),
    ("GET", "/api/v1/me/coordis"): EndpointNote(
        "Coordi",
        "Member",
        "실제 saved coordi 목록 반환",
        "-",
        "커서 페이지네이션",
    ),
    ("GET", "/api/v1/me/coordis/{savedCoordiId}"): EndpointNote(
        "Coordi",
        "Member",
        "실제 saved coordi 상세 반환",
        "-",
        "item/product detail 포함",
    ),
    ("PATCH", "/api/v1/me/coordis/{savedCoordiId}"): EndpointNote(
        "Coordi",
        "Member",
        "실제 saved coordi 수정",
        "-",
        "item 교체 가능",
    ),
    ("DELETE", "/api/v1/me/coordis/{savedCoordiId}"): EndpointNote(
        "Coordi",
        "Member",
        "실제 saved coordi 삭제",
        "-",
        "관련 item rows도 삭제",
    ),
    ("POST", "/api/v1/diagnoses"): EndpointNote(
        "Diagnosis",
        "Member",
        "job/file/DB 저장 흐름은 실제 구현",
        "손상 판정 provider는 MockDiagnosisProvider",
        "업로드 이미지와 등록상품 기준 deterministic mock 결과",
    ),
    ("GET", "/api/v1/diagnoses/{diagnosisId}"): EndpointNote(
        "Diagnosis",
        "Member",
        "실제 저장된 진단 상세 반환",
        "-",
        "damage rows 포함",
    ),
    ("GET", "/api/v1/diagnoses/{diagnosisId}/care-guide"): EndpointNote(
        "Diagnosis",
        "Member",
        "실제 진단 연계 care guide 반환",
        "-",
        "등록상품 기준",
    ),
    ("POST", "/api/v1/repair-reservations"): EndpointNote(
        "Repairs",
        "Member",
        "실제 예약 생성",
        "-",
        "진단의 repair_needed와 슬롯 충돌 검사",
    ),
    ("GET", "/api/v1/repair-reservations"): EndpointNote(
        "Repairs",
        "Member",
        "실제 예약 목록 반환",
        "-",
        "본인 예약만",
    ),
    ("POST", "/api/v1/repair-reservations/{repairReservationId}/cancel"): EndpointNote(
        "Repairs",
        "Member",
        "실제 예약 취소",
        "-",
        "confirmed 상태만 취소 가능",
    ),
}

GROUP_ORDER = [
    "Auth",
    "Guest",
    "Users",
    "Products",
    "Cart",
    "Orders",
    "Owned Products",
    "Stores",
    "Health",
    "OCR",
    "Jobs",
    "Files",
    "Avatar",
    "Try-on",
    "Recommendations",
    "Coordi",
    "Diagnosis",
    "Repairs",
]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    text = text or "-"
    words = text.split(" ")
    if len(words) == 1:
        return break_long_token(draw, text, font, max_width)

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = word
        else:
            lines.extend(break_long_token(draw, word, font, max_width))
            current = ""
    if current:
        lines.append(current)
    return lines or ["-"]


def break_long_token(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = ch
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or ["-"]


def collect_routes() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"})
        for method in methods:
            key = (method, route.path)
            note = NOTES.get(key)
            if note is None:
                raise KeyError(f"Missing metadata for {method} {route.path}")
            records.append(
                {
                    "group": note.group,
                    "method": method,
                    "path": route.path,
                    "summary": route.summary or "",
                    "auth": note.auth,
                    "returns": note.returns,
                    "fallback": note.fallback,
                    "notes": note.notes,
                }
            )
    records.sort(
        key=lambda item: (
            GROUP_ORDER.index(item["group"]),
            item["path"],
            item["method"],
        )
    )
    return records


def make_pdf(records: list[dict[str, str]]) -> None:
    title_font = ImageFont.truetype(str(TITLE_FONT_PATH), 34)
    subtitle_font = ImageFont.truetype(str(FONT_PATH), 18)
    header_font = ImageFont.truetype(str(FONT_PATH), 18)
    body_font = ImageFont.truetype(str(FONT_PATH), 16)

    column_defs = [
        ("Group", 170),
        ("Method", 110),
        ("Path", 510),
        ("Auth", 210),
        ("Returns", 470),
        ("Mock/Fallback", 410),
        ("Notes", 390),
    ]
    total_width = sum(width for _, width in column_defs)
    assert total_width <= PAGE_WIDTH - MARGIN_X * 2

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in records:
        grouped[row["group"]].append(row)

    pages: list[Image.Image] = []
    current_group_index = 0

    def new_page() -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        draw = ImageDraw.Draw(image)
        draw.text((MARGIN_X, MARGIN_Y), "Atelier Lens Backend Endpoint Inventory", fill="black", font=title_font)
        draw.text(
            (MARGIN_X, MARGIN_Y + 46),
            "Generated from code on 2026-08-20. Focus: implemented scope, actual data vs mock/fallback behavior.",
            fill="black",
            font=subtitle_font,
        )
        return image, draw, MARGIN_Y + 95

    image, draw, y = new_page()

    for group in GROUP_ORDER:
        rows = grouped.get(group, [])
        if not rows:
            continue

        group_title_height = 30
        header_height = 34

        if y + group_title_height + header_height + 40 > PAGE_HEIGHT - MARGIN_Y:
            pages.append(image)
            image, draw, y = new_page()

        draw.text((MARGIN_X, y), f"[{group}]", fill="black", font=header_font)
        y += group_title_height

        x = MARGIN_X
        for title, width in column_defs:
            draw.rectangle((x, y, x + width, y + header_height), outline="black", width=2, fill="#EAEAEA")
            draw.text((x + 8, y + 7), title, fill="black", font=header_font)
            x += width
        y += header_height

        for row in rows:
            wrapped_columns: list[list[str]] = []
            row_height = 0
            for key, width in [
                ("group", 170),
                ("method", 110),
                ("path", 510),
                ("auth", 210),
                ("returns", 470),
                ("fallback", 410),
                ("notes", 390),
            ]:
                lines = wrap_text(draw, row[key], body_font, width - ROW_PADDING_X * 2)
                wrapped_columns.append(lines)
                line_height = sum(draw.textbbox((0, 0), line, font=body_font)[3] for line in lines)
                line_height += (len(lines) - 1) * 4
                row_height = max(row_height, line_height + ROW_PADDING_Y * 2)

            if y + row_height + TABLE_TOP_GAP > PAGE_HEIGHT - MARGIN_Y:
                pages.append(image)
                image, draw, y = new_page()
                draw.text((MARGIN_X, y), f"[{group}] (cont.)", fill="black", font=header_font)
                y += group_title_height
                x = MARGIN_X
                for title, width in column_defs:
                    draw.rectangle((x, y, x + width, y + header_height), outline="black", width=2, fill="#EAEAEA")
                    draw.text((x + 8, y + 7), title, fill="black", font=header_font)
                    x += width
                y += header_height

            x = MARGIN_X
            for (title, width), lines in zip(column_defs, wrapped_columns, strict=True):
                draw.rectangle((x, y, x + width, y + row_height), outline="black", width=1)
                text_y = y + ROW_PADDING_Y
                for line in lines:
                    draw.text((x + ROW_PADDING_X, text_y), line, fill="black", font=body_font)
                    text_y += draw.textbbox((0, 0), line, font=body_font)[3] + 4
                x += width
            y += row_height

        y += TABLE_TOP_GAP
        current_group_index += 1

    pages.append(image)
    pages[0].save(OUTPUT_PATH, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])


def main() -> None:
    records = collect_routes()
    make_pdf(records)
    print(f"Created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
