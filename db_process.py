# db_process.py
from flask import Flask, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from config import Config
from mail_send_process import *
from sms_send_process import * 
from app_function import  * 
import pyotp

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)
app.secret_key = 'hal_2023'
mysql = MySQL(app)
mail = Mail(app)

#shere_DB接続
def connect_db(app):
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            cur.close()

            # 接続が成功した旨をコンソールに表示
            print("FlaskアプリケーションがMySQLデータベースに正常に接続しました！")

            # テーブル名を表示
            print("データベース内のテーブル:")
            for table in tables:
                print(table[0])

    except Exception as e:
        # 接続エラーが発生した場合、エラーをコンソールに表示
        print(f"データベース接続エラー: {str(e)}")
        import traceback
        traceback.print_exc()

#index_出勤処理
def attendance(uuid, today, now):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM job_history WHERE uuid= %s AND attendance_flag = %s AND work_day = %s AND leave_flag = %s"
            cur.execute(sql_query, (uuid, 1, today,0))
            result = cur.fetchone()

            if result:
                # 出勤済みのレコードが見つかった場合
                return False
            else:
                # 出勤していないレコードが見つからなかった場合、新しいレコードを挿入
                sql_insert = "INSERT INTO job_history (uuid, work_day, attendance_time, attendance_flag) VALUES (%s, %s, %s, %s)"
                cur.execute(sql_insert, (uuid, today, now, 1))
                mysql.connection.commit()
                return True

    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False
    
#index_退勤処理
def work_out(uuid, today, now):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            # 出勤フラグが1かつ退勤フラグが0のレコードを検索
            sql_query = "SELECT * FROM job_history WHERE uuid = %s AND attendance_flag = %s AND leave_flag = %s AND work_day = %s"
            cur.execute(sql_query, (uuid, 1, 0, today))
            result = cur.fetchone()

            if result:
                # 出勤しているレコードが見つかった場合、退勤処理を行う
                # 退勤レコードを更新してleave_flagを1にし、退勤時間を記録
                sql_update = "UPDATE job_history SET workout_day = %s, leave_time = %s, leave_flag = %s WHERE uuid = %s AND attendance_flag = %s AND leave_flag = %s AND work_day = %s"
                cur.execute(sql_update, (today, now, 1, uuid, 1, 0, today))
                mysql.connection.commit()
                return True
            else:
                # 出勤していない場合や既に退勤済みの場合はエラーメッセージを返す
                error_msg.append("出勤していないか、既に退勤しています。")
                return False

    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

#login_ログイン処理
def login_trial(mail, password, error_msg):
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM staff_list WHERE mail = %s"
            cur.execute(sql_query, (mail,))
            user_info = cur.fetchone()
            if user_info:
                stored_salt = user_info[4][:29].encode('utf-8')
                
                hashed_input_password = bcrypt.hashpw(password.encode('utf-8'), stored_salt)

                if hashed_input_password == user_info[4].encode('utf-8'):
                    if int(user_info[18]) == 0: #ログインフラグのチェック
                        session['user'] = user_info
                        return True
                    else:
                        error_msg.append("※ログインが無効化されています。")
                        return False
                else:
                    error_msg.append("※メールアドレスまたはパスワードが間違っています。")
                    return False
            else:
                error_msg.append("※メールアドレスまたはパスワードが間違っています。")
                return False
            
    except Exception as e:
        error_msg.append("SQL文エラー: " + str(e))
        return False

#login_SMS認証コード送信
def login_authcode(uuid):
    authcode = generate_authcode()
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()

            sql_query = "UPDATE staff_list SET authcode = %s WHERE uuid = %s"
            cur.execute(sql_query, (authcode, uuid))
            mysql.connection.commit()

            if send_sms(session['user'][8], authcode):
                return True
            else:
                # 送信失敗時の処理
                mysql.connection.rollback()  # ロールバック
                print("DB登録エラー：" + str(e))
                error_msg.append("SMSが送信できません。")
                return False

    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

#login_SMS認証コード確認
def login_confirm_sms(uuid,authcode):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM staff_list WHERE authcode = %s AND uuid = %s"
            cur.execute(sql_query, (authcode, uuid))
            result = cur.fetchone()
            
            if result:
                cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
                updated_user = cur.fetchone()
                session['user'] = updated_user
                
                return True
            else:
                error_msg.append("認証コードが正しくありません。再度入力してください。")
                return False
    except Exception as e:
        error_msg.append("SQL文エラー" + str(e))
        return False

#login_ICカードIdm一致確認処理
def confirm_idm(uuid,idm):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM staff_list WHERE idm = %s AND uuid = %s"
            cur.execute(sql_query, (idm, uuid))
            result = cur.fetchone()
            
            if result:
                cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
                updated_user = cur.fetchone()
                session['user'] = updated_user
                return True
            else:
                error_msg.append("正しいICカードではありません。再度スキャンしてください。")
                return False
    except Exception as e:
        error_msg.append("SQL文エラー" + str(e))
        return False

#login_認証アプリ一致確認
def confirm_app_authcode(app_authcode):
    error_msg = []
    totp = pyotp.TOTP(random_base32)
    result = totp.verify(app_authcode)
    
    if result:
        return True
    else:
        return False

#register_仮登録処理
def temp_register(data,password):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            
            # INSERT文の作成
            sql_query = """
                INSERT INTO staff_list (
                    uuid, staff_id, full_name, full_name_kana, password, 
                    mail, tel, birthday, sex, office, office_group, join_day, 
                    leave_day, create_at, update_at, login_flag, password_flag, 
                    sms_flag, card_flag, app_flag, postcode, address, role
                    ) VALUES (
                        %(uuid)s, %(staff_id)s, %(full_name)s, %(full_name_kana)s, %(password)s,
                        %(mail)s, %(tel)s, %(birthday)s, %(sex)s, %(office)s, %(office_group)s, 
                        %(join_day)s, %(leave_day)s, %(create_at)s, %(update_at)s, %(login_flag)s,
                        %(password_flag)s, %(sms_flag)s, %(card_flag)s, %(app_flag)s, %(postcode)s, %(address)s, %(role)s
                        )
                        """

            # データベースにINSERT文を実行
            cur.execute(sql_query, data)
            print("INSERT完了")  
            print(password)  
            # メール送信
            if register_authcode_send(data['full_name'], data['office'], data['office_group'], password, data['mail']):
                # 変更をコミットする
                mysql.connection.commit()
                print("メール送信とDB登録が完了しました。")
                cur.close()
                return True
            else:
                # メール送信に失敗した場合はロールバック
                mysql.connection.rollback()
                cur.close()
                return False

    except Exception as e:
        error_msg.append(f"DB登録中にエラーが発生しました: {str(e)}")
        print(error_msg[-1])  # エラーメッセージを表示
        return False

#settings_パスワード変更処理
def c_password(uuid,new_password):
    
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "UPDATE staff_list SET password = %s, password_flag = %s WHERE uuid = %s"
            cur.execute(sql_query,(new_password,1,uuid))
            mysql.connection.commit()
            print("パスワード変更完了")
            return True
    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

# settings_SMS認証コード登録・送信処理
def send_register_authcode(uuid, authcode):
    
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()

            sql_query = "UPDATE staff_list SET authcode = %s WHERE uuid = %s"
            cur.execute(sql_query, (authcode, uuid))
            mysql.connection.commit()

            if send_sms(session['user'][8], authcode):
                return True
            else:
                # 送信失敗時の処理
                mysql.connection.rollback()  # ロールバック
                print("DB登録エラー：" + str(e))
                error_msg.append("SMSが送信できません。")
                return False

    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

#settings_SMS認証コード確認処理
def confirm_authcode(authcode, uuid):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM staff_list WHERE authcode = %s AND uuid = %s"
            cur.execute(sql_query, (authcode, uuid))
            result = cur.fetchone()
                        
            if result:
                
                # 最新のアカウント情報を取得してsession['user']に格納
                cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
                updated_user = cur.fetchone()
                session['user'] = updated_user
                
                return True
            else:
                error_msg.append("認証コードが正しくありません。再度入力してください。")
                return False
    except Exception as e:
        error_msg.append("SQL文エラー" + str(e))
        return False

#settings_電話番号変更・認証コード登録処理
def update_tel(uuid, tel, authcode):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()

            sql_query = "UPDATE staff_list SET tel = %s, authcode = %s WHERE uuid = %s"
            cur.execute(sql_query, (tel, authcode, uuid))
            mysql.connection.commit()

            if send_sms(tel, authcode):
                return True
            else:
                # 送信失敗時の処理
                mysql.connection.rollback()  # ロールバック
                print("SMS送信エラー")
                error_msg.append("SMSが送信できません。")
                return False

    except Exception as e:
        print("DB登録エラー：" + str(e))
        error_msg.append("DB登録エラー：" + str(e))
        return False

#setitngs_ICカードリーダー登録
def register_card_uid(uuid, ic_idm):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "UPDATE staff_list SET idm = %s WHERE uuid = %s"
            cur.execute(sql_query, (ic_idm,uuid))
            mysql.connection.commit()
            
            # 最新のアカウント情報を取得してsession['user']に格納
            cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
            updated_user = cur.fetchone()
            session['user'] = updated_user
            print("カードのUIDをデータベースに登録しました。")
            return True
    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

#register_app_認証アプリ用QRコード生成
def genarate_qr():
    # uriを作成
    uri = pyotp.totp.TOTP(random_base32).provisioning_uri(name="ths10630",issuer_name="多要素認証型タイムカード「ANCHOR」")
    # QRコードを作成
    img = qrcode.make(uri)
    img.save('./static/img/register_app.png')

    # 1000秒間OneTimePasswordを表示
    totp = pyotp.TOTP(random_base32)
    for i in range(30):
        print(totp.now())
    time.sleep(1)

#register_app_認証アプリ用認証コード確認
def f_confirm_app_authcode(app_authcode,uuid):
    error_msg = []
    totp = pyotp.TOTP(random_base32)
    result = totp.verify(app_authcode)
    
    if result:
        try:
            with app.app_context():
                cur = mysql.connection.cursor()                
                # 最新のアカウント情報を取得してsession['user']に格納
                cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
                updated_user = cur.fetchone()
                session['user'] = updated_user
                return True

        except Exception as e:
            print(str(e))
            error_msg.append("SQL文エラー: " + str(e))
            return False    
    else:
        error_msg.append("認証コードが一致しません。")
        return False

#settings_認証形式選択
def change_auth_format(uuid,auth_format):
    error_msg = []
    if auth_format == "sms":
        sms_flag = 1
        card_flag = 0
        app_flag = 0
    elif auth_format == "card":
        sms_flag = 0
        card_flag = 1
        app_flag = 0
    else:
        sms_flag = 0
        card_flag = 0
        app_flag = 1
        
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "UPDATE staff_list SET sms_flag = %s, card_flag = %s, app_flag = %s WHERE uuid = %s"
            cur.execute(sql_query, (sms_flag,card_flag,app_flag,uuid))
            mysql.connection.commit()
            
            # 最新のアカウント情報を取得してsession['user']に格納
            cur.execute("SELECT * FROM staff_list WHERE uuid = %s", (uuid,))
            updated_user = cur.fetchone()
            session['user'] = updated_user
            return True
    except Exception as e:
        print(str(e))
        error_msg.append("SQL文エラー: " + str(e))
        return False

#staff_list_登録されているスタッフリストを表示
def display_stafflist():
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            sql_query = "SELECT * FROM staff_list"
            cur.execute(sql_query)
            # テーブルのデータを取得
            user_data = cur.fetchall()
            cur.close()
            return user_data, None
    except Exception as e:
        print(str(e))
        error_msg.append("従業員データを取得できませんでした。エラー：" + str(e))
        return None, error_msg

def search_data(s_staff_id, full_name, s_office, s_group):
    try:
        with app.app_context():
            cur = mysql.connection.cursor()

            sql_query = "SELECT * FROM staff_list WHERE 1=1"

            params = []

            if s_staff_id:
                sql_query += " AND staff_id = %s"
                params.append(s_staff_id)
            if full_name:
                sql_query += " AND full_name = %s"
                params.append(full_name)
            if s_office:
                sql_query += " AND office = %s"
                params.append(s_office)
            if s_group:
                sql_query += " AND group = %s"
                params.append(s_group)

            cur.execute(sql_query, params)

            data = cur.fetchall()
            print("検索結果：" + str(data))
            cur.close()
            return data

    except Exception as e:
        print(f"検索エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def Attendance_history(uuid):
    error_msg = []
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            
            sql_query = 'SELECT * FROM job_history WHERE uuid = %s'
            cur.execute(sql_query,(uuid))
            result = cur.fetchall()
            cur.close()
            return result
    except Exception as e:
        print(f"エラー：{str(e)}")
        return None