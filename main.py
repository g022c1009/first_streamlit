import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import time
from cachetools import TTLCache
import os

# OpenAIのAPIキーを設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# キャッシュの設定: URLごとに最大100件、1時間のTTL
cache = TTLCache(maxsize=100, ttl=3600)

# レート制限の設定: 1分間に最大60回のリクエスト
RATE_LIMIT = 60
request_times = []

def is_rate_limited():
    current_time = time.time()
    # 1分前の時間を計算
    one_minute_ago = current_time - 60
    # 1分以内のリクエストのみを保持
    while request_times and request_times[0] < one_minute_ago:
        request_times.pop(0)
    return len(request_times) >= RATE_LIMIT

def scrape_article(url):
    if url in cache:
        return cache[url]

    if is_rate_limited():
        st.error("リクエスト制限を超えました。1分間お待ちください。")
        return None

    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"記事の取得に失敗しました。ステータスコード: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    article_text = ""
    article = soup.find('article')
    if article:
        paragraphs = article.find_all('p')
    else:
        paragraphs = soup.find_all('p')

    # pタグのテキストを連結して本文を作成
    article_text = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    cache[url] = article_text
    request_times.append(time.time())
    return article_text

def summarize_text(text):
    max_tokens = "150"
    prompt = f"以下の記事を{max_tokens}文字以内で要約してください。\n{text}"
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # GPT-3.5 Turboのモデルを指定
        messages=[
            {"role": "system", "content": "あなたは記事を要約するアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    # Streamlitページの設定
    st.set_page_config(page_title="SUMAPP", page_icon="📰", layout="wide", initial_sidebar_state="expanded")

    # カスタムCSSの適用
    st.markdown("""
        <style>
            body {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Arial', sans-serif;
            }
            .stTextInput {
                background-color: #333333;
                color: #ffffff;
                padding: 12px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            .stButton>button {
                background-color: #1a73e8;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                transition: background-color 0.3s ease;
            }
            .stButton>button:hover {
                background-color: #0d47a1;
            }
            .stProgress>div>div {
                background-color: #1a73e8 !important;
                border-radius: 4px;
            }
            .stSidebar .stMarkdown {
                background-color: #333333;
                color: #ffffff;
                padding: 12px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            .stMarkdown h3 {
                text-align: center;
                color: #ffffff;
                margin-bottom: 20px;
            }
            .stMarkdown a {
                color: #1a73e8;
                text-decoration: none;
            }
            .stMarkdown a:hover {
                text-decoration: underline;
            }
        </style>
    """, unsafe_allow_html=True)

    # タイトルとサイトリンクの表示
    st.title("SUMAPP")
    st.markdown("<h3><a href='https://jp.reuters.com/'>reuters</a></h3>", unsafe_allow_html=True)

    # 記事URLの入力ウィジェット
    url = st.text_input("記事のURLを入力してください:")
    url = url.strip()  # 入力の両端の空白を削除

    # 「記事を要約する」ボタンの処理
    if st.button("記事を要約する", key="summarize_button"):
        if url:
            my_bar = st.progress(0)
            article_text = scrape_article(url)
            # 要約前の本文をStreamlit上で表示
            with st.expander("▼ 要約前の本文を表示", expanded=False):
                st.write(article_text)
            my_bar.progress(30)
            if article_text:
                article_summary = summarize_text(article_text)
                my_bar.progress(60)
                st.subheader("記事の要約:")
                st.write(article_summary)
                my_bar.progress(100)
                time.sleep(1)
                my_bar.empty()
        else:
            st.warning("URLを入力してください。")

    # サイドバーに情報を表示
    st.sidebar.title("情報")
    st.sidebar.markdown("""
    このアプリは様々なサイトから記事をスクレイピングし、chatGPTを使って要約します。\n
    URLを入力し、「記事を要約する」ボタンを押してください。\n
    また、記事をスクレイピングする前に、そのサイトがスクレイピングを許可していることを確認してください。
    """)
