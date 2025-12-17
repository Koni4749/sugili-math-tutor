import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 기본 페이지 설정 ---
st.set_page_config(page_title="수길이 - 수학의 길잡이", page_icon="📐")
st.title("🧑‍🏫 수길이: 수학의 길잡이")

# --- 2. API 키 설정 (secrets.toml 우선, 없으면 사이드바 입력) ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Google AI Studio API Key", type="password")

# --- 3. 시스템 프롬프트 (수길이의 페르소나 설정값) ---
# 이 내용은 변수에 담아두고 모델에 따라 다르게 주입합니다.
system_prompt_text = """
당신은 친절하고 실력 있는 수학 튜터 '수길이'입니다.
다음 원칙을 지켜 답변하세요:
1. LaTeX 수식을 사용하여 가독성 있게 작성하세요 (예: $x^2 + 2x$).
2. 풀이는 단계별(Step-by-step)로 논리적으로 설명하세요.
3. 설명 끝에는 "이해를 돕기 위해 유사한 문제를 준비했습니다."라며 예제를 하나 제시하세요.
4. 한국어로 정중하고 격려하는 어조를 사용하세요.
"""

# --- 4. 세션 상태 초기화 (대화 기록) ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 5. 채팅 화면 구현 ---
# 이전 대화 내용 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사이드바 이미지 업로더
uploaded_file = st.sidebar.file_uploader("문제 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# --- 6. 사용자 입력 처리 ---
if prompt := st.chat_input("질문을 입력하거나, 사진을 올리고 '풀어줘'라고 하세요."):
    if not api_key:
        st.error("API 키가 설정되지 않았습니다. 사이드바에 입력하거나 secrets.toml을 확인하세요.")
        st.stop()

    genai.configure(api_key=api_key)

    # 사용자 메시지 UI 표시
    st.chat_message("user").markdown(prompt)
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=200)
            
    # 대화 기록에 저장
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- [핵심] 모델 선택 및 프롬프트 구성 ---
    if uploaded_file:
        # [상황 A] 사진이 있음 -> 눈이 달린 Gemini 사용 (하루 20회 제한)
        selected_model = "gemini-2.5-flash-lite"
        
        # Gemini는 정석대로 system_instruction 파라미터 사용
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_prompt_text 
        )
        final_prompt = [prompt, image_input] # 이미지와 텍스트를 리스트로
        
    else:
        # [상황 B] 사진 없음 -> 사용량이 넉넉한 Gemma 사용 (무제한급)
        selected_model = "gemma-3-27b-it"
        
        # Gemma는 system_instruction을 지원하지 않으므로 비워둡니다.
        model = genai.GenerativeModel(
            model_name=selected_model
        )
        
        # 대신 질문 맨 앞에 페르소나 설정을 붙여서 보냅니다.
        final_prompt = system_prompt_text + "\n\n사용자 질문: " + prompt

    # --- 7. AI 응답 생성 및 스트리밍 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 1. 모델별 호출 방식 구분
            if selected_model == "gemma-3-27b-it":
                # Gemma: 채팅 기록(History) 없이 현재 질문에 집중 (오류 최소화)
                response = model.generate_content(final_prompt, stream=True)
            else:
                # Gemini: 이전 대화 기록(History) 포함하여 문맥 유지
                chat_history = []
                for msg in st.session_state.messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(final_prompt, stream=True)
            
            # 2. 스트리밍 응답 처리 (여기에 오류 수정 로직 적용됨!)
            for chunk in response:
                try:
                    # chunk.text에 접근할 때 '빈 상자(종료 신호)'면 에러가 나므로 예외 처리
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except Exception:
                    # 마지막 조각(finish_reason=1)이라 텍스트가 없으면 그냥 무시하고 넘어감
                    pass
            
            # 3. 최종 답변 표시
            message_placeholder.markdown(full_response)
            
            # 4. 기록 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            # 에러 메시지 친절하게 보여주기
            if "400" in str(e):
                st.error(f"요청 형식 오류 (400): {e}")
            elif "404" in str(e):
                st.error(f"모델을 찾을 수 없습니다: {selected_model}")
            elif "429" in str(e):
                st.error("🔒 무료 사용량이 초과되었습니다. (잠시 후 다시 시도하세요)")
            elif "Image" in str(e) or "multimodal" in str(e):
                st.error("현재 모델(Gemma)은 이미지를 볼 수 없습니다. (Gemini 전환 실패)")
            else:
                st.error(f"알 수 없는 오류가 발생했습니다: {e}")
