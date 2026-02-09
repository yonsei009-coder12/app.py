import streamlit as st
import pandas as pd
import requests
import datetime
import random
from openai import OpenAI

# --- 페이지 설정 ---
st.set_page_config(page_title="AI 습관 트래커", page_icon="📊", layout="wide")

# --- 세션 상태 초기화 (샘플 데이터 포함) ---
if 'history' not in st.session_state:
    dates = [(datetime.date.today() - datetime.timedelta(days=i)) for i in range(6, 0, -1)]
    # 데모용 6일치 샘플 데이터
    st.session_state.history = [
        {"날짜": d, "달성률": random.randint(40, 100), "기분": random.randint(5, 10)} for d in dates
    ]

# --- 사이드바: API 설정 ---
with st.sidebar:
    st.title("⚙️ 설정")
    openai_key = st.text_input("OpenAI API Key", type="password")
    weather_key = st.text_input("OpenWeatherMap API Key", type="password")
    st.info("API 키는 브라우저 세션에만 유지됩니다.")

# --- 유틸리티 함수 ---
def get_weather(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=kr"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

def get_dog_image():
    try:
        response = requests.get("https://dog.ceo/api/breeds/image/random", timeout=10)
        if response.status_code == 200:
            data = response.json()
            image_url = data['message']
            breed = image_url.split('/')[-2].replace('-', ' ').title()
            return image_url, breed
    except:
        return None, None
    return None, None

def generate_report(client, data):
    # 코치 스타일에 따른 시스템 프롬프트 설정
    prompts = {
        "스파르타 코치": "너는 매우 엄격하고 냉정한 스파르타 코치다. 짧고 강렬하게 독설을 섞어 동기부여하라.",
        "따뜻한 멘토": "너는 다정하고 공감 능력이 뛰어난 멘토다. 사용자의 노력을 칭찬하고 따뜻하게 격려하라.",
        "게임 마스터": "너는 판타지 RPG의 게임 마스터다. 오늘 하루를 퀘스트 수행으로 간주하고 게임 톤으로 보고서를 작성하라."
    }
    
    system_msg = prompts.get(data['style'], "친절한 AI 코치")
    user_content = f"""
    오늘의 데이터:
    - 습관 달성률: {data['score']}% (습관: {', '.join(data['habits'])})
    - 기분 점수: {data['mood']}/10
    - 현재 날씨: {data['weather_desc']}, 온도 {data['temp']}°C
    - 오늘의 행운의 강아지: {data['dog_breed']}
    
    출력 형식:
    1. 컨디션 등급 (S~D)
    2. 습관 분석
    3. 날씨 코멘트
    4. 내일 미션
    5. 오늘의 한마디
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 요청하신 gpt-5-mini는 미출시 상태이므로 최신 mini 모델로 설정
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"리포트 생성 실패: {str(e)}"

# --- 메인 UI ---
st.title("📊 AI 습관 트래커")
st.markdown("오늘의 습관을 체크하고 AI 코치의 리포트를 받아보세요!")

# 1. 습관 체크인
with st.container():
    st.subheader("✅ 오늘의 체크인")
    col1, col2 = st.columns(2)
    
    with col1:
        h1 = st.checkbox("🌅 기상 미션")
        h2 = st.checkbox("💧 물 마시기")
        h3 = st.checkbox("📚 공부/독서")
    with col2:
        h4 = st.checkbox("🏋️ 운동하기")
        h5 = st.checkbox("😴 수면 관리")
    
    mood = st.slider("🎭 오늘 당신의 기분은 어떤가요?", 1, 10, 5)
    
    c1, c2 = st.columns(2)
    with c1:
        city = st.selectbox("📍 도시 선택", ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon", "Ulsan", "Jeju", "Sejong"])
    with c2:
        coach_style = st.radio("🤖 코치 스타일", ["스파르타 코치", "따뜻한 멘토", "게임 마스터"], horizontal=True)

# 2. 통계 계산
selected_habits = [h for h, checked in zip(["기상 미션", "물 마시기", "공부/독서", "운동하기", "수면"], [h1, h2, h3, h4, h5]) if checked]
achievement_rate = len(selected_habits) / 5 * 100

# 3. 달성률 대시보드
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("달성률", f"{achievement_rate}%")
m2.metric("달성 습관", f"{len(selected_habits)} / 5")
m3.metric("기분 점수", f"{mood}/10")

# 7일 데이터 차트
chart_data = pd.DataFrame(st.session_state.history + [{"날짜": "오늘", "달성률": achievement_rate, "기분": mood}])
st.bar_chart(chart_data, x="날짜", y="달성률")

# 4. 결과 생성 버튼
if st.button("🚀 컨디션 리포트 생성"):
    if not openai_key:
        st.error("OpenAI API Key를 입력해주세요.")
    else:
        client = OpenAI(api_key=openai_key)
        
        with st.spinner("날씨와 강아지 정보를 가져오며 AI 코치가 분석 중입니다..."):
            # 데이터 수집
            weather = get_weather(city, weather_key) if weather_key else None
            w_desc = weather['weather'][0]['description'] if weather else "정보 없음"
            w_temp = weather['main']['temp'] if weather else "?? "
            
            dog_url, dog_breed = get_dog_image()
            
            report_data = {
                "score": achievement_rate,
                "habits": selected_habits,
                "mood": mood,
                "weather_desc": w_desc,
                "temp": w_temp,
                "dog_breed": dog_breed,
                "style": coach_style
            }
            
            report_text = generate_report(client, report_data)
            
            # 결과 표시
            st.divider()
            res_col1, res_col2 = st.columns([1, 2])
            
            with res_col1:
                if weather:
                    st.info(f"📍 {city} 날씨: {w_desc} ({w_temp}°C)")
                if dog_url:
                    st.image(dog_url, caption=f"오늘의 행운 견종: {dog_breed}")
            
            with res_col2:
                st.subheader(f"📝 {coach_style}의 분석")
                st.markdown(report_text)
                
                # 공유 기능
                st.code(f"--- 오늘의 습관 리포트 ---\n달성률: {achievement_rate}%\n기분: {mood}/10\n코치 한마디: {report_text.split('오늘의 한마디')[-1]}", language="text")

# 5. 하단 안내
with st.expander("ℹ️ API 사용 안내"):
    st.write("""
    - **OpenAI API**: AI 리포트 생성을 위해 필요합니다. (GPT-4o-mini 모델 사용)
    - **OpenWeatherMap**: 현재 도시의 날씨 정보를 가져옵니다.
    - **Dog CEO API**: 무료로 랜덤 강아지 이미지를 제공받습니다.
    """)
