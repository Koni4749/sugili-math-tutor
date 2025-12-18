import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 디자인 및 기본 설정 ---
st.set_page_config(page_title="수길이 - 수학의 길잡이", page_icon="📐", layout="centered")

# --- 2. 커스텀 CSS ---
st.markdown("""
<style>
    .stChatMessage { font-family: 'Pretendard', sans-serif; }
    h1 { color: #2E86C1; }
    .stButton button { border-radius: 20px; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span { display: none; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div > small { display: none; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "여기를 클릭해서 문제/풀이 사진을 올리세요";
        display: block; font-weight: bold; font-size: 14px; color: #333; margin-bottom: 8px;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
        content: "JPG, PNG, WEBP (최대 200MB)";
        display: block; font-size: 11px; color: #888; margin-top: 8px;
    }
    [data-testid="stFileUploaderDropzone"] button { position: relative; color: transparent !important; }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "파일 찾기"; color: #333; position: absolute; left: 50%; top: 50%;
        transform: translate(-50%, -50%); font-size: 14px; font-weight: normal; white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 사이드바 ---
with st.sidebar:
    st.title("⚙️ 설정 및 도구")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("🔑 API Key 입력", type="password")
        if not api_key:
            st.info("API 키를 입력해야 수길이가 작동합니다.")
    
    st.divider()

    st.subheader("🎓 학습 모드")
    teaching_mode = st.radio("역할 선택:", ("🌟 친절한 풀이 선생님", "🕵️‍♀️ 꼼꼼한 첨삭 코치"), index=0)
    
    coach_option = "기본"
    if teaching_mode == "🕵️‍♀️ 꼼꼼한 첨삭 코치":
        st.caption("🧐 코칭 방식")
        coach_option = st.radio("코칭 방식:", ("💡 힌트 및 오답 체크", "📚 관련 개념/원리 설명"), index=0, label_visibility="collapsed")
    
    st.markdown("---")

    st.subheader("🧪 엔진 실험실")
    # 여기가 핵심입니다! 선생님이 발견한 모델로 교체!
    use_advanced_model = st.toggle("💎 히든 모델 (Gemini 2.5)", value=False)
    
    if use_advanced_model:
        st.success("🧪 **실험 모드 가동!**\nGemini 2.5 Audio-Dialog 모델을 테스트합니다.")
    else:
        st.info("🍀 **기본 모드 (Gemma 3)**\n안정적이고 무제한입니다.")

    st.divider()
    if st.button("🧹 대화 내용 지우기", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# --- 4. 메인 화면 ---
st.title("🧑‍🏫 수길이: 수학의 길잡이")

# 프롬프트 설정 (공통)
base_instruction = """
당신은 수학 교육을 전공한 대학생 멘토 '수길이'입니다.
오직 수학/과학 질문에만 답변하며, 수식은 LaTeX($$)를 사용해 가독성 있게 작성하세요.
한국어로 정중하고 격려하는 어조(해요체)를 사용하세요.

[⚠️ 필수 논리 점검 사항]
1. 부정 조건("존재하지 않는다", "아니다")을 주의 깊게 해석하세요.
2. 그래프 개형이나 특수성을 함부로 가정하지 마세요.
"""

prompt_solver = base_instruction + """
**[Mode: Solver & Explainer]**
1. 단계별(Step-by-step)로 논리적인 풀이 과정을 제시하세요.
2. 최종 정답을 명확히 알려주세요.
3. 답변 끝에 유사 문제(Example)를 하나 제안하세요.
"""

prompt_coach_hint = base_instruction + """
**[Mode: Error Checker & Hint Giver]**
1. **절대 정답을 먼저 알려주지 마세요.**
2. 사용자의 풀이에서 오류나 논리적 비약을 찾아 질문형 힌트를 주세요.
"""

prompt_coach_concept = base_instruction + """
**[Mode: Concept Explainer]**
1. 문제 풀이보다는 '원리'와 '핵심 공식' 설명에 집중하세요.
"""

if teaching_mode == "🌟 친절한 풀이 선생님":
    current_system_prompt = prompt_solver
else:
    if coach_option == "📚 관련 개념/원리 설명":
        current_system_prompt = prompt_coach_concept
    else:
        current_system_prompt = prompt_coach_hint

# --- 5. 세션 및 채팅 표시 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

uploaded_file = st.sidebar.file_uploader("📸 문제/풀이 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# --- 6. 입력 처리 및 모델 호출 ---
if prompt := st.chat_input("질문하거나, 내가 푼 식을 적어보세요..."):
    if not api_key:
        st.error("⚠️ API 키가 필요합니다!")
        st.stop()

    genai.configure(api_key=api_key)

    st.chat_message("user").markdown(prompt)
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=300)
            
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- [대망의 모델 호출부] ---
    try:
        if use_advanced_model:
            # 🚀 선생님이 발견하신 히든 모델!
            # (만약 이 이름이 코드에서 인식 안 되면 404 오류가 뜰 수 있습니다)
            model_name = "gemini-2.5-flash-native-audio-dialog"
            
            # 오디오 모델이라 system instruction이 잘 안 먹힐 수도 있지만 일단 시도
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=current_system_prompt
            )
        else:
            # 🍀 든든한 국밥 Gemma
            model_name = "gemma-3-27b-it"
            model = genai.GenerativeModel(model_name=model_name)
            # Gemma는 프롬프트를 텍스트에 합치기
            prompt = current_system_prompt + "\n\n[Question]: " + prompt

        # 프롬프트 구성
        if image_input:
            final_prompt = [prompt, image_input]
        else:
            final_prompt = prompt

        # --- 응답 생성 ---
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # 모델 이름 표시 (디버깅용)
            spinner_text = f"🧪 실험체({model_name}) 가동 중..." if use_advanced_model else "🍀 수길이(Gemma)가 풀이 중..."

            with st.spinner(spinner_text):
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

    except Exception as e:
        # 오류 발생 시 상세 메시지 출력
        if "404" in str(e):
            st.error(f"❌ 모델을 찾을 수 없대요: {model_name}")
            st.info("이 모델은 아직 API로 공개되지 않았거나, 이름이 다를 수 있습니다.")
        elif "400" in str(e):
            st.error(f"❌ 요청 오류: {e}")
            st.info("오디오 모델이라 텍스트/이미지 입력을 거부했을 수도 있어요.")
        else:
            st.error(f"오류 발생: {e}")
            st.write("잠시 끄고 Gemma 모드로 돌아가주세요 😭")
