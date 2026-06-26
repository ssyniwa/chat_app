import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="異界通信アプリ", page_icon="🔮", layout="centered")

# カスタムCSSでUIを洗練
st.markdown("""
    <style>
    .main { background-color: #0d0221; color: #f0f0f0; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #1a0b2e; color: #00f2ff; border: 1px solid #00f2ff; }
    .stTextInput>div>div>input { background-color: #1a0b2e; color: #f0f0f0; border-radius: 10px; }
    .chat-bubble { padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    .user-bubble { background-color: #2e1a47; border-left: 5px solid #00f2ff; }
    .ai-bubble { background-color: #1a1a2e; border-right: 5px solid #ffd700; }
    </style>
    """, unsafe_allow_stdio=True)

# --- 初期設定 & API接続 ---
# セッション状態の初期化
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "character" not in st.session_state: st.session_state.character = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# APIキー設定 (Secretsから取得)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.warning("APIキーが設定されていません。.streamlit/secrets.tomlを確認してください。")

# Google Sheets接続
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 関数: 履歴の保存と読込 ---
def save_to_sheets(user_id, char_name, role, content):
    # 既存データを読み込んで追加（簡易版。本来はappend専用メソッドが望ましい）
    new_data = pd.DataFrame([{
        "user_id": user_id,
        "character": char_name,
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    # ここでは既存シートに追記するロジック（環境に合わせて調整が必要）
    # conn.create(data=new_data) # streamlit-gsheetsの書き込み仕様に準拠
    pass 

def load_history(user_id):
    try:
        df = conn.read()
        user_df = df[df['user_id'] == user_id]
        return user_df.to_dict('records')
    except:
        return []

# --- 画面遷移ロジック ---

# 1. ログイン画面
if not st.session_state.logged_in:
    st.title("🔮 異界通信プロトコル")
    user_id = st.text_input("識別ID（ユーザーID）を入力してください", placeholder="例: explorer_01")
    if st.button("接続開始"):
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            # 履歴の復元
            saved_msgs = load_history(user_id)
            for m in saved_msgs:
                st.session_state.chat_history.append({"role": m['role'], "content": m['content']})
            st.rerun()

# 2. キャラクター選択画面
elif st.session_state.character is None:
    st.title("📡 通信相手の選択")
    st.write(f"ようこそ、{st.session_state.user_id}。次元の裂け目から信号を検知しました。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.image("https://placehold.co/300x400/2E1A47/00F2FF?text=Onyx", caption="魔族姫オニキス")
        if st.button("オニキスと通信"):
            st.session_state.character = "オニキス"
            st.rerun()
    with col2:
        st.image("https://placehold.co/300x400/1A1A2E/FFD700?text=Sebastian", caption="AI執事セバスチャン")
        if st.button("セバスチャンと通信"):
            st.session_state.character = "セバスチャン"
            st.rerun()

# 3. メイン会話画面
else:
    st.subheader(f"📟 {st.session_state.character} との通信中...")
    
    # チャット履歴の表示
    for chat in st.session_state.chat_history:
        role_class = "user-bubble" if chat["role"] == "user" else "ai-bubble"
        st.markdown(f'<div class="chat-bubble {role_class}">{chat["content"]}</div>', unsafe_allow_html=True)

    # 選択肢ボタン
    options = {
        "オニキス": ["「もしも太陽が消えたら、魔界はどうなる？」", "「そっちの食べ物を送ってくれないか？」", "「少し疲れた、癒やしてくれ」"],
        "セバスチャン": ["「この世界のAIの未来を予測してくれ」", "「異次元の効率的な整理術は？」", "「今日の通信はここまでにしよう」"]
    }
    
    selected_option = st.selectbox("送信内容を選択:", options[st.session_state.character])
    
    if st.button("信号を送信"):
        # ユーザー発言追加
        st.session_state.chat_history.append({"role": "user", "content": selected_option})
        
        # Geminiによる返答生成
        prompt = f"あなたは{st.session_state.character}です。相手は{st.session_state.user_id}です。以下の問いに、あなたのキャラクター設定を守って答えてください：{selected_option}"
        model = genai.GenerativeModel("gemini-1.5-flash") # 3.1 FlashがGAになればここを書き換え
        response = model.generate_content(prompt)
        
        ai_msg = response.text
        st.session_state.chat_history.append({"role": "assistant", "content": ai_msg})
        
        # スプレッドシートへ保存（非同期または最後にまとめて行うのが理想）
        save_to_sheets(st.session_state.user_id, st.session_state.character, "user", selected_option)
        save_to_sheets(st.session_state.user_id, st.session_state.character, "assistant", ai_msg)
        
        st.rerun()

    if st.sidebar.button("通信を終了（ログアウト）"):
        st.session_state.clear()
        st.rerun()


