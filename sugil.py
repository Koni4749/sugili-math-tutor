import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 기본 설정 ---
st.set_page_config(page_title="수길이 (Gemma 실험실)", page_icon="🧪")
st.title("🧪 수길이: Gemma 3 시력 테스트 중")
st.warning("⚠️ 이 버전은 실험용입니다! Gemma가 사진을 볼 수 있는지 테스트합니다.")

# --- 2. API 키 설정 ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Google AI Studio API Key", type="password")

# --- 3. 시스템 프롬프트 (꼼수용) ---
system_prompt_text = """
당신은 친절하고 실력 있는 수학 튜터 '수길이'입니다.
LaTeX 수식을 사용해 단계별로 설명하고, 마지막엔 유사 문제를 제안하세요.
"""

# --- 4. 세션 상태 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 5. 채팅 화면 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

uploaded_file = st.sidebar.file_uploader("문제 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# --- 6. 입력 처리 ---
if prompt := st.chat_input("사진을 올리고 질문해보세요!"):
    if not api_key:
        st.error("API 키가 필요합니다!")
        st.stop()

    genai.configure(api_key=api_key)

    # UI 표시
    st.chat_message("user").markdown(prompt)
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=200, caption="Gemma에게 이 사진을 보냅니다...")
            
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- [실험 핵심] 무조건 Gemma만 사용! ---
    selected_model = "gemma-3-27b-it"  # 타협은 없다. 무조건 Gemma!
    
    # Gemma는 시스템 프롬프트 지원 안 하므로 비워서 생성
    model = genai.GenerativeModel(model_name=selected_model)

    # 프롬프트 구성 (시스템 설정 + 질문 + 이미지)
    if uploaded_file:
        # 이미지가 있으면 리스트에 담아서 보냄 (멀티모달 시도)
        # 꼼수: 텍스트 부분에 페르소나를 섞어서 보냄
        combined_text = system_prompt_text + "\n\n사용자 질문: " + prompt
        final_prompt = [combined_text, image_input] 
    else:
        # 텍스트만 있을 때
        final_prompt = system_prompt_text + "\n\n사용자 질문: " + prompt

    # --- 7. 응답 생성 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 스트리밍으로 응답 요청
            response = model.generate_content(final_prompt, stream=True)
            
            for chunk in response:
                try:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except Exception:
                    pass
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # 성공했다면 축하 메시지!
            if uploaded_file and full_response:
                st.balloons()
                st.success("🎉 대박! Gemma 3가 이미지를 인식했습니다! 이제 완전 무제한입니다!")

        except Exception as e:
            # 실패하면 원인 분석 메시지 출력
            st.error("🧪 실험 실패!")
            if "400" in str(e) or "Media not supported" in str(e) or "multimodal" in str(e):
                st.error(f"결론: '{selected_model}' 모델은 역시 이미지를 볼 수 없네요. (텍스트 전용)")
                st.info("👉 다시 이전의 '하이브리드 코드(Gemma+Gemini)'로 복구해주세요.")
            else:
                st.error(f"오류 내용: {e}")
