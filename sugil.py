import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 기본 설정 및 디자인 ---
# 브라우저 탭 이름도 '수학의 길잡이'로 통일했습니다.
st.set_page_config(page_title="수길이 - 수학의 길잡이", page_icon="📐")

# 메인 타이틀 변경
st.title("🧑‍🏫 수길이: 수학의 길잡이")
# 기존의 st.caption("...") 코드는 삭제했습니다.

# 사이드바에서 API 키 입력받기
api_key = st.sidebar.text_input("Google AI Studio API Key를 입력하세요", type="password")

# --- 2. 시스템 프롬프트 (수길이의 페르소나) ---
system_prompt = """
당신은 친절하고 실력 있는 수학 튜터 '수길이'입니다.
다음 원칙을 지켜 답변하세요:
1. LaTeX 수식을 사용하여 가독성 있게 작성하세요 (예: $x^2 + 2x$).
2. 풀이는 단계별(Step-by-step)로 논리적으로 설명하세요.
3. 설명이 끝난 후에는 반드시 "이해를 돕기 위해 유사한 문제를 준비했습니다. 한번 풀어보시겠어요?"라고 말하고, 비슷한 난이도의 예제를 하나 제시하세요.
4. 한국어로 정중하고 격려하는 어조를 사용하세요.
"""

# --- 3. 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 채팅 인터페이스 구현 ---
# 기존 대화 내용 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 이미지 업로더
uploaded_file = st.sidebar.file_uploader("문제 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하거나, 사진을 올리고 '풀어줘'라고 하세요."):
    if not api_key:
        st.error("왼쪽 사이드바에 Google API Key를 먼저 입력해주세요!")
        st.stop()

    # Gemini 설정
    genai.configure(api_key=api_key)
    
    # 모델 설정 (최신 모델 gemini-2.5-flash 적용됨)
    model = genai.GenerativeModel(
        model_name="gemini-exp-1206",
        system_instruction=system_prompt
    )

    # 사용자 메시지 화면 표시
    st.chat_message("user").markdown(prompt)
    
    # 이미지 처리
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, caption="업로드한 문제", use_column_width=False, width=200)

    # 대화 기록 저장 (UI용)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- 5. Gemini API 호출 준비 ---
    chat_history = []
    for msg in st.session_state.messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    current_parts = [prompt]
    if image_input:
        current_parts.append(image_input)

    # --- 6. AI 응답 생성 (Stream) ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(current_parts, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # AI 응답 기록 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")




