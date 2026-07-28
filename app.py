# -*- coding: utf-8 -*-
"""
반도체/신소재 데이터 분석 플랫폼 (Streamlit) — v1.1 (CSV/Excel 입력 지원)

실행:
    pip install streamlit pandas plotly mp-api matplotlib
    streamlit run app.py

MP API 키:
    .streamlit/secrets.toml 에  MP_API_KEY = "..."  저장 (권장)
    또는 환경변수 MP_API_KEY, 또는 앱 내 입력창 사용.
"""

import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# 0. 기본 설정
# ──────────────────────────────────────────────────────────────────────────────
_page_icon = os.path.join("assets", "favicon.png")
if not os.path.exists(_page_icon):
    _page_icon = ":material/memory:"   # 파일 없으면 칩 모양 Material 아이콘
st.set_page_config(layout="wide", page_title="Material Property Analyzer",
                   page_icon=_page_icon)

# ── 블루 팔레트 (반도체 테마) ──────────────────────────────────────────────────
NAVY, BLUE, SKY, CYAN = "#0a1f44", "#2563eb", "#60a5fa", "#0e7490"
BLUE_SEQ = ["#1d4ed8", "#0891b2", "#3b82f6", "#7dd3fc",
            "#1e3a8a", "#60a5fa", "#0e7490", "#93c5fd", "#075985"]
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = BLUE_SEQ
px.defaults.color_continuous_scale = "Blues"

# ── 커스텀 CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Material 아이콘 1.4배 확대 (탭·버튼·헤더·expander 등 전역) */
span[data-testid="stIconMaterial"] {
    font-size: 1.4em !important;
    width: 1.4em !important; height: 1.4em !important;
    vertical-align: middle;
}
/* 탭 바 */
button[data-baseweb="tab"] {
    font-weight: 600; color: #4a6a95;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #1d4ed8;
}
div[data-baseweb="tab-highlight"] { background-color: #2563eb; }

/* 메트릭 카드 */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e1e0d9;
    border-radius: 8px;
    padding: 14px 16px;
}
div[data-testid="stMetric"] label { color: #4a6a95 !important; }

/* 기본 버튼 */
div.stButton > button[kind="primary"], div.stDownloadButton > button {
    background: linear-gradient(90deg, #1d4ed8 0%, #0891b2 100%);
    color: white; border: none; border-radius: 8px; font-weight: 600;
}

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #edf4fc 0%, #e2edf9 100%);
    border-right: 1px solid #d4e3f5;
}

/* 소제목 색 */
h3 { color: #123c78; }

/* 제목 배너를 스크롤을 내려도 상단에 고정 (Streamlit 요소 컨테이너를 sticky로).
   Streamlit 기본 상단 바(약 3.75rem)에 가려 잘리지 않도록 그 아래에 고정. */
div[data-testid="stElementContainer"]:has(#hero-sticky) {
    position: sticky;
    top: 3.75rem;
    z-index: 999;
    background: #f5f8fc;
    padding: 6px 0 8px;
}
/* Streamlit 상단 바를 불투명하게 해서 고정 배너와 겹칠 때 깔끔하게 */
header[data-testid="stHeader"] { background: #f5f8fc; }

/* 주기율표 셀: 마우스를 올리면 눌리는 듯한(버튼 같은) 효과 */
.ptcell {
    transition: transform .08s ease, box-shadow .08s ease, filter .08s ease;
    cursor: pointer;
}
.ptcell:hover {
    transform: translateY(-2px) scale(1.10);
    box-shadow: 0 3px 9px rgba(10,31,68,.35);
    filter: brightness(1.08);
    position: relative; z-index: 3;
}
</style>
""", unsafe_allow_html=True)

# ── 로고 임베드 헬퍼 (헤더에 PAND·DKU 로고를 넣기 위해 배너 앞에 정의) ──────
import base64


def _logo_data_uri(keywords):
    """assets/ 또는 폴더에서 키워드에 맞는 로고를 찾아 data URI로 반환."""
    exts = (".png", ".jpg", ".jpeg", ".webp", ".svg")
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".webp": "image/webp", ".svg": "image/svg+xml"}
    dirs = []
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        _here = os.getcwd()
    for base in (os.getcwd(), _here):
        for sub in ("assets", ""):
            d = os.path.join(base, sub) if sub else base
            if os.path.isdir(d) and d not in dirs:
                dirs.append(d)
    for d in dirs:
        try:
            for f in sorted(os.listdir(d)):
                n = f.lower()
                if n.endswith(exts) and any(k in n for k in keywords):
                    p = os.path.join(d, f)
                    ext = os.path.splitext(p)[1].lower()
                    b = base64.b64encode(open(p, "rb").read()).decode()
                    return f"data:{mimes.get(ext, 'image/png')};base64,{b}"
        except OSError:
            continue
    return ""


_pand_uri = _logo_data_uri(["pand"])
_dku_uri = _logo_data_uri(["dku", "dankook"])
_hero_logos = ""
# PAND 로고는 밝은 색이라 어두운 카드, DKU 로고는 진한 색이라 흰 카드에 배치
if _pand_uri:
    _hero_logos += (
        f'<div style="background:#0a1f44; border:1px solid #2c4a7a; '
        f'border-radius:8px; padding:8px 14px; height:74px; display:flex; '
        f'align-items:center; box-shadow:0 2px 8px rgba(0,0,0,.25);">'
        f'<img src="{_pand_uri}" style="height:48px; max-width:170px; '
        f'object-fit:contain;"></div>')
if _dku_uri:
    _hero_logos += (
        f'<div style="background:#ffffff; border-radius:8px; padding:6px 12px; '
        f'height:74px; display:flex; align-items:center; '
        f'box-shadow:0 2px 8px rgba(0,0,0,.25);">'
        f'<img src="{_dku_uri}" style="height:62px; max-width:120px; '
        f'object-fit:contain;"></div>')

# ── 히어로 배너 (회로 + 칩 SVG) — 스크롤해도 상단 고정(sticky) ────────────────
st.markdown(f"""
<div id="hero-sticky" style="position:relative; border-radius:14px;
            overflow:hidden; margin-bottom:1.2rem;
            box-shadow:0 4px 14px rgba(10,31,68,.25);">
<svg viewBox="0 0 1000 150" preserveAspectRatio="xMidYMid slice"
     style="display:block; width:100%; height:150px;">
  <defs>
    <linearGradient id="heroBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#081a3a"/>
      <stop offset="0.6" stop-color="#0f3268"/>
      <stop offset="1" stop-color="#12508c"/>
    </linearGradient>
    <linearGradient id="chipBody" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1e3a8a"/>
      <stop offset="1" stop-color="#0b234f"/>
    </linearGradient>
  </defs>
  <rect width="1000" height="150" fill="url(#heroBg)"/>
  <!-- 회로 배선 -->
  <g stroke="#3b82f6" stroke-width="1.6" fill="none" opacity="0.5">
    <path d="M0 30 H150 L185 65 H330 L360 35 H520"/>
    <path d="M0 75 H90 L130 115 H300"/>
    <path d="M0 120 H210 L250 80 H420 L450 110 H600"/>
    <path d="M540 20 H700 L740 60 H830"/>
    <path d="M480 140 H640 L680 100 H760"/>
    <path d="M900 15 V60 L940 100 V150"/>
  </g>
  <!-- 접점 노드 -->
  <g fill="#7dd3fc" opacity="0.9">
    <circle cx="520" cy="35" r="3.5"/><circle cx="300" cy="115" r="3.5"/>
    <circle cx="600" cy="110" r="3.5"/><circle cx="830" cy="60" r="3.5"/>
    <circle cx="760" cy="100" r="3.5"/><circle cx="150" cy="30" r="3"/>
    <circle cx="90" cy="75" r="3"/><circle cx="210" cy="120" r="3"/>
  </g>
  <!-- (웨이퍼·칩 패키지 장식은 로고와 겹치지 않도록 오른쪽에서 제거) -->
</svg>
<div style="position:absolute; top:50%; left:36px; transform:translateY(-50%);">
  <div style="display:flex; align-items:center; gap:12px; color:#fff;
              font-size:1.75rem; font-weight:700; letter-spacing:.3px;
              text-shadow:0 2px 8px rgba(0,0,0,.4);">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#7dd3fc"
         stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <rect x="6" y="6" width="12" height="12" rx="2"/>
      <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>
      <rect x="10" y="10" width="4" height="4" rx="1"/></svg>
    <span>반도체 및 신소재 데이터 분석 플랫폼</span></div>
  <div style="color:#aecdf2; font-size:.95rem; margin-top:4px;">
    Material Property Analyzer · Electronic Structure · Thermoelectric Screening</div>
</div>
<div style="position:absolute; top:50%; right:26px; transform:translateY(-50%);
            display:flex; align-items:center; gap:14px;">{_hero_logos}</div>
</div>
""", unsafe_allow_html=True)

# ── 로고 영역 (제목 배너 바로 아래, 중앙 정렬) ───────────────────────────────
import base64

_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}


def _find_logo(keywords):
    """로고 이미지를 유연하게 탐색.
    - 실행 위치(cwd)와 app.py가 있는 폴더 양쪽을 확인
    - assets 하위 폴더와 폴더 최상위 양쪽을 확인
    - 파일명에 키워드가 포함되면 매칭 (대소문자 무시)"""
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        _here = os.getcwd()
    search_dirs = []
    for base in (os.getcwd(), _here):
        for sub in ("assets", ""):
            d = os.path.join(base, sub) if sub else base
            if os.path.isdir(d) and d not in search_dirs:
                search_dirs.append(d)
    for d in search_dirs:
        try:
            for f in sorted(os.listdir(d)):
                n = f.lower()
                if n.endswith(_IMG_EXTS) and any(k in n for k in keywords):
                    return os.path.join(d, f)
        except OSError:
            continue
    return None


def _logo_card(path, label, bg, border, img_h=88, pad="10px 20px", fill=False):
    """로고 이미지를 배경 카드에 담아 표시. 파일 없으면 텍스트 배지.
    fill=True면 이미지가 카드 직사각형을 꽉 채움."""
    base = ("display:flex; align-items:center; justify-content:center; "
            f"height:120px; border-radius:12px; background:{bg}; "
            f"border:1.5px solid {border}; padding:{'0' if fill else pad}; "
            "overflow:hidden;")
    if path and os.path.exists(path):
        ext = os.path.splitext(path)[1].lower()
        mime = _MIME.get(ext, "image/png")
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        img_style = ("width:100%; height:100%; object-fit:contain;" if fill
                     else f"max-height:{img_h}px; max-width:100%; "
                          "object-fit:contain;")
        return (f'<div style="{base}">'
                f'<img src="data:{mime};base64,{b64}" '
                f'style="{img_style}"></div>')
    text_color = "#ffffff" if bg != "#ffffff" else "#123c78"
    return (f'<div style="{base} color:{text_color}; font-weight:700; '
            f'font-size:1.1rem; letter-spacing:.5px;">{label}</div>')


# (PAND·DKU 로고는 상단 제목 배너(sticky header) 안으로 이동했습니다.)

DATA_FILE = "merged_materials_Fermi.csv"

# ── 화학 조성 필터용 정의 ─────────────────────────────────────────────────────
_ELEMENT_RE = re.compile(r"[A-Z][a-z]?")

ELEMENT_GROUPS = {  # IUPAC 1~18족
    1: ["H", "Li", "Na", "K", "Rb", "Cs", "Fr"],
    2: ["Be", "Mg", "Ca", "Sr", "Ba", "Ra"],
    3: ["Sc", "Y", "La", "Ac"],
    4: ["Ti", "Zr", "Hf", "Rf"],
    5: ["V", "Nb", "Ta"],
    6: ["Cr", "Mo", "W"],
    7: ["Mn", "Tc", "Re"],
    8: ["Fe", "Ru", "Os"],
    9: ["Co", "Rh", "Ir"],
    10: ["Ni", "Pd", "Pt"],
    11: ["Cu", "Ag", "Au"],
    12: ["Zn", "Cd", "Hg"],
    13: ["B", "Al", "Ga", "In", "Tl"],
    14: ["C", "Si", "Ge", "Sn", "Pb"],
    15: ["N", "P", "As", "Sb", "Bi"],
    16: ["O", "S", "Se", "Te", "Po"],
    17: ["F", "Cl", "Br", "I", "At"],
    18: ["He", "Ne", "Ar", "Kr", "Xe", "Rn"],
}

ANION_CLASSES = {
    "산화물 (O 포함)": {"O"},
    "질화물 (N 포함)": {"N"},
    "황화물 (S 포함)": {"S"},
    "탄화물 (C 포함)": {"C"},
    "인화물 (P 포함)": {"P"},
    "할로겐화물 (F/Cl/Br/I)": {"F", "Cl", "Br", "I"},
}


_TRUE_SET = {"true", "t", "yes", "y", "1", "1.0", "o", "금속", "안정"}
_FALSE_SET = {"false", "f", "no", "n", "0", "0.0", "x", "비금속", "불안정"}


def _normalize_bool(series: pd.Series) -> pd.Series:
    """bool 컬럼 정규화 — True/False 문자열, 0/1 숫자, yes/no 등 모두 처리."""
    if series.dtype == bool:
        return series

    def conv(v):
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, (int, float, np.integer, np.floating)):
            return np.nan if pd.isna(v) else bool(v)
        s = str(v).strip().lower()
        if s in _TRUE_SET:
            return True
        if s in _FALSE_SET:
            return False
        return np.nan

    out = series.map(conv)
    # 변환이 전부 실패하면 (전부 NaN) 원본을 유지해 필터가 데이터를 지우지 않게 함
    if out.isna().all() and series.notna().any():
        return series
    return out


# 컬럼명 유연 인식: "is metal", "Is_Metal", "stable" 등도 표준 이름으로 매핑
_CANON_COLS = {
    "is_metal": ["is_metal", "is metal", "ismetal", "metallic"],
    "is_stable": ["is_stable", "is stable", "isstable", "stable", "stability"],
    "crystal_system": ["crystal_system", "crystal system", "crystalsystem"],
    "electronic_band_gap": ["electronic_band_gap", "electronic band gap",
                            "band_gap", "band gap", "bandgap"],
    "e_fermi": ["e_fermi", "e fermi", "efermi", "fermi_energy", "fermi energy"],
    "material_id": ["material_id", "material id", "mp_id", "mpid"],
}


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    def norm(c):
        return re.sub(r"[^a-z0-9]", "", str(c).lower())
    norm_map = {norm(c): c for c in df.columns}
    renames = {}
    for canon, cands in _CANON_COLS.items():
        if canon in df.columns:
            continue
        for cand in cands:
            if norm(cand) in norm_map:
                renames[norm_map[norm(cand)]] = canon
                break
    return df.rename(columns=renames) if renames else df


@st.cache_data
def load_data(src, name=None):
    fname = (name or str(src)).lower()
    if fname.endswith((".xlsx", ".xls")):
        df = pd.read_excel(src)
    else:
        df = pd.read_csv(src, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]  # 공백 제거
    df = _canonicalize_columns(df)
    for col in ("is_stable", "is_metal"):
        if col in df.columns:
            df[col] = _normalize_bool(df[col])
    # 화학식 → 구성 원소 집합 파싱 (예: "Zr5N5O2" → {Zr, N, O})
    fcol = next((c for c in ("formula_file1", "formula_pretty", "formula")
                 if c in df.columns), None)
    if fcol:
        df["_elements"] = df[fcol].astype(str).map(
            lambda f: frozenset(_ELEMENT_RE.findall(f)))
    return df


# ── 패키지에 포함된 데이터 파일 자동 로드 (앞에 있을수록 우선) ───────────────
DATA_FILES = ("merged_materials_full.csv.gz",    # 배포용 압축본 (권장)
              "merged_materials_full.csv",       # 완전판 (mobility 포함, 빠름)
              "merged_materials_full.xlsx",      # 완전판 원본
              "merged_materials_Fermi.csv",
              "merged_materials_Fermi_carriers_300K.xlsx",
              "merged_materials_Fermi.xlsx")
_existing = next((f for f in DATA_FILES if os.path.exists(f)), None)
if _existing:
    df = load_data(_existing)
else:
    st.error("데이터 파일이 없습니다. 다음 중 하나를 앱과 같은 폴더에 넣고 "
             f"새로고침하세요: {', '.join(DATA_FILES)}")
    st.stop()

# ── 데이터 출처 태그 (Materials Project) + M3D Hub 데이터 병합 ────────────────
if "source" not in df.columns:
    df["source"] = "Materials Project"
_M3D_FILES = ("m3d_hub.csv.gz", "m3d_hub.csv")
_m3d_path = next((f for f in _M3D_FILES if os.path.exists(f)), None)
_n_m3d = 0
if _m3d_path is not None:
    try:
        _m3d = load_data(_m3d_path)
        if "source" not in _m3d.columns:
            _m3d["source"] = "M3D Hub"
        _n_m3d = len(_m3d)
        # 공통 컬럼 정렬 후 세로 병합 (없는 컬럼은 NaN)
        df = pd.concat([df, _m3d], ignore_index=True, sort=False)
    except Exception as _e:
        st.warning(f"M3D 데이터를 불러오지 못했습니다: {_e}")

# ── 전역 필터: 금속 제외, 비금속(반도체·절연체)만 분석 대상으로 사용 ──────────
_n_all = len(df)
if "is_metal" in df.columns:
    df = df[df["is_metal"] == False].reset_index(drop=True)
_n_nonmetal = len(df)
# 출처별 개수 (개요 카드용)
_n_mp = int((df["source"] == "Materials Project").sum()) if "source" in df.columns else _n_nonmetal
_n_m3d_kept = int((df["source"] == "M3D Hub").sum()) if "source" in df.columns else 0

# 자주 쓰는 컬럼 존재 여부
HAS = {c: c in df.columns for c in
       ["crystal_system", "electronic_band_gap", "e_fermi", "is_metal",
        "is_stable", "material_id", "formula_file1", "volume"]}
FORMULA_COL = "formula_file1" if HAS["formula_file1"] else None

# ═════════════════════════════════════════════════════════════════════════════
# Mobility 예측 모델 정의 (개요의 모델 카드와 Tab6 예측이 공유하므로 상단에 배치)
# ═════════════════════════════════════════════════════════════════════════════
_DERIVED = ("EF_minus_VBM", "CBM_minus_EF", "log_m_p", "log_m_n")
# 예측 폼에 크게 노출할 핵심 물성 (나머지는 '고급 입력'으로 접어둠)
_KEY_FEATS = [
    "electronic_band_gap", "e_fermi", "vbm", "cbm",
    "m_n_epsilon|avg", "m_p_epsilon|avg", "density", "volume",
    "mean_electronegativity", "dDOS_dE_CBM_fit", "dDOS_dE_VBM_fit",
    "energy_above_hull",
]
_BINARY_FEATS = {"is_stable", "is_metal", "is_gap_direct"}
# 학습 제외 컬럼 (ID·문자열·타깃·leakage) — 노트북 NON_FEATURE_COLS
_NON_FEATURE = {
    "material_id", "formula", "formula_file1", "formula_file2", "task", "task_id",
    "atomic_positions", "functional", "crystal_system", "space_group_symbol",
    "point_group", "magnetic_ordering", "S_mu_n", "S_mu_p",
    "S_p", "S_n", "PF_p", "PF_n", "kappa_p", "kappa_n", "sigma_p", "sigma_n",
    "Nc_300K_cm-3", "Nv_300K_cm-3", "n_300K_cm-3", "p_300K_cm-3",
    "experimentally_observed", "total_magnetization",
}


def _add_derived_cols(data):
    """데이터프레임에 파생 feature 추가 (학습·예측 공통 공식)."""
    d = data.copy()
    if {"e_fermi", "vbm"} <= set(d.columns):
        d["EF_minus_VBM"] = d["e_fermi"] - d["vbm"]
    if {"cbm", "e_fermi"} <= set(d.columns):
        d["CBM_minus_EF"] = d["cbm"] - d["e_fermi"]
    if "m_p_epsilon|avg" in d.columns:
        d["log_m_p"] = np.log(d["m_p_epsilon|avg"].clip(lower=1e-6))
    if "m_n_epsilon|avg" in d.columns:
        d["log_m_n"] = np.log(d["m_n_epsilon|avg"].clip(lower=1e-6))
    return d


def _add_derived_row(vals: dict) -> dict:
    """base 입력값(dict)으로 파생 feature 계산."""
    out = dict(vals)
    ef, vbm, cbm = vals.get("e_fermi"), vals.get("vbm"), vals.get("cbm")
    if ef is not None and vbm is not None:
        out["EF_minus_VBM"] = ef - vbm
    if ef is not None and cbm is not None:
        out["CBM_minus_EF"] = cbm - ef
    for src, dst in [("m_p_epsilon|avg", "log_m_p"), ("m_n_epsilon|avg", "log_m_n")]:
        v = vals.get(src)
        if v is not None:
            out[dst] = float(np.log(max(v, 1e-6)))
    return out


R2_SOURCE = "앱 라이브 계산 · dDOS0.1 모델 재현 · 5-fold CV"

# 반대 캐리어(교차 채널) feature 제외 — 노트북 dDOS0.1 방법론.
# n형 예측엔 정공계(m_p*, vbm, EF_minus_VBM, log_m_p)가, p형 예측엔
# 전자계(m_n*, cbm, CBM_minus_EF, log_m_n)가 물리적으로 무관하므로 제외한다.
_CROSS_EXCLUDE = {
    "S_mu_n": {"m_p_epsilon1", "m_p_epsilon2", "m_p_epsilon3", "m_p_epsilon|avg",
               "log_m_p", "EF_minus_VBM", "vbm"},
    "S_mu_p": {"m_n_epsilon1", "m_n_epsilon2", "m_n_epsilon3", "m_n_epsilon|avg",
               "log_m_n", "CBM_minus_EF", "cbm"},
}

# 노트북과 동일한 전용 학습 데이터(있으면 우선 사용). feature 파일은
# merged_materials_Fermi_carriers_300K, 정답은 mobility_score_*.
_MOB_FEATURE_FILES = ("mobility_features.csv.gz",
                      "merged_materials_Fermi_carriers_300K.xlsx")
_MOB_SCORE_FILES = {
    "n-type": ("mobility_score_ntype.csv.gz", "mobility_score_ntype.xlsx"),
    "p-type": ("mobility_score_ptype.csv.gz", "mobility_score_ptype.xlsx"),
}


@st.cache_data(show_spinner=False)
def _load_mobility_training():
    """노트북과 동일한 mobility 전용 데이터 로드 → 파생 feature 추가.
    반환: (X_df with 파생, {채널: y_df}) 또는 전용 파일이 없으면 (None, None)."""
    fpath = next((f for f in _MOB_FEATURE_FILES if os.path.exists(f)), None)
    if fpath is None:
        return None, None
    Xd = pd.read_excel(fpath) if fpath.lower().endswith(("xlsx", "xls")) \
        else pd.read_csv(fpath)
    Xd.columns = [str(c).strip() for c in Xd.columns]
    Xd = _add_derived_cols(Xd)                       # EF_minus_VBM 등 4종
    ys = {}
    for ch, (tgt, cands) in [("n-type", ("S_mu_n", _MOB_SCORE_FILES["n-type"])),
                             ("p-type", ("S_mu_p", _MOB_SCORE_FILES["p-type"]))]:
        sp = next((f for f in cands if os.path.exists(f)), None)
        if sp is None:
            continue
        yd = pd.read_excel(sp) if sp.lower().endswith(("xlsx", "xls")) \
            else pd.read_csv(sp)
        yd.columns = [str(c).strip() for c in yd.columns]
        if tgt in yd.columns:
            ys[ch] = yd[["material_id", tgt]]
    return Xd, ys


@st.cache_resource(show_spinner="Mobility 예측 모델을 학습하는 중입니다... "
                                "(최초 1회, 약 30초~1분)")
def get_mobility_models():
    """노트북 방법론을 그대로 재현해 앱에서 직접 학습·검증한다.
    전용 데이터(mobility_features + mobility_score_*)가 있으면 그것으로,
    없으면 메인 데이터셋으로 폴백한다. 정확도(cv_r2_best)는 노트북과 동일한
    80/20 분할의 train에 대한 5-fold CV로 라이브 계산한다."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import cross_val_score, KFold, train_test_split
    from sklearn.metrics import r2_score

    def _winsorize(s):
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        return s.clip(q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))

    Xd, ys = _load_mobility_training()
    _dedicated = Xd is not None and bool(ys)
    if not _dedicated:                               # 폴백: 메인 데이터셋
        Xd = _add_derived_cols(df)
        ys = {ch: Xd[["material_id", t]]
              for ch, t in [("n-type", "S_mu_n"), ("p-type", "S_mu_p")]
              if t in Xd.columns}

    bundles = {}
    for ch, target, wins in [("n-type", "S_mu_n", False),
                             ("p-type", "S_mu_p", True)]:
        if ch not in ys:
            continue
        merged = Xd.merge(ys[ch], on="material_id",
                          suffixes=("", "_y")).dropna(subset=[target])
        if merged.empty:
            continue
        _excl = _NON_FEATURE | _CROSS_EXCLUDE.get(target, set())
        feat_cols = [c for c in merged.columns
                     if c not in _excl and not c.endswith("_y")
                     and pd.api.types.is_numeric_dtype(merged[c])]
        v = merged[target].abs()                     # |μ| (노트북과 동일)
        if wins:
            v = _winsorize(v)                        # p형: |μ| 기준 winsorize
        y = np.log1p(v)
        X = merged[feat_cols].fillna(0)              # 노트북과 동일하게 0 대치
        # 노트북과 동일: 80/20 분할 → train에 대한 5-fold CV + 20% test
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2,
                                              random_state=42)
        m = HistGradientBoostingRegressor(random_state=42, max_iter=300)
        cv = cross_val_score(m, Xtr, ytr, scoring="r2",
                             cv=KFold(5, shuffle=True, random_state=42),
                             n_jobs=-1)
        m.fit(Xtr, ytr)
        test_r2 = float(r2_score(yte, m.predict(Xte)))
        m.fit(X, y)                                  # 예측용 전체 재학습
        mu = v.to_numpy()
        bundles[ch] = {
            "model": m,
            "meta": {
                "feat_cols": feat_cols,
                "medians": {c: (None if pd.isna(merged[c].median())
                                else float(merged[c].median()))
                            for c in feat_cols},
                "pct_grid": np.percentile(mu, np.arange(0, 101)).tolist(),
                "best_model": "HistGradientBoosting",
                "cv_r2_best": round(float(cv.mean()), 4),
                "cv_r2_std": round(float(cv.std()), 4),
                "test_r2": round(test_r2, 4),
                "r2_source": R2_SOURCE,
                "dedicated": _dedicated,
                "n_train": int(len(merged)),
            },
        }
    return bundles


@st.cache_data(show_spinner="feature 중요도 계산 중...")
def get_mobility_importance(channel, top=8):
    """permutation importance 상위 feature (모델 카드용). 캐시됨."""
    from sklearn.inspection import permutation_importance
    from sklearn.model_selection import train_test_split
    bundles = get_mobility_models()
    b = bundles.get(channel)
    if b is None:
        return pd.DataFrame(columns=["feature", "importance"])
    target = "S_mu_n" if channel == "n-type" else "S_mu_p"
    fc = b["meta"]["feat_cols"]
    Xd, ys = _load_mobility_training()
    if Xd is not None and ys and channel in ys:
        d = Xd.merge(ys[channel], on="material_id",
                     suffixes=("", "_y")).dropna(subset=[target])
    else:
        d = _add_derived_cols(df).dropna(subset=[target])
    _v = d[target].abs()
    if channel == "p-type":
        _q1, _q3 = _v.quantile(0.25), _v.quantile(0.75)
        _v = _v.clip(_q1 - 1.5 * (_q3 - _q1), _q3 + 1.5 * (_q3 - _q1))
    y = np.log1p(_v)
    _Xfc = d.reindex(columns=fc).fillna(0)
    _, X_te, _, y_te = train_test_split(_Xfc, y, test_size=0.2,
                                        random_state=42)
    X_te = X_te.sample(min(400, len(X_te)), random_state=42)
    y_te = y_te.loc[X_te.index]
    r = permutation_importance(b["model"], X_te, y_te, n_repeats=5,
                               random_state=42, scoring="r2", n_jobs=-1)
    return (pd.DataFrame({"feature": fc, "importance": r.importances_mean})
            .sort_values("importance", ascending=False).head(top))


def predict_mobility_row(base_vals):
    """물성 dict → (mu_n, pn, mu_p, pp). 모델 없으면 None.
    n형·p형 모델은 CROSS_EXCLUDE로 feature 집합이 다르므로 각자 자기 feature로."""
    bundles = get_mobility_models()
    bn, bp = bundles.get("n-type"), bundles.get("p-type")
    if not bn or not bp:
        return None
    full = _add_derived_row(dict(base_vals))

    def _pr(b):
        _feat = b["meta"]["feat_cols"]
        _X = pd.DataFrame([[full.get(c, np.nan) for c in _feat]],
                          columns=_feat)
        mu = float(np.expm1(b["model"].predict(_X)[0]))
        g = np.asarray(b["meta"]["pct_grid"])
        return max(mu, 0.0), int(np.clip(np.searchsorted(g, mu), 0, 100))
    mn, pn = _pr(bn)
    mp_, pp = _pr(bp)
    return mn, pn, mp_, pp


def recommend_apps(gap, direct, pn, pp):
    """활용 분야 추천 규칙 → [(분야, 적합도0~100, 근거, 스펙)] 정렬 리스트."""
    if gap is None or pd.isna(gap):
        return []
    mu_hi = max(pn, pp)

    def _wl(g):
        return 1240.0 / g if g and g > 0 else float("inf")
    a = []
    if gap <= 0.05:
        a.append(("전극·배선 (도전체)", 68, "밴드갭이 0에 가까워 전도체로 분류.",
                  f"Eg≈{gap:.2f} eV"))
    if 0.05 < gap <= 0.7:
        a.append(("열전 변환 소재", min(95, max(30, 45 + (mu_hi - 50) * 0.6)),
                  "좁은 갭으로 상온 캐리어 여기 용이. 파워팩터·κ 확인 필요.",
                  f"Eg={gap:.2f} eV · 이동도 상위 {100 - mu_hi:.0f}%"))
    if 0.1 <= gap <= 0.9:
        a.append(("적외선(IR) 광검출", 62, f"흡수 파장 ~{_wl(gap):.0f} nm.",
                  f"λ≈{_wl(gap):.0f} nm"))
    if 0.9 <= gap <= 1.9:
        _d = abs(gap - 1.34)
        a.append(("태양전지 광흡수층",
                  min(98, max(35, 100 - _d * 70 + (8 if direct else -10))),
                  "SQ 최적(~1.34 eV) " + ("근접" if _d < 0.2 else "부분 부합")
                  + (", 직접천이" if direct else ", 간접천이"),
                  f"Eg={gap:.2f} eV · λ≈{_wl(gap):.0f} nm"))
    if 0.4 <= gap <= 2.5 and mu_hi >= 60:
        a.append(("트랜지스터 채널", min(96, 50 + (mu_hi - 60) * 0.9),
                  "적정 갭+상위 이동도 조합.",
                  f"Eg={gap:.2f} eV · 이동도 상위 {100 - mu_hi:.0f}%"))
    if 1.6 <= gap <= 3.3 and direct:
        a.append(("가시광 LED·레이저", 74, f"직접천이, λ≈{_wl(gap):.0f} nm.",
                  f"λ≈{_wl(gap):.0f} nm"))
    if 1.8 <= gap <= 3.2:
        a.append(("광촉매·물분해", 56, "물분해 문턱(1.23 eV)+과전압 만족. "
                  "밴드 정렬 검증 필요.", f"Eg={gap:.2f} eV"))
    if 3.1 <= gap <= 4.5:
        a.append(("자외선(UV) 검출", 60, f"UV 대역 λ≈{_wl(gap):.0f} nm.",
                  f"λ≈{_wl(gap):.0f} nm"))
    if gap >= 2.3 and pn >= 60:
        a.append(("전력 반도체 (WBG)", min(96, 55 + (pn - 60) * 0.8),
                  "넓은 갭+상위 전자 이동도.",
                  f"Eg={gap:.2f} eV · n형 상위 {100 - pn:.0f}%"))
    if gap >= 3.0 and pn >= 65:
        a.append(("투명 전도막 (TCO)", 64, "가시광 투과+전자 전도.",
                  f"Eg={gap:.2f} eV · n형 상위 {100 - pn:.0f}%"))
    if gap >= 4.5 and mu_hi < 50:
        a.append(("게이트 유전체·절연막", 62, "넓은 갭+낮은 이동도.",
                  f"Eg={gap:.2f} eV"))
    if not a:
        a.append(("범용 반도체", 40, f"{'직접' if direct else '간접'}천이형, "
                  "특화 조건 미달.", f"Eg={gap:.2f} eV"))
    a.sort(key=lambda x: x[1], reverse=True)
    return a


# ═════════════════════════════════════════════════════════════════════════════
# 개요 페이지 ↔ 분석 페이지 전환
# ═════════════════════════════════════════════════════════════════════════════
if "view" not in st.session_state:
    st.session_state.view = "overview"

if st.session_state.view == "overview":
    st.subheader("반도체·신소재 데이터 분석 플랫폼 소개")
    st.write(
        "Materials Project 기반 소재 데이터셋 중 **비금속(반도체·절연체) 물질만** "
        "대상으로 탐색·스크리닝하는 대시보드입니다. "
        "분석 화면에서는 결정계·밴드갭·화학 조성 필터, 전자 구조 분석, "
        "물성 스크리닝, 상관관계 히트맵, DOS 상세 분석 기능을 사용할 수 있으며, "
        "캐리어 타입(n/p)을 선택하면 해당 mobility 점수로 소재를 평가할 수 있습니다."
    )

    # ── 데이터 분석 시작 버튼 (소개 바로 아래) ───────────────────────────────
    _intro_b1, _intro_b2 = st.columns([1, 2.4])
    with _intro_b1:
        if st.button("데이터 분석 시작하기", icon=":material/analytics:",
                     type="primary", use_container_width=True,
                     key="start_top"):
            st.session_state.view = "analysis"
            st.rerun()

    # ── 플랫 카드 스타일 헬퍼 ────────────────────────────────────────────────
    _NO_BAR = {"displayModeBar": False}

    def _flat(fig, h=240, legend_h=False):
        fig.update_layout(
            height=h, margin=dict(t=8, b=8, l=8, r=8),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(size=11, color="#52514e"),
            legend=(dict(orientation="h", yanchor="top", y=-0.12,
                         xanchor="center", x=0.5, font=dict(size=11))
                    if legend_h else None))
        fig.update_xaxes(gridcolor="#e1e0d9", zeroline=False)
        fig.update_yaxes(gridcolor="#e1e0d9", zeroline=False)
        return fig

    def _card_title(text):
        st.markdown(f'<p style="font-size:13px; font-weight:600; '
                    f'color:#0b0b0b; margin:0 0 4px;">{text}</p>',
                    unsafe_allow_html=True)

    def _section(text, color="#2a78d6"):
        st.markdown(
            '<div style="display:flex; align-items:center; gap:8px; '
            'margin:16px 0 6px;">'
            f'<span style="width:4px; height:17px; background:{color}; '
            'border-radius:2px; display:inline-block;"></span>'
            f'<span style="font-size:14px; font-weight:700; color:#1a2b45;">'
            f'{text}</span></div>',
            unsafe_allow_html=True)

    def _donut(labels, values, colors, h=230):
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.62,
            marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
            textinfo="none"))
        fig.update_layout(showlegend=True)
        return _flat(fig, h=h, legend_h=True)

    # ── 데이터 카드 (출처·규모·커버리지) ────────────────────────────────────
    _section("데이터셋 개요 (Data Card)")

    # 전문 아이콘 (Tabler outline SVG)
    _IC = {
        "atom": ('<circle cx="12" cy="12" r="1.5"/><path d="M12 21c-3.5-3.5-5.'
                 '5-7.5-5.5-9S8.5 3 12 3s5.5 6.5 5.5 9-2 5.5-5.5 9"/><path d="M'
                 '3 12c3.5-3.5 7.5-5.5 9-5.5S18.5 8.5 21 12s-6.5 5.5-9 5.5S6.5 '
                 '15.5 3 12"/>'),
        "columns": ('<rect x="4" y="4" width="6" height="16" rx="1"/><rect x="'
                    '14" y="4" width="6" height="16" rx="1"/>'),
        "shield": ('<path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>'
                   '<path d="M9 12l2 2 4-4"/>'),
        "chart": ('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    }

    def _dcard(label, value, icon, sub="", clr="#2a78d6"):
        svg = (f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
               f'stroke="{clr}" stroke-width="1.8" stroke-linecap="round" '
               f'stroke-linejoin="round">{_IC[icon]}</svg>')
        subhtml = (f'<div style="font-size:9.5px; color:#8a97a8; margin-top:2px;">'
                   f'{sub}</div>' if sub else "")
        return (
            '<div style="flex:1; background:#ffffff; border:1px solid #e4e9f2; '
            'border-radius:9px; padding:8px 10px;">'
            '<div style="display:flex; justify-content:space-between; '
            'align-items:center;">'
            f'<span style="font-size:10.5px; color:#5f6b7a; line-height:1.2;">'
            f'{label}</span>'
            f'<span style="width:28px; height:28px; border-radius:7px; '
            f'background:{clr}14; display:flex; align-items:center; '
            f'justify-content:center; flex:0 0 auto;">{svg}</span></div>'
            f'<div style="font-size:19px; font-weight:700; color:#0b1a30; '
            f'margin-top:2px;">{value}</div>{subhtml}</div>')

    _src_col = df["source"] if "source" in df.columns else pd.Series(
        ["Materials Project"] * len(df), index=df.index)
    _is_mp = _src_col == "Materials Project"
    _mp_n = int((df["S_mu_n"].notna() & _is_mp).sum()) if "S_mu_n" in df.columns else 0
    _mp_p = int((df["S_mu_p"].notna() & _is_mp).sum()) if "S_mu_p" in df.columns else 0
    _m3d_n = int((df.get("mobility_type") == "n-type").sum()) \
        if "mobility_type" in df.columns else 0
    _m3d_p = int((df.get("mobility_type") == "p-type").sum()) \
        if "mobility_type" in df.columns else 0
    _m3d_doped = int((df.get("doped_system") == "Yes").sum()) \
        if "doped_system" in df.columns else 0
    _m3d_undoped = max(0, _n_m3d_kept - _m3d_doped)
    _stable = (f"{int((df['is_stable'] == True).sum()):,}"
               if HAS["is_stable"] else "—")

    # 그래프를 제외한 데이터 카드는 모두 왼쪽, 구성 원소 분포는 오른쪽
    _card_specs = [
        ("M3D Hub 물질", f"{_n_m3d_kept:,}", "atom", "DKU·KIST 계산 DB", "#0e7490"),
        ("mobility 점수 · n형", f"{_mp_n:,}", "chart", "S_mu_n (MP)", "#7f77dd"),
        ("mobility 점수 · p형", f"{_mp_p:,}", "chart", "S_mu_p (MP)", "#9aa5b1"),
        ("M3D n형 (electron)", f"{_m3d_n:,}", "chart", "mobility type", "#2a78d6"),
        ("M3D p형 (hole)", f"{_m3d_p:,}", "chart", "mobility type", "#eb6834"),
        ("M3D 실험 증명 (doped)", f"{_m3d_doped:,}", "shield",
         "doped system = Yes", "#1baf7a"),
        ("M3D 미증명", f"{_m3d_undoped:,}", "shield", "doped 아님", "#9aa5b1"),
        ("물성 변수 수", f"{df.shape[1]:,}", "columns", "", "#0e7490"),
    ]

    # ── 주기율표 데이터 + 선택 원소 (네이티브 버튼 클릭으로 갱신 · 새로고침 없음) ─
    _PT = {}

    def _pt_add(row, els, sc):
        for _i, _e in enumerate(els):
            if _e:
                _PT[_e] = (row, sc + _i)
    _PT["H"] = (1, 1); _PT["He"] = (1, 18)
    _pt_add(2, ["Li", "Be"], 1)
    _pt_add(2, ["B", "C", "N", "O", "F", "Ne"], 13)
    _pt_add(3, ["Na", "Mg"], 1)
    _pt_add(3, ["Al", "Si", "P", "S", "Cl", "Ar"], 13)
    _pt_add(4, ["K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni",
                "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr"], 1)
    _pt_add(5, ["Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
                "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe"], 1)
    _pt_add(6, ["Cs", "Ba"], 1); _PT["La"] = (6, 3)
    _pt_add(6, ["Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl",
                "Pb", "Bi", "Po", "At", "Rn"], 4)
    _pt_add(7, ["Fr", "Ra"], 1); _PT["Ac"] = (7, 3)
    _pt_add(8, ["Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
                "Er", "Tm", "Yb", "Lu"], 4)
    _elc = pd.Series(dtype=int)
    if FORMULA_COL:
        from collections import Counter
        _cnt = Counter()
        for _f in df[FORMULA_COL].dropna().astype(str):
            for _e in set(_ELEMENT_RE.findall(_f)):
                _cnt[_e] += 1
        _elc = pd.Series(_cnt)
    _SCALE = ["#e6f1fb", "#b5d4f4", "#6fa8dc", "#2a6db5", "#0a2c5e"]
    _maxlog = float(np.log10(_elc.max() + 1)) if not _elc.empty else 1.0

    def _cell_color(v):
        if v <= 0:
            return "#f4f6fa"
        frac = np.log10(v + 1) / (_maxlog or 1)
        return _SCALE[max(0, min(4, int(frac * 5 - 1e-9)))]

    def _pick_el(e):
        st.session_state["ov_sel_el"] = e
    if "ov_sel_el" not in st.session_state:
        st.session_state["ov_sel_el"] = "O" if "O" in _PT else next(iter(_PT), "O")
    _sel_el = st.session_state["ov_sel_el"]

    _ovL, _ovR = st.columns([1, 1.05])
    with _ovL:
        _grid = "".join(_dcard(l, v, ic, s, c)
                        for (l, v, ic, s, c) in _card_specs)
        st.markdown(
            '<div style="display:grid; grid-template-columns:1fr 1fr; '
            f'gap:8px;">{_grid}</div>', unsafe_allow_html=True)

        # 주요 물성 데이터 보유율 — 한 줄 정리
        _cov_items = [
            ("밴드갭", "electronic_band_gap", "#2a78d6"),
            ("밴드 에지(CBM/VBM)", "cbm", "#2a78d6"),
            ("열전(PF)", "PF_n", "#1baf7a"),
            ("S_mu_n", "S_mu_n", "#7f77dd"),
            ("S_mu_p", "S_mu_p", "#9aa5b1"),
        ]
        _chips = ""
        for _lab, _col, _clr in _cov_items:
            if _col not in df.columns:
                continue
            _cntv = int(df[_col].notna().sum())
            _chips += (
                f'<div style="flex:1; min-width:82px; background:#ffffff; '
                f'border:1px solid #e4e9f2; border-radius:8px; padding:6px 8px;">'
                f'<div style="font-size:10px; color:#5f6b7a;">{_lab}</div>'
                f'<div style="font-size:15px; font-weight:700; color:{_clr};">'
                f'{_cntv:,}<span style="font-size:9px; color:#8a97a8; '
                f'font-weight:400;">개</span></div></div>')
        st.markdown(
            '<p style="font-size:11px; color:#52514e; margin:10px 0 4px;">'
            '주요 물성 데이터 보유 물질 수 (coverage)</p>'
            f'<div style="display:flex; gap:6px; flex-wrap:wrap;">{_chips}</div>',
            unsafe_allow_html=True)

    with _ovR:
        # ── 구성 원소 분포 (주기율표) — 원소 버튼 클릭으로 선택 (새로고침 없음) ──
        _section("구성 원소 분포 (주기율표) · 원소를 클릭해 선택", "#1baf7a")
        # 정사각형 셀 + 좁은 간격 + 그리드 최대 너비 고정(셀이 과도하게 커지지 않게)
        _btn_css = ("div[class*='st-key-ptbtn_'] button{padding:0!important;"
                    "min-height:0!important;height:auto!important;"
                    "aspect-ratio:1!important;width:100%!important;"
                    "font-size:12px!important;font-weight:700!important;"
                    "border-radius:5px!important;line-height:1!important;"
                    "transition:transform .08s ease, box-shadow .08s ease, "
                    "filter .08s ease!important;}"
                    "div[class*='st-key-ptbtn_'] button p{margin:0!important;"
                    "line-height:1!important;font-size:12px!important;}"
                    "div[class*='st-key-ptbtn_']{width:100%!important;}"
                    # 마우스를 올리면 떠오르는(눌리는 듯한) 효과
                    "div[class*='st-key-ptbtn_'] button:hover{"
                    "transform:translateY(-2px) scale(1.07)!important;"
                    "box-shadow:0 4px 11px rgba(10,31,68,.42)!important;"
                    "filter:brightness(1.08)!important;position:relative;"
                    "z-index:5;}"
                    "div[class*='st-key-ptbtn_'] button:active{"
                    "transform:translateY(0) scale(0.95)!important;}"
                    # 간격 축소 + 그리드 최대 너비 + 가운데 정렬
                    ".st-key-ptgrid{max-width:760px!important;"
                    "margin-left:auto!important;margin-right:auto!important;}"
                    "div[data-testid='stHorizontalBlock']:has("
                    "div[class*='st-key-ptbtn_']){gap:4px!important;}"
                    ".st-key-ptgrid div[data-testid='stVerticalBlock']"
                    "{gap:4px!important;}")
        for _e in _PT:
            _v = int(_elc.get(_e, 0))
            _bg = _cell_color(_v)
            _dark = _v > 0 and (np.log10(_v + 1) / (_maxlog or 1)) >= 0.6
            _fg = "#ffffff" if _dark else ("#1a2b45" if _v > 0 else "#c4ccd8")
            _btn_css += (f".st-key-ptbtn_{_e} button{{background:{_bg}!important;"
                         f"color:{_fg}!important;border:1px solid {_bg}!important;}}")
            if _e == _sel_el:
                _btn_css += (f".st-key-ptbtn_{_e} button{{outline:2px solid "
                             f"#eb6834!important;outline-offset:-1px;}}")
        st.markdown(f"<style>{_btn_css}</style>", unsafe_allow_html=True)
        _pos = {(r, c): e for e, (r, c) in _PT.items()}
        with st.container(key="ptgrid"):
            for _r in range(1, 9):
                _rowcols = st.columns(18, gap="small")
                for _c in range(1, 19):
                    _e = _pos.get((_r, _c))
                    if _e:
                        with _rowcols[_c - 1]:
                            st.button(_e, key=f"ptbtn_{_e}", on_click=_pick_el,
                                      args=(_e,), use_container_width=True,
                                      help=f"{_e}: {int(_elc.get(_e, 0)):,}개 물질")
        if not _elc.empty:
            _top5 = ", ".join(f"{k}({v:,})" for k, v in
                              _elc.sort_values(ascending=False).head(5).items())
            st.caption(f"최다: {_top5} · 색이 진할수록 자주 등장 · 클릭해 선택")

        # ── 선택 원소 요약 ──────────────────────────────────────────────────
        _section(f"선택 원소 요약 · {_sel_el}", "#1baf7a")
        with st.container(border=True):
            if "_elements" in df.columns:
                _emask = df["_elements"].map(
                    lambda s: _sel_el in s
                    if isinstance(s, (set, frozenset)) else False)
            else:
                _emask = df[FORMULA_COL].astype(str).str.contains(
                    _sel_el, na=False) if FORMULA_COL else pd.Series(
                    False, index=df.index)
            _edf = df[_emask]
            _ecnt = len(_edf)

            def _favg(col):
                if col in _edf.columns and _edf[col].notna().any():
                    return f"{_edf[col].mean():.2f}"
                return "—"
            _agap, _an, _ap = (_favg("electronic_band_gap"),
                               _favg("S_mu_n"), _favg("S_mu_p"))
            st.markdown(
                f'<div style="display:flex; gap:8px; flex-wrap:wrap; '
                f'font-size:12px; color:#1a2b45;">'
                f'<span style="background:#fff; border:1px solid #dbe6f5; '
                f'border-radius:6px; padding:4px 8px;">물질 수 '
                f'<b>{_ecnt:,}</b></span>'
                f'<span style="background:#fff; border:1px solid #dbe6f5; '
                f'border-radius:6px; padding:4px 8px;">평균 밴드갭 '
                f'<b>{_agap}</b> eV</span>'
                f'<span style="background:#fff; border:1px solid #dbe6f5; '
                f'border-radius:6px; padding:4px 8px;">평균 S_mu_n '
                f'<b>{_an}</b></span>'
                f'<span style="background:#fff; border:1px solid #dbe6f5; '
                f'border-radius:6px; padding:4px 8px;">평균 S_mu_p '
                f'<b>{_ap}</b></span></div>',
                unsafe_allow_html=True)
            if _ecnt and {"S_mu_n", "S_mu_p"} <= set(_edf.columns):
                _mm = _edf[["S_mu_n", "S_mu_p"]].max(axis=1)
                _topd = _edf.assign(_m=_mm).dropna(subset=["_m"]).nlargest(5, "_m")
                if not _topd.empty:
                    _cols = [c for c in ["material_id", "source", FORMULA_COL,
                                         "electronic_band_gap", "S_mu_n", "S_mu_p"]
                             if c and c in _topd.columns]
                    st.caption(f"{_sel_el} 포함 · mobility 상위 물질")
                    st.dataframe(_topd[_cols].reset_index(drop=True),
                                 use_container_width=True, height=150)

    st.markdown("---")

    # ── 구조·결정 분포 (전체 / mobility 상위 10% 선택) ───────────────────────
    _section("구조·결정 분포")
    _struct_scope = st.radio(
        "표시 범위", ["전체", "mobility 상위 10%"], horizontal=True,
        key="ov_struct_scope",
        help="mobility 상위 10%: S_mu_n·S_mu_p 중 큰 값 기준 상위 10% 물질")
    _sdf = df
    if _struct_scope.startswith("mobility") and {"S_mu_n", "S_mu_p"} <= set(df.columns):
        _mmax = df[["S_mu_n", "S_mu_p"]].max(axis=1)
        if _mmax.notna().any():
            _thr = _mmax.quantile(0.90)
            _sdf = df[_mmax >= _thr]
    st.caption(f"현재 표시 대상: {len(_sdf):,}개 물질 ({_struct_scope})")
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        if HAS["crystal_system"]:
            _card_title("결정계별 물질 수")
            vc = _sdf["crystal_system"].value_counts().sort_values().reset_index()
            vc.columns = ["결정계", "물질 수"]
            fig = px.bar(vc, x="물질 수", y="결정계", orientation="h",
                         color="물질 수", color_continuous_scale="Blues",
                         text="물질 수")
            fig.update_traces(texttemplate="%{text:,}", textposition="outside",
                              marker_line_width=0)
            fig.update_layout(showlegend=False, coloraxis_showscale=False,
                              xaxis_title=None, yaxis_title=None)
            st.plotly_chart(_flat(fig, h=300), use_container_width=True,
                            config=_NO_BAR)
    with c2, st.container(border=True):
        if "space_group_symbol" in _sdf.columns:
            _card_title("공간군 Top 10")
            sg = _sdf["space_group_symbol"].value_counts().head(10)
            sg = sg.sort_values().reset_index()
            sg.columns = ["공간군", "물질 수"]
            fig = px.bar(sg, x="물질 수", y="공간군", orientation="h",
                         color="물질 수", color_continuous_scale="Teal")
            fig.update_traces(marker_line_width=0)
            fig.update_layout(showlegend=False, coloraxis_showscale=False,
                              xaxis_title=None, yaxis_title=None)
            st.plotly_chart(_flat(fig, h=300), use_container_width=True,
                            config=_NO_BAR)

    # ── 밴드갭 분포 (n형 / p형 분리, 전체 / mobility 상위 10% 선택) ──────────
    _section("밴드갭 분포 (캐리어 타입별)")
    _bg_scope = st.radio(
        "표시 범위 ", ["전체", "mobility 상위 10%"], horizontal=True,
        key="ov_bg_scope",
        help="mobility 상위 10%: 각 캐리어의 mobility 점수(S_mu) 상위 10% 물질")
    c3, c4 = st.columns(2)
    for _cc, _mcol, _title, _clr in [
            (c3, "S_mu_n", "n형 물질 밴드갭 분포", "#2a78d6"),
            (c4, "S_mu_p", "p형 물질 밴드갭 분포", "#eb6834")]:
        with _cc, st.container(border=True):
            if HAS["electronic_band_gap"] and _mcol in df.columns:
                _card_title(_title)
                _sub = df[(df["electronic_band_gap"] > 0.001) &
                          (df["electronic_band_gap"] <= 8) &
                          (df[_mcol].notna())]
                if _bg_scope.startswith("mobility") and not _sub.empty:
                    _thr = _sub[_mcol].quantile(0.90)
                    _sub = _sub[_sub[_mcol] >= _thr]
                fig = px.histogram(_sub, x="electronic_band_gap", nbins=60,
                                   color_discrete_sequence=[_clr],
                                   labels={"electronic_band_gap": "밴드갭 (eV)"})
                fig.update_layout(yaxis_title="물질 수", bargap=0.12,
                                  showlegend=False)
                st.plotly_chart(_flat(fig, h=300), use_container_width=True,
                                config=_NO_BAR)
                st.caption(f"{_mcol} 보유 물질 {len(_sub):,}개 기준 ({_bg_scope})")

    with st.expander("데이터셋 주요 변수 설명", icon=":material/menu_book:"):
        st.markdown("""
| 변수 | 설명 |
|---|---|
| `electronic_band_gap` | 전자 밴드갭 (eV). 0이면 금속성 |
| `e_fermi` | 페르미 에너지 (eV) |
| `S_p`, `S_n` | 제베크 계수 (p형 / n형) |
| `PF_p`, `PF_n` | 열전 파워 팩터 |
| `sigma_p`, `sigma_n` | 전기 전도도 |
| `S_mu_n`, `S_mu_p` | 캐리어 mobility 점수 (n형 / p형) |
| `Nc/Nv_300K_cm-3` | 300 K 유효 상태 밀도 (전도대/가전자대) |
| `n/p_300K_cm-3` | 300 K 캐리어 농도 |
| `dDOS_dE_CBM/VBM_fit` | 밴드 에지 DOS 기울기 (창 선형 피팅) |
| `energy_above_hull` | 열역학적 안정성 지표 (0에 가까울수록 안정) |
| `formation_energy_per_atom` | 원자당 형성 에너지 (eV/atom) |
""")
    st.caption("위 통계는 전체 데이터(필터 미적용) 기준입니다. "
               "데이터 출처: Materials Project 기반 병합 데이터셋")

    # ── Mobility 예측 모델 카드 ──────────────────────────────────────────────
    _section("Mobility 예측 모델 카드 (Machine Learning)", "#1baf7a")
    with st.container(border=True):
        _card_title("HistGradientBoosting 회귀 · log(1+μ) 학습")
        st.caption("아래 버튼을 누르면 서버에서 모델을 학습·평가하고 성능과 "
                   "AI feature 중요도를 표시합니다 (배포 환경 안정성을 위해 "
                   "부팅 시 자동 실행하지 않습니다).")
        if st.button("모델 성능·AI feature 중요도 계산",
                     icon=":material/insights:", use_container_width=True):
            try:
                _mb = get_mobility_models()
                _bn, _bp = _mb.get("n-type"), _mb.get("p-type")
                if _bn and _bp:
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("n형 정확도 (CV R²)",
                               f"{_bn['meta']['cv_r2_best']:.3f}",
                               delta=f"n={_bn['meta']['n_train']:,}",
                               delta_color="off",
                               help=_bn['meta'].get('r2_source'))
                    mc2.metric("p형 정확도 (CV R²)",
                               f"{_bp['meta']['cv_r2_best']:.3f}",
                               delta=f"n={_bp['meta']['n_train']:,}",
                               delta_color="off",
                               help=_bp['meta'].get('r2_source'))
                    mc3.metric("입력 feature 수",
                               f"{len(_bn['meta']['feat_cols'])}",
                               delta="HistGB", delta_color="off")
                    st.caption("※ 정확도는 노트북과 동일한 방법론"
                               "(전용 feature + |μ|→winsorize→log(1+μ), "
                               "80/20 분할의 train에 대한 5-fold CV)으로 앱에서 "
                               "직접 계산한 값입니다.")
                    ic1, ic2 = st.columns(2)
                    for _cc, _ch, _clr, _lab in [(ic1, "n-type", "#2a78d6", "n형"),
                                                 (ic2, "p-type", "#eb6834", "p형")]:
                        with _cc:
                            _card_title(f"{_lab} feature 중요도 (Top 8)")
                            _imp = get_mobility_importance(_ch)
                            if not _imp.empty:
                                _imp = _imp.sort_values("importance")
                                _fig = px.bar(_imp, x="importance", y="feature",
                                              orientation="h",
                                              color_discrete_sequence=[_clr])
                                _fig.update_traces(marker_line_width=0)
                                _fig.update_layout(showlegend=False,
                                                   xaxis_title="중요도 (R² 감소량)",
                                                   yaxis_title=None)
                                _fig2 = _flat(_fig, h=300)
                                _fig2.update_layout(margin=dict(t=8, b=8,
                                                                l=8, r=8))
                                st.plotly_chart(_fig2, use_container_width=True,
                                                config=_NO_BAR)
                    st.caption("중요도는 permutation importance(테스트셋에서 각 "
                               "feature를 무작위로 섞을 때 R² 감소량) 기준입니다. "
                               "물리 파생 feature(밴드에지·유효질량)가 상위를 "
                               "차지하는 것이 특징입니다.")
            except ImportError:
                st.warning("scikit-learn 미설치 — run.bat으로 재실행 시 자동 설치.")
            except Exception as e:
                st.error(f"모델 계산 실패: {e}")

    st.stop()  # 개요 페이지에서는 아래 분석 UI를 렌더링하지 않음

# ── 분석 페이지: 사이드바 상단에 개요 복귀 버튼 ──────────────────────────────
if st.sidebar.button("← 개요로 돌아가기", use_container_width=True):
    st.session_state.view = "overview"
    st.rerun()

# ── Mobility 데이터 병합 (n-type / p-type 선택) ──────────────────────────────
MOBILITY_FILES = {"n-type": "mobility_score_ntype.xlsx",
                  "p-type": "mobility_score_ptype.xlsx"}


@st.cache_data
def load_mobility(path):
    m = pd.read_excel(path)
    m.columns = [str(c).strip() for c in m.columns]
    return m.drop_duplicates("material_id")


st.sidebar.markdown("### :material/bolt: 캐리어 타입 (Mobility)")
carrier_type = st.sidebar.radio(
    "mobility 점수 기준", ["n-type", "p-type", "둘 다 (n+p)"],
    horizontal=True, label_visibility="collapsed")

# 선택에 따른 mobility 점수 컬럼(들)
if carrier_type == "n-type":
    MOB_SCORE_COLS = ["S_mu_n"]
elif carrier_type == "p-type":
    MOB_SCORE_COLS = ["S_mu_p"]
else:
    MOB_SCORE_COLS = ["S_mu_n", "S_mu_p"]
MOB_SCORE_COLS = [c for c in MOB_SCORE_COLS if c in df.columns]
# 하위 호환용 단일 컬럼 (둘 다일 때는 n형 기준)
MOB_SCORE_COL = MOB_SCORE_COLS[0] if MOB_SCORE_COLS else None

if MOB_SCORE_COLS:
    _cap = " · ".join(
        f"{c.replace('S_mu_', '').upper()}형 {int(df[c].notna().sum()):,}개"
        for c in MOB_SCORE_COLS)
    st.sidebar.caption(f"mobility 점수 보유: {_cap}")
else:
    st.sidebar.caption("mobility 데이터 없음")

# ──────────────────────────────────────────────────────────────────────────────
# 1. 사이드바 필터
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.header(":material/tune: 데이터 필터 조건")
filtered_df = df.copy()

# ── 데이터 출처 필터 (Materials Project / M3D Hub) — 모든 분석에 적용 ────────
if "source" in df.columns:
    _src_opts = ["전체", "Materials Project", "M3D Hub"]
    _src_sel = st.sidebar.radio("데이터 출처", _src_opts, index=0,
                                help="MP 물질과 M3D Hub 물질을 구분해 분석합니다.")
    if _src_sel != "전체":
        filtered_df = filtered_df[filtered_df["source"] == _src_sel]

if HAS["crystal_system"]:
    all_crystals = sorted(df["crystal_system"].dropna().unique().tolist())
    selected = st.sidebar.multiselect("결정계 (Crystal System)", all_crystals,
                                      default=all_crystals)  # 기본: 전체
    filtered_df = filtered_df[filtered_df["crystal_system"].isin(selected)]

if HAS["electronic_band_gap"]:
    bg = df["electronic_band_gap"].dropna()
    if not bg.empty:
        lo, hi = float(bg.min()), float(bg.max())
        default_hi = min(5.0, hi)  # 데이터 범위로 클램프
        bg_range = st.sidebar.slider("밴드갭 (eV) 범위", lo, hi, (lo, default_hi))
        filtered_df = filtered_df[
            filtered_df["electronic_band_gap"].between(*bg_range)]

st.sidebar.caption("ℹ️ 금속은 전역적으로 제외되어 비금속만 표시됩니다.")

# 안정성 필터 (금속 여부는 전역 제외되어 필터에서 삭제됨)
for _col, _label, _true_lbl, _false_lbl in [
        ("is_stable", "안정성 (is_stable)", "안정 상만", "준안정 상만")]:
    if not HAS[_col]:
        st.sidebar.selectbox(_label, ["전체"], key=f"filter_{_col}",
                             disabled=True,
                             help=f"데이터에서 '{_col}' 컬럼을 찾지 못해 비활성화됨")
        continue
    _vals = df[_col].dropna().unique().tolist()
    _boolish = len(_vals) > 0 and all(
        isinstance(v, (bool, np.bool_)) for v in _vals)
    if _boolish:
        _opt = st.sidebar.selectbox(_label, ["전체", _true_lbl, _false_lbl],
                                    key=f"filter_{_col}")
        if _opt != "전체":
            filtered_df = filtered_df[filtered_df[_col] == (_opt == _true_lbl)]
    elif _vals:
        # bool로 변환되지 않은 형식 → 실제 값 그대로 선택지 제공
        _opt = st.sidebar.selectbox(_label,
                                    ["전체"] + [str(v) for v in _vals[:10]],
                                    key=f"filter_{_col}")
        if _opt != "전체":
            filtered_df = filtered_df[filtered_df[_col].astype(str) == _opt]

# ── 화학 조성 필터 (산화물/질화물, 주기율표 족) ───────────────────────────────
if "_elements" in df.columns:
    with st.sidebar.expander("화학 조성 필터", icon=":material/science:",
                             expanded=True):
        sel_anions = st.multiselect(
            "화합물 종류", list(ANION_CLASSES),
            help="여러 개 선택 시 OR 조건 (산화물 또는 질화물 등)")
        if sel_anions:
            targets = set().union(*(ANION_CLASSES[a] for a in sel_anions))
            filtered_df = filtered_df[
                filtered_df["_elements"].map(lambda s: bool(s & targets))]

        sel_groups = st.multiselect(
            "주기율표 족 (1~18족)", list(ELEMENT_GROUPS),
            format_func=lambda g: f"{g}족 ({', '.join(ELEMENT_GROUPS[g][:4])}…)"
            if len(ELEMENT_GROUPS[g]) > 4
            else f"{g}족 ({', '.join(ELEMENT_GROUPS[g])})",
            help="예: 2족=Be,Mg,Ca…  4족=Ti,Zr,Hf  13족=B,Al,Ga…  14족=C,Si,Ge…")
        if sel_groups:
            g_elems = set().union(*(set(ELEMENT_GROUPS[g]) for g in sel_groups))
            mode = st.radio("족 필터 방식",
                            ["선택 족 원소를 하나 이상 포함",
                             "모든 구성 원소가 선택 족에 속함"])
            if mode.startswith("선택"):
                filtered_df = filtered_df[
                    filtered_df["_elements"].map(lambda s: bool(s & g_elems))]
            else:
                filtered_df = filtered_df[
                    filtered_df["_elements"].map(
                        lambda s: bool(s) and s <= g_elems)]

        el_query = st.text_input(
            "특정 원소 포함 (쉼표 구분)", placeholder="예: Ti, O",
            help="입력한 원소를 모두 포함하는 물질만 표시")
        if el_query.strip():
            need = {e.strip().capitalize() for e in el_query.split(",") if e.strip()}
            filtered_df = filtered_df[
                filtered_df["_elements"].map(lambda s: need <= s)]

if len(filtered_df) == 0 and len(df) > 0:
    st.sidebar.error("조건에 맞는 데이터가 0개입니다. 필터를 완화해 보세요.")
    with st.sidebar.expander("값 진단 (0개 원인 확인)",
                             icon=":material/search:"):
        for c in ("is_metal", "is_stable"):
            if c in df.columns:
                vals = df[c].dropna().unique()[:5]
                st.write(f"`{c}` 값 예시: {list(vals)}")

st.sidebar.markdown(f"**선택된 데이터: {len(filtered_df):,} / {len(df):,}**")

numeric_cols = filtered_df.select_dtypes(include="number").columns.tolist()

# ──────────────────────────────────────────────────────────────────────────────
# 2. 탭 구성
# ──────────────────────────────────────────────────────────────────────────────
# ── 관심 물질 장바구니 (세션 유지) ───────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []   # material_id 리스트


def _add_to_cart(ids):
    added = 0
    for i in ids:
        if i and i not in st.session_state.cart:
            st.session_state.cart.append(i)
            added += 1
    return added


st.sidebar.markdown(
    f"### :material/bookmark_star: 관심목록: {len(st.session_state.cart)}개")

# ── MP API 공용 헬퍼 (스크리닝 탭에서도 사용하므로 상단 배치) ──────────
def _get_mp_key():
    """secrets → 환경변수 → 세션 순으로 MP API 키를 찾음 (입력창 없음)."""
    try:
        k = st.secrets.get("MP_API_KEY", "")
    except Exception:
        k = ""
    return k or os.environ.get("MP_API_KEY", "") or \
        st.session_state.get("mp_api_key", "")


@st.cache_resource(show_spinner=False)
def fetch_phase_diagram_figure(chemsys, api_key, show_unstable=0.1):
    """화학계의 볼록 껍질 위상도(plotly)를 PDPlotter로 생성해 반환.
    반환: (plotly figure, 안정상 개수, 전체 entry 개수)"""
    from mp_api.client import MPRester
    from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
    els = sorted(set(chemsys))
    with MPRester(api_key) as mpr:
        entries = mpr.get_entries_in_chemsys(els)
    if not entries:
        return None, 0, 0
    pd_ = PhaseDiagram(entries)
    plotter = PDPlotter(pd_, show_unstable=show_unstable, backend="plotly")
    # 안정상 + 준안정상 모두 화학식 라벨 표시 (전문 위상도 표기)
    try:
        fig = plotter.get_plot(label_stable=True, label_unstable=True)
    except Exception:
        fig = plotter.get_plot()
    fig.update_layout(
        title=f"{'-'.join(els)} 볼록 껍질 위상도 (Convex Hull)",
        font=dict(size=13), plot_bgcolor="white", paper_bgcolor="white",
        height=580,
        # 삼각도(3원계) 꼭짓점 라벨이 잘리지 않도록 여백을 넉넉히
        margin=dict(t=80, b=90, l=90, r=90))
    # 3원계: 기본 축 제목이 꼭짓점 마커와 겹치므로, 제목은 숨기고
    #        각 꼭짓점 바깥쪽에 큰 글씨 원소 라벨을 별도로 배치한다.
    if len(els) == 3:
        import plotly.graph_objects as go
        _t = fig.layout.ternary
        _a = _t.aaxis.title.text or ""       # 위 꼭짓점
        _b = _t.baxis.title.text or ""       # 왼쪽 아래 꼭짓점
        _c = _t.caxis.title.text or ""       # 오른쪽 아래 꼭짓점
        fig.update_ternaries(
            aaxis=dict(title_text="", ticks="", showticklabels=False),
            baxis=dict(title_text="", ticks="", showticklabels=False),
            caxis=dict(title_text="", ticks="", showticklabels=False))
        fig.add_trace(go.Scatterternary(
            a=[1, 0, 0], b=[0, 1, 0], c=[0, 0, 1], mode="text",
            text=[_a, _b, _c],
            textposition=["top center", "bottom left", "bottom right"],
            textfont=dict(size=24, color="#0a1f44", family="Arial Black"),
            showlegend=False, hoverinfo="skip", cliponaxis=False))
    return fig, len(pd_.stable_entries), len(entries)


@st.cache_resource(show_spinner=False)
def fetch_phase_diagram_mpl(chemsys, api_key, show_unstable=0.0):
    """PDF 리포트용 볼록 껍질 위상도를 matplotlib(백엔드)로 생성해 반환.
    plotly는 이미지 변환에 Chrome이 필요해 PDF 임베드가 어려우므로 별도로 둔다.
    준안정상까지 라벨을 달면 화학식이 심하게 겹치므로, 기본은 안정상만
    (show_unstable=0) 표시하고 라벨 글자도 줄인다.
    반환: (matplotlib fig, 안정상 개수, 전체 entry 개수). 실패 시 (None,0,0)."""
    import matplotlib.pyplot as plt
    from mp_api.client import MPRester
    from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
    els = sorted(set(chemsys))
    if not (2 <= len(els) <= 3):
        return None, 0, 0            # 2·3원계만 그림으로 표현 가능
    with MPRester(api_key) as mpr:
        entries = mpr.get_entries_in_chemsys(els)
    if not entries:
        return None, 0, 0
    pd_ = PhaseDiagram(entries)
    plt.close("all")
    PDPlotter(pd_, show_unstable=show_unstable,
              backend="matplotlib").get_plot()
    fig = plt.gcf()
    fig.set_size_inches(7, 5.8)
    # 라벨 겹침 완화: 남은 화학식 라벨 글자 크기를 줄이고
    #                혹시 남은 준안정상(파란) 라벨은 제거한다.
    if fig.axes:
        _ax = fig.axes[0]
        for _t in list(_ax.texts):
            _col = _t.get_color()
            _blue = (_col in ("b", "blue")
                     or (isinstance(_col, (tuple, list)) and len(_col) >= 3
                         and _col[0] < 0.4 and _col[2] > 0.6))
            if _blue:
                _t.remove()
            else:
                _t.set_fontsize(8.5)
    fig.suptitle(f"{'-'.join(els)} Convex Hull (안정상만 표시)", fontsize=11,
                 fontweight="bold", y=0.99)
    fig.tight_layout()
    return fig, len(pd_.stable_entries), len(entries)


# ── 밴드(fat band) 헬퍼: tab2에서 사용하므로 탭 앞에 배치 ──────────────
def _tidy_band_xticks(fig, merge_frac=0.012, fontsize=11):
    """밴드 경로 그림의 x축 고대칭점 라벨 겹침을 정리한다.
    ① 거의 같은 위치(경로 불연속점)에 놓인 눈금은 'A|L'처럼 하나로 합치고,
    ② 짧은 구간에 라벨이 몰려도 읽히도록 글자 크기를 낮춘다."""
    if not fig.axes:
        return fig
    ax = fig.axes[0]
    ticks = list(ax.get_xticks())
    labels = [t.get_text() for t in ax.get_xticklabels()]
    if not ticks or len(ticks) != len(labels):
        for a in fig.axes:
            for t in a.get_xticklabels():
                t.set_fontsize(fontsize)
        return fig
    x0, x1 = ax.get_xlim()
    thr = merge_frac * ((x1 - x0) or 1.0)

    def _clean(lab):                       # LaTeX·중복 토큰 제거 후 부분 목록
        lab = (lab.replace("$", "").replace("\\mid", "|")
                  .replace("\\Gamma", "Γ").replace("\\Sigma", "Σ"))
        return [p.strip() for p in lab.split("|") if p.strip()]

    new_t, new_l, i, n = [], [], 0, len(ticks)
    while i < n:
        j = i
        while j + 1 < n and (ticks[j + 1] - ticks[j]) < thr:
            j += 1
        if j > i:                          # 겹치는 눈금들을 'A|L'로 병합
            parts = []
            for k in range(i, j + 1):
                for p in _clean(labels[k]):
                    if not parts or parts[-1] != p:
                        parts.append(p)
            new_t.append(0.5 * (ticks[i] + ticks[j]))
            new_l.append("|".join(parts))
        else:
            new_t.append(ticks[i])
            new_l.append("|".join(_clean(labels[i])) or labels[i])
        i = j + 1
    ax.set_xticks(new_t)
    ax.set_xticklabels(new_l, fontsize=fontsize)
    return fig


def parse_vasprun_band_figure(vasprun_path, kpoints_path=None, mode="element"):
    """업로드한 vasprun.xml을 파싱해 궤도 투영 밴드(fat band) 그림 생성.
    반환: (matplotlib fig, 밴드갭 eV, 투영 여부)."""
    import matplotlib.pyplot as plt
    from pymatgen.io.vasp.outputs import Vasprun
    from pymatgen.electronic_structure.plotter import (BSPlotter,
                                                       BSPlotterProjected)
    vr = Vasprun(vasprun_path, parse_projected_eigen=True)
    bs = vr.get_band_structure(kpoints_filename=kpoints_path, line_mode=True)
    if bs is None:
        return None, None, False
    _gap = None
    try:
        _gap = float(bs.get_band_gap().get("energy"))
    except Exception:
        _gap = None
    has_proj = bool(getattr(bs, "projections", None))
    plt.close("all")
    try:
        if has_proj and mode == "element":
            BSPlotterProjected(bs).get_elt_projected_plots_color()
        elif has_proj and mode == "spd":
            _els = [str(e) for e in bs.structure.composition.elements]
            BSPlotterProjected(bs).get_projected_plots_dots(
                {el: ["s", "p", "d"] for el in _els})
        else:
            BSPlotter(bs).get_plot()
            has_proj = False
    except Exception:
        # 투영 실패 시 일반 밴드로 폴백
        plt.close("all")
        BSPlotter(bs).get_plot()
        has_proj = False
    fig = plt.gcf()
    fig.set_size_inches(9, 6)
    _tidy_band_xticks(fig)
    fig.tight_layout()
    return fig, _gap, has_proj


@st.cache_resource(show_spinner=False)
def fetch_fatband_from_mp(material_id, api_key, mode="element"):
    """MP API로 밴드 구조를 받아 궤도 투영 밴드(fat band) 그림 생성 (업로드 불필요).
    반환: (matplotlib fig, 밴드갭 eV, 투영 여부). 투영 데이터가 없으면 일반 밴드."""
    import matplotlib.pyplot as plt
    from mp_api.client import MPRester
    from pymatgen.electronic_structure.plotter import (BSPlotter,
                                                       BSPlotterProjected)
    with MPRester(api_key) as mpr:
        bs = mpr.get_bandstructure_by_material_id(material_id)
    if bs is None:
        return None, None, False
    _gap = None
    try:
        _gap = float(bs.get_band_gap().get("energy"))
    except Exception:
        _gap = None
    has_proj = bool(getattr(bs, "projections", None))
    plt.close("all")
    try:
        if has_proj and mode == "element":
            BSPlotterProjected(bs).get_elt_projected_plots_color()
        elif has_proj and mode == "spd":
            _els = [str(e) for e in bs.structure.composition.elements]
            BSPlotterProjected(bs).get_projected_plots_dots(
                {el: ["s", "p", "d"] for el in _els})
        else:
            BSPlotter(bs).get_plot()
            has_proj = False
    except Exception:
        plt.close("all")
        BSPlotter(bs).get_plot()
        has_proj = False
    fig = plt.gcf()
    fig.set_size_inches(9, 6)
    _tidy_band_xticks(fig)
    fig.tight_layout()
    return fig, _gap, has_proj


# 상위 탭: 데이터 탐색 · DOS 상세 분석 · Mobility 예측 · 기타
# '기타' 안에 전자 구조 분석 · 물성 스크리닝 · 상관관계 히트맵 · 관심목록을 배치
tab1, tab5, tab6, _tab_etc = st.tabs([
    ":material/table_chart: 데이터 탐색",
    ":material/query_stats: DOS 상세 분석",
    ":material/neurology: Mobility 예측",
    ":material/apps: 기타",
])
with _tab_etc:
    tab2, tab3, tab4, tab7 = st.tabs([
        ":material/bolt: 전자 구조 분석",
        ":material/science: 물성 스크리닝",
        ":material/grid_on: 상관관계 히트맵",
        ":material/bookmark_star: 관심목록·랭킹",
    ])

# ── Tab 1: 데이터 탐색 ────────────────────────────────────────────────────────
with tab1:
    st.subheader("데이터 필터링 결과")
    show_cols = [c for c in ["material_id", "source", FORMULA_COL,
                             "crystal_system", "electronic_band_gap",
                             "e_fermi", "volume"]
                 if c and c in filtered_df.columns]
    for _mc in MOB_SCORE_COLS:  # 선택된 캐리어 타입의 mobility 점수(들)
        if _mc in filtered_df.columns:
            show_cols.append(_mc)
    display_df = filtered_df.drop(columns=["_elements"], errors="ignore")

    # 항상 선택한 캐리어의 mobility 점수 랭킹(내림차순) 순으로 정렬
    _sort_cols = [c for c in MOB_SCORE_COLS if c in display_df.columns]
    if _sort_cols:
        _mkey = display_df[_sort_cols].max(axis=1)
        display_df = (display_df.assign(_mob_rank=_mkey)
                      .sort_values("_mob_rank", ascending=False,
                                   na_position="last")
                      .drop(columns="_mob_rank").reset_index(drop=True))
        st.caption(f"※ {' / '.join(_sort_cols)} 기준 mobility 점수 "
                   "높은 순으로 정렬했습니다.")

    # 표시할 컬럼 직접 선택 (기본값: 핵심 컬럼 + mobility 점수)
    _all_cols = display_df.columns.tolist()
    _defaults = [c for c in show_cols if c in _all_cols]
    sel_view_cols = st.multiselect(
        "표시할 컬럼 선택", _all_cols,
        default=_defaults or _all_cols[:6],
        help="원하는 컬럼을 추가/제거하면 테이블과 CSV 다운로드에 반영됩니다.")
    _view = display_df[sel_view_cols] if sel_view_cols else display_df
    st.dataframe(_view, use_container_width=True, height=420)

    st.download_button(
        "필터링 결과 CSV 다운로드 (선택한 컬럼)", icon=":material/download:",
        data=_view.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_materials.csv", mime="text/csv",
    )

    # 관심목록에 담기
    if HAS["material_id"]:
        st.markdown(":material/bookmark_add: **관심목록에 담기**")
        _ac1, _ac2 = st.columns([3, 1])
        with _ac1:
            _ids_pool = filtered_df["material_id"].dropna().unique().tolist()
            _fmap0 = (filtered_df.set_index("material_id")[FORMULA_COL].to_dict()
                      if FORMULA_COL else {})
            _pick = st.multiselect(
                "물질 선택 (필터 결과에서)", _ids_pool,
                format_func=lambda i: f"{i} ({_fmap0.get(i, '?')})",
                key="cart_pick")
        with _ac2:
            st.write("")
            st.write("")
            if st.button("담기", use_container_width=True,
                         disabled=not _pick):
                _n = _add_to_cart(_pick)
                st.success(f"{_n}개 담김 (총 {len(st.session_state.cart)}개)")
        st.caption("담은 물질은 '관심목록·랭킹' 탭에서 비교·내보내기 할 수 "
                   "있습니다.")

    if st.checkbox("기초 통계치(describe) 보기"):
        st.write(filtered_df.describe())

# ── Tab 2: 전자 구조 분석 (궤도 투영 밴드) ───────────────────────────────────
with tab2:
    st.subheader("궤도 투영 밴드 구조 (Fat Band)")
    st.write("각 밴드에 어떤 원소·궤도가 기여하는지 선 색·점 크기로 표현한 "
             "궤도 투영 밴드입니다. VBM/CBM이 어떤 원소의 s/p/d 궤도로 "
             "구성되는지, 광학 전이가 어디서 일어나는지 분석할 수 있습니다.")

    _fb_src = st.radio(
        "데이터 소스",
        ["데이터셋에서 조회 (MP API)", "vasprun.xml 업로드 (내 계산)"],
        horizontal=True, key="fb_src")

    def _show_fatband(fig, gap, proj):
        if fig is None:
            st.warning("밴드 구조를 생성하지 못했습니다 (계산 데이터 부재 가능).")
        else:
            st.pyplot(fig)
            _msg = ("궤도 투영 포함" if proj else "투영 정보 없음 — 일반 밴드")
            st.caption((f"밴드갭 {gap:.3f} eV · " if gap else "") + _msg +
                       ". 색·점 크기가 각 밴드의 원소·궤도 기여를 나타냅니다.")

    if _fb_src.startswith("데이터셋"):
        _mode = "element"        # MP 밴드에는 투영이 없어 방식 선택은 무의미
        st.caption("데이터셋 물질을 선택하면 Materials Project에서 밴드 구조를 "
                   "받아 그립니다. (API 키 필요·조회 다소 느림)")
        st.info("ℹ️ Materials Project가 제공하는 밴드에는 궤도·원소 투영 정보가 "
                "없어 **일반 밴드 구조**로 표시됩니다. 원소별 색상 / s·p·d 점 "
                "크기 구분은 아래 **vasprun.xml 업로드**(LORBIT=11)에서만 "
                "가능합니다.", icon=":material/info:")
        _fbkey = _get_mp_key()
        if not _fbkey:
            _fbkey = st.text_input("MP API Key", type="password",
                                   key="fb_key_input",
                                   help="DOS 탭에서 저장하면 자동 사용됩니다.")
            if _fbkey:
                st.session_state["mp_api_key"] = _fbkey
        if HAS["material_id"]:
            _fids = filtered_df["material_id"].dropna().unique().tolist()
            _ffmap = (filtered_df.set_index("material_id")[FORMULA_COL].to_dict()
                      if FORMULA_COL else {})
            _fbmid = st.selectbox(
                "물질 선택 (필터링 결과 기준)", _fids,
                format_func=lambda i: f"{i} ({_ffmap.get(i, '?')})",
                key="fb_mid") if _fids else None
        else:
            _fbmid = st.text_input("MP ID 직접 입력", placeholder="mp-149",
                                   key="fb_mid_txt")
        if _fbkey and _fbmid and st.button(
                "Fat Band 그리기", icon=":material/show_chart:",
                type="primary", key="btn_fatband_mp"):
            try:
                with st.spinner(f"{_fbmid} 밴드 구조를 가져오는 중..."):
                    _ff, _fg, _fp = fetch_fatband_from_mp(_fbmid, _fbkey, _mode)
                _show_fatband(_ff, _fg, _fp)
            except ImportError:
                st.error("pymatgen이 필요합니다. run.bat 재실행 시 자동 설치.")
            except Exception as _e:
                st.error(f"밴드 조회/렌더 실패: {_e}")
    else:
        st.caption("직접 수행한 DFT 밴드 계산의 vasprun.xml(LORBIT=11, 투영 "
                   "포함)을 올리세요. 고대칭점 라벨을 위해 KPOINTS도 함께 올리면 "
                   "좋습니다.")
        _fbmode = st.radio(
            "투영 방식",
            ["원소별 색상 (RGB)", "s/p/d 궤도별 점 크기"],
            horizontal=True, key="fb_mode",
            help="원소별: 밴드 색으로 어느 원소인지 표시 · s/p/d: 점 크기로 "
                 "어느 궤도인지 표시. (투영 정보가 있는 계산에서만 구분됨)")
        _mode = "element" if _fbmode.startswith("원소") else "spd"
        _uv = st.file_uploader("vasprun.xml", type=["xml"], key="vasp_up")
        _uk = st.file_uploader("KPOINTS (선택 — 고대칭점 라벨용)", type=None,
                               key="kpt_up")
        if _uv is not None and st.button(
                "Fat Band 그리기", icon=":material/show_chart:",
                type="primary", key="btn_fatband_up"):
            import tempfile
            import os as _os
            try:
                _tmpd = tempfile.mkdtemp()
                _vp = _os.path.join(_tmpd, "vasprun.xml")
                with open(_vp, "wb") as _f:
                    _f.write(_uv.getbuffer())
                _kp = None
                if _uk is not None:
                    _kp = _os.path.join(_tmpd, "KPOINTS")
                    with open(_kp, "wb") as _f:
                        _f.write(_uk.getbuffer())
                with st.spinner("vasprun.xml 파싱 및 밴드 렌더링 중..."):
                    _ff, _fg, _fp = parse_vasprun_band_figure(_vp, _kp, _mode)
                _show_fatband(_ff, _fg, _fp)
            except ImportError:
                st.error("pymatgen이 필요합니다. run.bat 재실행 시 자동 설치.")
            except Exception as _e:
                st.error(f"파싱/렌더 실패: {_e}")

# ── Tab 3: 물성 스크리닝 ──────────────────────────────────────────────────────
with tab3:
    st.subheader("물성 스크리닝")

    # ── 파레토 전선 (다목적 최적 후보) ───────────────────────────────────────
    st.markdown("##### :material/track_changes: 파레토 전선 (다목적 최적 후보)")
    st.write("두 물성을 동시에 최적화할 때, 다른 어떤 물질에도 밀리지 않는 "
             "**파레토 최적(non-dominated) 후보**를 찾아 강조합니다. "
             "기본값은 열전 성능(ZT) 트레이드오프인 파워팩터(↑) vs "
             "열전도도(↓)입니다.")
    if len(numeric_cols) >= 2:
        pc1, pc2, pc3, pc4 = st.columns([2, 1.2, 2, 1.2])

        def _pidx(name, d=0):
            return numeric_cols.index(name) if name in numeric_cols else d
        with pc1:
            obj1 = st.selectbox("목표 1", numeric_cols,
                                index=_pidx("PF_n"), key="par_o1")
        with pc2:
            dir1 = st.selectbox("방향 1", ["높을수록", "낮을수록"], key="par_d1")
        with pc3:
            obj2 = st.selectbox("목표 2", numeric_cols,
                                index=_pidx("kappa_n", 1), key="par_o2")
        with pc4:
            dir2 = st.selectbox("방향 2", ["낮을수록", "높을수록"], key="par_d2")

        if obj1 == obj2:
            st.info("서로 다른 두 물성을 선택하세요.")
        else:
            _pdf = filtered_df.dropna(subset=[obj1, obj2]).copy()
            if _pdf.empty:
                st.warning("두 물성이 모두 있는 물질이 없습니다.")
            else:
                # 두 목표를 '최대화' 문제로 통일 (낮을수록 좋으면 부호 반전)
                s1 = (_pdf[obj1] * (1 if dir1 == "높을수록" else -1)).to_numpy()
                s2 = (_pdf[obj2] * (1 if dir2 == "높을수록" else -1)).to_numpy()
                pts = np.column_stack([s1, s2])
                # 목표1 내림차순, 동점 시 목표2 내림차순으로 정렬
                order = np.lexsort((-pts[:, 1], -pts[:, 0]))
                is_par = np.zeros(len(pts), dtype=bool)
                best2 = -np.inf
                for i in order:
                    if pts[i, 1] > best2:   # 엄격 부등호 → 지배되는 점 제외
                        is_par[i] = True
                        best2 = pts[i, 1]
                _pdf["파레토"] = np.where(is_par, "파레토 최적", "일반")
                _front = _pdf[is_par].sort_values(obj1,
                                                  ascending=(dir1 != "높을수록"))
                _hover = [c for c in ["material_id", FORMULA_COL]
                          if c and c in _pdf.columns]
                fig = px.scatter(
                    _pdf, x=obj1, y=obj2, color="파레토",
                    color_discrete_map={"파레토 최적": "#e24b4a",
                                        "일반": "#c9d4e4"},
                    hover_data=_hover, opacity=0.6,
                    title=f"{obj1}({dir1}) vs {obj2}({dir2}) — 파레토 전선")
                fig.update_traces(marker=dict(size=6),
                                  selector=dict(name="파레토 최적"))
                # 파레토 전선을 선으로 연결
                _fl = _front.sort_values(obj1)
                fig.add_scatter(x=_fl[obj1], y=_fl[obj2], mode="lines",
                                line=dict(color="#e24b4a", width=1.5, dash="dot"),
                                name="전선", showlegend=False)
                # y축 상한 2M로 제한 (열전도도 등 극단값 물질로 축이 늘어나는 것 방지)
                _ymin = float(_pdf[obj2].min())
                if float(_pdf[obj2].max()) > 2e6:
                    fig.update_yaxes(range=[min(_ymin, 0), 2e6])
                    st.caption("※ y축을 2,000,000까지로 제한했습니다 "
                               "(초과 물질은 화면 밖).")
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"파레토 최적 {len(_front):,}개 (전체 "
                           f"{len(_pdf):,}개 중). 빨간 점이 두 목표를 동시에 "
                           "만족하는 최적 후보입니다.")
                _show = [c for c in ["material_id", FORMULA_COL, obj1, obj2]
                         if c and c in _front.columns]
                st.dataframe(_front[_show].reset_index(drop=True),
                             use_container_width=True, height=240)
                if HAS["material_id"] and st.button(
                        "파레토 후보 관심목록에 담기",
                        icon=":material/bookmark_add:", key="par_cart"):
                    _n = _add_to_cart(_front["material_id"].tolist())
                    st.success(f"{_n}개 담김 (총 "
                               f"{len(st.session_state.cart)}개)")

    # ── 볼록 껍질(Convex Hull) 위상도 (MP API) ──────────────────────────────
    st.markdown("---")
    st.markdown("##### △ 볼록 껍질 위상도 (합성 안정성, Convex Hull)")
    st.write("선택한 화학계의 형성에너지 볼록 껍질을 그려 껍질 위(안정상)와 "
             "위쪽(준안정상)을 구분합니다. 신소재의 열역학적 합성 가능성 "
             "스크리닝에 쓰입니다. (Materials Project API 키 필요)")
    _pd_key = _get_mp_key()
    if not _pd_key:
        _pd_key = st.text_input(
            "MP API Key", type="password", key="pd_key_input",
            help="DOS 탭에서 키를 저장하면 여기서도 자동으로 사용됩니다.")
        if _pd_key:
            st.session_state["mp_api_key"] = _pd_key
    _chem = st.text_input("화학계 (원소를 하이픈으로, 예: Li-Fe-O)",
                          key="pd_chem", placeholder="Ti-O")
    if _pd_key and st.button("위상도 생성", icon=":material/change_history:",
                             key="btn_pd_scr", disabled=not _chem.strip()):
        _els = [e.strip() for e in _chem.split("-") if e.strip()]
        if not (2 <= len(_els) <= 4):
            st.warning("원소 2~4개를 하이픈(-)으로 구분해 입력하세요.")
        else:
            try:
                with st.spinner(f"{'-'.join(_els)} 계의 entry를 가져와 "
                                "위상도를 계산하는 중..."):
                    _pf, _nstab, _ntot = fetch_phase_diagram_figure(
                        _els, _pd_key)
                if _pf is None:
                    st.warning("해당 화학계의 데이터를 찾지 못했습니다.")
                else:
                    st.plotly_chart(_pf, use_container_width=True)
                    st.caption(f"{'-'.join(_els)} 계 · 전체 {_ntot}개 중 "
                               f"안정상 {_nstab}개 (껍질 위). 준안정상은 "
                               "껍질로부터의 거리로 표시됩니다.")
            except ImportError:
                st.error("pymatgen이 필요합니다. run.bat 재실행 시 자동 설치.")
            except Exception as _e:
                st.error(f"위상도 생성 실패: {_e}")

# ── Tab 4: 상관관계 히트맵 ────────────────────────────────────────────────────
with tab4:
    st.subheader("수치형 변수 상관관계")
    default_cols = [c for c in ["a", "b", "c", "volume", "density",
                                "electronic_band_gap", "e_fermi",
                                "mean_electronegativity"] if c in numeric_cols]
    sel_cols = st.multiselect("변수 선택", numeric_cols,
                              default=default_cols or numeric_cols[:8])
    method = st.radio("상관계수", ["pearson", "spearman"], horizontal=True,
                      help="물성 간 비선형 단조 관계는 spearman이 더 잘 잡습니다.")
    if len(sel_cols) >= 2:
        corr = filtered_df[sel_cols].corr(method=method)
        fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1,
                        color_continuous_scale="RdBu_r", aspect="equal",
                        title=f"{method.capitalize()} 상관관계 히트맵")
        # 정사각형: 셀을 정방형으로 고정하고 변수 수에 맞춰 동일 가로·세로
        _sz = int(min(860, max(420, len(sel_cols) * 46 + 190)))
        fig.update_xaxes(constrain="domain")
        fig.update_yaxes(scaleanchor="x", constrain="domain")
        fig.update_layout(width=_sz, height=_sz,
                          margin=dict(l=10, r=10, t=50, b=10))
        _lc, _cc, _rc = st.columns([1, 6, 1])
        with _cc:
            st.plotly_chart(fig, use_container_width=False)
    else:
        st.info("2개 이상의 변수를 선택하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# Tab 5: DOS 상세 분석 (Materials Project API + 창 선형 피팅)
# ──────────────────────────────────────────────────────────────────────────────
def fit_edge_slope(energies, densities, edge, side, window):
    """밴드 에지 근처 window(eV) 구간 선형 피팅 → (기울기, 절편, mask)."""
    if side == "vbm":
        mask = (energies <= edge) & (energies >= edge - window)
    else:
        mask = (energies >= edge) & (energies <= edge + window)
    if mask.sum() < 3:
        return None, None, mask
    slope, intercept = np.polyfit(energies[mask], densities[mask], 1)
    return slope, intercept, mask


@st.cache_data(show_spinner=False)
def fetch_dos(material_id: str, api_key: str):
    """MP에서 DOS를 가져와 캐시 가능한 순수 배열/스칼라로 반환."""
    from mp_api.client import MPRester
    with MPRester(api_key) as mpr:
        dos = mpr.get_dos_by_material_id(material_id)
    if dos is None:
        return None
    cbm, vbm = dos.get_cbm_vbm()
    return {
        "energies": np.asarray(dos.energies),
        "densities": np.asarray(dos.get_densities()),
        "efermi": float(dos.efermi),
        "vbm": float(vbm),
        "cbm": float(cbm),
        "gap": float(dos.get_gap()),
    }


@st.cache_resource(show_spinner=False)
def fetch_band_dos_figure(material_id, api_key, vb_range=4.0, cb_range=4.0):
    """밴드 구조 + PDOS를 pymatgen BSDOSPlotter로 그려 (matplotlib fig, 수준) 반환.
    일부 물질은 DOS에 궤도 투영 정보가 없어, 투영 수준을 단계적으로 낮춰 재시도한다:
    궤도(orbitals) → 원소(elements) → 총 DOS(None) → 밴드만."""
    import matplotlib.pyplot as plt
    from mp_api.client import MPRester
    from pymatgen.electronic_structure.plotter import BSDOSPlotter
    with MPRester(api_key) as mpr:
        bs = mpr.get_bandstructure_by_material_id(material_id)
        try:
            dos = mpr.get_dos_by_material_id(material_id)
        except Exception:
            dos = None
    if bs is None:
        return None, None

    _levels = [("orbitals", dos, "밴드 구조 + 궤도별 PDOS (s/p/d)"),
               ("elements", dos, "밴드 구조 + 원소별 PDOS"),
               (None, dos, "밴드 구조 + 총 DOS"),
               (None, None, "밴드 구조 (DOS 없음)")]
    for _proj, _dos, _label in _levels:
        if _dos is None and _proj is not None:
            continue
        try:
            plt.close("all")
            plotter = BSDOSPlotter(
                bs_projection="elements", dos_projection=_proj,
                vb_energy_range=vb_range, cb_energy_range=cb_range,
                fig_size=(11, 6), font="DejaVu Sans", axis_fontsize=13,
                tick_fontsize=10, legend_fontsize=10)
            plotter.get_plot(bs, _dos)
            return plt.gcf(), _label
        except Exception:
            continue
    return None, None


def plot_dos(d, material_id, window, fit_v, fit_c, avg_v, avg_c):
    import matplotlib.pyplot as plt
    e, dens = d["energies"], d["densities"]
    vbm, cbm, gap = d["vbm"], d["cbm"], d["gap"]

    fig, ax = plt.subplots(figsize=(12, 6.5), facecolor="#f4f8fd")
    ax.set_facecolor("#fbfdff")
    for spine in ax.spines.values():
        spine.set_color("#b9cfe8")
    ax.fill_between(e, 0, dens, where=(e <= vbm), alpha=0.25,
                    color="#1e3a8a", label="Valence Band")
    ax.fill_between(e, 0, dens, where=(e >= cbm), alpha=0.25,
                    color="#0891b2", label="Conduction Band")
    ax.plot(e, dens, color="black", lw=1.2, label="Total DOS")
    ax.axvline(vbm, color="#1e3a8a", lw=1.5, ls="--", alpha=0.8,
               label=f"VBM ({vbm:.3f} eV)")
    ax.axvline(cbm, color="#0891b2", lw=1.5, ls="--", alpha=0.8,
               label=f"CBM ({cbm:.3f} eV)")

    xlo, xhi = vbm - 3.0, cbm + 3.0
    view = (e >= xlo) & (e <= xhi)
    y_top = 1.2 * dens[view].max() if view.any() else 60

    y_br = 0.88 * y_top
    ax.annotate("", xy=(cbm, y_br), xytext=(vbm, y_br),
                arrowprops=dict(arrowstyle="<->", color="gray", lw=1.5))
    ax.text((vbm + cbm) / 2, y_br + 0.01 * y_top, f"Gap = {gap:.3f} eV",
            ha="center", va="bottom", fontsize=12, color="gray",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85))

    for (slope, icept), edge, side, color, name in [
            (fit_v, vbm, "vbm", "#1e3a8a", "VBM"),
            (fit_c, cbm, "cbm", "#0891b2", "CBM")]:
        if slope is None:
            continue
        if side == "vbm":
            x_fit = np.linspace(edge - window - 0.05, edge + 0.02, 50)
        else:
            x_fit = np.linspace(edge - 0.02, edge + window + 0.05, 50)
        ax.plot(x_fit, np.clip(slope * x_fit + icept, 0, None), color=color,
                lw=1.8, ls="-.",
                label=f"dDOS/dE @ {name} ({window} eV fit) = {slope:.2f} st/eV²")

    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("Density of States (states/eV)")
    ax.set_title(f"DOS — {material_id}  |  VBM {vbm:.3f}  CBM {cbm:.3f}  "
                 f"Gap {gap:.3f} eV")
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(0, y_top)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(axis="x", ls=":", alpha=0.4)
    fig.tight_layout()
    return fig


with tab5:
    st.subheader("Materials Project DOS + 창 선형 피팅 분석")

    # API 키: secrets → 환경변수 → 입력창 (하드코딩 금지)
    # secrets.toml 파일이 아예 없으면 st.secrets 접근 자체가 예외를 던지므로 try 필요
    try:
        api_key = st.secrets.get("MP_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        api_key = os.environ.get("MP_API_KEY", "")
    if not api_key:
        api_key = st.session_state.get("mp_api_key", "")
    if not api_key:
        _k1, _k2 = st.columns([3, 1])
        with _k1:
            _key_in = st.text_input("MP API Key", type="password",
                                    help="materialsproject.org에서 발급. "
                                         "'키 저장'을 누르면 다음 실행부터 "
                                         "자동으로 사용됩니다.")
        with _k2:
            st.write("")
            st.write("")
            if st.button("키 저장", icon=":material/save:",
                         disabled=not _key_in, use_container_width=True):
                os.makedirs(".streamlit", exist_ok=True)
                _sf = os.path.join(".streamlit", "secrets.toml")
                _lines = []
                if os.path.exists(_sf):
                    _lines = [l for l in
                              open(_sf, encoding="utf-8").read().splitlines()
                              if not l.strip().startswith("MP_API_KEY")]
                _lines.append(f'MP_API_KEY = "{_key_in}"')
                with open(_sf, "w", encoding="utf-8") as _fp:
                    _fp.write("\n".join(_lines) + "\n")
                st.success("저장 완료 — 재시작해도 유지됩니다.")
        api_key = _key_in
        if api_key:
            st.session_state["mp_api_key"] = api_key  # 세션 내 유지

    # mobility 점수를 보유한 물질 ID 집합 (★ 표시 및 필터용)
    _score_ids = set()
    for _sc in ("S_mu_n", "S_mu_p"):
        if _sc in df.columns:
            _score_ids |= set(df.loc[df[_sc].notna(), "material_id"])

    c1, c2 = st.columns([2, 1])
    with c1:
        if HAS["material_id"]:
            only_scored = st.checkbox(
                f":material/star: mobility 점수 보유 물질만 보기 "
                f"({len(_score_ids):,}개)",
                value=True,
                help="원본 데이터에서 mobility 점수가 계산된 물질만 목록에 표시")
            ids = filtered_df["material_id"].dropna().unique().tolist()
            if only_scored:
                ids = [i for i in ids if i in _score_ids]
            if not ids:
                st.warning("조건에 맞는 물질이 없습니다. 필터를 완화하거나 "
                           "체크박스를 해제해 보세요.")
                mid = None
            elif FORMULA_COL:
                fmap = filtered_df.set_index("material_id")[FORMULA_COL].to_dict()
                mid = st.selectbox(
                    "물질 선택 (필터링 결과 기준, ★=점수 보유)", ids,
                    format_func=lambda i: f"{i}  ({fmap.get(i, '?')})"
                    + ("  ★" if i in _score_ids else ""))
            else:
                mid = st.selectbox("물질 선택 (필터링 결과 기준)", ids)
        else:
            mid = st.text_input("MP ID 직접 입력", placeholder="mp-149")
    with c2:
        window = st.number_input("에너지 창 (eV)", 0.05, 1.0, 0.1, 0.05,
                                 help="격자 간격 ~0.02 eV → 0.1 eV 이상 권장")
    show_band = st.checkbox("밴드 구조도 함께 표시 (MP API · 다소 느림)",
                            value=True, key="dos_show_band")

    if st.button("DOS 분석 실행", type="primary", disabled=not (api_key and mid)):
        d, fetch_error = None, False
        try:
            with st.spinner(f"{mid}의 DOS 데이터를 가져오는 중..."):
                d = fetch_dos(mid, api_key)
        except ImportError:
            st.error("`mp-api` 패키지가 없습니다. `pip install mp-api` 후 재실행하세요.")
            fetch_error = True
        except Exception as e:
            st.error(f"DOS 조회 실패: {e}")
            fetch_error = True

        if d is None:
            if not fetch_error:
                st.warning("해당 물질의 DOS 데이터가 없습니다 (계산 데이터 부재 가능).")
        else:
            e_arr, dens = d["energies"], d["densities"]
            vbm, cbm = d["vbm"], d["cbm"]

            # CSV 갭과 비교 (계산 방식 차이로 값이 다를 수 있음 → 그 차이도 정보)
            csv_gap = np.nan
            if HAS["electronic_band_gap"] and HAS["material_id"]:
                row = df.loc[df["material_id"] == mid, "electronic_band_gap"]
                if not row.empty:
                    csv_gap = float(row.iloc[0])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("DOS Band Gap", f"{d['gap']:.3f} eV")
            m2.metric("데이터셋 Band Gap",
                      "—" if np.isnan(csv_gap) else f"{csv_gap:.3f} eV",
                      delta=None if np.isnan(csv_gap)
                      else f"{d['gap'] - csv_gap:+.3f} eV (DOS−CSV)")
            m3.metric("E_fermi", f"{d['efermi']:.3f} eV")
            m4.metric("VBM / CBM", f"{vbm:.2f} / {cbm:.2f} eV")

            if d["gap"] <= 1e-3:
                st.warning("갭이 0에 가깝습니다(금속성). "
                           "밴드 에지 창 피팅은 의미가 없어 생략합니다.")
                fit_v = fit_c = (None, None)
                avg_v = avg_c = np.nan
            else:
                mask_v = (e_arr <= vbm) & (e_arr >= vbm - window)
                mask_c = (e_arr >= cbm) & (e_arr <= cbm + window)
                avg_v = dens[mask_v].mean() if mask_v.any() else np.nan
                avg_c = dens[mask_c].mean() if mask_c.any() else np.nan
                sv, iv, _ = fit_edge_slope(e_arr, dens, vbm, "vbm", window)
                sc, ic, _ = fit_edge_slope(e_arr, dens, cbm, "cbm", window)
                fit_v, fit_c = (sv, iv), (sc, ic)

                r1, r2 = st.columns(2)
                r1.metric(f"평균 정공 DOS ({window} eV 창)", f"{avg_v:.3f} st/eV")
                r2.metric(f"평균 전자 DOS ({window} eV 창)", f"{avg_c:.3f} st/eV")
                if sv is not None:
                    r1.metric("dDOS/dE @ VBM (창 피팅)", f"{sv:.3f} st/eV²")
                if sc is not None:
                    r2.metric("dDOS/dE @ CBM (창 피팅)", f"{sc:.3f} st/eV²")

            st.pyplot(plot_dos(d, mid, window, fit_v, fit_c, avg_v, avg_c))

            # ── DOS와 함께 밴드 구조 출력 (체크 시) ─────────────────────────
            if show_band:
                st.markdown("**밴드 구조 + 궤도별 PDOS**")
                try:
                    with st.spinner(f"{mid} 밴드 구조를 가져오는 중... "
                                    "(다소 느림)"):
                        _bfig, _blevel = fetch_band_dos_figure(mid, api_key)
                    if _bfig is None:
                        st.info("이 물질은 밴드 구조 데이터가 없습니다 "
                                "(계산 미제공 가능).")
                    else:
                        st.pyplot(_bfig)
                        st.caption(f"{_blevel} · 좌: 밴드 구조(색=원소 기여) · "
                                   "우: 상태밀도. E−E_F=0 공통 에너지축.")
                except ImportError:
                    st.warning("pymatgen 미설치 — run.bat 재실행 시 자동 설치.")
                except Exception as _e:
                    st.warning(f"밴드 구조 조회 생략: {_e}")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 6: Mobility 예측 (머신러닝 모델) — 모델 정의는 상단으로 이동됨
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader(":material/neurology: 새 물질의 Mobility 예측")
    st.write("물질의 물성 값을 입력하면 머신러닝 모델이 n형·p형 "
             "mobility 점수(S_mu)를 예측합니다. 기존 물질을 템플릿으로 불러와 "
             "일부 물성만 바꿔 가상 물질을 실험해 볼 수도 있습니다.")

    try:
        _bundles = get_mobility_models()
        bundle_n = _bundles.get("n-type")
        bundle_p = _bundles.get("p-type")
    except ImportError:
        st.warning("scikit-learn이 설치되어 있지 않습니다. 앱을 종료하고 "
                   "run.bat으로 다시 실행하면 자동 설치됩니다.")
        bundle_n = bundle_p = None
    except Exception as e:
        st.error(f"모델 학습 실패: {e}")
        bundle_n = bundle_p = None

    if True:
        if bundle_n and bundle_p:
            meta = bundle_n["meta"]
            # n형·p형 모델의 feature 집합이 다르므로(CROSS_EXCLUDE) 입력 폼은
            # 두 모델 feature의 합집합을 받아 어느 쪽도 결측이 없도록 한다.
            feat_cols = list(dict.fromkeys(
                bundle_n["meta"]["feat_cols"] + bundle_p["meta"]["feat_cols"]))
            base_feats = [c for c in feat_cols
                          if c not in _DERIVED and c != "is_metal"]
            # 중앙값도 두 모델 것을 병합 (예측 시 결측 대치용)
            medians = {**bundle_p["meta"]["medians"], **bundle_n["meta"]["medians"]}

            c1, c2 = st.columns(2)
            _r2n = bundle_n["meta"]["cv_r2_best"]
            _r2p = bundle_p["meta"]["cv_r2_best"]
            _src = bundle_p["meta"].get("r2_source", "")
            c1.metric("n형 모델 정확도 (CV R²)", f"{_r2n:.3f}",
                      delta=bundle_n["meta"]["best_model"], delta_color="off",
                      help=_src)
            c2.metric("p형 모델 정확도 (CV R²)", f"{_r2p:.3f}",
                      delta=bundle_p["meta"]["best_model"], delta_color="off",
                      help=_src)
            st.caption(f"※ 위 정확도는 {_src}로 계산했습니다 "
                       f"(test R²: n {bundle_n['meta'].get('test_r2')} / "
                       f"p {bundle_p['meta'].get('test_r2')}).")

            # 템플릿: 중앙값 / 기존 물질 / 파일 업로드
            st.markdown("##### 1) 시작값 선택")
            use_template = st.radio(
                "입력 시작값",
                ["데이터 중앙값", "기존 물질 불러오기", "파일 업로드 (CSV/Excel)"],
                horizontal=True, label_visibility="collapsed")
            template = dict(medians)
            tmpl_name = "데이터 중앙값"
            _missing = set()   # 이 물질에 값이 없는 물성 → 입력칸을 빈칸으로

            if use_template == "기존 물질 불러오기" and HAS["material_id"]:
                _ids = df["material_id"].dropna().unique().tolist()
                _fmap = (df.set_index("material_id")[FORMULA_COL].to_dict()
                         if FORMULA_COL else {})
                _sel = st.selectbox(
                    "템플릿 물질", _ids,
                    format_func=lambda i: f"{i} ({_fmap.get(i, '?')})")
                _row = df[df["material_id"] == _sel]
                if not _row.empty:
                    tmpl_name = f"{_sel} ({_fmap.get(_sel, '?')})"
                    for c in base_feats:
                        if c in _row.columns and pd.notna(_row.iloc[0][c]):
                            template[c] = float(_row.iloc[0][c])
                        else:
                            _missing.add(c)   # 값 없음 → 빈칸 처리

            elif use_template == "파일 업로드 (CSV/Excel)":
                _up = st.file_uploader(
                    "물성이 담긴 CSV 또는 Excel 파일 업로드 "
                    "(컬럼명이 데이터셋과 같으면 자동 매칭)",
                    type=["csv", "xlsx", "xls"], key="pred_upload")
                if _up is not None:
                    try:
                        if _up.name.lower().endswith((".xlsx", ".xls")):
                            _udf = pd.read_excel(_up)
                        else:
                            _udf = pd.read_csv(_up)
                        _udf.columns = [str(c).strip() for c in _udf.columns]
                        _udf = _canonicalize_columns(_udf)
                        _udf = _add_derived_cols(_udf)
                        _matched = [c for c in base_feats if c in _udf.columns]
                        st.caption(f"업로드 {len(_udf)}행 · 매칭된 물성 "
                                   f"{len(_matched)}/{len(base_feats)}개")
                        if len(_udf) > 1:
                            _label_col = ("material_id"
                                          if "material_id" in _udf.columns
                                          else (FORMULA_COL
                                                if FORMULA_COL in _udf.columns
                                                else None))
                            _idx = st.selectbox(
                                "예측할 행 선택", list(range(len(_udf))),
                                format_func=lambda i:
                                (f"{i}: {_udf.iloc[i][_label_col]}"
                                 if _label_col else f"{i}행"))
                        else:
                            _idx = 0
                        _urow = _udf.iloc[int(_idx)]
                        tmpl_name = f"업로드 파일 · {_up.name} ({int(_idx)}행)"
                        for c in base_feats:
                            if c in _udf.columns and pd.notna(_urow[c]):
                                template[c] = float(_urow[c])
                            else:
                                _missing.add(c)
                        if not _matched:
                            st.warning("매칭된 물성 컬럼이 없습니다. 컬럼명이 "
                                       "데이터셋 변수명과 같은지 확인하세요 "
                                       "(예: electronic_band_gap, e_fermi, vbm).")
                    except Exception as _e:
                        st.error(f"파일을 읽지 못했습니다: {_e}")
                else:
                    st.info("파일을 올리기 전에는 중앙값이 시작값으로 사용됩니다.")

            def _clean(v):
                return 0.0 if v is None or pd.isna(v) else float(v)

            # 템플릿(물질)이 바뀌면 위젯 key도 바뀌어 새 시작값으로 재초기화된다.
            # (값이 없는 물성은 value=None → 입력칸이 빈칸으로 표시됨)
            _sig = ("median" if use_template == "데이터 중앙값" else tmpl_name)
            _sig_h = str(abs(hash(_sig)) % 1_000_000)

            st.markdown("##### 2) 물성 입력 (필요한 값만 수정)")
            st.caption(f"현재 시작값: **{tmpl_name}** "
                       "— 물질을 바꾸면 아래 값이 자동으로 갱신됩니다.")
            if _missing:
                st.caption(f"※ 이 물질에 값이 없는 물성 {len(_missing)}개는 "
                           "**빈칸**으로 표시됩니다. 비워두면 예측 시 중앙값 대체 "
                           "없이 **NaN(결측)** 으로 모델에 전달됩니다.")
            inputs = {}

            def _num_input(col, label=None):
                k = f"pred_{col}_{_sig_h}"
                if col in _BINARY_FEATS:
                    _dv = (False if col in _missing
                           else bool(round(_clean(template.get(col)))))
                    return 1.0 if st.checkbox(label or col, value=_dv,
                                              key=k) else 0.0
                _dv = None if col in _missing else _clean(template.get(col))
                v = st.number_input(label or col, value=_dv, format="%.4f",
                                    key=k, placeholder="값 없음")
                return v  # 빈칸이면 None

            _key_present = [c for c in _KEY_FEATS if c in base_feats]
            cols = st.columns(3)
            for i, c in enumerate(_key_present):
                with cols[i % 3]:
                    inputs[c] = _num_input(c)

            with st.expander("고급 입력 — 나머지 물성 (열지 않으면 시작값 사용)"):
                _rest = [c for c in base_feats if c not in _key_present]
                rcols = st.columns(3)
                for i, c in enumerate(_rest):
                    with rcols[i % 3]:
                        inputs[c] = _num_input(c)

            # 값 없는 물성은 중앙값으로 대체하지 않고 NaN으로 둔다
            # (HistGradientBoosting은 NaN을 그대로 처리함).
            full = dict(template)
            for _c in _missing:
                full[_c] = np.nan
            full.update({_k: _v for _k, _v in inputs.items() if _v is not None})
            full = _add_derived_row(full)

            st.markdown("##### 3) 예측")
            if st.button("Mobility 예측 실행", icon=":material/play_circle:",
                         type="primary", use_container_width=True):
                def _predict(bundle):
                    # 각 모델은 CROSS_EXCLUDE로 feature 집합이 다르므로
                    # 자기 feature 순서대로 입력 행을 만든다. 없는 값은 NaN.
                    _fc = bundle["meta"]["feat_cols"]
                    _Xrow = pd.DataFrame(
                        [[full.get(c, np.nan) for c in _fc]], columns=_fc)
                    mu = float(np.expm1(bundle["model"].predict(_Xrow)[0]))
                    grid = np.asarray(bundle["meta"]["pct_grid"])
                    pctile = int(np.clip(np.searchsorted(grid, mu), 0, 100))
                    return max(mu, 0.0), pctile

                mu_n, pn = _predict(bundle_n)
                mu_p, pp = _predict(bundle_p)

                rc1, rc2 = st.columns(2)
                rc1.metric("예측 n형 mobility (S_mu_n)",
                           f"{mu_n:.3f}" if mu_n >= 0.01 else f"{mu_n:.2e}",
                           delta=f"상위 {100 - pn}%")
                rc2.metric("예측 p형 mobility (S_mu_p)",
                           f"{mu_p:.3f}" if mu_p >= 0.01 else f"{mu_p:.2e}",
                           delta=f"상위 {100 - pp}%")

                better = "n형" if pn >= pp else "p형"
                st.success(f"이 물질은 **{better}** 캐리어에서 상대적으로 우수한 "
                           f"mobility가 예상됩니다 "
                           f"(n형 상위 {100 - pn}% · p형 상위 {100 - pp}%).")
                st.caption(f"시작값: {tmpl_name} · 모델: HistGradientBoosting "
                           f"(log(1+μ) 학습, n={bundle_n['meta']['n_train']:,} / "
                           f"{bundle_p['meta']['n_train']:,})")



# ══════════════════════════════════════════════════════════════════════════════
# Tab 7: 관심목록 & 다중 조건 가중 랭킹 & 리포트 내보내기
# ══════════════════════════════════════════════════════════════════════════════
def _to_excel_bytes(sheets: dict) -> bytes:
    """{시트명: DataFrame} → xlsx 바이트."""
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, d in sheets.items():
            d.to_excel(xw, sheet_name=name[:31], index=False)
    return buf.getvalue()


def _report_html(title, tables: dict) -> str:
    """간단한 HTML 리포트 문자열."""
    import datetime
    css = ("body{font-family:sans-serif;color:#12263a;margin:24px;}"
           "h1{color:#0a1f44;font-size:20px;}h2{color:#123c78;font-size:15px;"
           "border-bottom:2px solid #2563eb;padding-bottom:3px;margin-top:24px;}"
           "table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0;}"
           "th{background:#123c78;color:#fff;padding:5px 8px;text-align:left;}"
           "td{border:1px solid #cdd8e8;padding:4px 8px;}"
           "tr:nth-child(even){background:#f0f6fd;}"
           ".cap{color:#667;font-size:11px;}")
    parts = [f"<html><head><meta charset='utf-8'><style>{css}</style></head>"
             f"<body><h1>{title}</h1>"
             f"<p class='cap'>생성: {datetime.datetime.now():%Y-%m-%d %H:%M} · "
             "Material Property Analyzer</p>"]
    for name, d in tables.items():
        parts.append(f"<h2>{name}</h2>")
        parts.append(d.to_html(index=False, na_rep="—", border=0))
    parts.append("</body></html>")
    return "".join(parts)


def _set_korean_font():
    """matplotlib(차트)용 한글 폰트 설정."""
    import matplotlib
    from matplotlib import font_manager
    for name in ["Malgun Gothic", "AppleGothic", "NanumGothic",
                 "Noto Sans CJK KR", "Noto Sans KR", "Noto Sans CJK JP"]:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            matplotlib.rcParams["font.family"] = name
            matplotlib.rcParams["axes.unicode_minus"] = False
            return True
        except Exception:
            continue
    return False


def _register_report_fonts():
    """reportlab(본문)용 한글 TrueType 폰트 등록. Windows 맑은고딕 우선,
    없으면 앱에 번들된 assets/report_kr.ttf 사용."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as RLTTF
    if "KR" in pdfmetrics.getRegisteredFontNames():
        return True
    reg_cands = [r"C:\Windows\Fonts\malgun.ttf",
                 os.path.join("assets", "report_kr.ttf"),
                 "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]
    bold_cands = [r"C:\Windows\Fonts\malgunbd.ttf",
                  os.path.join("assets", "report_kr.ttf")]
    reg = next((p for p in reg_cands if os.path.exists(p)), None)
    if not reg:
        return False
    bold = next((p for p in bold_cands if os.path.exists(p)), reg)
    try:
        pdfmetrics.registerFont(RLTTF("KR", reg))
        pdfmetrics.registerFont(RLTTF("KR-B", bold))
        pdfmetrics.registerFontFamily("KR", normal="KR", bold="KR-B",
                                      italic="KR", boldItalic="KR-B")
        return True
    except Exception:
        return False


def _fig_to_image(fig, width_mm, flowable_cls, align="CENTER"):
    """matplotlib figure → reportlab Image (지정 폭, 실제 종횡비 유지, 중앙 정렬)."""
    import io
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    import matplotlib.pyplot as plt
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    b.seek(0)
    iw, ih = ImageReader(b).getSize()   # 저장된 PNG 실제 픽셀 크기
    b.seek(0)
    w = width_mm * mm
    img = flowable_cls(b, width=w, height=w * (ih / iw))
    img.hAlign = align                   # 보고서 중앙 정렬
    return img


def _build_report_pdf(cart_df, include_dos=False, api_key="",
                      include_band=False, include_hull=False,
                      include_fatband=False):
    """관심목록 물질의 비교 차트·예측·추천을 담은 전문 PDF (reportlab).
    include_dos/include_band/include_hull/include_fatband: 물질별로 DOS·밴드+
    PDOS·볼록 껍질 위상도·궤도 투영 밴드(Fat Band)를 함께 그려 넣는다
    (모두 MP API 키 필요·느림)."""
    import io
    import datetime
    import matplotlib.pyplot as plt
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable,
                                    Image, KeepTogether)

    if cart_df.empty:
        return None
    _set_korean_font()
    has_kr = _register_report_fonts()
    F = "KR" if has_kr else "Helvetica"
    FB = "KR-B" if has_kr else "Helvetica-Bold"
    NAVY = colors.HexColor("#0a1f44")
    BLUE = colors.HexColor("#123c78")
    LINEC = colors.HexColor("#c9daf0")
    ROW = colors.HexColor("#eef4fb")
    cart_df = cart_df.reset_index(drop=True)
    _fcol = FORMULA_COL if FORMULA_COL in cart_df.columns else "material_id"
    CW = 174.0   # content width (mm)

    st_title = ParagraphStyle("t", fontName=FB, fontSize=19, textColor=NAVY,
                              leading=23, spaceAfter=2)
    st_sub = ParagraphStyle("s", fontName=F, fontSize=9.5,
                            textColor=colors.HexColor("#666666"), leading=13)
    st_h2 = ParagraphStyle("h2", fontName=FB, fontSize=13.5, textColor=BLUE,
                           leading=17, spaceBefore=8, spaceAfter=4)
    st_h3 = ParagraphStyle("h3", fontName=FB, fontSize=11.5, textColor=NAVY,
                           leading=15, spaceBefore=6, spaceAfter=2)
    st_body = ParagraphStyle("b", fontName=F, fontSize=9.3, leading=14,
                             textColor=colors.HexColor("#1a1a1a"))
    st_small = ParagraphStyle("sm", fontName=F, fontSize=8.2, leading=11,
                              textColor=colors.HexColor("#555555"))
    st_cell = ParagraphStyle("c", fontName=F, fontSize=8, leading=10.5)
    st_cellb = ParagraphStyle("cb", fontName=FB, fontSize=8, leading=10.5,
                              textColor=colors.white)

    def _name(r):
        return f"{r.get('material_id', '?')} ({r.get(_fcol, '?')})"

    def _fmt(v):
        if isinstance(v, (int, float)) and pd.notna(v):
            return f"{v:.4g}"
        return "—" if (v is None or (isinstance(v, float) and pd.isna(v))) \
            else str(v)

    # 예측 계산
    try:
        _feat = get_mobility_models()["n-type"]["meta"]["feat_cols"]
    except Exception:
        _feat = []
    preds = {}
    for _, r in cart_df.iterrows():
        vals = {c: (float(r[c]) if c in r and pd.notna(r[c]) else None)
                for c in _feat}
        try:
            preds[r["material_id"]] = predict_mobility_row(vals)
        except Exception:
            preds[r["material_id"]] = None

    story = []
    story.append(Paragraph("소재 스크리닝 종합 리포트", st_title))
    story.append(Paragraph(
        f"생성 {datetime.datetime.now():%Y-%m-%d %H:%M} · "
        f"관심목록 {len(cart_df)}개 물질 · Material Property Analyzer",
        st_sub))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.4, color=NAVY,
                            spaceAfter=8))

    # ── 1. 요약 표 ───────────────────────────────────────────────────────────
    story.append(Paragraph("1. 관심목록 요약", st_h2))
    sum_cols = [("material_id", "ID"), (_fcol, "화학식"),
                ("crystal_system", "결정계"),
                ("electronic_band_gap", "Eg(eV)"), ("e_fermi", "E_f"),
                ("S_mu_n", "S_mu_n"), ("S_mu_p", "S_mu_p"),
                ("energy_above_hull", "hull")]
    sum_cols = [(c, h) for c, h in sum_cols if c in cart_df.columns]
    head = [Paragraph(h, st_cellb) for _, h in sum_cols]
    data = [head]
    for _, r in cart_df.iterrows():
        data.append([Paragraph(_fmt(r.get(c)), st_cell) for c, _ in sum_cols])
    tbl = Table(data, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, LINEC),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    # ── 2. 비교 분석 (차트) ──────────────────────────────────────────────────
    story.append(Paragraph("2. 비교 분석", st_h2))
    names = [_name(r) for _, r in cart_df.iterrows()]
    n = len(cart_df)
    CHART_W = 152.0   # 비교 차트 폭(mm) — 페이지 폭보다 좁게 하여 중앙 배치

    if "electronic_band_gap" in cart_df.columns:
        fig, ax = plt.subplots(figsize=(7.2, max(1.8, 0.42 * n)))
        _b = cart_df["electronic_band_gap"].fillna(0)
        ax.barh(names, _b, color="#7f77dd")
        ax.invert_yaxis()
        ax.set_xlabel("밴드갭 (eV)")
        ax.set_title("밴드갭 비교", fontsize=12, fontweight="bold")
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(axis="x", ls=":", alpha=0.4)
        fig.tight_layout()
        story.append(_fig_to_image(fig, CW, Image))
        story.append(Spacer(1, 6))

    have_pred = [r["material_id"] for _, r in cart_df.iterrows()
                 if preds.get(r["material_id"])]
    if have_pred:
        fig, ax = plt.subplots(figsize=(7.2, max(2.0, 0.5 * n)))
        yy = np.arange(n)
        nv = [preds[r["material_id"]][0] if preds.get(r["material_id"]) else 0
              for _, r in cart_df.iterrows()]
        pv = [preds[r["material_id"]][2] if preds.get(r["material_id"]) else 0
              for _, r in cart_df.iterrows()]
        ax.barh(yy - 0.2, nv, 0.4, label="n형 예측", color="#2a78d6")
        ax.barh(yy + 0.2, pv, 0.4, label="p형 예측", color="#eb6834")
        ax.set_yticks(yy)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("예측 mobility 점수 (S_mu)")
        ax.set_title("예측 mobility 비교 (n형 vs p형)", fontsize=12,
                     fontweight="bold")
        ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
        ax.grid(axis="x", ls=":", alpha=0.4)
        fig.tight_layout()
        story.append(_fig_to_image(fig, CW, Image))
        story.append(Spacer(1, 6))

    # ── 속성 레이더(스파이더) 차트 — 물질 간 정규화 물성 비교 ──────────────
    _axes = [
        ("밴드갭", lambda r, pr: r.get("electronic_band_gap"), False),
        ("예측 mobility", lambda r, pr: (max(pr[0], pr[2]) if pr else None),
         False),
        ("안정성", lambda r, pr: r.get("energy_above_hull"), True),  # 낮을수록↑
        ("밀도", lambda r, pr: r.get("density"), False),
        ("전기음성도", lambda r, pr: r.get("mean_electronegativity"), False),
    ]
    _rows = list(cart_df.iterrows())
    _show = _rows[:6]     # 과밀 방지: 최대 6개
    # 물성별 값 수집
    raw = {lab: [] for lab, _, _ in _axes}
    for _, r in _show:
        pr = preds.get(r["material_id"])
        for lab, fn, _inv in _axes:
            v = fn(r, pr)
            raw[lab].append(v if (v is not None and pd.notna(v)) else np.nan)
    # 사용할 축: 유효값이 2개 이상인 축만
    use_axes = [(lab, inv) for (lab, _, inv) in _axes
                if np.isfinite(np.array(raw[lab], float)).sum() >= 2]
    if len(_show) >= 2 and len(use_axes) >= 3:
        import matplotlib.pyplot as plt
        labels = [lab for lab, _ in use_axes]
        # min-max 정규화 (안정성은 역방향)
        norm = {}
        for lab, inv in use_axes:
            arr = np.array(raw[lab], float)
            finite = arr[np.isfinite(arr)]
            lo, hi = finite.min(), finite.max()
            rng = (hi - lo) or 1.0
            vals = (arr - lo) / rng
            if inv:
                vals = 1 - vals
            vals = np.where(np.isfinite(vals), vals, 0.0)
            norm[lab] = 0.08 + 0.92 * vals    # 0 근처도 보이도록 하한
        ang = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        ang += ang[:1]
        # 범례를 차트 하단에 배치해 그래프와 겹치지 않게
        fig = plt.figure(figsize=(7.0, 7.4))
        axr = fig.add_axes([0.10, 0.24, 0.80, 0.66], polar=True)
        cmap = plt.get_cmap("tab10")
        for i, (_, r) in enumerate(_show):
            vals = [norm[lab][i] for lab in labels]
            vals += vals[:1]
            c = cmap(i % 10)
            axr.plot(ang, vals, color=c, lw=1.6, label=_name(r))
            axr.fill(ang, vals, color=c, alpha=0.08)
        axr.set_xticks(ang[:-1])
        axr.set_xticklabels(labels, fontsize=9)
        axr.set_yticks([0.25, 0.5, 0.75, 1.0])
        axr.set_yticklabels(["", "", "", ""], fontsize=7)
        axr.set_ylim(0, 1.05)
        axr.set_title("물질 속성 레이더 (관심목록 내 상대 비교, 정규화)",
                      fontsize=12, fontweight="bold", pad=22)
        axr.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06),
                   ncol=2, fontsize=7.5, framealpha=0.9,
                   handlelength=1.6, columnspacing=1.4)
        story.append(_fig_to_image(fig, 138.0, Image))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "※ 각 축은 관심목록 물질 내에서 0~1로 정규화한 상대값입니다 "
            "(안정성은 energy above hull이 낮을수록 높게 표시). "
            + ("물질이 많아 상위 6개만 표시했습니다." if len(_rows) > 6 else ""),
            st_small))

    story.append(PageBreak())

    # ── 3. 물질별 상세 ───────────────────────────────────────────────────────
    story.append(Paragraph("3. 물질별 상세 분석", st_h2))
    prop_rows = [("crystal_system", "결정계"),
                 ("electronic_band_gap", "밴드갭 (eV)"),
                 ("e_fermi", "페르미 에너지 (eV)"), ("vbm", "VBM (eV)"),
                 ("cbm", "CBM (eV)"),
                 ("energy_above_hull", "energy above hull (eV/atom)"),
                 ("formation_energy_per_atom", "형성에너지 (eV/atom)"),
                 ("density", "밀도 (g/cm³)"), ("S_mu_n", "S_mu_n (n형)"),
                 ("S_mu_p", "S_mu_p (p형)")]

    for _, r in cart_df.iterrows():
        block = [Paragraph(_name(r), st_h3)]
        _pr = [(lab, _fmt(r.get(c))) for c, lab in prop_rows
               if c in cart_df.columns]
        # 2열 배치 (좌/우)
        half = (len(_pr) + 1) // 2
        left, right = _pr[:half], _pr[half:]
        rows2 = []
        for i in range(half):
            l = left[i]
            rr = right[i] if i < len(right) else ("", "")
            rows2.append([Paragraph(l[0], st_cell), Paragraph(l[1], st_cell),
                          Paragraph(rr[0], st_cell), Paragraph(rr[1], st_cell)])
        pt = Table(rows2, colWidths=[CW * 0.28 * mm, CW * 0.22 * mm,
                                     CW * 0.28 * mm, CW * 0.22 * mm])
        pt.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, LINEC),
            ("BACKGROUND", (0, 0), (0, -1), ROW),
            ("BACKGROUND", (2, 0), (2, -1), ROW),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        block.append(pt)
        block.append(Spacer(1, 4))

        pr = preds.get(r["material_id"])
        gap = r.get("electronic_band_gap", np.nan)
        direct = r.get("is_gap_direct", 0) in (1, True, "1", "True")
        if pr:
            mn, pn, mp_, pp = pr
            better = "n형" if pn >= pp else "p형"
            block.append(Paragraph(
                f"<b>예측 Mobility (ML):</b>  n형 S_mu_n = {mn:.3f} "
                f"(상위 {100 - pn}%)  ·  p형 S_mu_p = {mp_:.3f} "
                f"(상위 {100 - pp}%)  →  <b>{better}</b> 캐리어 우세",
                st_body))
            recs = recommend_apps(gap, direct, pn, pp)[:4]
            if recs:
                block.append(Spacer(1, 2))
                block.append(Paragraph("활용 분야 추천", st_body))
                rr = [[Paragraph("분야", st_cellb),
                       Paragraph("적합도", st_cellb),
                       Paragraph("근거 / 스펙", st_cellb)]]
                for nm, sc, why, spec in recs:
                    rr.append([Paragraph(nm, st_cell),
                               Paragraph(f"{sc:.0f}", st_cell),
                               Paragraph(f"{why}<br/><font color='#888'>"
                                         f"{spec}</font>", st_cell)])
                rt = Table(rr, colWidths=[CW * 0.26 * mm, CW * 0.12 * mm,
                                          CW * 0.62 * mm], repeatRows=1)
                rt.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINEC),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, ROW]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
                block.append(rt)
        else:
            block.append(Paragraph("예측 모델을 사용할 수 없어 예측·추천을 "
                                   "생략합니다.", st_small))

        # DOS (옵션)
        if include_dos and api_key and "fetch_dos" in globals():
            try:
                d = fetch_dos(r["material_id"], api_key)
                if d is not None and d["gap"] > 1e-3:
                    e_arr, dens = d["energies"], d["densities"]
                    vbm, cbm = d["vbm"], d["cbm"]
                    fig, ax = plt.subplots(figsize=(7.2, 4.4))
                    # 가전자대/전도대 영역 색칠
                    ax.fill_between(e_arr, 0, dens, where=(e_arr <= vbm),
                                    color="#2563eb", alpha=0.20)
                    ax.fill_between(e_arr, 0, dens, where=(e_arr >= cbm),
                                    color="#dc2626", alpha=0.18)
                    ax.plot(e_arr, dens, color="black", lw=1.1,
                            label="Total DOS")
                    ax.axvline(vbm, color="#2563eb", lw=1.8, ls="--",
                               label=f"VBM ({vbm:.2f} eV)")
                    ax.axvline(cbm, color="#dc2626", lw=1.8, ls="--",
                               label=f"CBM ({cbm:.2f} eV)")
                    ax.set_xlim(vbm - 3, cbm + 3)
                    ax.set_ylim(bottom=0)
                    ax.set_xlabel("Energy (eV)")
                    ax.set_ylabel("Density of States (states/eV)")
                    ax.set_title(f"DOS — {r['material_id']}  "
                                 f"(Gap {d['gap']:.2f} eV)", fontsize=12,
                                 fontweight="bold")
                    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
                    ax.grid(axis="x", ls=":", alpha=0.4)
                    block.append(Spacer(1, 4))
                    block.append(_fig_to_image(fig, CW, Image))
            except Exception:
                pass

        # 밴드 구조 (옵션) — 전자 구조 분석과 동일한 BSDOSPlotter 그림
        if include_band and api_key \
                and "fetch_band_dos_figure" in globals():
            try:
                bfig, blabel = fetch_band_dos_figure(r["material_id"],
                                                     api_key)
                if bfig is not None:
                    block.append(Spacer(1, 4))
                    block.append(Paragraph(
                        f"<b>전자 구조 —</b> {blabel or '밴드 구조'}",
                        st_small))
                    block.append(_fig_to_image(bfig, CW, Image))
            except Exception:
                pass

        # 궤도 투영 밴드 (Fat Band, 옵션) — 전자 구조 분석 탭과 동일
        if include_fatband and api_key \
                and "fetch_fatband_from_mp" in globals():
            try:
                ffig, _fg, _fp = fetch_fatband_from_mp(r["material_id"],
                                                       api_key, "element")
                if ffig is not None:
                    _cap = ("원소 투영 포함" if _fp else
                            "투영 정보 없음 — 일반 밴드 (MP 제공 밴드 한계)")
                    block.append(Spacer(1, 4))
                    block.append(Paragraph(
                        f"<b>궤도 투영 밴드 (Fat Band) —</b> {_cap}", st_small))
                    block.append(_fig_to_image(ffig, CW, Image))
            except Exception:
                pass

        # 볼록 껍질 위상도 (옵션) — 물질의 화학계 열역학적 안정성
        if include_hull and api_key \
                and "fetch_phase_diagram_mpl" in globals():
            try:
                from pymatgen.core import Composition
                _els = [str(e) for e in
                        Composition(str(r.get(_fcol))).elements]
                hfig, n_stab, n_tot = fetch_phase_diagram_mpl(_els, api_key)
                if hfig is not None:
                    block.append(Spacer(1, 4))
                    block.append(Paragraph(
                        f"<b>볼록 껍질 위상도 —</b> {'-'.join(sorted(set(_els)))} "
                        f"화학계 · 안정상 {n_stab}개 / 전체 {n_tot}개",
                        st_small))
                    block.append(_fig_to_image(hfig, CW, Image))
                elif len(set(_els)) > 3:
                    block.append(Paragraph(
                        "※ 원소가 4종 이상이라 볼록 껍질 위상도를 2·3원계 "
                        "그림으로 표현할 수 없어 생략합니다.", st_small))
            except Exception:
                pass

        block.append(Spacer(1, 8))
        block.append(HRFlowable(width="100%", thickness=0.5, color=LINEC,
                                spaceAfter=6))
        story.append(KeepTogether(block))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "※ 예측 mobility와 적합도 점수는 머신러닝·규칙 기반 참고 지표입니다. "
        "광흡수계수·결함·도핑 한계·밴드 정렬·계면 등 실제 소자 성능을 좌우하는 "
        "요소는 별도 검증이 필요합니다.", st_small))

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(F, 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawCentredString(A4[0] / 2, 12 * mm, f"- {doc.page} -")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm,
                               "Material Property Analyzer")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm,
                            rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="소재 스크리닝 리포트")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()

with tab7:
    # ── (A) 다중 조건 가중 스코어링 랭킹 ────────────────────────────────────
    st.subheader(":material/leaderboard: 다중 조건 가중 랭킹")
    st.write("여러 물성에 가중치와 목표 방향을 지정하면, 필터링된 물질을 종합 "
             "점수(0~100)로 순위 매깁니다. 소재 후보를 빠르게 좁힐 수 있습니다.")

    _num_cols_all = filtered_df.select_dtypes(include="number").columns.tolist()
    _score_defaults = [c for c in ["electronic_band_gap", "S_mu_n", "S_mu_p",
                                   "energy_above_hull"] if c in _num_cols_all]
    _crit = st.multiselect("점수에 반영할 물성 선택", _num_cols_all,
                           default=_score_defaults)

    _goal_help = {"높을수록 좋음": "max", "낮을수록 좋음": "min",
                  "목표값에 가까울수록 좋음": "target"}
    weights, goals, targets = {}, {}, {}
    if _crit:
        st.markdown("**각 물성의 가중치·목표 방향**")
        for _c in _crit:
            g1, g2, g3 = st.columns([2, 2, 2])
            with g1:
                st.markdown(f"`{_c}`")
            with g2:
                weights[_c] = st.slider(f"가중치·{_c}", 0.0, 5.0, 1.0, 0.5,
                                        key=f"w_{_c}", label_visibility="collapsed")
            with g3:
                _gl = st.selectbox(f"방향·{_c}", list(_goal_help),
                                   key=f"g_{_c}", label_visibility="collapsed")
                goals[_c] = _goal_help[_gl]
            if goals[_c] == "target":
                targets[_c] = st.number_input(
                    f"목표값 · {_c}", value=float(
                        filtered_df[_c].median() if filtered_df[_c].notna().any()
                        else 0.0), key=f"t_{_c}")

    _rank_topn = st.number_input(
        "표시할 상위 개수 (0 = 전체)", min_value=0, max_value=100000,
        value=200, step=50,
        help="필터링된 물질 중 종합점수 상위 N개를 표시합니다. 0을 입력하면 "
             "조건을 만족하는 물질 전체를 표시합니다.")

    if _crit and st.button("랭킹 계산", icon=":material/calculate:",
                           type="primary"):
        base = filtered_df.dropna(subset=_crit).copy()
        if base.empty:
            st.warning("선택한 물성이 모두 있는 물질이 없습니다. 물성을 줄이거나 "
                       "필터를 완화하세요.")
        else:
            total = np.zeros(len(base))
            wsum = 0.0
            for _c in _crit:
                x = base[_c].astype(float)
                lo, hi = x.min(), x.max()
                rng = (hi - lo) or 1.0
                if goals[_c] == "max":
                    s = (x - lo) / rng
                elif goals[_c] == "min":
                    s = (hi - x) / rng
                else:  # target
                    s = 1 - (x - targets[_c]).abs() / rng
                    s = s.clip(lower=0)
                total += weights[_c] * s.to_numpy()
                wsum += weights[_c]
            base["종합점수"] = (total / (wsum or 1.0) * 100).round(1)
            _rank = base.sort_values("종합점수", ascending=False)
            _rcols = [c for c in ["material_id", FORMULA_COL, "종합점수",
                                  "crystal_system"] + _crit
                      if c and c in _rank.columns]
            _rank_full = _rank[_rcols].drop_duplicates().reset_index(drop=True)
            _rank_view = (_rank_full if int(_rank_topn) == 0
                          else _rank_full.head(int(_rank_topn)))
            st.session_state["last_rank"] = _rank_view
            st.caption(f"조건 만족 물질 {len(_rank_full):,}개 중 "
                       f"{len(_rank_view):,}개 표시")
            st.dataframe(_rank_view, use_container_width=True, height=420)

    if "last_rank" in st.session_state:
        _rv = st.session_state["last_rank"]
        _has_id = "material_id" in _rv.columns

        # (1) 상위 N개 일괄 담기
        _rc1, _rc2 = st.columns(2)
        with _rc1:
            _topn = st.number_input("상위 N개 관심목록에 담기", 1,
                                    max(1, len(_rv)), min(10, len(_rv)))
        with _rc2:
            st.write("")
            if st.button("상위 N개 담기", icon=":material/bookmark_add:",
                         use_container_width=True):
                _n = _add_to_cart(_rv["material_id"].head(int(_topn)).tolist()
                                  if _has_id else [])
                st.success(f"{_n}개 담김 (총 {len(st.session_state.cart)}개)")

        # (2) 원하는 물질만 직접 선택해 담기
        if _has_id:
            _rank_fmap = {}
            if FORMULA_COL and FORMULA_COL in _rv.columns:
                _rank_fmap = dict(zip(_rv["material_id"], _rv[FORMULA_COL]))
            _pick = st.multiselect(
                "원하는 물질만 직접 선택해 담기",
                _rv["material_id"].tolist(),
                format_func=lambda i: (f"{i} ({_rank_fmap.get(i, '?')})"
                                       if _rank_fmap else str(i)),
                key="rank_pick",
                help="랭킹 표에서 material_id를 확인해 원하는 물질만 고르세요. "
                     "순위와 상관없이 자유롭게 담을 수 있습니다.")
            if st.button("선택한 물질 담기", icon=":material/playlist_add:",
                         disabled=not _pick):
                _n = _add_to_cart(_pick)
                st.success(f"{_n}개 담김 (총 {len(st.session_state.cart)}개)")

        st.download_button(
            "랭킹 결과 Excel 다운로드", icon=":material/download:",
            data=_to_excel_bytes({"ranking": _rv}),
            file_name="material_ranking.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")

    # ── (B) 관심목록 (장바구니) 비교 & 리포트 ────────────────────────────────
    st.subheader(
        f":material/bookmark: 관심목록 비교 ({len(st.session_state.cart)}개)")
    if not st.session_state.cart:
        st.info("아직 담은 물질이 없습니다. '데이터 탐색' 탭 또는 위 랭킹에서 "
                "물질을 담아보세요.")
    else:
        cart_df = df[df["material_id"].isin(st.session_state.cart)].copy()
        _cmp_cols = [c for c in ["material_id", FORMULA_COL, "crystal_system",
                                 "electronic_band_gap", "e_fermi",
                                 "S_mu_n", "S_mu_p", "energy_above_hull",
                                 "formation_energy_per_atom", "density"]
                     if c and c in cart_df.columns]
        _extra = st.multiselect("비교 표에 추가할 물성",
                                [c for c in df.select_dtypes(include="number").columns
                                 if c not in _cmp_cols],
                                key="cart_extra")
        cart_show = cart_df[_cmp_cols + _extra].drop(
            columns=["_elements"], errors="ignore").reset_index(drop=True)
        st.dataframe(cart_show, use_container_width=True)

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            _rm = st.selectbox("제거할 물질", ["(선택)"] +
                               st.session_state.cart, key="cart_rm")
            if st.button("선택 제거", use_container_width=True,
                         disabled=_rm == "(선택)"):
                st.session_state.cart.remove(_rm)
                st.rerun()
        with rc2:
            if st.button("전체 비우기", icon=":material/delete:",
                         use_container_width=True):
                st.session_state.cart = []
                st.rerun()
        with rc3:
            st.download_button(
                "비교표 Excel", icon=":material/download:",
                data=_to_excel_bytes({"관심목록": cart_show}),
                file_name="watchlist.xlsx",
                mime="application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet", use_container_width=True)

        # 종합 리포트 (HTML) — 관심목록 + (있으면) 랭킹
        _tables = {"관심목록 비교": cart_show}
        if "last_rank" in st.session_state:
            _tables["가중 랭킹 Top"] = st.session_state["last_rank"]
        st.download_button(
            "표 리포트 다운로드 (HTML)", icon=":material/description:",
            data=_report_html("소재 스크리닝 리포트",
                              _tables).encode("utf-8"),
            file_name="material_report.html", mime="text/html")

        # ── 📘 종합 PDF 리포트 (차트 + 예측 + 추천, 물질별 페이지) ────────────
        st.markdown(":material/picture_as_pdf: **종합 PDF 리포트** — "
                    "비교 차트 + 물질별 예측·활용 추천")
        st.caption("아래 항목은 물질별로 Materials Project API를 호출해 "
                   "그림을 그립니다 (키 필요 · 물질 수에 비례해 느려짐).")
        _rp1, _rp2 = st.columns(2)
        with _rp1:
            _inc_dos = st.checkbox("DOS 그래프 포함", value=False,
                                   key="rep_dos")
            _inc_band = st.checkbox("밴드 구조 + PDOS 포함", value=False,
                                    key="rep_band")
        with _rp2:
            _inc_fat = st.checkbox("밴드 투영 (Fat Band) 포함", value=False,
                                   key="rep_fat")
            _inc_hull = st.checkbox("볼록 껍질 위상도 포함", value=False,
                                    key="rep_hull")
        _rep_key = ""
        if _inc_dos or _inc_band or _inc_hull or _inc_fat:
            try:
                _rep_key = st.secrets.get("MP_API_KEY", "")
            except Exception:
                _rep_key = ""
            _rep_key = (_rep_key or os.environ.get("MP_API_KEY", "")
                        or st.session_state.get("mp_api_key", ""))
            if not _rep_key:
                st.caption(":material/warning: API 키가 없어 DOS·밴드·위상도는 생략됩니다 "
                           "(DOS 탭에서 키를 저장하면 반영).")
            else:
                st.caption(":material/info: 볼록 껍질 위상도는 2·3원계 물질만 그림으로 "
                           "표현됩니다(4원계 이상은 자동 생략).")

        if st.button("PDF 리포트 생성", icon=":material/picture_as_pdf:",
                     type="primary"):
            with st.spinner("리포트 생성 중... (예측·차트·전자구조 렌더링)"):
                _pdf = _build_report_pdf(cart_df.copy(), _inc_dos, _rep_key,
                                         include_band=_inc_band,
                                         include_hull=_inc_hull,
                                         include_fatband=_inc_fat)
            if _pdf:
                st.download_button(
                    "PDF 다운로드", icon=":material/download:", data=_pdf,
                    file_name="material_report.pdf",
                    mime="application/pdf")
                st.success("리포트가 생성되었습니다. 위 버튼으로 내려받으세요.")
