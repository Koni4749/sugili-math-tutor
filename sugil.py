import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 디자인 및 기본 설정 ---
st.set_page_config(
    page_title="수길이 - 수학의 길잡이", 
    page_icon="📐",
    layout="centered"
)

# --- 2. 커스텀 CSS (디자인 디테일) ---
st.markdown("""
<style>
    .stChatMessage { font-family: 'Pretendard', sans-serif; }
    h1 { color: #2E86C1; }
    .stButton button { border-radius: 20px; }

    /* 업로더 디자인 수정 (한글화) */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span { display: none; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div > small { display: none; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "여기를 클릭해서 문제 또는 풀이 사진을 올리세요";
        display: block;
        font-weight: bold;
        font-size: 14px;
        color: #333;
        margin-bottom: 8px;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
        content: "JPG, PNG, WEBP (최대 200MB)";
        display: block;
        font-size: 11px;
        color: #888;
        margin-top: 8px;
    }
    [data-testid="stFileUploaderDropzone"] button {
        position: relative;
        color: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "파일 찾기";
        color: #333;
        position: absolute;
        left: 50%; top: 50%;
        transform: translate(-50%, -50%);
        font-size: 14px;
        font-weight: normal;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 사이드바 (설정 및 도구) ---
with st.sidebar:
    st.title("⚙️ 설정 및 도구")
    
    # API 키 처리
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("🔑 API Key 입력", type="password")
        if not api_key:
            st.info("API 키를 입력해야 수길이가 작동합니다.")
    
    st.divider()

    # [메인 모드 선택]
    st.subheader("🎓 학습 모드 선택")
    teaching_mode = st.radio(
        "수길이의 역할을 정해주세요:",
        ("🌟 친절한 풀이 선생님", "🕵️‍♀️ 꼼꼼한 첨삭 코치"),
        index=0
    )
    
    # [코치 모드일 때만 나타나는 서브 옵션]
    coach_option = "기본" # 기본값 초기화
    if teaching_mode == "🕵️‍♀️ 꼼꼼한 첨삭 코치":
        st.markdown("---") # 구분선
        st.caption("🧐 구체적으로 무엇을 도와드릴까요?")
        coach_option = st.radio(
            "코칭 방식 선택:",
            ("💡 힌트 및 오답 체크", "📚 관련 개념/원리 설명"),
            index=0,
            label_visibility="collapsed" # 라벨 숨김 (깔끔하게)
        )
    
    st.divider()
    
    # 대화 초기화 버튼
    if st.button("🧹 대화 내용 지우기", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# --- 4. 메인 화면 ---
st.title("🧑‍🏫 수길이: 수학의 길잡이")

# 모드별 안내 문구 동적 변경
if teaching_mode == "🌟 친절한 풀이 선생님":
    mode_guide = "문제를 주시면 **정답과 풀이 과정**을 시원하게 알려드려요!"
elif coach_option == "💡 힌트 및 오답 체크":
    mode_guide = "푼 식을 보여주세요. 정답 대신 **틀린 부분과 힌트**만 콕 집어드릴게요."
else:
    mode_guide = "문제 풀이보다는 **이 문제에 쓰인 수학 공식과 개념**을 설명해 드릴게요."

with st.expander(f"📘 현재 모드: {teaching_mode} ({'풀이' if teaching_mode.startswith('🌟') else coach_option})"):
    st.info(mode_guide)

# --- 5. 프롬프트 엔지니어링 (3단 분기) ---

# 공통 기본 설정
base_instruction = """
당신은 수학 교육을 전공한 대학생 멘토 '수길이'입니다.
오직 수학/과학 질문에만 답변하며, 수식은 LaTeX($$)를 사용해 가독성 있게 작성하세요.
한국어로 정중하고 격려하는 어조(해요체)를 사용하세요.
"""

# 1. 풀이 모드 (정답 O)
prompt_solver = base_instruction + """
**[Mode: Solver & Explainer]**
1. 사용자가 문제를 제시하면 **단계별(Step-by-step)로 논리적인 풀이 과정**을 제시하세요.
2. 최종적으로 **정답**을 명확히 알려주세요.
3. 답변 끝에는 학습자의 이해를 돕기 위해 비슷한 유형의 **유사 문제(Example)**를 하나 제안하세요.
"""

# 2. 코치 모드 - 힌트/체크 (정답 X)
prompt_coach_hint = base_instruction + """
**[Mode: Error Checker & Hint Giver]**
1. **절대 정답이나 전체 풀이를 먼저 알려주지 마세요.**
2. 사용자의 풀이를 분석하여 **오류(Error)나 논리적 비약**을 찾아내세요.
3. "이 부분 부호가 맞나요?", "여기서 어떤 공식을 적용해야 할까요?"처럼 **질문형 힌트**를 주세요.
4. 사용자가 스스로 다시 풀어보도록 격려하세요.
"""

# 3. 코치 모드 - 개념 설명 (정답 X, 개념 O)
prompt_coach_concept = base_instruction + """
**[Mode: Concept Explainer]**
1. **문제 풀이보다는 '원리' 설명에 집중하세요.** 정답을 바로 알려주지 마세요.
2. 이 문제를 풀기 위해 필요한 **핵심 수학 개념(Key Concept)이나 공식**이 무엇인지 파악해 설명해주세요. (예: 피타고라스 정리, 미분계수의 정의 등)
3. 개념 설명을 마친 후, "이제 이 개념을 문제에 어떻게 적용하면 될까요?"라고 물으며 사용자가 다시 문제로 돌아가게 유도하세요.
"""

# 최종 프롬프트 결정 로직
if teaching_mode == "🌟 친절한 풀이 선생님":
    current_system_prompt = prompt_solver
else:
    # 코치 모드일 때는 서브 옵션에 따라 결정
    if coach_option == "📚 관련 개념/원리 설명":
        current_system_prompt = prompt_coach_concept
    else:
        current_system_prompt = prompt_coach_hint


# --- 6. 세션 상태 관리 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 7. 채팅 내용 표시 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 이미지 업로더
uploaded_file = st.sidebar.file_uploader("📸 문제/풀이 사진 업로드", type=["jpg", "png", "jpeg", "webp"])

# --- 8. 사용자 입력 처리 ---
if prompt := st.chat_input("질문하거나, 내가 푼 식을 적어보세요..."):
    if not api_key:
        st.error("⚠️ API 키가 필요합니다!")
        st.stop()

    genai.configure(api_key=api_key)

    # 사용자 메시지 표시
    st.chat_message("user").markdown(prompt)
    
    # 이미지 처리
    image_input = None
    if uploaded_file:
        image_input = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image_input, width=300)
            
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- 9. Gemma 3 호출 ---
    model = genai.GenerativeModel(model_name="gemma-3-27b-it")

    # 프롬프트 조립
    combined_text = current_system_prompt + "\n\n[User Question]: " + prompt
    
    if image_input:
        final_prompt = [combined_text, image_input]
    else:
        final_prompt = combined_text

    # --- 10. AI 응답 생성 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # 로딩 멘트도 상황에 맞게!
        if teaching_mode == "🌟 친절한 풀이 선생님":
            loading_msg = "수길이가 풀이하는 중... 🧠"
        elif coach_option == "📚 관련 개념/원리 설명":
            loading_msg = "관련된 수학 개념을 찾는 중... 📖"
        else:
            loading_msg = "풀이 과정을 꼼꼼히 살펴보는 중... 🧐"

        with st.spinner(loading_msg):
            try:
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
                st.error("앗, 수길이가 잠시 생각을 멈췄어요. (새로고침 하거나 다시 질문해주세요)")
