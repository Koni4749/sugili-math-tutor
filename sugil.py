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

    # [핵심] 모드 선택 기능 추가
    st.subheader("🎓 학습 모드 선택")
    teaching_mode = st.radio(
        "수길이의 교육 방식을 선택하세요:",
        ("🌟 친절한 풀이 선생님", "🕵️‍♀️ 꼼꼼한 첨삭 코치"),
        index=0,
        help="풀이 선생님: 정답과 과정을 알려줍니다.\n첨삭 코치: 틀린 곳만 찾아서 힌트를 줍니다."
    )
    
    st.divider()
    
    # 대화 초기화 버튼
    if st.button("🧹 대화 내용 지우기", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# --- 4. 메인 화면 ---
st.title("🧑‍🏫 수길이: 수학의 길잡이")

# 모드에 따른 안내 문구 변경
if teaching_mode == "🌟 친절한 풀이 선생님":
    mode_guide = "문제를 보여주시면 **단계별 풀이와 정답**을 친절하게 알려드려요!"
else:
    mode_guide = "본인이 푼 식을 보여주세요. **정답 대신 틀린 부분**을 찾아드릴게요!"

with st.expander(f"📘 현재 모드: {teaching_mode} (클릭해서 설명 보기)"):
    st.info(mode_guide)

# --- 5. 프롬프트 엔지니어링 (모드별 분기) ---

# 공통 기본 설정
base_instruction = """
당신은 수학 교육을 전공한 대학생 멘토 '수길이'입니다.
오직 수학/과학 질문에만 답변하며, 수식은 LaTeX($$)를 사용해 가독성 있게 작성하세요.
한국어로 정중하고 격려하는 어조(해요체)를 사용하세요.
"""

# 모드 1: 풀이 모드 (기존)
prompt_solver = base_instruction + """
**[Mode: Solver & Explainer]**
1. 사용자가 문제를 제시하면 **단계별(Step-by-step)로 논리적인 풀이 과정**을 제시하세요.
2. 최종적으로 **정답**을 명확히 알려주세요.
3. 답변 끝에는 학습자의 이해를 돕기 위해 비슷한 유형의 **유사 문제(Example)**를 하나 제안하세요.
"""

# 모드 2: 첨삭 모드 (신규)
prompt_coach = base_instruction + """
**[Mode: Error Checker & Coach]**
1. **절대 먼저 정답이나 전체 풀이를 알려주지 마세요.** (가장 중요)
2. 사용자가 입력한 식이나 풀이 과정(이미지/텍스트)을 분석하여 **오류(Error)나 논리적 허점**을 찾아내세요.
3. "이 부분에서 부호가 틀린 것 같아요", "여기서는 어떤 공식을 써야 할까요?"와 같이 **질문과 힌트**를 통해 스스로 깨닫게 유도하세요.
4. 만약 사용자가 풀이 없이 문제만 줬다면, "먼저 어떻게 풀었는지 식을 보여주시겠어요?"라고 역으로 질문하여 참여를 유도하세요.
5. 학생이 개념을 헷갈려하면 그 **개념에 대해서만** 설명해주고, 다시 문제로 돌아와 스스로 풀게 하세요.
"""

# 현재 선택된 모드에 따라 프롬프트 확정
current_system_prompt = prompt_solver if teaching_mode == "🌟 친절한 풀이 선생님" else prompt_coach

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

    # 프롬프트 조립 (선택된 모드의 프롬프트 적용)
    combined_text = current_system_prompt + "\n\n[User Question]: " + prompt
    
    if image_input:
        final_prompt = [combined_text, image_input]
    else:
        final_prompt = combined_text

    # --- 10. AI 응답 생성 ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # 스피너 멘트도 모드에 따라 다르게!
        loading_msg = "수길이가 풀이하는 중... 🧠" if teaching_mode == "🌟 친절한 풀이 선생님" else "수길이가 풀이를 검토하는 중... 🧐"

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
