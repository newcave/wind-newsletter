"""
YOLO11 실시간 객체 검출기 - 로컬 Streamlit 앱
실행: streamlit run app.py
"""

import streamlit as st
import numpy as np
import cv2
import time
from PIL import Image
from ultralytics import YOLO

try:
    import mss, mss.tools
    MSS_OK = True
except ImportError:
    MSS_OK = False

# ─────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────
st.set_page_config(
    page_title="YOLO11 실시간 검출기",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 YOLO11 실시간 객체 검출기")
st.caption("ultralytics YOLO11 · 로컬 전용 (웹캠 / 화면캡처 / 이미지)")

# ─────────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    model_choice = st.selectbox(
        "모델",
        ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt"],
        index=0,
        help="n=nano(최경량·추천), s=small, m=medium"
    )
    conf_thresh = st.slider("신뢰도 임계값", 0.10, 0.90, 0.40, 0.05)
    fps_cap     = st.slider("FPS 상한", 1, 30, 10, 1)
    show_labels = st.checkbox("라벨 표시", value=True)
    show_conf   = st.checkbox("신뢰도 표시", value=True)

    st.markdown("---")
    st.markdown("**모델 비교 (COCO mAP)**")
    st.markdown("| 모델 | mAP | 크기 |")
    st.markdown("|------|-----|------|")
    st.markdown("| yolo11n | 39.5% | ~5 MB |")
    st.markdown("| yolo11s | 47.0% | ~19 MB |")
    st.markdown("| yolo11m | 51.5% | ~38 MB |")

    st.markdown("---")
    if not MSS_OK:
        st.warning("⚠️ 화면캡처 불가\n`pip install mss` 실행하세요")

# ─────────────────────────────────────────────────
# 모델 로드 (캐시)
# ─────────────────────────────────────────────────
@st.cache_resource
def load_model(name: str):
    return YOLO(name)

with st.spinner(f"모델 로딩 중: {model_choice} ..."):
    model = load_model(model_choice)

# ─────────────────────────────────────────────────
# 유틸 - 단일 프레임 추론
# ─────────────────────────────────────────────────
def detect_frame(frame_bgr: np.ndarray) -> tuple[np.ndarray, list]:
    """BGR 이미지를 받아 (annotated_BGR, detections_list) 반환"""
    results = model.predict(
        source=frame_bgr,
        conf=conf_thresh,
        verbose=False,
        show_labels=show_labels,
        show_conf=show_conf,
    )
    annotated = results[0].plot()          # BGR numpy
    dets = []
    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        name   = model.names[cls_id]
        conf   = float(box.conf[0])
        dets.append({"클래스": name, "신뢰도": f"{conf:.1%}"})
    return annotated, dets

# ─────────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────────
tab_cam, tab_screen, tab_image = st.tabs(
    ["📷 웹캠 실시간", "🖥️ 화면 캡처 실시간", "🖼️ 이미지 업로드"]
)

# ══════════════════════════════════════════════════
# TAB 1 ─ 웹캠 실시간
# ══════════════════════════════════════════════════
with tab_cam:
    cam_idx = st.number_input("카메라 인덱스", 0, 5, 0, 1)
    col_start, col_stop = st.columns([1, 1])
    start_cam = col_start.button("▶ 시작", key="cam_start")
    stop_cam  = col_stop.button("⏹ 중지", key="cam_stop")

    frame_box  = st.empty()
    info_box   = st.empty()
    fps_box    = st.empty()

    if "cam_running" not in st.session_state:
        st.session_state.cam_running = False
    if start_cam:
        st.session_state.cam_running = True
    if stop_cam:
        st.session_state.cam_running = False

    if st.session_state.cam_running:
        cap = cv2.VideoCapture(int(cam_idx), cv2.CAP_DSHOW)
        if not cap.isOpened():
            st.error("카메라를 열 수 없습니다. 인덱스를 확인하세요.")
            st.session_state.cam_running = False
        else:
            interval = 1.0 / fps_cap
            while st.session_state.cam_running:
                t0 = time.time()
                ret, frame = cap.read()
                if not ret:
                    st.warning("프레임 읽기 실패")
                    break

                annotated, dets = detect_frame(frame)
                frame_box.image(annotated, channels="BGR", use_container_width=True)

                if dets:
                    info_box.dataframe(dets, use_container_width=True)
                else:
                    info_box.info("검출 없음")

                elapsed = time.time() - t0
                fps_box.caption(f"처리 FPS: {1/elapsed:.1f}")
                leftover = interval - elapsed
                if leftover > 0:
                    time.sleep(leftover)

            cap.release()

# ══════════════════════════════════════════════════
# TAB 2 ─ 화면 캡처 실시간
# ══════════════════════════════════════════════════
with tab_screen:
    if not MSS_OK:
        st.error("`mss` 라이브러리가 없습니다. `pip install mss` 후 재시작하세요.")
    else:
        st.markdown("모니터 번호를 선택하거나 캡처 영역을 직접 지정하세요.")

        capture_mode = st.radio("캡처 모드", ["전체 화면", "영역 지정"], horizontal=True)

        if capture_mode == "전체 화면":
            monitor_idx = st.number_input("모니터 번호 (1=주모니터)", 1, 4, 1, 1)
        else:
            c1, c2, c3, c4 = st.columns(4)
            cap_left   = c1.number_input("Left(px)",   0, 3840, 0)
            cap_top    = c2.number_input("Top(px)",    0, 2160, 0)
            cap_width  = c3.number_input("Width(px)",  100, 3840, 1280)
            cap_height = c4.number_input("Height(px)", 100, 2160, 720)

        col_s, col_e = st.columns([1, 1])
        start_scr = col_s.button("▶ 시작", key="scr_start")
        stop_scr  = col_e.button("⏹ 중지", key="scr_stop")

        scr_frame_box = st.empty()
        scr_info_box  = st.empty()
        scr_fps_box   = st.empty()

        if "scr_running" not in st.session_state:
            st.session_state.scr_running = False
        if start_scr:
            st.session_state.scr_running = True
        if stop_scr:
            st.session_state.scr_running = False

        if st.session_state.scr_running:
            interval = 1.0 / fps_cap
            with mss.mss() as sct:
                if capture_mode == "전체 화면":
                    monitor = sct.monitors[int(monitor_idx)]
                else:
                    monitor = {
                        "left": int(cap_left), "top": int(cap_top),
                        "width": int(cap_width), "height": int(cap_height)
                    }

                while st.session_state.scr_running:
                    t0 = time.time()
                    screenshot = np.array(sct.grab(monitor))           # BGRA
                    frame_bgr  = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

                    annotated, dets = detect_frame(frame_bgr)
                    scr_frame_box.image(annotated, channels="BGR", use_container_width=True)

                    if dets:
                        scr_info_box.dataframe(dets, use_container_width=True)
                    else:
                        scr_info_box.info("검출 없음")

                    elapsed = time.time() - t0
                    scr_fps_box.caption(f"처리 FPS: {1/elapsed:.1f}")
                    leftover = interval - elapsed
                    if leftover > 0:
                        time.sleep(leftover)

# ══════════════════════════════════════════════════
# TAB 3 ─ 이미지 업로드
# ══════════════════════════════════════════════════
with tab_image:
    uploaded = st.file_uploader("이미지 업로드 (jpg / png)", type=["jpg","jpeg","png"])

    if uploaded:
        pil_img = Image.open(uploaded).convert("RGB")
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        col_orig, col_result = st.columns(2)
        with col_orig:
            st.subheader("원본")
            st.image(pil_img, use_container_width=True)

        with st.spinner("추론 중..."):
            annotated, dets = detect_frame(img_bgr)

        with col_result:
            st.subheader(f"검출 결과 ({len(dets)}개)")
            st.image(annotated, channels="BGR", use_container_width=True)

        if dets:
            st.dataframe(dets, use_container_width=True)
        else:
            st.info("검출된 객체가 없습니다. 신뢰도 임계값을 낮춰보세요.")
