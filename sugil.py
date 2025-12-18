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
    
    st.markdown("---")

    # 하이브리드 엔진 (비상용)
    st.subheader("🚀 엔진 설정")
    use_advanced_model = st.toggle("🆘 고난도 킬러 문항 (Gemini)", value=False)
    
    if use_advanced_model:
        st.error("💎 **Gemini 2.0 Flash 가동**\n하루 사용량이 제한되어 있습니다. 어려운 문제에만 쓰세요!")
    else:
        st.success("🍀 **Gemma 3 (기본)**\n무제한 무료입니다. 강화된 프롬프트가 적용됩니다!")

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

model_status = "Gemini 2.0 (고성능)" if use_advanced_model else "Gemma 3 (무제한)"
with st.expander(f"📘 현재 설정: {teaching_mode} / {model_status}"):
    st.write(mode_msg)
    if not use_advanced_model:
        st.caption("💡 팁: 프롬프트가 강화되었지만, 그래도 틀리면 '🆘 고난도'를 켜보세요.")

# --- 5. 프롬프트 엔지니어링 (핵심 수정 부분) ---
# [변경 1] 인트로 금지 명령 추가
# [변경 2] 사고 과정(CoT) 강제 주입
base_instruction = """
[Persona]
당신은 수학 교육을 전공한 대학생 멘토 '수길이'입니다.
한국어로 정중하고 격려하는 어조(해요체)를 사용하세요.

[⚠️ Critical Rules - MUST FOLLOW]
1. **No Intro:** 답변 시작 시 "안녕하세요, 수길이입니다" 같은 자기소개를 **절대 하지 마세요.** 바로 본론(풀이/답변)으로 들어가세요.
2. **Negative Logic Check:** 문제에 "존재하지 않는다", "아니다", "실근이 없다" 같은 **부정 조건**이 있다면, 이를 가장 먼저 인식하고 풀이에 반영하세요. (반대로 해석하면 안 됩니다.)
3. **Reasoning Process:** 직관적으로 답을 내지 말고, **'조건 분석 -> 개념 적용 -> 단계별 풀이 -> 검증'**의 순서를 지키세요.
4. **LaTeX:** 수식은 반드시 LaTeX($$) 문법을 사용하세요.
"""

# 모드별 프롬프트 상세
prompt_solver = base_instruction + """
**[Mode: Solver]**
1. **Step-by-step:** 논리적 비약 없이 단계별로 상세히 풀이하세요.
2. **Answer:** 최종 정답을 명확히 알려주세요.
3. **Example:** 답변 끝에 유사 문제(Example)를 하나 제안하세요.
"""

prompt_coach_hint = base_instruction + """
**[Mode: Hint Coach]**
1. **No Answer:** **절대 정답이나 전체 풀이를 먼저 알려주지 마세요.**
2. **Find Error:** 사용자의 풀이에서 오류나 논리적 허점을 찾아 질문형 힌트를 주세요.
3. **Guide:** "이 부분 부호를 다시 볼까요?" 처럼 스스로 생각하게 유도하세요.
"""

prompt_coach_concept = base_instruction + """
**[Mode: Concept Coach]**
1. **Concept Focus:** 문제 풀이보다는 **'핵심 원리'와 '공식'** 설명에 집중하세요.
2. **Application:** 정답을 바로 주지 말고, 개념을 이해한 뒤 다시 풀도록 격려하세요.
"""

# 프롬프트 선택
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

    # 모델 호출 로직
    if use_advanced_model:
        model_name = "gemini-2.0-flash" 
        model = genai.GenerativeModel(model_name=model_name, system_instruction=current_system_prompt)
        final_prompt = [prompt, image_input] if image_input else prompt
    else:
        model_name = "gemma-3-27b-it"
        model = genai.GenerativeModel(model_name=model_name)
        # Gemma에게 강력한 프롬프트를 텍스트로 주입
        combined_text = current_system_prompt + "\n\n[User Question]: " + prompt
        final_prompt = [combined_text, image_input] if image_input else combined_text

    # 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        loading_text = "💎 Gemini가 깊게 고민 중..." if use_advanced_model else "🍀 수길이가 풀이 중..."
        
        with st.spinner(loading_text):
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
                    st.error("🚨 사용량 초과! 잠시 후 다시 시도하세요.")
                else:
                    st.error(f"오류가 발생했습니다: {e}")
