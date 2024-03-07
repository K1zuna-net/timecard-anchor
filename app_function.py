from flask import redirect, url_for
import random
import uuid
import bcrypt
import string
import datetime
import qrcode
import pyotp
import time

#------------------------
#認証コード生成
def generate_authcode():
    return str(random.randint(100000, 999999))

#------------------------
#uuid生成
def gen_uuid():
    #生成して返す
    return str(uuid.uuid4())

#------------------------
# パスワードハッシュ化
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

#------------------------
# パスワード検証
def verify_password(input_password, hashed_password):
    return bcrypt.checkpw(input_password.encode('utf-8'), hashed_password)

#------------------------
#社員番号生成
def genarate_staff_id():
    return 100000

#------------------------
#パスワード生成
def gen_password(length=15):
    # 使用する文字のセットを定義
    characters = string.ascii_letters + string.digits + string.punctuation
    
    # ランダムな文字列を生成
    password = ''.join(random.choice(characters) for _ in range(length))
    
    return password

#------------------------
#今日の日付取得
def today():
    return datetime.date.today()


def now():
    # 現在の日付と時刻を取得
    current_datetime = datetime.datetime.now()

    # 現在の時刻のみを取得
    current_time = datetime.datetime.now().time()

    # フォーマットを指定して現在の日付と時刻を取得
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_datetime

#--------------------------
#電話番号の一部を伏字にする
def mask_tel(tel):
    parts = tel.split('-')
    
    # 最初のパート
    first_part = parts[0]
    
    # 真ん中のパートを伏字に変換
    middle_part = parts[1][:1] + '*' * (len(parts[1]) - 2) + parts[1][-1:]
    
    # 最後のパートを伏字に変換
    last_part = parts[2][:1] + '*' * (len(parts[2]) - 2) + parts[2][-1:]
    
    # 伏字に変換したパーツを結合して返す
    return f"{first_part}-{middle_part}-{last_part}"

#--------------------------
#文字列をすべて伏字にする
def hide_characters(text):
    return '*' * len(text)

#--------------------------
# ユーザーに渡す乱数を作成
random_base32 = pyotp.random_base32()
#--------------------------
