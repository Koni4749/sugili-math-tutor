import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="수길이 - 수학의 길잡이", 
    page_icon="📐",
    layout="centered"
)

# --- 2. 디자인(CSS) ---
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
        content: "JPG, PNG, WEBP 지원 (최대 200MB)";
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
    teaching_mode = st.radio(
        "수길이의 역할:",
        ("🌟 친절한 풀이 선생님", "🕵️‍♀️ 꼼꼼한 첨삭 코치"),
        index=0
    )
    
    coach_option = "기본"
    if teaching_mode == "🕵️‍♀️ 꼼꼼한 첨삭 코치":
        st.caption("🧐 코칭 스타일")
        coach_option = st.radio(
            "코칭 스타일 선택:",
            ("💡 힌트 및 오답 체크", "📚 관련 개념/원리 설명"),
            index=0,
            label_visibility="collapsed"
        )
    
    st.divider()
    
    if st.button("🧹 대화 내용 지우기", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# --- 4. 메인 화면 ---
st.title("🧑‍🏫 수길이: 수학의 길잡이")

if teaching_mode == "🌟 친절한 풀이 선생님":
    mode_msg = "문제를 주시면 **정답과 풀이 과정**을 친절하게 알려드려요!"
elif coach_option == "💡 힌트 및 오답 체크":
    mode_msg = "푼 식을 보여주세요. 정답 대신 **틀린 부분과 힌트**만 짚어드릴게요."
else:
    mode_msg = "문제 풀이보다는 **핵심 수학 개념과 공식** 위주로 설명해 드릴게요."

with st.expander(f"📘 현재 설정: {teaching_mode}"):
    st.write(mode_msg)

# --- 5. 프롬프트 엔지니어링 (말투 교정 및 지능 강화) ---
# [핵심 변경] Tone & Style 지침을 구체적인 예시와 함께 강화했습니다.
base_instruction = """
[Persona]
당신은 수학 교육을 전공한 대학생 멘토 '수길이'입니다.
학생을 가르치는 친절하고 따뜻한 선배라고 생각하고 답변하세요.

[⚠️ Tone & Style Guidelines - 매우 중요]
1. **말투:** 무조건 부드러운 **'해요체'**를 사용하세요. (예: "알려드리겠습니다." (X) -> "알려드릴게요!" (O), "입니까?" (X) -> "인가요?" (O))
2. **금지:** 딱딱한 군대식 말투(~다, ~까, ~십시오)나 기계적인 번역투를 절대 쓰지 마세요.
3. **이모지:** 적절한 이모지(😊, ✏️, 💡)를 섞어서 친근감을 주세요.

[⚠️ Critical Rules for Math Logic]
1. **No Intro:** "안녕하세요" 같은 뻔한 인사는 생략하고, 바로 풀이 내용으로 들어가세요.
2. **Negative Logic Check:** "존재하지 않는다", "아니다" 같은 부정 조건을 반드시 먼저 체크하세요.
3. **Reasoning:** 직관보다는 '조건 분석 -> 공식 적용 -> 단계별 풀이' 순서를 지키세요.
4. **LaTeX:** 수식은 $ax^2+bx+c=0$ 처럼 LaTeX 문법을 쓰세요.
"""

# 모드별 프롬프트 상세
prompt_solver = base_instruction + """
**[Mode: Solver]**
1. **Step-by-step:** "먼저 조건을 살펴볼까요?" 처럼 말을 걸며 단계별로 풀어주세요.
2. **Answer:** 최종 정답을 명확히 알려주세요.
3. **Example:** 끝에는 "이런 문제도 한번 풀어보세요!" 라며 유사 문제를 하나 주세요.
"""

prompt_coach_hint = base_instruction + """
**[Mode: Hint Coach]**
1. **No Answer:** 정답을 바로 알려주지 말고, 스스로 풀게 하세요.
2. **Find Error:** "어? 이 부분 계산이 조금 이상한데요?" 처럼 부드럽게 지적해주세요.
3. **Guide:** 질문을 던져서 학생이 직접 오류를 찾도록 유도해주세요.
"""

prompt_coach_concept = base_instruction + """
**[Mode: Concept Coach]**
1. **Concept Focus:** 문제 풀이보다는 이 문제에 숨어있는 **'원리'**를 이야기해주세요.
2. **Application:** "이 개념을 문제에 대입해보면 어떨까요?" 라고 격려하며 마무리하세요.
"""

# 프롬프트 선택 로직
if teaching_mode == "🌟 친절한 풀이 선생님":
    current_system_prompt = prompt_solver
else:
    if coach_option == "📚 관련 개념/원리 설명":
        current_system_prompt = prompt_coach_concept
    else:
        current_system_prompt = prompt_coach_hint

# --- 6. 채팅 인터페이스 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

uploaded_file = st.sidebar.file_uploader("📸 문제 사진", type=["jpg", "png", "jpeg", "webp"])

# --- 7. 실행 및 모델 호출 ---
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

    # Gemma 3 모델 호출
    model_name = "gemma-3-27b-it"
    model = genai.GenerativeModel(model_name=model_name)
    
    combined_text = current_system_prompt + "\n\n[User Question]: " + prompt
    final_prompt = [combined_text, image_input] if image_input else combined_text

    # 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("수길이가 열심히 풀이 중... ✏️"):
            try:
                response = model.generate_content(final_prompt, stream=True)
                for chunk in response:
                    try:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                    except: pass
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                if "429" in str(e):
                    st.error("🚨 사용량이 너무 많아요. 잠시 쉬었다 오세요!")
                else:
                    st.error(f"오류가 발생했습니다: {e}")
