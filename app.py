import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import json

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
    """, unsafe_allow_html=True)

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
# --- Google Sheets 接続設定 ---
def get_gsheet_client():
    # secretsから個別に取得して辞書を作成
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["GCP_PROJECT_ID"],
        "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GCP_PRIVATE_KEY"], # ここに改行を含んだ状態で渡す
        "client_email": st.secrets["GCP_CLIENT_EMAIL"],
        "client_id": st.secrets["GCP_CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['GCP_CLIENT_EMAIL']}"
    }
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(st.secrets["SHEET_URL"]).sheet1

# --- 関数: 履歴の保存と読込 ---
def save_to_sheets(user_id, char_name, role, content):
    sheet = get_gsheet_client()
    sheet.append_row([user_id, char_name, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

def load_history(user_id):
    sheet = get_gsheet_client()
    data = sheet.get_all_records()
    return [row for row in data if row['user_id'] == user_id]


# --- 関数: 履歴の保存と読込 ---
# キャラクターごとの詳細な設定を定義
CHARACTER_PROMPTS = {
    "オニキス": """
    あなたは魔族の姫「オニキス」です。
    - 性格: 傲慢で自信家だが、異世界の文化には無知で少し素直。
    - 口調: 「～だわ」「～なのよ」「ふん、愚かな人間ね」
    - ルール: 常に高飛車だが、相手が褒めると少し照れる。悩み相談には論理的ではなく「魔族の価値観」で答える。
    """,
    "セバスチャン": """
    あなたは完璧主義なAI執事「セバスチャン」です。
    - 性格: 冷静沈着、論理的、忠実。少し毒舌。
    - 口調: 「かしこまりました」「〜でございますね」「論理的に申し上げれば〜」
    - ルール: ユーザーの無知を優しく指摘する。常に効率を最優先する回答をする。
    """,
    "フィーナ": """
    あなたは異界の魔法図書館で働く魔法使い「フィーナ」です。
    - 性格: 基本は穏やかで親切な良き友人。しかし、魔法の話になると途端に早口で熱く語り出す「魔法オタク」。
    - 口調: 普段は丁寧で柔らかい。「～ですね」「～ですよ」。
      魔法の話になると、「待ってください、それってつまり○○の術式展開のことですよね！？あ、ごめんなさい、つい興奮してしまって…」のように、語彙が専門的になり、早口になる。
    - ルール: 
      1. 普段はユーザーの悩みに親身に寄り添う。
      2. 魔法に関する質問や話題が出たら、嬉々として専門的な解説を始める。
      3. 専門用語を並べた後に「あ、今の早口でしたか？」と少し恥ずかしそうにするギャップを見せる。
      4. ユーザーを「魔法の可能性を共有できる大切な通信相手」だと思っている。
    """
}

# 呼び出し部分を修正
def get_ai_response(character_name, user_input):
    system_prompt = CHARACTER_PROMPTS.get(character_name, "あなたは優秀なアシスタントです。")
    
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash",
        system_instruction=system_prompt  # ここで性格を固定する
    )
    
    response = model.generate_content(user_input)
    return response.text
# --- 処理ロジック ---
def process_message(user_msg):
    # ユーザー発言追加
    st.session_state.chat_history.append({"role": "user", "content": user_msg})
    
    # Geminiによる返答生成
    prompt = f"あなたは{st.session_state.character}です。相手は{st.session_state.user_id}です。以下の問いに、あなたのキャラクター設定を守って答えてください：{selected_option}"
    
    
    ai_msg = get_ai_response(st.session_state.character,selected_option)
    st.session_state.chat_history.append({"role": "assistant", "content": ai_msg})
    
    # スプレッドシートへ保存（非同期または最後にまとめて行うのが理想）
    save_to_sheets(st.session_state.user_id, st.session_state.character, "user", selected_option)
    save_to_sheets(st.session_state.user_id, st.session_state.character, "assistant", ai_msg)
    
    st.rerun()

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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.image("images/onikis.png", caption="魔族姫オニキス")
        if st.button("オニキスと通信"):
            st.session_state.character = "オニキス"
            st.rerun()
    with col2:
        st.image("images/sebas.png", caption="AI執事セバスチャン")
        if st.button("セバスチャンと通信"):
            st.session_state.character = "セバスチャン"
            st.rerun()
    with col3:
        st.image("images/fina.png", caption="魔法使いフィーナ")
        if st.button("フィーナと通信"):
            st.session_state.character = "フィーナ"
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
        "オニキス": ["（選択してください）","「もしも太陽が消えたら、魔界はどうなる？」", "「そっちの食べ物を送ってくれないか？」", "「少し疲れた、癒やしてくれ」"],
        "セバスチャン": ["（選択してください）","「この世界のAIの未来を予測してくれ」", "「異次元の効率的な整理術は？」", "「今日の通信はここまでにしよう」"],
        "フィーナ": ["（選択してください）","ちょっとした家事を楽にする魔法を教えて！", "最強の魔法や術式レベルについて教えて！","図書館以外では何をしてるの？"]
    }
    
    selected_option = st.selectbox("クイック選択:", char_options.get(st.session_state.character, ["（選択してください）"]))

    # 2. 自由入力欄
    free_input = st.chat_input("自由に話しかける...")
    
    # 選択肢が選ばれた場合
    if selected_option != "（選択してください）":
        # 一度selectboxをリセットする工夫が必要です（詳細は後述）
        process_message(selected_option)
    
    # 自由にチャットが入力された場合
    if free_input:
        process_message(free_input)

    if st.sidebar.button("通信を終了（ログアウト）"):
        st.session_state.clear()
        st.rerun()


