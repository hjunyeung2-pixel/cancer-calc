# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from collections import defaultdict
from io import BytesIO

# ReportLab (PDF)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics

# -----------------------------
# 안전한 폰트 등록 (TTF만 사용, 실패 시 자동 폴백)
# -----------------------------
import os, re
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab import rl_config

# 이모지(미지원 글리프) 제거
_EMOJI_RE = re.compile(r"[\U00010000-\U0010FFFF]")
def safe_text(s: str) -> str:
    return _EMOJI_RE.sub("", s or "")

# Streamlit 환경에서 자주 쓰는 폴더 경로 후보
CANDIDATE_DIRS = [
    Path.cwd() / "fonts",
    Path(__file__).parent / "fonts" if "__file__" in globals() else Path.cwd() / "fonts",
    Path("/app/fonts"),  # Streamlit Cloud 등에서 직접 지정한 경로가 있다면
]

# 사용할 파일명 후보(TTF만!) — 프로젝트 fonts 폴더에 실제로 넣어두세요.
PREFERRED_REGULAR_FILES = ["NanumGothic.ttf", "NotoSansKR-Regular.ttf"]
PREFERRED_BOLD_FILES    = ["NanumGothicBold.ttf", "NotoSansKR-Bold.ttf"]

REGULAR_PATH = None
BOLD_PATH = None

def find_first_existing(candidates, dirs):
    for d in dirs:
        if not d.exists():
            continue
        for name in candidates:
            p = d / name
            if p.exists() and p.suffix.lower() == ".ttf":  # TTF만 허용
                return str(p)
    return None

REGULAR_PATH = find_first_existing(PREFERRED_REGULAR_FILES, CANDIDATE_DIRS)
BOLD_PATH    = find_first_existing(PREFERRED_BOLD_FILES,    CANDIDATE_DIRS)

FONT_MODE = "CID-FALLBACK"
BODY_FONT = "HYGoThic-Medium"  # CID 폴백 기본값
BOLD_FONT = "HYGoThic-Medium"

try:
    if not (REGULAR_PATH and BOLD_PATH):
        raise FileNotFoundError("TTF not found in fonts dir")

    # ❗ 주의: OTF(CFF), TTC, Variable TTF는 절대 넣지 마세요 (TTFError 유발)
    pdfmetrics.registerFont(TTFont("KR-Regular", REGULAR_PATH))
    pdfmetrics.registerFont(TTFont("KR-Bold",    BOLD_PATH))
    pdfmetrics.registerFontFamily("KR", normal="KR-Regular", bold="KR-Bold",
                                  italic="KR-Regular", boldItalic="KR-Bold")
    BODY_FONT = "KR-Regular"
    BOLD_FONT = "KR-Bold"
    FONT_MODE = "TTF-EMBED"

except (TTFError, OSError, FileNotFoundError) as e:
    # 폰트 등록 실패 → 안전한 CID 폴백으로 전환(임베딩은 안 되지만 한글은 보이게)
    pdfmetrics.registerFont(UnicodeCIDFont('HYGoThic-Medium'))
    BODY_FONT = "HYGoThic-Medium"
    BOLD_FONT = "HYGoThic-Medium"
    FONT_MODE = f"CID-FALLBACK ({type(e).__name__})"

# 미지원 글리프 경고 활성화
rl_config.warnOnMissingFontGlyphs = True

# (선택) 화면에 진단 정보 표시
try:
    import streamlit as st
    st.caption(f"🔤 PDF Font Mode: {FONT_MODE}")
    st.caption(f"📁 Fonts searched: {', '.join(str(p) for p in CANDIDATE_DIRS)}")
    st.caption(f"✅ Regular: {REGULAR_PATH or 'CID fallback'}")
    st.caption(f"✅ Bold: {BOLD_PATH or 'CID fallback'}")
    st.caption(f"📜 Registered: {', '.join(sorted(pdfmetrics.getRegisteredFontNames()))}")
except Exception:
    pass


# -----------------------------
# 스타일 정의
# -----------------------------
def build_pdf_styles():
    styles = getSampleStyleSheet()
    # BODY_FONT / BOLD_FONT 는 실제 등록된 폰트 이름이어야 합니다.
    # 예) BODY_FONT="KR-Regular", BOLD_FONT="KR-Bold"
    # (TTF 실패 시 둘 다 "HYGoThic-Medium")
    styles.add(ParagraphStyle(
        name='CenterTitle',
        fontName=BOLD_FONT,     # 제목은 굵게 페이스 직접 지정
        fontSize=18,
        alignment=1,
        leading=24,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='KoreanBody',
        fontName=BODY_FONT,     # 본문은 보통 페이스
        fontSize=11,
        leading=16
    ))
    styles.add(ParagraphStyle(
        name='KoreanBold',
        fontName=BOLD_FONT,     # 굵게 스타일은 굵은 페이스
        fontSize=12,
        leading=16
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName=BOLD_FONT,     # 섹션 헤더도 굵게
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=6
    ))
    return styles


# -----------------------------
# PDF 저장 함수 (화면과 동일 구조)
# -----------------------------
def save_pdf(customer_name, company_data, yearly_events, yearly_payouts, total_amount):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30
    )
    styles = build_pdf_styles()
    story = []

    # 제목
    story.append(Paragraph(safe_text("암주요치료비 보장 통합 제안서"), styles['CenterTitle']))
    story.append(Spacer(1, 10))

    # 고객명: <b> 태그 대신 표로 굵게 처리
    customer_table = Table(
        [["고객명", safe_text(customer_name or "")]],
        colWidths=[60, 380]
    )
    customer_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,0), BOLD_FONT),   # 라벨 굵게
        ('FONTNAME', (1,0), (1,0), BODY_FONT),   # 값 보통
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',    (0,0), (0,0), 'LEFT'),
        ('ALIGN',    (1,0), (1,0), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING',    (0,0), (-1,-1), 2),
    ]))
    story.append(customer_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        safe_text("본 제안서는 고객님의 건강을 든든히 지켜드릴 맞춤형 보장을 정리한 자료입니다."),
        styles['KoreanBody']
    ))
    story.append(Spacer(1, 20))

    # 회사별 가입 담보
    if company_data:
        story.append(Paragraph(safe_text("1. 회사별 가입 담보 정리"), styles['SectionHeader']))
        for comp, rows in company_data.items():
            if not rows:
                continue
            table_data = [["담보명", "가입금액(만원)"]] + [[safe_text(a), safe_text(b)] for a, b in rows]
            table = Table(table_data, colWidths=[290, 150])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d9eaf7")),
                ('FONTNAME', (0,0), (-1,0), BOLD_FONT),
                ('FONTNAME', (0,1), (-1,-1), BODY_FONT),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            story.append(Paragraph(safe_text(f"◼ {comp}"), styles['KoreanBold']))
            story.append(table)
            story.append(Spacer(1, 12))

    # 연도별 치료 내역
    if yearly_events:
        story.append(Paragraph(safe_text("2. 연도별 치료 내역"), styles['SectionHeader']))
        table_data = [["연도", "치료 내역"]]
        for year, evs in yearly_events.items():
            if not evs:
                continue
            table_data.append([f"{year}년차", safe_text(" / ".join(evs))])
        table = Table(table_data, colWidths=[120, 320])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fde9d9")),
            ('FONTNAME', (0,0), (-1,0), BOLD_FONT),
            ('FONTNAME', (0,1), (-1,-1), BODY_FONT),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)

    story.append(PageBreak())

    # -----------------------------
    # 3. 연도별 지급 내역 (같은 연도 + 합계까지 병합)
    # -----------------------------
    if yearly_payouts:
        story.append(Paragraph(safe_text("3. 연도별 지급 내역"), styles['SectionHeader']))

        table_data = [["연도", "특약명", "지급금액(만원)"]]
        spans = []             # 연도 셀 병합 지시어 모음
        grand_total = 0
        row_idx = 1            # 헤더 다음 행부터 1로 시작

        for year, pays in yearly_payouts.items():
            visible_rows_start = row_idx
            item_count = 0
            year_total = 0

            # 개별 지급 항목
            for (treaty, amt) in pays:
                if amt <= 0:
                    continue
                table_data.append([f"{year}년차", safe_text(treaty), f"{amt:,}"])
                row_idx += 1
                item_count += 1
                year_total += amt

            # 항목이 없으면 대시 한 줄(병합 대상에 포함)
            if item_count == 0:
                table_data.append([f"{year}년차", "-", "0"])
                row_idx += 1
                item_count = 1

            # 연도 합계 줄 추가 (연도칸은 임시로 값 채움 → 병합 후 첫 칸만 보이게 처리)
            table_data.append([f"{year}년차", "▶ 합계", f"{year_total:,}"])
            row_idx += 1

            # (핵심) 연도 칸 병합 범위: 첫 행 ~ '합계' 행까지 모두 포함
            span_end = row_idx - 1  # 방금 추가한 합계 행 인덱스
            if span_end > visible_rows_start:
                spans.append(('SPAN', (0, visible_rows_start), (0, span_end)))
                # 병합 영역에서 첫 행을 제외한 모든 연도칸을 공백으로 치환
                for r in range(visible_rows_start + 1, span_end + 1):
                    table_data[r][0] = ""

            grand_total += year_total

        table = Table(table_data, colWidths=[60, 280, 100])
        style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d9eaf7")),
            ('FONTNAME',   (0,0), (-1,0), BOLD_FONT),
            ('FONTNAME',   (0,1), (-1,-1), BODY_FONT),
            ('ALIGN',      (0,0), (-1,0), 'CENTER'),  # 헤더 중앙
            ('ALIGN',      (0,1), (0,-1), 'CENTER'),  # 연도열 중앙
            ('ALIGN',      (1,1), (1,-1), 'LEFT'),    # 특약명 좌
            ('ALIGN',      (2,1), (2,-1), 'RIGHT'),   # 금액 우
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE',   (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.grey),
        ]
        style.extend(spans)  # ← 병합 적용
        table.setStyle(style)

        story.append(table)
        story.append(Spacer(1, 20))

        total_table = Table([["총 지급보험금", f"{grand_total:,} 만원"]], colWidths=[240, 200])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fde9d9")),
            ('TEXTCOLOR',  (0,0), (0,-1), colors.black),
            ('FONTNAME',   (0,0), (-1,-1), BOLD_FONT),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE',   (0,0), (-1,-1), 14),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID',       (0,0), (-1,-1), 1, colors.black),
        ]))
        story.append(total_table)
        story.append(Spacer(1, 15))

        story.append(Paragraph(
            safe_text(f"총 {grand_total:,} 만원의 보험금이 지급될 수 있습니다. "
                      "이 금액은 고객님의 치료 과정 전반에 걸쳐 발생할 수 있는 비용을 든든하게 대비해드립니다."),
            styles['KoreanBody']
        ))

    doc.build(story)
    buffer.seek(0)
    return buffer




# -------------------------
# 축약 매핑
# -------------------------
SHORT_NAMES = {
    # 삼성
    "암직접치료보장": "직접",
    "암주요치료보장": "주요",
    "갑상선·기타피부암직접치료보장": "유사직접",
    "갑상선·기타피부암주요치료보장": "유사주요",
    "상급종합병원 암직접치료보장": "상급직접",
    "상급종합병원 갑상선·기타피부암직접치료보장": "상급유사직접",
    "프리미엄암직접치료보장": "프리미엄",
    "프리미엄클래스암특정치료보장": "프리미엄클래스",
    "항암방사선치료특약": "방사선",
    "항암약물치료특약": "약물",
    "항암중입자방사선치료특약": "중입자",
    # KB
    "암(유사암 제외) 주요치료비": "암주요",
    "유사암 주요치료비": "유사암",
    "비급여 암 주요치료비 II": "비급여주요",
    "비급여 항암약물치료비 II": "비급여약물",
}

def shorten_details(details):
    if not details:
        return "-"
    return "\n".join([f"{SHORT_NAMES.get(t, t)}:{amt}" for t, amt in details])

# -------------------------
# 삼성생명 MAPPING
# -------------------------
MAPPING_SAMSUNG = {
    "수술": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), 
            ("상급종합병원 암직접치료보장", 1, 1.0)],
    "방사선": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), 
            ("상급종합병원 암직접치료보장", 1, 1.0) ,("항암방사선치료특약", 1, 1.0)],
    "항암약물": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), 
             ("상급종합병원 암직접치료보장", 1, 1.0) ,("항암약물치료특약", 1, 1.0)],
    "항암호르몬치료제": [("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0) ], 
    "중입자": [("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0) ,
            ("항암방사선치료특약", 1, 1.0), ("항암중입자방사선치료특약", 1, 1.0)],
    "세기조절": [("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0) ,
             ("항암방사선치료특약", 1, 1.0), ("프리미엄암직접치료보장", 1, 1.0)],
    "양성자": [("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0) ,
            ("항암방사선치료특약", 1, 1.0), ("프리미엄암직접치료보장", 1, 1.0)],
    "정위적": [("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0) ,
            ("항암방사선치료특약", 1, 1.0), ("프리미엄암직접치료보장", 1, 1.0)],
    "로봇수술": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0), 
             ("프리미엄암직접치료보장", 1, 1.0), ("프리미엄클래스암특정치료보장", 1, 1.0)],
    "표적(급여)": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0),
               ("프리미엄암직접치료보장", 1, 1.0)], 
    "표적(비급여)": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0),
                ("프리미엄암직접치료보장", 2, 1.0), ("프리미엄클래스암특정치료보장", 1, 1.0)],
    "면역(급여)": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0), 
               ("프리미엄암직접치료보장", 2, 1.0)],
    "면역(비급여)": [("암주요치료보장", 1, 1.0), ("암직접치료보장", 1, 1.0), ("상급종합병원 암직접치료보장", 1, 1.0),
                ("프리미엄암직접치료보장", 4, 1.0), ("프리미엄클래스암특정치료보장", 2, 1.0)],
}

DEFAULT_AMOUNTS_SAMSUNG = {
    "암주요치료보장": 0, "갑상선·기타피부암주요치료보장": 0, "암직접치료보장": 0,
    "갑상선·기타피부암직접치료보장": 0, "상급종합병원 암직접치료보장": 0,
    "상급종합병원 갑상선·기타피부암직접치료보장": 0, "프리미엄암직접치료보장": 0,
    "프리미엄클래스암특정치료보장": 0, "항암방사선치료특약": 0, "항암약물치료특약": 0, "항암중입자방사선치료특약": 0,
}
MAX_USAGE_SAMSUNG = {
    "암주요치료보장": 50, "갑상선·기타피부암주요치료보장": 50, "암직접치료보장": 10,
    "갑상선·기타피부암직접치료보장": 10, "상급종합병원 암직접치료보장": 10,
    "상급종합병원 갑상선·기타피부암직접치료보장": 10, "프리미엄암직접치료보장": 80,
    "프리미엄클래스암특정치료보장": 20, "항암방사선치료특약": 1, "항암약물치료특약": 1, "항암중입자방사선치료특약": 1,
}

# -------------------------
# KB손해보험 MAPPING
# -------------------------
MAPPING_KB = {
    "수술": [("암(유사암 제외) 주요치료비", 1, 1.0)],
    "로봇수술": [("암(유사암 제외) 주요치료비", 1, 1.0), ("비급여 암 주요치료비 II", 1, 1.0)],
    "표적(급여)": [("암(유사암 제외) 주요치료비", 1, 1.0), ("항암약물치료특약", 1, 1.0)],
    "표적(비급여)": [("암(유사암 제외) 주요치료비", 1, 1.0), ("비급여 암 주요치료비 II", 1, 1.0), 
                ("비급여 항암약물치료비 II", 1, 1.0), ("항암약물치료특약", 1, 1.0)],
    "면역(급여)": [("암(유사암 제외) 주요치료비", 1, 1.0), ("항암약물치료특약", 1, 1.0)],
    "면역(비급여)": [("암(유사암 제외) 주요치료비", 1, 1.0), ("비급여 암 주요치료비 II", 1, 1.0), 
                ("비급여 항암약물치료비 II", 1, 1.0), ("항암약물치료특약", 1, 1.0)],
    "세기조절": [("암(유사암 제외) 주요치료비", 1, 1.0), ("항암방사선치료특약", 1, 1.0)],
    "양성자": [("암(유사암 제외) 주요치료비", 1, 1.0), ("항암방사선치료특약", 1, 1.0)],
    "정위적": [("암(유사암 제외) 주요치료비", 1, 1.0), ("항암방사선치료특약", 1, 1.0)],
    "중입자": [("암(유사암 제외) 주요치료비", 1, 1.0), ("비급여 암 주요치료비 II", 1, 1.0), 
            ("항암방사선치료특약", 1, 1.0), ("항암중입자방사선치료특약", 1, 1.0)],
    "항암호르몬치료제": [("암(유사암 제외) 주요치료비", 1, 1.0)],
    "중환자실": [("암(유사암 제외) 주요치료비", 1, 0.5)],
}
DEFAULT_AMOUNTS_KB = {
    "암(유사암 제외) 주요치료비": 0, "유사암 주요치료비": 0,
    "비급여 암 주요치료비 II": 0, "비급여 항암약물치료비 II": 0,
    "항암방사선치료특약": 0, "항암약물치료특약": 0, "항암중입자방사선치료특약": 0,
}
MAX_USAGE_KB = {
    "암(유사암 제외) 주요치료비": 50, "유사암 주요치료비": 50,
    "비급여 암 주요치료비 II": 10, "비급여 항암약물치료비 II": 10,
    "항암방사선치료특약": 1, "항암약물치료특약": 1, "항암중입자방사선치료특약": 1,
}

# -------------------------
# 계산 함수
# -------------------------
def calc_payments(events, insurance_amounts, usage_counter, MAPPING, MAX_USAGE, year):
    total, details = 0, []
    for ev in events:
        if ev and ev in MAPPING:
            for (treaty, cnt, rate) in MAPPING[ev]:
                if treaty in ["비급여 암 주요치료비 II", "암직접치료보장", "상급종합병원 암직접치료보장"]:
                    if usage_counter.get((year, treaty), 0) >= 1:
                        continue
                if usage_counter.get(treaty, 0) >= MAX_USAGE[treaty]:
                    continue
                amt = int(round(insurance_amounts.get(treaty, 0) * cnt * rate))
                if amt > 0:
                    total += amt
                    details.append((treaty, amt))
                    usage_counter[treaty] = usage_counter.get(treaty, 0) + 1
                    usage_counter[(year, treaty)] = usage_counter.get((year, treaty), 0) + 1
    return total, details, usage_counter

# -------------------------
# Streamlit UI
# -------------------------
st.title("암치료비 통합 계산기 (삼성생명 + KB손해보험 비교판)")

# 고객명 입력
customer_name = st.text_input("고객명 입력")

# 가입 담보금액 입력
st.markdown("### 가입 담보금액 입력")
col1, col2 = st.columns(2)

with col1:
    st.subheader("삼성생명 담보금액 (만원)")
    insurance_amounts_samsung = {}
    for treaty, default_amt in DEFAULT_AMOUNTS_SAMSUNG.items():
        insurance_amounts_samsung[treaty] = st.number_input(
            f"{treaty}", value=default_amt, step=100, key=f"samsung_{treaty}"
        )

with col2:
    st.subheader("KB손해보험 담보금액 (만원)")
    insurance_amounts_kb = {}
    for treaty, default_amt in DEFAULT_AMOUNTS_KB.items():
        insurance_amounts_kb[treaty] = st.number_input(
            f"{treaty}", value=default_amt, step=100, key=f"kb_{treaty}"
        )

# 연도 선택
years = st.slider("연도 선택 (최대 10년차)", 1, 10, (1, 1))
usage_counter_samsung, usage_counter_kb = {}, {}
all_results_samsung, all_results_kb = [], []

for year in range(years[0], years[1] + 1):
    st.subheader(f"{year}년차")
    events = st.multiselect(
        f"{year}년차 치료내역 선택 (최대 5개)",
        list(set(list(MAPPING_SAMSUNG.keys()) + list(MAPPING_KB.keys()))),
        key=f"year_{year}"
    )
    total_s, details_s, usage_counter_samsung = calc_payments(
        events, insurance_amounts_samsung, usage_counter_samsung,
        MAPPING_SAMSUNG, MAX_USAGE_SAMSUNG, year
    )
    total_k, details_k, usage_counter_kb = calc_payments(
        events, insurance_amounts_kb, usage_counter_kb,
        MAPPING_KB, MAX_USAGE_KB, year
    )
    all_results_samsung.append((year, total_s, details_s))
    all_results_kb.append((year, total_k, details_k))


# -------------------------
# 전체 계산
# -------------------------
if st.button("전체 계산하기"):
    grand_total_s, grand_total_k = 0, 0
    rows = []

    for year in range(years[0], years[1] + 1):
        year_s = next((item for item in all_results_samsung if item[0] == year), None)
        year_k = next((item for item in all_results_kb if item[0] == year), None)
        total_s, details_s = (year_s[1], year_s[2]) if year_s else (0, [])
        total_k, details_k = (year_k[1], year_k[2]) if year_k else (0, [])

        # 삼성
        if details_s:
            for idx, (t, amt) in enumerate(details_s):
                rows.append({
                    "연도": f"{year}년차" if idx == 0 else "",
                    "보험사": "삼성생명" if idx == 0 else "",
                    "특약명": t,
                    "지급금액(만원)": int(amt)
                })
        else:
            rows.append({
                "연도": f"{year}년차",
                "보험사": "삼성생명",
                "특약명": "-",
                "지급금액(만원)": 0
            })
        grand_total_s += total_s

        # KB
        if details_k:
            for idx, (t, amt) in enumerate(details_k):
                rows.append({
                    "연도": "" if idx > 0 else "",
                    "보험사": "KB손해보험" if idx == 0 else "",
                    "특약명": t,
                    "지급금액(만원)": int(amt)
                })
        else:
            rows.append({
                "연도": "",
                "보험사": "KB손해보험",
                "특약명": "-",
                "지급금액(만원)": 0
            })
        grand_total_k += total_k

        # 연도 합계
        rows.append({
            "연도": "",
            "보험사": "▶ 연도 총합",
            "특약명": f"{year}년차 합계",
            "지급금액(만원)": int(total_s + total_k)
        })

    df_compare = pd.DataFrame(rows)

    st.markdown("### 📊 연도별 지급내역 (항목별 + 연도 총합)")
    st.dataframe(df_compare, use_container_width=True)

    st.markdown(f"## 👉 삼성생명 전체 합계: **{grand_total_s} 만원**")
    st.markdown(f"## 👉 KB손해보험 전체 합계: **{grand_total_k} 만원**")
    st.markdown(f"## 👉 두 보험사 전체 합계: **{grand_total_s + grand_total_k} 만원**")

    # -------------------------
    # PDF 생성에 필요한 데이터 준비
    # -------------------------
    # 회사별 담보 정리용 (0원 담보 제외)
    company_data = {
        "삼성생명": [(t, f"{amt} 만원") for t, amt in insurance_amounts_samsung.items() if amt > 0],
        "KB손해보험": [(t, f"{amt} 만원") for t, amt in insurance_amounts_kb.items() if amt > 0],
    }

    # 연도별 치료 내역 (UI 선택값 그대로)
    treatments_by_year = {y: st.session_state.get(f"year_{y}", []) for y in range(years[0], years[1] + 1)}

    # 연도별 지급 내역 (삼성 + KB 합산)
    yearly_payouts = {}
    for year in range(years[0], years[1] + 1):
        pays = []
        year_s = next((item for item in all_results_samsung if item[0] == year), None)
        year_k = next((item for item in all_results_kb if item[0] == year), None)
        if year_s and year_s[2]:
            pays.extend(year_s[2])
        if year_k and year_k[2]:
            pays.extend(year_k[2])
        yearly_payouts[year] = pays

    # -------------------------
    # PDF 생성
    # -------------------------
    pdf_buffer = save_pdf(
        customer_name=customer_name,
        company_data=company_data,
        yearly_events=treatments_by_year,
        yearly_payouts=yearly_payouts,
        total_amount=grand_total_s + grand_total_k
    )

    st.download_button(
        label="📥 PDF 다운로드",
        data=pdf_buffer.getvalue(),
        file_name=f"{customer_name or '고객'}_암치료비_통합제안서.pdf",
        mime="application/pdf",
    )
