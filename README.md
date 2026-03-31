# 🌬 풍력 모닝 뉴스레터

Anthropic Claude API + Web Search로 매일 최신 풍력 에너지 뉴스를 자동 검색·요약하는 Streamlit 앱

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## 📁 파일 구성

```
wind-newsletter/
├── app.py                    # 메인 앱
├── requirements.txt          # 패키지 목록
├── .gitignore
├── .streamlit/
│   └── config.toml           # 다크 테마 설정
└── README.md
```

> ⚠️ `.streamlit/secrets.toml`은 로컬 전용입니다. `.gitignore`에 포함되어 있으므로 GitHub에 올라가지 않습니다.

---

## ☁️ Streamlit Cloud 배포 (무료)

### 1단계 — GitHub 업로드

```bash
git init
git add .
git commit -m "init: 풍력 뉴스레터"
git remote add origin https://github.com/<your-username>/wind-newsletter.git
git push -u origin main
```

### 2단계 — Streamlit Cloud 연결

1. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 로그인
2. **New app** → 저장소 선택 → Main file: `app.py`
3. **Advanced settings → Secrets** 에 아래 추가:

```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```

4. **Deploy** 클릭 → 완료!

---

## 💻 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

로컬 API Key 설정 (선택):
```toml
# .streamlit/secrets.toml  (gitignore 처리됨)
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```

---

## 기능

- 국내 풍력 / 해외 풍력 / 정책·규제 / 기업·투자 4개 카테고리
- Claude + Web Search 실시간 뉴스 검색·요약
- 카테고리별 필터 탭
- 다크 테마 카드 UI

## 기술 스택

| | |
|---|---|
| Frontend | Streamlit |
| AI | Anthropic Claude (`claude-opus-4-5`) |
| 검색 | Claude Web Search Tool |
| 배포 | Streamlit Cloud (무료) |
