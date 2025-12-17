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

# --- 3. 시스템 프롬프트 (수길이 페르소나) ---
# Gemma는 시스템 설정 칸이 없으므로, 질문 앞에 붙일 텍스트로 준비합니다.
system_prompt_text = """
당신은 친절하고 실력 있는 수학 튜터 '수길이'입니다.
다음 원칙을 지켜 답변하세요:
1. LaTeX 수식을 사용하여 가독성 있게 작성하세요 (예: $x^2 + 2x$).
2. 풀이는 단계별(Step-by-step)로 논리적으로 설명하세요.
3. 설명 끝에는 "이해를 돕기 위해 유사한 문제를 준비했습니다."라며 예제를 하나 제시하세요.
4. 한국어로 정중하고 격려하는 어조를 사용하세요.
"""

# --- 4. 세션 상태 (대화 기록) ---
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
        st.error("API 키가 필요합니다! 사이드바를 확인해주세요.")
        st.stop()

    genai.configure(api_key=api_key)

    # UI에 사용자 질문 표시
    st.chat_message("user").markdown(prompt)
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=200)
            
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- [핵심] Gemma 3 단일 모델 설정 ---
    # 이제 복잡한 분기 처리 없이 Gemma 하나로 통일합니다!
    model = genai.GenerativeModel(model_name="gemma-3-27b-it")

    # 프롬프트 구성 (페르소나 주입 + 질문 + 이미지)
    combined_text = system_prompt_text + "\n\n사용자 질문: " + prompt
    
    if image_input:
        # 이미지가 있으면 리스트로 묶어서 전달
        final_prompt = [combined_text, image_input]
    else:
        # 텍스트만 있으면 문자열 그대로 전달
        final_prompt = combined_text

    # --- 7. AI 응답 생성 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Gemma에게 질문 전송 (이미지 포함 가능!)
            response = model.generate_content(final_prompt, stream=True)
            
            # 스트리밍 응답 처리 (오류 방지 로직 포함)
            for chunk in response:
                try:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except Exception:
                    pass # 마지막 빈 조각은 무시
            
            message_placeholder.markdown(full_response)
            
            # 대화 기록 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
