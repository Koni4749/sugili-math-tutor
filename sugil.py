import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 기본 설정 ---
st.set_page_config(page_title="수길이 - 수학의 길잡이", page_icon="📐")
st.title("🧑‍🏫 수길이: 수학의 길잡이")

# --- 2. API 키 설정 ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Google AI Studio API Key", type="password")

# --- 3. 시스템 프롬프트 (수길이의 페르소나) ---
# 이 내용은 변수에만 담아두고, 모델에 따라 다르게 주입합니다.
system_prompt_text = """
당신은 친절하고 실력 있는 수학 튜터 '수길이'입니다.
다음 원칙을 지켜 답변하세요:
1. LaTeX 수식을 사용하여 가독성 있게 작성하세요 (예: $x^2 + 2x$).
2. 풀이는 단계별(Step-by-step)로 논리적으로 설명하세요.
3. 설명 끝에는 "이해를 돕기 위해 유사한 문제를 준비했습니다."라며 예제를 하나 제시하세요.
"""

# --- 4. 세션 상태 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 5. 채팅 인터페이스 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

uploaded_file = st.sidebar.file_uploader("문제 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# --- 6. 사용자 입력 처리 ---
if prompt := st.chat_input("질문을 입력하거나, 사진을 올리고 '풀어줘'라고 하세요."):
    if not api_key:
        st.error("API 키가 필요합니다!")
        st.stop()

    genai.configure(api_key=api_key)

    # 사용자 메시지 표시
    st.chat_message("user").markdown(prompt)
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=200)
            
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- [핵심] 모델 선택 및 설정 분기 ---
    if uploaded_file:
        # [상황 A] 사진이 있음 -> Gemini (시스템 프롬프트 지원 O)
        selected_model = "gemini-2.5-flash-lite"
        ai_name = "Gemini"
        
        # Gemini는 정석대로 설정
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_prompt_text 
        )
        final_prompt = [prompt, image_input] # 이미지는 리스트로 묶어서
        
    else:
        # [상황 B] 사진 없음 -> Gemma (시스템 프롬프트 지원 X)
        selected_model = "gemma-3-27b-it"
        ai_name = "Gemma"
        
        # Gemma는 system_instruction 파라미터를 아예 빼야 합니다! (이게 오류 원인)
        model = genai.GenerativeModel(
            model_name=selected_model
        )
        
        # 대신 질문 앞에 페르소나를 '몰래' 붙여서 보냅니다.
        final_prompt = system_prompt_text + "\n\n사용자 질문: " + prompt

    # --- 7. AI 응답 생성 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # st.caption(f"🚀 {ai_name} 모델이 답변 중... (무료)") # 디버깅용

            # 히스토리 처리 (Gemma의 경우 히스토리 관리가 복잡해질 수 있어 1회성 질문으로 처리하거나 단순화)
            # 여기서는 오류 방지를 위해 '채팅 기록' 기능은 Gemini일 때만 완벽 지원하고
            # Gemma는 현재 질문에 집중하게 합니다. (가장 안전한 방법)
            
            if selected_model == "gemma-3-27b-it":
                # Gemma는 채팅 기록 없이 바로 생성 (오류 최소화)
                response = model.generate_content(final_prompt, stream=True)
            else:
                # Gemini는 채팅 기록 포함
                chat_history = []
                for msg in st.session_state.messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(final_prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            if "400" in str(e):
                st.error(f"설정 오류: {e}")
            elif "404" in str(e):
                st.error(f"모델을 찾을 수 없습니다: {selected_model}")
            elif "429" in str(e):
                st.error("사용량이 초과되었습니다.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
