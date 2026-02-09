import streamlit as st
import pandas as pd
import requests
import datetime
from openai import OpenAI
from streamlit_calendar import calendar

# --- 설정 및 초기화 ---
st.set_page_config(page_title="AI Habit Master", page_icon="📊", layout="wide")

# 라이브러리 설치 안내: pip install streamlit streamlit-calendar openai requests pandas
if 'habit_data' not in st.session_state:
    st.session_state.habit_data = [] # {start: '2023-10-01', title: '80%', color: '#ff4b4b'} 형식

# --- 사이드바 API 설정 ---
with st.sidebar:
    st.header("🔑 API Settings")
    openai_key = st.text_input("OpenAI API Key", type="password")
    weather_key = st.text_input("OpenWeatherMap Key", type="password")
    st.divider()
    coach_style = st.selectbox("🤖 코치 선택", ["스파르타", "따뜻한 멘토", "게임 마스터"])
    city = st.text_input("📍 도시 입력", value="Seoul")

# --- 유틸리티 함수 ---
def get_weather_info(city, key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric&lang=kr"
        res = requests.get(url, timeout=5).json()
        return {"temp": res['main']['temp'], "desc": res['weather'][0]['description'], "main": res['weather'][0]['main']}
    except: return None

def get_dog_data():
    try:
        res = requests.get("https://dog.ceo/api/breeds/image/random", timeout=5).json()
        breed = res['message'].split('/')[-2].replace('-', ' ')
        return {"url": res['message'], "breed": breed}
    except: return None

# --- 메인 레이아웃 ---
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("✅ 오늘의 습관 체크인")
    
    # 날씨 기반 AI 추천 미션 (API 연동)
    weather = get_weather_info(city, weather_key)
    suggested_habit = "스트레칭 하기" # 기본값
    if weather:
        if "Rain" in weather['main']: suggested_habit = "창밖 보며 명상하기"
        elif weather['temp'] > 25: suggested_habit = "시원한 물 2리터 마시기"
        st.caption(f"☁️ 현재 {city} 날씨({weather['desc']})에 맞춘 추천 미션: **{suggested_habit}**")

    # 습관 입력 폼
    with st.form("habit_form"):
        h1 = st.checkbox("🌅 미라클 모닝")
        h2 = st.checkbox(f"✨ {suggested_habit} (오늘의 미션)")
        h3 = st.checkbox("📖 독서/공부 30분")
        h4 = st.checkbox("💪 운동/산책")
        h5 = st.checkbox("🥗 건강한 식단")
        mood = st.select_slider("🎭 오늘 컨디션", options=range(1, 11), value=5)
        submitted = st.form_submit_button("기록 저장 및 AI 분석")

    if submitted:
        if not openai_key:
            st.warning("분석을 위해 OpenAI API 키가 필요합니다.")
        else:
            # 데이터 계산
            habits = [h1, h2, h3, h4, h5]
            score = sum(habits) * 20
            dog = get_dog_data()
            
            # AI 리포트 생성 (데이터 통합)
            client = OpenAI(api_key=openai_key)
            prompt = f"""
            사용자 정보:
            - 오늘 습관 달성률: {score}%
            - 컨디션: {mood}/10
            - 날씨: {weather['desc'] if weather else '알 수 없음'}
            - 오늘의 강아지: {dog['breed'] if dog else '믹스견'}
            - 코치 스타일: {coach_style}
            
            요청사항:
            1. 강아지 품종의 특징과 날씨를 엮어서 오늘 하루를 분석해줘.
            2. '컨디션 등급(S-D)'을 매겨줘.
            3. {coach_style} 말투로 내일의 독한/따뜻한 미션을 하나 제안해줘.
            """
            
            with st.spinner("AI가 오늘의 데이터를 조합 중..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_comment = response.choices[0].message.content
                
                # 달력 데이터 저장
                new_event = {
                    "title": f"{score}%",
                    "start": datetime.date.today().isoformat(),
                    "color": "#00ff00" if score > 70 else "#ff4b4b"
                }
                st.session_state.habit_data.append(new_event)
                
                # 결과 출력
                st.success("오늘의 기록이 저장되었습니다!")
                st.markdown(ai_comment)
                if dog: st.image(dog['url'], caption=f"오늘의 파트너: {dog['breed']}", width=300)

with col_right:
    st.subheader("📅 습관 달력")
    
    # 달력 설정
    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"},
        "initialView": "dayGridMonth",
        "selectable": True,
    }
    
    # 달력 렌더링
    calendar(events=st.session_state.habit_data, options=calendar_options)
    
    st.divider()
    st.subheader("📈 통계")
    if st.session_state.habit_data:
        df = pd.DataFrame(st.session_state.habit_data)
        st.info(f"지금까지 총 {len(df)}일간 습관을 트래킹했습니다. 계속 정진하세요!")
    else:
        st.write("아직 기록이 없습니다. 왼쪽에서 첫 체크인을 완료하세요!")
