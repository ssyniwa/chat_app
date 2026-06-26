import streamlit as st
import google.generativeai as genai

# --- 1. 設定 ---
# ※実際の運用時はStreamlitのSecretsに保存してください
# genai.configure(api_key="YOUR_GEMINI_API_KEY")

st.title("異界通信アプリ")

# --- 2. 状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "character" not in st.session_state:
    st.session_state.character = None

# --- 3. ログイン画面 ---
if not st.session_state.logged_in:
    user_id = st.text_input("ユーザーIDを入力してログイン")
    if st.button("ログイン"):
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.rerun()
else:
    st.write(f"ようこそ、{st.session_state.user_id}さん")
    
    # --- 4. キャラクター選択 ---
    if not st.session_state.character:
        char = st.selectbox("通信相手を選択してください", ["魔族姫オニキス", "謎のAI執事"])
        if st.button("通信開始"):
            st.session_state.character = char
            st.session_state.messages = [{"role": "assistant", "content": f"{char}と接続しました。何か話しかけてください。"}]
            st.rerun()
    
    # --- 5. 会話エリア ---
    else:
        st.subheader(f"通信相手: {st.session_state.character}")
        
        # 履歴表示
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # 選択肢ベースの会話入力
        options = ["「もしも明日、太陽が消えたら？」", "「異界の食べ物ってどんな味？」", "「少し休まない？」"]
        user_input = st.selectbox("話す内容を選択:", options)
        
        if st.button("送信"):
            # ユーザーの発言を保存
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # AIの回答生成（本来はここでgenai.GenerativeModelを呼ぶ）
            # プロトタイプなので固定返答です
            ai_response = f"{st.session_state.character}: 「ふむ、その質問は興味深いわね……(AIからの返答をここに生成)」"
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            st.rerun()

        if st.button("通信を切断してキャラ選択に戻る"):
            st.session_state.character = None
            st.session_state.messages = []
            st.rerun()
