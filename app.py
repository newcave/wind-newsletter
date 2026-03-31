import streamlit as st
import anthropic
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="풍력 모닝 뉴스레터",
    page_icon="🌬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');

/* 배경 - 사이드바 CSS 일절 건드리지 않음 */
.stApp { background: #0F172A; font-family: 'Noto Sans KR', sans-serif; }

/* Streamlit 기본 UI 제거 - 사이드바와 무관한 요소만 */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* Hero 카드 */
.nl-hero {
  background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #0F2027 100%);
  border: 1px solid rgba(38,166,154,0.25);
  border-radius: 16px;
  padding: 2rem 2.5rem;
  margin-bottom: 1.5rem;
}
.nl-hero-date {
  font-family: 'DM Mono', monospace;
  font-size: 12px; color: #26A69A;
  letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;
}
.nl-hero-title { font-size: 28px; font-weight: 700; color: #F8FAFC; margin: 0; }
.nl-hero-sub   { font-size: 14px; color: #94A3B8; margin-top: 6px; }

/* 메트릭 */
.metric-pill {
  background: #1E293B;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px; padding: 12px 20px; text-align: center;
}
.metric-pill .mp-val  { font-size: 26px; font-weight: 700; line-height: 1.1; }
.metric-pill .mp-label { font-size: 12px; color: #94A3B8; margin-top: 2px; }
.mp-total    .mp-val { color: #E2E8F0; }
.mp-domestic .mp-val { color: #60A5FA; }
.mp-global   .mp-val { color: #26A69A; }
.mp-policy   .mp-val { color: #FBBF24; }
.mp-biz      .mp-val { color: #A78BFA; }

/* 섹션 헤딩 */
.section-heading {
  font-size: 11px; font-weight: 500;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: #94A3B8; margin: 1.5rem 0 0.75rem;
  display: flex; align-items: center; gap: 8px;
}
.section-heading::after {
  content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.07);
}

/* 뉴스 카드 */
.news-card {
  background: #1E293B;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 1.1rem 1.4rem;
  margin-bottom: 10px; position: relative; overflow: hidden;
}
.news-card::before {
  content: ''; position: absolute;
  top: 0; left: 0; width: 3px; height: 100%;
}
.nc-domestic::before { background: #60A5FA; }
.nc-global::before   { background: #26A69A; }
.nc-policy::before   { background: #FBBF24; }
.nc-biz::before      { background: #A78BFA; }

.nc-header  { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.nc-badge   { font-size: 10px; font-weight: 500; padding: 3px 9px; border-radius: 20px; white-space: nowrap; flex-shrink: 0; }
.badge-domestic { background: rgba(96,165,250,0.15);  color: #60A5FA; }
.badge-global   { background: rgba(38,166,154,0.15);  color: #26A69A; }
.badge-policy   { background: rgba(251,191,36,0.15);  color: #FBBF24; }
.badge-biz      { background: rgba(167,139,250,0.15); color: #A78BFA; }

.nc-title   { font-size: 15px; font-weight: 500; color: #F1F5F9; line-height: 1.45; }
.nc-summary { font-size: 13px; color: #94A3B8; line-height: 1.65; margin-top: 6px; }
.nc-footer  { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
.nc-source  { font-family: 'DM Mono', monospace; font-size: 11px; color: #475569; }
.nc-link    { font-size: 12px; color: #26A69A; text-decoration: none; }

/* 빈 상태 */
.state-box {
  background: #1E293B; border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 3rem; text-align: center; color: #94A3B8;
}

/* 버튼 */
.stButton > button {
  background: #00796B !important; color: #fff !important;
  border: none !important; border-radius: 10px !important;
  font-family: 'Noto Sans KR', sans-serif !important;
  font-weight: 500 !important;
}
.stButton > button:hover { background: #26A69A !important; }
</style>
""", unsafe_allow_html=True)

# ── 상수 ───────────────────────────────────────────────────────────────────────
CATEGORIES = {
    "domestic": {"label": "국내 풍력", "badge": "badge-domestic", "card": "nc-domestic", "emoji": "🇰🇷"},
    "global":   {"label": "해외 풍력", "badge": "badge-global",   "card": "nc-global",   "emoji": "🌏"},
    "policy":   {"label": "정책·규제", "badge": "badge-policy",   "card": "nc-policy",   "emoji": "📋"},
    "biz":      {"label": "기업·투자", "badge": "badge-biz",      "card": "nc-biz",      "emoji": "💼"},
}

# ── API Key ────────────────────────────────────────────────────────────────────
def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return ""

# ── 뉴스 수집 ──────────────────────────────────────────────────────────────────
def fetch_news(api_key, categories, news_count):
    client = anthropic.Anthropic(api_key=api_key)
    date_str = datetime.now().strftime("%Y년 %m월 %d일")
    cat_desc = {
        "domestic": "국내(한국) 풍력 발전 관련 뉴스",
        "global":   "해외 풍력 발전 관련 뉴스 (유럽·미국·아시아 등)",
        "policy":   "풍력 관련 정책, 인허가, 규제 동향",
        "biz":      "풍력 기업 동향, 투자, M&A, 프로젝트 수주",
    }
    cats_str = "\n".join(f"- {c}: {cat_desc[c]}" for c in categories)
    prompt = f"""오늘({date_str}) 기준 최신 풍력 에너지 뉴스를 웹에서 검색해주세요.

수집 카테고리 (각 {news_count}개):
{cats_str}

마크다운·코드블록 없이 순수 JSON 배열만 반환:
[
  {{
    "category": "카테고리코드",
    "title": "뉴스 제목 (한국어)",
    "summary": "핵심 내용 2~3문장 요약 (한국어, 구체적 수치·사실 포함)",
    "source": "출처 매체명",
    "url": "기사 URL"
  }}
]"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        system="당신은 풍력 에너지 전문 뉴스 큐레이터입니다. 웹 검색으로 최신 뉴스를 수집·요약합니다.",
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "web-search-2025-03-05"},
    )
    text = " ".join(b.text for b in response.content if b.type == "text" and hasattr(b, "text"))
    text = re.sub(r"```(?:json)?|```", "", text).strip()
    s, e = text.find("["), text.rfind("]")
    if s == -1 or e == -1:
        raise ValueError("응답에서 JSON을 찾을 수 없습니다.")
    return json.loads(text[s:e+1])

# ── 렌더 함수 ──────────────────────────────────────────────────────────────────
def render_hero():
    now = datetime.now()
    wd  = {"Monday":"월","Tuesday":"화","Wednesday":"수","Thursday":"목",
           "Friday":"금","Saturday":"토","Sunday":"일"}.get(now.strftime("%A"), "")
    st.markdown(f"""
    <div class="nl-hero">
      <div class="nl-hero-date">🌬 WIND ENERGY — {now.strftime("%Y.%m.%d")} ({wd})</div>
      <div class="nl-hero-title">풍력 모닝 뉴스레터</div>
      <div class="nl-hero-sub">AI가 실시간으로 검색·요약한 최신 풍력 에너지 소식</div>
    </div>""", unsafe_allow_html=True)

def render_metrics(news):
    counts = {c: sum(1 for n in news if n.get("category") == c) for c in CATEGORIES}
    data = [
        ("전체",    len(news),           "mp-total"),
        ("국내 풍력", counts["domestic"], "mp-domestic"),
        ("해외 풍력", counts["global"],   "mp-global"),
        ("정책·규제", counts["policy"],   "mp-policy"),
        ("기업·투자", counts["biz"],      "mp-biz"),
    ]
    cols = st.columns(5)
    for col, (label, val, cls) in zip(cols, data):
        with col:
            st.markdown(f"""
            <div class="metric-pill {cls}">
              <div class="mp-val">{val}</div>
              <div class="mp-label">{label}</div>
            </div>""", unsafe_allow_html=True)

def render_card(item):
    cat = item.get("category", "domestic")
    cfg = CATEGORIES.get(cat, CATEGORIES["domestic"])
    link = f'<a class="nc-link" href="{item["url"]}" target="_blank">원문 보기 →</a>' if item.get("url") else ""
    st.markdown(f"""
    <div class="news-card {cfg['card']}">
      <div class="nc-header">
        <div class="nc-title">{item.get('title','')}</div>
        <span class="nc-badge {cfg['badge']}">{cfg['label']}</span>
      </div>
      <div class="nc-summary">{item.get('summary','')}</div>
      <div class="nc-footer">
        <span class="nc-source">{item.get('source','')}</span>
        {link}
      </div>
    </div>""", unsafe_allow_html=True)

def render_by_category(news, cats):
    for cat in cats:
        items = [n for n in news if n.get("category") == cat]
        if not items:
            continue
        cfg = CATEGORIES[cat]
        st.markdown(f'<div class="section-heading">{cfg["emoji"]} {cfg["label"]}</div>', unsafe_allow_html=True)
        for item in items:
            render_card(item)

# ── 사이드바 ───────────────────────────────────────────────────────────────────
def render_sidebar(secrets_key):
    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        st.divider()

        if secrets_key:
            st.success("🔐 API Key: Secrets 적용됨")
            api_key = secrets_key
        else:
            api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

        st.markdown("**뉴스 카테고리**")
        selected = [c for c in CATEGORIES
                    if st.checkbox(f"{CATEGORIES[c]['emoji']} {CATEGORIES[c]['label']}", value=True, key=f"cat_{c}")]

        count = st.slider("카테고리별 뉴스 수", 1, 5, 3)

        st.divider()
        btn = st.button("🔍 뉴스 가져오기", use_container_width=True)

        st.divider()
        st.markdown(
            "<div style='font-size:12px;color:#64748B;line-height:1.8;'>"
            "<b style='color:#94A3B8;'>📦 GitHub</b><br>"
            "<a href='https://github.com/newcave' style='color:#26A69A;'>github.com/newcave</a><br><br>"
            "<b style='color:#94A3B8;'>☁️ Streamlit Cloud</b><br>"
            "<a href='https://share.streamlit.io' style='color:#26A69A;'>share.streamlit.io</a>"
            "</div>", unsafe_allow_html=True)

    return api_key, selected, count, btn

# ── 메인 ───────────────────────────────────────────────────────────────────────
def main():
    render_hero()

    secrets_key = get_api_key()
    api_key, selected_cats, news_count, fetch_btn = render_sidebar(secrets_key)

    if "news"       not in st.session_state: st.session_state.news = []
    if "last_fetch" not in st.session_state: st.session_state.last_fetch = None

    if fetch_btn:
        if not api_key:
            st.error("⚠️ API Key를 입력하거나 Streamlit Secrets에 등록해주세요.")
        elif not selected_cats:
            st.warning("최소 1개 카테고리를 선택해주세요.")
        else:
            with st.spinner("🌬 AI가 최신 풍력 뉴스를 검색·요약 중입니다..."):
                try:
                    news = fetch_news(api_key, selected_cats, news_count)
                    st.session_state.news = news
                    st.session_state.last_fetch = datetime.now().strftime("%H:%M:%S")
                    st.success(f"✅ 총 {len(news)}개 뉴스를 불러왔습니다.")
                except anthropic.AuthenticationError:
                    st.error("❌ API Key가 유효하지 않습니다.")
                except Exception as ex:
                    st.error(f"❌ 오류: {ex}")

    if st.session_state.news:
        render_metrics(st.session_state.news)
        if st.session_state.last_fetch:
            st.caption(f"마지막 업데이트: {st.session_state.last_fetch}")
        view_opts = ["전체"] + [CATEGORIES[c]["label"] for c in selected_cats if c in CATEGORIES]
        view = st.radio("", view_opts, horizontal=True, label_visibility="collapsed")
        st.divider()
        if view == "전체":
            render_by_category(st.session_state.news, selected_cats)
        else:
            cat_key = next((k for k, v in CATEGORIES.items() if v["label"] == view), None)
            if cat_key:
                render_by_category(st.session_state.news, [cat_key])
    else:
        st.markdown("""
        <div class="state-box">
          <div style="font-size:36px;margin-bottom:12px;">🌬</div>
          <div style="font-size:16px;color:#94A3B8;margin-bottom:6px;">뉴스를 불러올 준비가 됐습니다</div>
          <div style="font-size:13px;">사이드바에서 카테고리를 선택하고 <b>뉴스 가져오기</b>를 클릭하세요</div>
        </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
