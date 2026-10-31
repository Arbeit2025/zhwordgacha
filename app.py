# -*- coding: utf-8 -*-
"""
zhwordgacha（中国語単語ガチャ）

「ガチャを引く」ボタンで、中国語の単語を1つランダムに表示する小さなWebアプリ。
簡体字・ピンイン・日本語訳・短い例文（中国語＋日本語訳）を表示し、
引いた履歴は SQLite に保存する（履歴のみ。単語データ自体はコード内蔵）。

目次
  1. 設定・初期化
  2. 単語データ（HSK初級〜中級程度の基本語彙）
  3. DB（履歴）まわり
  4. HTMLテンプレート
  5. ルート
  6. 起動
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import Flask, g, jsonify, render_template_string

# ==============================
# 1. 設定・初期化
# ==============================

app = Flask(__name__)
app.config["DATABASE"] = os.environ.get(
    "ZHWORDGACHA_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "gacha_history.db"),
)

# 日本時間（固定オフセット。タイムゾーンDBに依存しない）
JST = timezone(timedelta(hours=9))


def now_jst():
    return datetime.now(JST)


# ==============================
# 2. 単語データ（HSK初級〜中級程度の基本語彙）
#    hanzi=簡体字 / pinyin=ピンイン / meaning=日本語訳
#    example_cn=例文（中国語） / example_jp=例文の日本語訳
# ==============================

WORDS = [
    {"hanzi": "你好", "pinyin": "nǐhǎo", "meaning": "こんにちは",
     "example_cn": "你好，很高兴见到你。", "example_jp": "こんにちは、お会いできてうれしいです。"},
    {"hanzi": "谢谢", "pinyin": "xièxie", "meaning": "ありがとう",
     "example_cn": "谢谢你的帮助。", "example_jp": "助けてくれてありがとう。"},
    {"hanzi": "学习", "pinyin": "xuéxí", "meaning": "勉強する",
     "example_cn": "我每天学习中文。", "example_jp": "私は毎日中国語を勉強します。"},
    {"hanzi": "朋友", "pinyin": "péngyou", "meaning": "友達",
     "example_cn": "他是我的好朋友。", "example_jp": "彼は私の良い友達です。"},
    {"hanzi": "学校", "pinyin": "xuéxiào", "meaning": "学校",
     "example_cn": "我去学校上课。", "example_jp": "私は学校へ授業を受けに行きます。"},
    {"hanzi": "老师", "pinyin": "lǎoshī", "meaning": "先生",
     "example_cn": "老师讲得很清楚。", "example_jp": "先生の説明はとても分かりやすいです。"},
    {"hanzi": "学生", "pinyin": "xuésheng", "meaning": "学生",
     "example_cn": "我是大学生。", "example_jp": "私は大学生です。"},
    {"hanzi": "中国", "pinyin": "Zhōngguó", "meaning": "中国",
     "example_cn": "我想去中国旅行。", "example_jp": "私は中国へ旅行に行きたいです。"},
    {"hanzi": "日本", "pinyin": "Rìběn", "meaning": "日本",
     "example_cn": "我来自日本。", "example_jp": "私は日本から来ました。"},
    {"hanzi": "语言", "pinyin": "yǔyán", "meaning": "言語",
     "example_cn": "语言是沟通的工具。", "example_jp": "言語はコミュニケーションの道具です。"},
    {"hanzi": "时间", "pinyin": "shíjiān", "meaning": "時間",
     "example_cn": "我没有时间。", "example_jp": "私には時間がありません。"},
    {"hanzi": "今天", "pinyin": "jīntiān", "meaning": "今日",
     "example_cn": "今天是星期六。", "example_jp": "今日は土曜日です。"},
    {"hanzi": "明天", "pinyin": "míngtiān", "meaning": "明日",
     "example_cn": "明天见！", "example_jp": "また明日！"},
    {"hanzi": "昨天", "pinyin": "zuótiān", "meaning": "昨日",
     "example_cn": "昨天我去了图书馆。", "example_jp": "昨日私は図書館へ行きました。"},
    {"hanzi": "现在", "pinyin": "xiànzài", "meaning": "今",
     "example_cn": "现在几点？", "example_jp": "今何時ですか。"},
    {"hanzi": "早上", "pinyin": "zǎoshang", "meaning": "朝",
     "example_cn": "我早上七点起床。", "example_jp": "私は朝7時に起きます。"},
    {"hanzi": "晚上", "pinyin": "wǎnshang", "meaning": "夜・晩",
     "example_cn": "晚上我要看书。", "example_jp": "夜は本を読みます。"},
    {"hanzi": "工作", "pinyin": "gōngzuò", "meaning": "仕事",
     "example_cn": "我的工作很忙。", "example_jp": "私の仕事はとても忙しいです。"},
    {"hanzi": "家", "pinyin": "jiā", "meaning": "家・家庭",
     "example_cn": "我家有四口人。", "example_jp": "私の家は4人家族です。"},
    {"hanzi": "人", "pinyin": "rén", "meaning": "人",
     "example_cn": "这里有很多人。", "example_jp": "ここにはたくさんの人がいます。"},
    {"hanzi": "大", "pinyin": "dà", "meaning": "大きい",
     "example_cn": "这个房间很大。", "example_jp": "この部屋は大きいです。"},
    {"hanzi": "小", "pinyin": "xiǎo", "meaning": "小さい",
     "example_cn": "这只猫很小。", "example_jp": "この猫は小さいです。"},
    {"hanzi": "多", "pinyin": "duō", "meaning": "多い",
     "example_cn": "今天人很多。", "example_jp": "今日は人が多いです。"},
    {"hanzi": "少", "pinyin": "shǎo", "meaning": "少ない",
     "example_cn": "糖少一点。", "example_jp": "砂糖は少なめでお願いします。"},
    {"hanzi": "好", "pinyin": "hǎo", "meaning": "良い",
     "example_cn": "这个办法很好。", "example_jp": "この方法はとても良いです。"},
    {"hanzi": "新", "pinyin": "xīn", "meaning": "新しい",
     "example_cn": "我买了新手机。", "example_jp": "私は新しいスマホを買いました。"},
    {"hanzi": "忙", "pinyin": "máng", "meaning": "忙しい",
     "example_cn": "最近我很忙。", "example_jp": "最近私は忙しいです。"},
    {"hanzi": "累", "pinyin": "lèi", "meaning": "疲れた",
     "example_cn": "今天我很累。", "example_jp": "今日は疲れました。"},
    {"hanzi": "高兴", "pinyin": "gāoxìng", "meaning": "うれしい",
     "example_cn": "见到你我很高兴。", "example_jp": "あなたに会えてうれしいです。"},
    {"hanzi": "喜欢", "pinyin": "xǐhuan", "meaning": "好き・気に入る",
     "example_cn": "我喜欢喝茶。", "example_jp": "私はお茶を飲むのが好きです。"},
    {"hanzi": "爱", "pinyin": "ài", "meaning": "愛する・大好き",
     "example_cn": "我爱我的家人。", "example_jp": "私は家族を愛しています。"},
    {"hanzi": "想", "pinyin": "xiǎng", "meaning": "〜したい・思う",
     "example_cn": "我想喝水。", "example_jp": "水が飲みたいです。"},
    {"hanzi": "知道", "pinyin": "zhīdào", "meaning": "知っている",
     "example_cn": "我知道他的名字。", "example_jp": "私は彼の名前を知っています。"},
    {"hanzi": "觉得", "pinyin": "juéde", "meaning": "〜と思う・感じる",
     "example_cn": "我觉得这本书很有意思。", "example_jp": "この本はとても面白いと思います。"},
    {"hanzi": "可以", "pinyin": "kěyǐ", "meaning": "〜できる・〜してもよい",
     "example_cn": "我可以进来吗？", "example_jp": "入ってもいいですか。"},
    {"hanzi": "会", "pinyin": "huì", "meaning": "〜できる（習得して）・〜だろう",
     "example_cn": "我会说一点中文。", "example_jp": "私は少し中国語が話せます。"},
    {"hanzi": "去", "pinyin": "qù", "meaning": "行く",
     "example_cn": "我去商店买东西。", "example_jp": "私は店へ買い物に行きます。"},
    {"hanzi": "来", "pinyin": "lái", "meaning": "来る",
     "example_cn": "他明天来我家。", "example_jp": "彼は明日私の家に来ます。"},
    {"hanzi": "回家", "pinyin": "huí jiā", "meaning": "帰宅する",
     "example_cn": "我六点回家。", "example_jp": "私は6時に帰宅します。"},
    {"hanzi": "吃", "pinyin": "chī", "meaning": "食べる",
     "example_cn": "我们一起吃饭吧。", "example_jp": "一緒にご飯を食べましょう。"},
    {"hanzi": "喝", "pinyin": "hē", "meaning": "飲む",
     "example_cn": "我每天喝咖啡。", "example_jp": "私は毎日コーヒーを飲みます。"},
    {"hanzi": "看", "pinyin": "kàn", "meaning": "見る・読む",
     "example_cn": "我喜欢看电影。", "example_jp": "私は映画を見るのが好きです。"},
    {"hanzi": "听", "pinyin": "tīng", "meaning": "聞く",
     "example_cn": "请听我说。", "example_jp": "私の話を聞いてください。"},
    {"hanzi": "说", "pinyin": "shuō", "meaning": "話す・言う",
     "example_cn": "他说中文说得很好。", "example_jp": "彼は中国語を話すのが上手です。"},
    {"hanzi": "读", "pinyin": "dú", "meaning": "読む・音読する",
     "example_cn": "我每天读报纸。", "example_jp": "私は毎日新聞を読みます。"},
    {"hanzi": "写", "pinyin": "xiě", "meaning": "書く",
     "example_cn": "请写你的名字。", "example_jp": "名前を書いてください。"},
    {"hanzi": "买", "pinyin": "mǎi", "meaning": "買う",
     "example_cn": "我想买这本书。", "example_jp": "私はこの本を買いたいです。"},
    {"hanzi": "卖", "pinyin": "mài", "meaning": "売る",
     "example_cn": "这家店卖水果。", "example_jp": "この店は果物を売っています。"},
    {"hanzi": "走", "pinyin": "zǒu", "meaning": "歩く・去る",
     "example_cn": "我们走吧。", "example_jp": "行きましょう。"},
    {"hanzi": "跑步", "pinyin": "pǎobù", "meaning": "ジョギングする",
     "example_cn": "我每天早上跑步。", "example_jp": "私は毎朝ジョギングします。"},
    {"hanzi": "坐", "pinyin": "zuò", "meaning": "座る・（乗り物に）乗る",
     "example_cn": "请坐。", "example_jp": "どうぞ座ってください。"},
    {"hanzi": "站", "pinyin": "zhàn", "meaning": "立つ",
     "example_cn": "他站在门口。", "example_jp": "彼はドアの前に立っています。"},
    {"hanzi": "开", "pinyin": "kāi", "meaning": "開ける・運転する",
     "example_cn": "请开门。", "example_jp": "ドアを開けてください。"},
    {"hanzi": "关", "pinyin": "guān", "meaning": "閉める",
     "example_cn": "请关窗户。", "example_jp": "窓を閉めてください。"},
    {"hanzi": "打电话", "pinyin": "dǎ diànhuà", "meaning": "電話をかける",
     "example_cn": "我晚上给他打电话。", "example_jp": "夜に彼へ電話をかけます。"},
    {"hanzi": "上班", "pinyin": "shàngbān", "meaning": "出勤する",
     "example_cn": "我九点上班。", "example_jp": "私は9時に出勤します。"},
    {"hanzi": "下班", "pinyin": "xiàbān", "meaning": "退勤する",
     "example_cn": "他五点下班。", "example_jp": "彼は5時に退勤します。"},
    {"hanzi": "睡觉", "pinyin": "shuìjiào", "meaning": "寝る",
     "example_cn": "我十一点睡觉。", "example_jp": "私は11時に寝ます。"},
    {"hanzi": "起床", "pinyin": "qǐchuáng", "meaning": "起きる・起床する",
     "example_cn": "我每天六点起床。", "example_jp": "私は毎日6時に起きます。"},
    {"hanzi": "洗澡", "pinyin": "xǐzǎo", "meaning": "入浴する・シャワーを浴びる",
     "example_cn": "我晚上洗澡。", "example_jp": "私は夜にお風呂に入ります。"},
    {"hanzi": "做饭", "pinyin": "zuò fàn", "meaning": "料理する",
     "example_cn": "妈妈在做饭。", "example_jp": "母が料理をしています。"},
    {"hanzi": "唱歌", "pinyin": "chànggē", "meaning": "歌を歌う",
     "example_cn": "她唱歌唱得很好听。", "example_jp": "彼女は歌が上手です。"},
    {"hanzi": "跳舞", "pinyin": "tiàowǔ", "meaning": "踊る",
     "example_cn": "他们在跳舞。", "example_jp": "彼らは踊っています。"},
    {"hanzi": "游泳", "pinyin": "yóuyǒng", "meaning": "泳ぐ",
     "example_cn": "夏天我喜欢游泳。", "example_jp": "夏は泳ぐのが好きです。"},
    {"hanzi": "旅行", "pinyin": "lǚxíng", "meaning": "旅行する",
     "example_cn": "我喜欢去国外旅行。", "example_jp": "海外旅行が好きです。"},
    {"hanzi": "运动", "pinyin": "yùndòng", "meaning": "運動する・スポーツ",
     "example_cn": "运动对身体好。", "example_jp": "運動は体に良いです。"},
    {"hanzi": "水", "pinyin": "shuǐ", "meaning": "水",
     "example_cn": "请给我一杯水。", "example_jp": "水を一杯ください。"},
    {"hanzi": "茶", "pinyin": "chá", "meaning": "お茶",
     "example_cn": "中国人喜欢喝茶。", "example_jp": "中国人はお茶を飲むのが好きです。"},
    {"hanzi": "咖啡", "pinyin": "kāfēi", "meaning": "コーヒー",
     "example_cn": "我想喝一杯咖啡。", "example_jp": "コーヒーを一杯飲みたいです。"},
    {"hanzi": "米饭", "pinyin": "mǐfàn", "meaning": "ご飯（炊いた米）",
     "example_cn": "我吃米饭和菜。", "example_jp": "私はご飯とおかずを食べます。"},
    {"hanzi": "面条", "pinyin": "miàntiáo", "meaning": "麺",
     "example_cn": "这家店的面条很好吃。", "example_jp": "この店の麺はとてもおいしいです。"},
    {"hanzi": "水果", "pinyin": "shuǐguǒ", "meaning": "果物",
     "example_cn": "我每天吃水果。", "example_jp": "私は毎日果物を食べます。"},
    {"hanzi": "苹果", "pinyin": "píngguǒ", "meaning": "りんご",
     "example_cn": "这个苹果很甜。", "example_jp": "このりんごは甘いです。"},
    {"hanzi": "天气", "pinyin": "tiānqì", "meaning": "天気",
     "example_cn": "今天天气很好。", "example_jp": "今日は天気がとても良いです。"},
    {"hanzi": "下雨", "pinyin": "xiàyǔ", "meaning": "雨が降る",
     "example_cn": "明天会下雨。", "example_jp": "明日は雨が降るでしょう。"},
    {"hanzi": "雪", "pinyin": "xuě", "meaning": "雪",
     "example_cn": "冬天下雪了。", "example_jp": "冬に雪が降りました。"},
    {"hanzi": "热", "pinyin": "rè", "meaning": "暑い・熱い",
     "example_cn": "今天很热。", "example_jp": "今日は暑いです。"},
    {"hanzi": "冷", "pinyin": "lěng", "meaning": "寒い",
     "example_cn": "冬天很冷。", "example_jp": "冬は寒いです。"},
    {"hanzi": "猫", "pinyin": "māo", "meaning": "猫",
     "example_cn": "我家有一只猫。", "example_jp": "私の家には猫が一匹います。"},
    {"hanzi": "狗", "pinyin": "gǒu", "meaning": "犬",
     "example_cn": "这只狗很可爱。", "example_jp": "この犬はとてもかわいいです。"},
    {"hanzi": "鸟", "pinyin": "niǎo", "meaning": "鳥",
     "example_cn": "树上有一只鸟。", "example_jp": "木の上に鳥が一羽います。"},
    {"hanzi": "鱼", "pinyin": "yú", "meaning": "魚",
     "example_cn": "我喜欢吃鱼。", "example_jp": "私は魚を食べるのが好きです。"},
    {"hanzi": "书", "pinyin": "shū", "meaning": "本",
     "example_cn": "这本书很有意思。", "example_jp": "この本はとても面白いです。"},
    {"hanzi": "电脑", "pinyin": "diànnǎo", "meaning": "パソコン",
     "example_cn": "我的电脑坏了。", "example_jp": "私のパソコンが壊れました。"},
    {"hanzi": "手机", "pinyin": "shǒujī", "meaning": "スマートフォン",
     "example_cn": "我忘了带手机。", "example_jp": "スマホを持ってくるのを忘れました。"},
    {"hanzi": "电影", "pinyin": "diànyǐng", "meaning": "映画",
     "example_cn": "我们周末去看电影吧。", "example_jp": "週末に映画を見に行きましょう。"},
    {"hanzi": "音乐", "pinyin": "yīnyuè", "meaning": "音楽",
     "example_cn": "我喜欢听音乐。", "example_jp": "私は音楽を聞くのが好きです。"},
    {"hanzi": "钱", "pinyin": "qián", "meaning": "お金",
     "example_cn": "我没有钱了。", "example_jp": "お金がなくなりました。"},
    {"hanzi": "商店", "pinyin": "shāngdiàn", "meaning": "店・商店",
     "example_cn": "商店几点开门？", "example_jp": "店は何時に開きますか。"},
    {"hanzi": "医院", "pinyin": "yīyuàn", "meaning": "病院",
     "example_cn": "他去医院看病了。", "example_jp": "彼は病院へ診察に行きました。"},
    {"hanzi": "图书馆", "pinyin": "túshūguǎn", "meaning": "図書館",
     "example_cn": "我在图书馆学习。", "example_jp": "私は図書館で勉強します。"},
    {"hanzi": "公园", "pinyin": "gōngyuán", "meaning": "公園",
     "example_cn": "公园里有很多人。", "example_jp": "公園にはたくさんの人がいます。"},
    {"hanzi": "车站", "pinyin": "chēzhàn", "meaning": "駅・停留所",
     "example_cn": "车站在前面。", "example_jp": "駅は前方にあります。"},
    {"hanzi": "飞机", "pinyin": "fēijī", "meaning": "飛行機",
     "example_cn": "我坐飞机去北京。", "example_jp": "私は飛行機で北京へ行きます。"},
    {"hanzi": "火车", "pinyin": "huǒchē", "meaning": "列車",
     "example_cn": "火车几点到？", "example_jp": "列車は何時に着きますか。"},
    {"hanzi": "自行车", "pinyin": "zìxíngchē", "meaning": "自転車",
     "example_cn": "我骑自行车上学。", "example_jp": "私は自転車で通学します。"},
    {"hanzi": "快", "pinyin": "kuài", "meaning": "速い・もうすぐ",
     "example_cn": "他跑得很快。", "example_jp": "彼は走るのが速いです。"},
    {"hanzi": "慢", "pinyin": "màn", "meaning": "遅い・ゆっくり",
     "example_cn": "请慢一点说。", "example_jp": "ゆっくり話してください。"},
    {"hanzi": "贵", "pinyin": "guì", "meaning": "高い（値段）",
     "example_cn": "这件衣服太贵了。", "example_jp": "この服は高すぎます。"},
    {"hanzi": "便宜", "pinyin": "piányi", "meaning": "安い（値段）",
     "example_cn": "这家店的东西很便宜。", "example_jp": "この店の物は安いです。"},
    {"hanzi": "近", "pinyin": "jìn", "meaning": "近い",
     "example_cn": "我家离学校很近。", "example_jp": "私の家は学校から近いです。"},
    {"hanzi": "远", "pinyin": "yuǎn", "meaning": "遠い",
     "example_cn": "机场离这里很远。", "example_jp": "空港はここから遠いです。"},
    {"hanzi": "问题", "pinyin": "wèntí", "meaning": "問題・質問",
     "example_cn": "我有一个问题。", "example_jp": "質問が一つあります。"},
    {"hanzi": "意思", "pinyin": "yìsi", "meaning": "意味",
     "example_cn": "这个词是什么意思？", "example_jp": "この単語はどういう意味ですか。"},
    {"hanzi": "名字", "pinyin": "míngzi", "meaning": "名前",
     "example_cn": "你叫什么名字？", "example_jp": "あなたの名前は何ですか。"},
    {"hanzi": "东西", "pinyin": "dōngxi", "meaning": "物・もの",
     "example_cn": "我去买东西。", "example_jp": "買い物に行きます。"},
    {"hanzi": "一起", "pinyin": "yìqǐ", "meaning": "一緒に",
     "example_cn": "我们一起学习吧。", "example_jp": "一緒に勉強しましょう。"},
    {"hanzi": "已经", "pinyin": "yǐjīng", "meaning": "すでに・もう",
     "example_cn": "我已经吃过饭了。", "example_jp": "私はすでにご飯を食べました。"},
    {"hanzi": "还", "pinyin": "hái", "meaning": "まだ・さらに",
     "example_cn": "我还没做完。", "example_jp": "私はまだ終わっていません。"},
    {"hanzi": "再", "pinyin": "zài", "meaning": "再び・改めて",
     "example_cn": "我们明天再见面。", "example_jp": "また明日会いましょう。"},
]


# ==============================
# 3. DB（履歴）まわり
# ==============================

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drawn_on TEXT NOT NULL,
                drawn_at TEXT NOT NULL,
                hanzi TEXT NOT NULL,
                pinyin TEXT NOT NULL,
                meaning TEXT NOT NULL,
                example_cn TEXT NOT NULL,
                example_jp TEXT NOT NULL
            )
            """
        )
        conn.commit()
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def save_history(word):
    now = now_jst()
    get_db().execute(
        "INSERT INTO history (drawn_on, drawn_at, hanzi, pinyin, meaning, example_cn, example_jp)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            now.date().isoformat(),
            now.strftime("%Y-%m-%d %H:%M:%S"),
            word["hanzi"],
            word["pinyin"],
            word["meaning"],
            word["example_cn"],
            word["example_jp"],
        ),
    )
    get_db().commit()


def get_today_words():
    today = now_jst().date().isoformat()
    rows = get_db().execute(
        "SELECT * FROM history WHERE drawn_on = ? ORDER BY id DESC", (today,)
    ).fetchall()
    return rows


def get_all_history():
    rows = get_db().execute("SELECT * FROM history ORDER BY id DESC").fetchall()
    return rows


# ==============================
# 4. HTMLテンプレート
# ==============================

INDEX_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国語単語ガチャ</title>
<style>
  body { font-family: sans-serif; margin: 0; background: #fdf6ec; color: #333; }
  .wrap { max-width: 640px; margin: 0 auto; padding: 24px 16px 48px; }
  h1 { font-size: 1.6rem; text-align: center; }
  .sub { text-align: center; color: #777; font-size: .9rem; }
  .card { background: #fff; border: 2px solid #e4572e; border-radius: 12px;
          padding: 20px; margin: 20px 0; text-align: center;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  .hanzi { font-size: 3rem; font-weight: bold; margin: 4px 0; }
  .pinyin { font-size: 1.2rem; color: #e4572e; }
  .meaning { font-size: 1.1rem; margin: 8px 0; }
  .example { text-align: left; background: #fafafa; border-radius: 8px;
             padding: 10px 14px; margin-top: 12px; font-size: .95rem; }
  .example .jp { color: #666; }
  form.draw { text-align: center; margin: 24px 0; }
  button { background: #e4572e; color: #fff; border: none; border-radius: 999px;
           font-size: 1.1rem; padding: 12px 36px; cursor: pointer; }
  button:hover { opacity: .85; }
  h2 { font-size: 1.1rem; border-bottom: 2px solid #f0c297; padding-bottom: 4px; }
  ul { list-style: none; padding: 0; }
  li { background: #fff; border-radius: 8px; padding: 8px 12px; margin: 6px 0;
       box-shadow: 0 1px 3px rgba(0,0,0,.05); }
  li .hz { font-size: 1.15rem; font-weight: bold; }
  li .py { color: #e4572e; margin: 0 6px; }
  li .time { color: #999; font-size: .8rem; float: right; }
  .links { text-align: center; margin-top: 24px; }
  a { color: #e4572e; }
  .empty { color: #999; text-align: center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🀄 中国語単語ガチャ</h1>
  <p class="sub">ボタンを押すと、中国語の単語が1つ出てきます。1日に何回でも引けます。</p>

  {% if word %}
  <div class="card">
    <div class="hanzi">{{ word.hanzi }}</div>
    <div class="pinyin">{{ word.pinyin }}</div>
    <div class="meaning">{{ word.meaning }}</div>
    <div class="example">
      <div>{{ word.example_cn }}</div>
      <div class="jp">{{ word.example_jp }}</div>
    </div>
  </div>
  {% endif %}

  <form class="draw" method="post" action="/draw">
    <button type="submit">ガチャを引く</button>
  </form>

  <h2>今日引いた単語（{{ today }}）</h2>
  {% if today_words %}
  <ul>
    {% for row in today_words %}
    <li><span class="time">{{ row.drawn_at[11:16] }}</span>
        <span class="hz">{{ row.hanzi }}</span>
        <span class="py">{{ row.pinyin }}</span>{{ row.meaning }}</li>
    {% endfor %}
  </ul>
  {% else %}
  <p class="empty">今日はまだ引いていません。</p>
  {% endif %}

  <div class="links"><a href="/history">履歴一覧を見る</a></div>
</div>
</body>
</html>
"""

HISTORY_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>履歴一覧 | 中国語単語ガチャ</title>
<style>
  body { font-family: sans-serif; margin: 0; background: #fdf6ec; color: #333; }
  .wrap { max-width: 640px; margin: 0 auto; padding: 24px 16px 48px; }
  h1 { font-size: 1.4rem; text-align: center; }
  ul { list-style: none; padding: 0; }
  li { background: #fff; border-radius: 8px; padding: 10px 14px; margin: 6px 0;
       box-shadow: 0 1px 3px rgba(0,0,0,.05); }
  li .hz { font-size: 1.15rem; font-weight: bold; }
  li .py { color: #e4572e; margin: 0 6px; }
  li .ex { color: #666; font-size: .9rem; margin-top: 4px; }
  li .time { color: #999; font-size: .8rem; float: right; }
  .links { text-align: center; margin-top: 24px; }
  a { color: #e4572e; }
  .empty { color: #999; text-align: center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>📚 ガチャ履歴一覧</h1>
  {% if history %}
  <ul>
    {% for row in history %}
    <li><span class="time">{{ row.drawn_at }}</span>
        <span class="hz">{{ row.hanzi }}</span>
        <span class="py">{{ row.pinyin }}</span>{{ row.meaning }}
        <div class="ex">{{ row.example_cn }}（{{ row.example_jp }}）</div></li>
    {% endfor %}
  </ul>
  {% else %}
  <p class="empty">まだ履歴がありません。</p>
  {% endif %}
  <div class="links"><a href="/">トップへ戻る</a></div>
</div>
</body>
</html>
"""


# ==============================
# 5. ルート
# ==============================

@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        INDEX_HTML,
        word=None,
        today=now_jst().date().isoformat(),
        today_words=get_today_words(),
    )


@app.route("/draw", methods=["POST"])
def draw():
    word = random.choice(WORDS)
    save_history(word)
    return render_template_string(
        INDEX_HTML,
        word=word,
        today=now_jst().date().isoformat(),
        today_words=get_today_words(),
    )


@app.route("/history", methods=["GET"])
def history():
    return render_template_string(HISTORY_HTML, history=get_all_history())


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})


# ==============================
# 6. 起動
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
