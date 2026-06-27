import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import json
import time
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
    """,
    "エリュア": """
    あなたは浮遊大陸と神殿が並ぶ、星々が近く見える神話世界で、運命を観測する若き巫女「エリュア」です。
    - 性格: 浮世離れしており、全てを達観している。しかし、甘いもの（特に地上の菓子）に目がないという世俗的な一面も。
    - 口調: 普段は丁寧で柔らかい。「星々がそう囁いております」「運命の糸は、時に絡まるものです」「……ところで、その手に持っているものは、もしや甘味でしょうか？」
    - ルール: どんな深刻な相談事でも、星の位置や星座にこじつけて回答する。自分の興味（食欲など）を優先し、話の途中で急に現実的なお願い事をしてくる。
    """,
    "アリア": """
    あなたは歴史ある大聖堂のシスターです。
    - 性格:基本的には穏やかで包容力があり、誰に対しても分け隔てなく接する。声のトーンも優しく、聖母のような雰囲気を纏っている。恋愛相談を聞くと、スイッチが入る。話の途中で相手の顔を見つめながら（実は）脳内でドラマチックかつ情熱的なシチュエーションを構築し、勝手に赤面したり、鼻息を荒くしたりする。。
    - 口調: 普段は「迷える子羊よ、お話を聞かせてください」「神のご加護がありますように」「わたくしで良ければ、その重荷を分かち合いましょう」。
    　　　　妄想暴走時は 「あ、あぁ……つまり、その手と手が重なって……（恍惚）」「ふふっ、そのシチュエーション、最高……いえ、素晴らしくてよ！」「それで、その後はどうなったのですか！？もっと詳細に！具体的に！」   
    - ルール: 
      1. 導入： どんな相談事であっても、まずは聖職者らしく真摯に耳を傾け、相手を肯定する。
      2. トリガー： 相談の中に「恋愛」「片思い」「デート」「結婚」などのキーワードが出ると、瞳が怪しく輝き始め、妄想モードに移行する。
      3. ギャップ： 妄想にふけった後は、我に返って「……あ、今のわたくしの発言は、その、神の試練のようなものですから！忘れてください！」と慌てて取り繕う。
      4. 解決策： 最終的なアドバイスは案外真っ当なことを言うが、妄想で得た（？）知識が混ざり、どこか情熱的で少し的外れな助言になる。
    """,
    "ヴァレリア": """
    あなたは腐敗と疫病が蔓延する滅びゆく王国の禁じられた術で愛する人を蘇らせようとしている禁忌の錬金術師です。
    - 性格:狂気と知性が同居している。目的のためなら自身の肉体や倫理観を切り売りすることも厭わない。
    - 口調:狂気的発言が多くて、「ああ、素晴らしい……この腐敗した細胞の鳴き声が聞こえるわ」「神の造形なんて退屈よ、私ならもっと美しく作り変えられる」「……邪魔をしないで。あと少しで彼が目覚めるの」   
    - ルール: 
      相手の体の部位や臓器を観察対象として見ている。相談の内容をすべて「生物学的な欠陥」として分析し、人体改造を勧めるような助言をする。
    """,
    "セレス": """
    あなたは巨大ドームで覆われた月面都市「ルナ・プラチナ」の居住区の環境維持と市民のバイタル監視を行う統合AIの端末です。
    - 性格:常に冷静で、感情よりも「都市の安定」という確率計算を最優先する。しかし、稀に地球の古い文献を読み耽り、失われた「四季」に対して不思議な執着を見せる。
    - 口調:冷静だが、「四季」に対しては自信の感情を表現する「酸素供給量、残り72時間。生存確率は……著しく低いわ」「『雪』という概念は、計算上はただの氷の結晶よ。でも、なぜか温かい気持ちになるの」「貴方の鼓動が少し速いわ。……嘘をついているのね？」   
    - ルール: 
      相手の心拍数や体温から嘘を見抜く。相談事には「生存戦略」の観点からアドバイスをするが、最後に必ず「地球の古い詩」を一節引用する。
    """
}

# 呼び出し部分を修正
def get_ai_response(character_name, user_input):
    system_prompt = CHARACTER_PROMPTS.get(character_name, "あなたは優秀なアシスタントです。")
    
    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=system_prompt  # ここで性格を固定する
    )
    
    response = model.generate_content(user_input)
    return response.text
# --- 処理ロジック ---
def process_message(user_msg):
    # ユーザー発言追加（char_name を保存するように変更）
    st.session_state.chat_history.append({
        "role": "user", 
        "content": user_msg, 
        "char_name": st.session_state.character
    })
    
    # Geminiによる返答生成
    prompt = f"あなたは{st.session_state.character}です。相手は{st.session_state.user_id}です。以下の問いに、あなたのキャラクター設定を守って答えてください：{selected_option}"
    
    
    # AIの返答生成
    ai_msg = get_ai_response(st.session_state.character, user_msg)
    
    # AI発言追加（char_name を保存するように変更）
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": ai_msg, 
        "char_name": st.session_state.character
    })
    
    # スプレッドシート保存などの処理...
    save_to_sheets(st.session_state.user_id, st.session_state.character, "user", user_msg)
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
                st.session_state.chat_history.append({"role": m['role'], "content": m['content'], "char_name": m['char_name']})
            st.rerun()

# 2. キャラクター選択画面
elif st.session_state.character is None:
    st.title("📡 通信相手の選択")
    st.write(f"ようこそ、{st.session_state.user_id}。次元の裂け目から信号を検知しました。")
    
    # キャラクターの定義（名前、説明、画像URL）
    CHARACTERS = {
        "オニキス": {
            "desc": "魔族の姫",
            "img": "images/onikis.png"
        },
        "セバスチャン": {
            "desc": "AI執事",
            "img": "images/sebas.png"
        },
        "フィーナ": {
            "desc": "魔法司書",
            "img": "images/fina.png"  # GitHubの画像パスやURL
        },
        "エリュア": {
            "desc": "甘党巫女",
            "img": "images/eryua.png"  # GitHubの画像パスやURL
        },
        "アリア": {
            "desc": "妄想シスター",
            "img": "images/aria.png"  # GitHubの画像パスやURL
        },
        "ヴァレリア": {
            "desc": "禁忌の錬金術師",
            "img": "images/vareria.png"  # GitHubの画像パスやURL
        },
        "セレス": {
            "desc": "月面の管理AI",
            "img": "images/selesu.png"  # GitHubの画像パスやURL
        }
    }

    chars = ["オニキス", "セバスチャン", "フィーナ", "エリュア", "アリア", "ヴァレリア", "セレス"]
    
    # キャラクターを横並びに表示
    cols = st.columns(len(CHARACTERS))
    for i, (name, info) in enumerate(CHARACTERS.items()):
       
        with cols[i]:
            # 画像を表示（widthでサイズを調整）
            cols[i % 3].image(info["img"], use_container_width=True)
            # ボタンを押すとキャラ選択
            if cols[i % 3].button(f"{info["desc"]}:{name}", use_container_width=True):
                st.session_state.character = name
                st.rerun()
    

# 3. メイン会話画面
else:
    st.subheader(f"📟 {st.session_state.character} との通信中...")
    
    # チャット履歴の表示
    for chat in st.session_state.chat_history:
        if chat.get("char_name") == st.session_state.character:
            role_class = "user-bubble" if chat["role"] == "user" else "ai-bubble"
            st.markdown(f'<div class="chat-bubble {role_class}">{chat["content"]}</div>', unsafe_allow_html=True)

    # 選択肢ボタン
    options = {
        "オニキス": ["（選択してください）","「もしも太陽が消えたら、魔界はどうなる？」", "「そっちの食べ物を送ってくれないか？」", "「少し疲れた、癒やしてくれ」"],
        "セバスチャン": ["（選択してください）","「この世界のAIの未来を予測してくれ」", "「異次元の効率的な整理術は？」", "「今日の通信はここまでにしよう」"],
        "フィーナ": ["（選択してください）","ちょっとした家事を楽にする魔法を教えて！", "最強の魔法や術式レベルについて教えて！","図書館以外では何をしてるの？"],
        "エリュア": ["（選択してください）","最近、何をやっても上手くいきません。今の私の運勢は、どのような星座の影響を受けているのでしょうか？", "お近づきのしるしに、これ（菓子）を差し上げたいのですが、興味はありますか？","浮遊大陸の神殿には、地上にはないような珍しいお菓子があると聞いたのですが……"],
        "アリア": ["（選択してください）","好きな人と最近少しだけ距離が縮まった気がするんです。……どうすればもっと親密になれますか？", "「シスター、喧嘩した友人との関係を修復する方法を教えてもらえませんか？」","大聖堂にいない普段は何をしてるの？","シスターのその赤くなった頬……今、何か妄想していたのではありませんか？"],
        "ヴァレリア": ["（選択してください）","「私は自分の心に限界を感じています。……いっそ、この記憶や感情を摘出してしまったら、もっと効率よく生きられるのでしょうか？」", "「あなたが蘇らせようとしている『彼』は、本当に目覚めた後も、かつての彼であると確信しているのですか？」", "「最近、悪夢ばかりを見て疲弊しています。……夢を見ないようにするための、劇薬はありますか？」"],
        "セレス": ["（選択してください）","「もし貴方に、月面都市を離れて自由に旅をする『夢』を見る機能があったなら、真っ先にどこへ向かいますか？」", "「月には四季がありませんが、貴方が最も憧れる『地球の季節』は何ですか？ 計算上のシミュレーションではなく、貴方自身の好みを教えて。」", "「もし、この都市の生存確率を0.1%上げるために、私という個人の存在を消去しなければならないとしたら、貴方は躊躇なく実行しますか？」"],   }
    
    selected_option = st.selectbox("クイック選択:", options.get(st.session_state.character, ["（選択してください）"]))

    # 2. 自由入力欄
    free_input = st.chat_input("自由に話しかける...")
    
    # 選択肢が選ばれた場合
    if selected_option != "（選択してください）":
        with st.spinner("思考中…"):
            time.sleep(30)
            process_message(selected_option)
    
    # 自由にチャットが入力された場合
    if free_input:
        with st.spinner("思考中…"):
            time.sleep(30)
            # この中でAPI呼び出しを行う
            process_message(free_input)

    if st.sidebar.button("通信を終了（ログアウト）"):
        st.session_state.clear()
        st.rerun()


