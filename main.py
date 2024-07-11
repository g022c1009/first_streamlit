import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import time
from cachetools import TTLCache
import os

openai.api_key = openai.api_key = os.getenv('OPENAI_API_KEY')  # APIキーを設定する

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
    for p in soup.find_all('p'):
        article_text += p.get_text()

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
    st.set_page_config(page_title="記事要約アプリ", page_icon="📰", layout="wide")

    st.title("記事要約アプリ")
    st.write("記事をスクレイピングできるサンプルサイト: [Bloomberg](https://www.bloomberg.co.jp/)")
    
    url = st.text_input("記事のURLを入力してください:")
    if st.button("記事を要約する"):
        if url:
            my_bar = st.progress(0)
            article_text = scrape_article(url)
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
    
    st.sidebar.title("情報")
    st.sidebar.info(
        "このアプリは様々なサイトから記事をスクレイピングし、chatGPTを使って要約します。\n"
        "URLを入力し、「記事を要約する」ボタンを押してください。\n"
        "また、記事をスクレイピングする前に、そのサイトがスクレイピングを許可していることを確認してください。"
    )
