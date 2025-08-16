# -*- coding: utf-8 -*-
import io
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

import streamlit as st


# ---------------------------------------------------------------------
# 1) 한글 폰트 등록 (깨짐 방지)
#    - 1순위: 시스템 '맑은 고딕'
#    - 2순위: 번들 나눔고딕 (fonts 폴더에 두신 경우)
#    - 3순위: ReportLab 내장 CJK 폰트(HYGothic-Medium, HYSMyeongJo-Medium)
# ---------------------------------------------------------------------
def register_korean_fonts():
    BODY, BOLD = None, None

    # 1) Windows '맑은 고딕'
    try:
        pdfmetrics.registerFont(TTFont('MalgunGothic', r'C:\Windows\Fonts\malgun.ttf'))
        pdfmetrics.registerFont(TTFont('MalgunGothic-Bold', r'C:\Windows\Fonts\malgunbd.ttf'))
        BODY, BOLD = 'MalgunGothic', 'MalgunGothic-Bold'
        return BODY, BOLD
    except Exception:
        pass

    # 2) 번들 나눔고딕
    try:
        pdfmetrics.registerFont(TTFont('NanumGothic', 'fonts/NanumGothic.ttf'))
        pdfmetrics.registerFont(TTFont('NanumGothic-Bold', 'fonts/NanumGothicBold.ttf'))
        BODY, BOLD = 'NanumGothic', 'NanumGothic-Bold'
        return BODY, BOLD
    except Exception:
        pass

    # 3) CJK 내장폰트 (한글 완전 호환, 파일 불필요)
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('HYGothic-Medium'))
        pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
        BODY, BOLD = 'HYGothic-Medium', 'HYSMyeongJo-Medium'  # 본문 고딕, 포인트 명조
        return BODY, BOLD
    except Exception:
        # 최후 fallback (영문 전용이므로 한글은 다시 네모로 나올 수 있음)
        return 'Helvetica', 'Helvetica-Bold'


BODY_FONT, BOLD_FONT = register_korean_fonts()


# ---------------------------------------------------------------------
# 2) PDF 생성 함수
#    섹션 순서: ① 가입 담보 내역 → ② 연간 치료 내역 → ③ 연도별 지급 내역 → 총 예상 보장금액
#    - samsung, kb: {"담보명": 금액(int)} 형태. 0 이하는 자동 제외.
#    - events_by_year: {연차(int 1~10): ["치료A","치료B",...]}
#    - detail: [(연차, "지급사유", 금액), ...]  ← 회사 구분 없이 한 줄씩
#    - total: detail 합계(int)
# ---------------------------------------------------------------------
def build_pdf(customer: str,
              events_by_year: dict,
              total: int,
              detail: list[tuple[int, str, int]],
              samsung: dict,
              kb: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=28, rightMargin=28, topMargin=30, bottomMargin=28
    )

    # 공통 스타일
    styles = {
        "base": ParagraphStyle("base", fontName=BODY_FONT, fontSize=11, leading=16),
        "title": ParagraphStyle("title", fontName=BOLD_FONT, fontSize=22, leading=28, alignment=1),   # center
        "hello": ParagraphStyle("hello", fontName=BOLD_FONT, fontSize=16, leading=22),
        "sub": ParagraphStyle("sub", fontName=BOLD_FONT, fontSize=12, leading=18, textColor=colors.HexColor("#0F3D91")),
        "note": ParagraphStyle("note", fontName=BODY_FONT, fontSize=10, leading=14, textColor=colors.HexColor("#666666")),
    }

    elems = []

    # --------------------- 헤더 ---------------------
    elems.append(Paragraph("맞춤형 암 치료 보장 제안서", styles["title"]))
    elems.append(Spacer(1, 18))
    elems.append(Paragraph(f"{customer} 고객님,", styles["hello"]))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(
        "고객님의 치료 과정을 가정하여 예상되는 보장 내역을 정리했습니다.<br/><br/>"
        "본 제안서는 이해를 돕기 위한 시뮬레이션 자료이며, 실제 보장 여부와 금액은 "
        "개별 약관 및 심사 결과에 따라 달라질 수 있습니다.",
        styles["base"]
    ))
    elems.append(Spacer(1, 18))

    # ----------------- ① 가입 담보 내역 -----------------
    elems.append(Paragraph("① 가입 담보 내역", styles["sub"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("현재 가입된 담보와 금액을 정리했습니다. (단위: 만원)", styles["note"]))
    elems.append(Spacer(1, 10))

    cover_data = [["회사", "담보명", "가입금액(만원)"]]
    for k, v in samsung.items():
        if v and v > 0:
            cover_data.append(["삼성생명", k, f"{v:,}"])
    for k, v in kb.items():
        if v and v > 0:
            cover_data.append(["KB손해보험", k, f"{v:,}"])
    if len(cover_data) == 1:
        cover_data.append(["-", "표시할 담보가 없습니다", "0"])

    cover_table = Table(cover_data, colWidths=[110, 300, 100])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), BODY_FONT),
        ('FONTSIZE',  (0, 0), (-1, 0), 11),
        ('FONTSIZE',  (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E8EEF9")),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor("#0F3D91")),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DA")),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
    ]))
    elems.append(cover_table)
    elems.append(Spacer(1, 18))

    # ----------------- ② 연간 치료 내역 -----------------
    elems.append(Paragraph("② 연간 치료 내역", styles["sub"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("시뮬레이션에 반영된 연간 치료 항목입니다.", styles["note"]))
    elems.append(Spacer(1, 10))

    treat_data = [["연도", "치료 항목"]]
    for y in sorted(events_by_year.keys()):
        items = events_by_year.get(y, [])
        treat_data.append([f"{y}년차", " / ".join(items) if items else "-"])

    treat_table = Table(treat_data, colWidths=[110, 400])
    treat_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), BODY_FONT),
        ('FONTSIZE',  (0, 0), (-1, 0), 11),
        ('FONTSIZE',  (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF7EC")),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor("#146C43")),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DA")),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
    ]))
    elems.append(treat_table)
    elems.append(Spacer(1, 18))

    # ------------- ③ 연도별 지급 내역 (년도 우선, 회사 구분 없음) -------------
    elems.append(Paragraph("③ 연도별 지급 내역", styles["sub"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("치료 시나리오에 따른 연도별 예상 보장금액입니다.", styles["note"]))
    elems.append(Spacer(1, 10))

    # detail: [(year, desc, amt), ...]
    yearly = defaultdict(list)
    for y, desc, amt in detail:
        yearly[y].append((desc, amt))

    pay_data = [["연도", "지급 사유", "지급금액(만원)"]]
    for y in sorted(yearly.keys()):
        year_total = 0
        first = True
        for desc, amt in yearly[y]:
            pay_data.append([
                f"{y}년차" if first else "",
                desc,
                f"{amt:,}"
            ])
            first = False
            year_total += int(amt)
        pay_data.append([f"{y}년 합계", "", f"{year_total:,}"])

    pay_table = Table(pay_data, colWidths=[110, 300, 100])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), BODY_FONT),
        ('FONTSIZE',  (0, 0), (-1, 0), 11),
        ('FONTSIZE',  (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FCE4D6")),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor("#8A1F11")),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D4DA")),
        # 연도 합계 행 볼드 처리
        ('FONTNAME', (0, 1), (0, -1), BODY_FONT),
        ('FONTNAME', (0, 1), (-1, -1), BODY_FONT),
        ('FONTNAME', (0, -1), (-1, -1), BOLD_FONT),
    ]))
    elems.append(pay_table)
    elems.append(Spacer(1, 22))

    # ----------------- 총 예상 보장금액 박스 -----------------
    total_table = Table(
        [[Paragraph("<b>총 예상 보장금액</b>", styles["base"]),
          Paragraph(f"<b><font size=14>{total:,} 만원</font></b>", styles["base"])]],
        colWidths=[310, 200],
        rowHeights=[42]
    )
    total_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), BODY_FONT),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#DDEBF7")),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#6C8EBF")),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elems.append(total_table)

    # ----------------- PDF 생성 -----------------
    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes



# -------------------------
# 삼성 계산 로직
# -------------------------
def calc_samsung(samsung, events_by_year, is_minor):
    total = 0
    detail = []
    rt_paid, drug_paid, carbon_paid = False, False, False

    for year, evs in events_by_year.items():
        # 주요치료, 직접치료, 상급종합 기존 로직 …
        if not is_minor and samsung["암주요"] > 0 and any(x in evs for x in ["수술","방사선","항암약물"]):
            total += samsung["암주요"]; detail.append((year,"삼성 암주요치료보장",samsung["암주요"]))
        if is_minor and samsung["갑상선주요"] > 0 and any(x in evs for x in ["수술","방사선","항암약물"]):
            total += samsung["갑상선주요"]; detail.append((year,"삼성 갑상선·기타피부암 주요치료보장",samsung["갑상선주요"]))

        if not is_minor and samsung["암직접"] > 0 and any(x in evs for x in ["수술","방사선","항암약물","항암호르몬"]):
            total += samsung["암직접"]; detail.append((year,"삼성 암직접치료보장",samsung["암직접"]))
        if is_minor and samsung["갑상선직접"] > 0 and any(x in evs for x in ["수술","방사선","항암약물","항암호르몬"]):
            total += samsung["갑상선직접"]; detail.append((year,"삼성 갑상선·기타피부암 직접치료보장",samsung["갑상선직접"]))

        if not is_minor and samsung["상급종합"] > 0 and "상급종합" in evs:
            total += samsung["상급종합"]; detail.append((year,"삼성 상급종합병원 암직접치료보장",samsung["상급종합"]))
        if is_minor and samsung["상급종합유사"] > 0 and "상급종합" in evs:
            total += samsung["상급종합유사"]; detail.append((year,"삼성 상급종합 갑상선·기타피부암 직접치료보장",samsung["상급종합유사"]))

        # -------------------------
        # 프리미엄암직접치료보장 (고정 로직)
        # -------------------------
        if samsung["프리미엄"] > 0:
            if "표적(급여)" in evs:
                total += samsung["프리미엄"]
                detail.append((year,"삼성 프리미엄-표적(급여)",samsung["프리미엄"]))
            if "표적(비급여)" in evs:
                total += samsung["프리미엄"]; detail.append((year,"삼성 프리미엄-표적(급여)",samsung["프리미엄"]))
                total += samsung["프리미엄"]; detail.append((year,"삼성 프리미엄-표적(비급여)",samsung["프리미엄"]))
            if "면역(급여)" in evs:
                total += samsung["프리미엄"]; detail.append((year,"삼성 프리미엄-표적(급여)",samsung["프리미엄"]))
                total += samsung["프리미엄"]; detail.append((year,"삼성 프리미엄-면역(급여)",samsung["프리미엄"]))
            if "면역(비급여)" in evs:
                total += samsung["프리미엄"]*4
                detail.append((year,"삼성 프리미엄-표적(급여)",samsung["프리미엄"]))
                detail.append((year,"삼성 프리미엄-표적(비급여)",samsung["프리미엄"]))
                detail.append((year,"삼성 프리미엄-면역(급여)",samsung["프리미엄"]))
                detail.append((year,"삼성 프리미엄-면역(비급여)",samsung["프리미엄"]))
            for opt in ["세기조절","양성자","정위적","로봇"]:
                if opt in evs:
                    total += samsung["프리미엄"]
                    detail.append((year,f"삼성 프리미엄-{opt}",samsung["프리미엄"]))

        # 최초1회 특약
        if not rt_paid and "방사선" in evs and samsung["항암방사선1회"] > 0:
            rt_paid=True; total+=samsung["항암방사선1회"]; detail.append((year,"삼성 항암방사선 최초1회",samsung["항암방사선1회"]))
        if not drug_paid and "항암약물" in evs and samsung["항암약물1회"] > 0:
            drug_paid=True; total+=samsung["항암약물1회"]; detail.append((year,"삼성 항암약물 최초1회",samsung["항암약물1회"]))
        if not carbon_paid and "중입자" in evs and samsung["중입자1회"] > 0:
            carbon_paid=True; total+=samsung["중입자1회"]; detail.append((year,"삼성 중입자 최초1회",samsung["중입자1회"]))

    return total, detail

# -------------------------
# KB 계산 로직 (간단화 예시, 필요시 확장)
# -------------------------
def calc_kb(kb, events_by_year, is_minor):
    total = 0
    detail = []
    year_counts = {y:0 for y in events_by_year.keys()}
    drug_nonpay_count = 0
    rt_once_paid, drug_once_paid, carbon_once_paid = False, False, False

    for year, evs in events_by_year.items():
        # 주요치료
        if not is_minor and kb["암주요"] > 0 and any(x in evs for x in ["수술","방사선","항암약물","항암호르몬","중환자실"]):
            if year_counts[year] < 5:
                amt = kb["암주요"] if "중환자실" not in evs else kb["암주요"]//2
                total+=amt; detail.append((year,"KB 암주요치료비",amt)); year_counts[year]+=1
        if is_minor and kb["유사암주요"] > 0 and any(x in evs for x in ["수술","방사선","항암약물","항암호르몬","중환자실"]):
            if year_counts[year] < 5:
                amt = kb["유사암주요"] if "중환자실" not in evs else kb["유사암주요"]//2
                total+=amt; detail.append((year,"KB 유사암주요치료비",amt)); year_counts[year]+=1

        # 비급여
        if kb["비급여주요"] > 0 and any(x in evs for x in ["표적(비급여)","면역(비급여)","로봇","중입자"]):
            total += kb["비급여주요"]; detail.append((year,"KB 비급여 암 주요치료비II",kb["비급여주요"]))
        if kb["비급여약물"] > 0 and any(x in evs for x in ["표적(비급여)","면역(비급여)"]) and drug_nonpay_count<10:
            drug_nonpay_count+=1; total+=kb["비급여약물"]; detail.append((year,"KB 비급여 항암약물치료비II",kb["비급여약물"]))

        # 최초1회
        if not rt_once_paid and "방사선" in evs and kb["항암방사선1회"]>0:
            rt_once_paid=True; total+=kb["항암방사선1회"]; detail.append((year,"KB 항암방사선 최초1회",kb["항암방사선1회"]))
        if not drug_once_paid and "항암약물" in evs and kb["항암약물1회"]>0:
            drug_once_paid=True; total+=kb["항암약물1회"]; detail.append((year,"KB 항암약물 최초1회",kb["항암약물1회"]))
        if not carbon_once_paid and "중입자" in evs and kb["중입자1회"]>0:
            carbon_once_paid=True; total+=kb["중입자1회"]; detail.append((year,"KB 항암중입자 최초1회",kb["중입자1회"]))

    return total, detail

# -------------------------
# Streamlit UI
# -------------------------
st.title("암치료 보장 계산기 (삼성 + KB 통합)")

customer = st.text_input("고객명", value="홍길동")
is_minor = st.checkbox("유사암 여부 (갑상선·기타피부암 등)", value=False)
treat_years = st.slider("치료 기간 (년차)", 1, 10, 5)

# 삼성 입력
st.subheader("삼성생명 가입금액 입력 (만원)")
col1,col2=st.columns(2)
with col1:
    s_major=st.number_input("삼성 암주요치료보장",0,step=10,value=0)
    s_minor=st.number_input("삼성 갑상선·기타피부암 주요치료보장",0,step=10,value=0)
    s_direct=st.number_input("삼성 암직접치료보장",0,step=10,value=0)
    s_minor_direct=st.number_input("삼성 갑상선·기타피부암 직접치료보장",0,step=10,value=0)
    s_top=st.number_input("삼성 상급종합병원 암직접치료보장",0,step=10,value=0)
    s_top_minor=st.number_input("삼성 상급종합병원 갑상선·기타피부암 직접치료보장",0,step=10,value=0)
with col2:
    s_premium=st.number_input("삼성 프리미엄암직접치료보장",0,step=10,value=0)
    s_premium_cls=st.number_input("삼성 프리미엄클래스암 특정치료보장",0,step=10,value=0)
    s_rt_once=st.number_input("삼성 항암방사선(최초1회)",0,step=10,value=0)
    s_drug_once=st.number_input("삼성 항암약물(최초1회)",0,step=10,value=0)
    s_carbon_once=st.number_input("삼성 중입자(최초1회)",0,step=10,value=0)

samsung={
    "암주요":s_major,"갑상선주요":s_minor,"암직접":s_direct,"갑상선직접":s_minor_direct,
    "상급종합":s_top,"상급종합유사":s_top_minor,"프리미엄":s_premium,"프리미엄클래스":s_premium_cls,
    "항암방사선1회":s_rt_once,"항암약물1회":s_drug_once,"중입자1회":s_carbon_once
}

# KB 입력
st.subheader("KB손보 가입금액 입력 (만원)")
col3,col4=st.columns(2)
with col3:
    kb_major=st.number_input("KB 암 주요치료비",0,step=10,value=0)
    kb_minor=st.number_input("KB 유사암 주요치료비",0,step=10,value=0)
    kb_nonpay=st.number_input("KB 비급여 암 주요치료비II",0,step=10,value=0)
    kb_drug=st.number_input("KB 비급여 항암약물치료비II",0,step=10,value=0)
with col4:
    kb_rt_once=st.number_input("KB 항암방사선(최초1회)",0,step=10,value=0)
    kb_drug_once=st.number_input("KB 항암약물(최초1회)",0,step=10,value=0)
    kb_carbon_once=st.number_input("KB 항암중입자(최초1회)",0,step=10,value=0)

kb={
    "암주요":kb_major,"유사암주요":kb_minor,"비급여주요":kb_nonpay,"비급여약물":kb_drug,
    "항암방사선1회":kb_rt_once,"항암약물1회":kb_drug_once,"중입자1회":kb_carbon_once
}

# 연도별 치료 입력
TREAT_CHOICES=["수술","방사선","항암약물","항암호르몬","중입자",
               "세기조절","양성자","정위적","로봇",
               "표적(급여)","표적(비급여)","면역(급여)","면역(비급여)","상급종합","중환자실"]

events_by_year={}
for y in range(1,treat_years+1):
    events=st.multiselect(f"{y}년차 치료",options=TREAT_CHOICES,default=[],key=f"year{y}")
    events_by_year[y]=events

# 결과 계산
if st.button("계산하기"):
    s_total,s_detail=calc_samsung(samsung,events_by_year,is_minor)
    kb_total,kb_detail=calc_kb(kb,events_by_year,is_minor)
    total=s_total+kb_total
    detail=s_detail+kb_detail

    st.subheader("결과 요약")
    st.write(f"삼성생명 합계: {s_total:,} 만원")
    st.write(f"KB손보 합계: {kb_total:,} 만원")
    st.write(f"총 보장금액: {total:,} 만원")

    st.subheader("지급 상세내역")
    for y,desc,amt in detail:
        st.write(f"{y}년차: {desc} → {amt:,} 만원")

    pdf=build_pdf(customer,events_by_year,total,detail,samsung,kb)
    st.download_button("📄 고객 제안서 PDF 다운로드",data=pdf,file_name="proposal.pdf",mime="application/pdf")
