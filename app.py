# 必要なモジュールをインポート
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL  # DB使用
from flask_socketio import SocketIO,emit  # ICカードリーダー
from config import Config  # 接続情報
from app_function import *  # 生成系関数
from form_validation import *  # バリデーション系
from db_process import *  # DB処理系
from datetime import datetime
import nfc
import threading
import time

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, manage_session=True)
mail = Mail(app)
# ユーザーが読み取ったICカードのIDを一時的に格納する変数
temp_ic_idm = None  # 追加
# session用の秘密鍵をsecret_keyの値代入
app.secret_key = 'hal_2023'

mysql = MySQL(app)
error_msg = []


#------------ルートURL("/")にアクセス------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':    
        if 'user' in session and 'auth' in session:
            return render_template('index.html')
        else:
            return redirect(url_for('login'))

    if request.method == 'POST':
        error_msg = []
        result = []
        #出勤ボタンの処理
        if 'r_attendance' in request.form:
            if attendance(session['user'][0], today(), now()):
                print(today())
                print(now())
                error_msg.append("出勤しました。")
                return render_template("index.html", error_msg=error_msg)
            else:
                error_msg.append("すでに打刻済みです。")
                return render_template("index.html", error_msg=error_msg)
        elif 'work-out' in request.form:
            if work_out(session['user'][0], today(), now()):
                print(today())
                print(now())
                error_msg.append("退勤しました。")
                return render_template("index.html", error_msg=error_msg)
            else:
                error_msg.append("出勤データが見つからないか、すでに退勤済みです。")
                return render_template("index.html", error_msg=error_msg)
        
        elif 'settings' in request.form:
            return redirect(url_for('settings'))
        
        elif 'Attendance' in request.form:
            if Attendance_history(uuid):
                return render_template("job_history.html",result=result)
            else:
                error_msg.append("取得時にエラーが発生しました。")
                return render_template("index.html",error_msg=error_msg)
            
        elif 'logout' in request.form:
            session.pop('user', None)  # ログアウト時にセッションから'user'を削除
            session.pop('auth', None)  # ログアウト時にセッションから'auth'を削除

            return redirect(url_for('login'))

    return render_template('index.html', error_msg=error_msg)

#------------ログインページ("/login")へアクセス------------
@app.route('/user/login', methods=['GET', 'POST'])
def login():
    error_msg = []
    
    # session['auth_flag'] の初期化
    if 'auth_flag' not in session:
        session['auth_flag'] = None  # もしくはデフォルトの値に置き換える
        
    global temp_ic_idm  # グローバル変数として使用するため、関数内で参照する
    if request.method == 'GET':
        temp_ic_idm = None
        if 'user' in session and 'auth' in session:
            return redirect("/")
        else:
            return render_template('login.html')
        
    if request.method == 'POST':
        print("フラグ" + str(session['auth_flag']))  # auth_flagをstrに変換して連結
        mail = request.form.get('mail', '')
        password = request.form.get('password', '')
        authcode = request.form.get('authcode', '')
        app_authcode = request.form.get('app_authcode', '')
        
        if authcode and session['auth_flag'] == 1:
            if login_confirm_sms(session['user'][0] ,authcode):
                session['auth'] = True
                return redirect("/")
            else:
                error_msg.append("認証コードが間違っています")
                return render_template("confirm_sms.html",error_msg=error_msg)
        
        elif 'register_btn' in request.form and session.get('auth_flag') == 2:
            if temp_ic_idm:
                print(session['user'][0])
                print(temp_ic_idm)
                if confirm_idm(session['user'][0], temp_ic_idm):
                    print("アカウントに紐づけられているIdmと一致しました。")
                    session['auth'] = True
                    return redirect("/")
                else:
                    print("紐づけられているIdmと一致しません。")
                    error_msg.append("※このカードはアカウントに登録されていません。")
                    return render_template("login.html",error_msg=error_msg)
            else:
                print("※Idmが読み取られていません。")
                error_msg.append("※カードのIdmが読み取れませんでした。")
                return render_template("scan_ic.html",error_msg=error_msg)
            
        elif 'app_authcode_send_btn' in request.form and session.get('auth_flag') == 3:
            if confirm_app_authcode(app_authcode):
                session['auth'] = True
                return redirect("/")
            else:
                error_msg.append("認証コードが正しくありません。正しいコードを入力してください。")
                return render_template("confirm_app.html",error_msg=error_msg)
            
        elif login_trial(mail, password, error_msg):
            if session['user'][19] == 0: #初回ログインはパスワード変更ページに移動させる
                return redirect(url_for("change_password"))
            
            elif session['user'][20] == 1:#SMS認証フラグ
                session['auth_flag'] = 1
                print("セッション：" + str(session['auth_flag']))
                if login_authcode(session['user'][0]):
                    return render_template("confirm_sms.html")
                else:
                    error_msg.append("認証コードの送信に失敗しました。")
                    return render_template("login.html", error_msg=error_msg)
            elif session['user'][21] == 1:#ICカードフラグ
                    session['auth_flag'] = 2
                    print("セッション：" + str(session['auth_flag']))
                    threading.Thread(target=nfc_reader_once).start()
                    return render_template("scan_ic.html",error_msg=error_msg)
            elif session['user'][22] == 1:#認証アプリフラグ
                    session['auth_flag'] = 3
                    print("セッション：" + str(session['auth_flag']))
                    return render_template("confirm_app.html")
            else:
                session['auth'] = True
                return redirect("/")
        else:
            return render_template("login.html", error_msg=error_msg)
    else:
        return render_template("login.html", error_msg=[])

#------------ユーザー登録ページ("/user/register")へアクセス------------
@app.route('/user/register', methods=['GET', 'POST'])
def register():
    
    error_msg = []
    
    if request.method == 'GET':
        return render_template('register.html')
    
    if request.method == 'POST':
        session.permanent = True
        
        # フォームの値を変数に代入する
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        first_name_kana = request.form['first_name_kana']
        last_name_kana = request.form['last_name_kana']
        tel = request.form['tel']
        mail = request.form['mail']
        sex = request.form['sex']
        b_year = request.form['b_year']
        b_month = request.form['b_month']
        b_day = request.form['b_day']
        postcode = request.form['postcode']
        add1 = request.form['add1']
        add2 = request.form['add2']
        add3 = request.form['add3']
        add4 = request.form['add4']
        office = request.form['office']
        group = request.form['group']
        j_year = request.form['j_year']
        j_month = request.form['j_month']
        j_day = request.form['j_day']
        
        # フォームのバリデーションをする
        with app.app_context():
            cur = mysql.connection.cursor()
            error_msg = form_register_validation(cur, first_name, last_name, first_name_kana, last_name_kana, tel, mail, sex, b_year, b_month, b_day, postcode, add1, add2, add3, office, group, j_year, j_month, j_day)
            cur.close()
            
        # バリデーションエラーがなかった時に実行
        if not error_msg:
            uuid = gen_uuid()
            staff_id = genarate_staff_id()
            full_name = first_name + last_name
            full_name_kana = first_name_kana + last_name_kana 
            password = gen_password()
            hased_password = hash_password(password)
            birthDay = b_year + "/" + b_month + "/" + b_day
            join_day = j_year + "/" + j_month + "/" + j_day
            leave_day = "9999-12-31"  # 仮で入れる
            create_at = today()
            update_at = str(today()) + " _新規登録@jinji" #仮で入れる
            address = add1 + add2 + add3 + add4
            login_flag = 0
            password_flag = 0
            sms_flag = 0
            card_flag = 0 
            app_flag = 0
            auth_flag = 0
            role = 0
            
            # DBに登録するデータ
            data = {
                'uuid': uuid,
                'staff_id': staff_id,
                'full_name': full_name,
                'full_name_kana': full_name_kana,
                'password': hased_password,
                'mail': mail,
                'tel': tel,
                'birthday': birthDay,
                'sex': sex,
                'office': office,
                'office_group': group,
                'join_day': join_day,
                'leave_day': leave_day,
                'create_at': create_at,
                'update_at': update_at,
                'login_flag': login_flag,
                'password_flag': password_flag,
                'sms_flag': sms_flag,
                'card_flag': card_flag,
                'app_flag': app_flag,
                'postcode': postcode,
                'address': address,                
                'auth_flag': auth_flag,    
                'role': role            

            }
            
            if temp_register(data,password):
                return redirect(url_for("login"))
            else:
                # 登録できなかったときのelse
                error_msg.append("登録エラー")
                return render_template("register.html", error_msg=error_msg)
            
    return render_template("register.html", error_msg=error_msg)

#------------ユーザー登録ページ("/user/register")へアクセス------------
@app.route('/user/jinji/', methods=['GET', 'POST'])
def staff_list():
    error_msg = []
    if request.method == 'GET':
        if session.get('user') == "":
            return redirect("login")
        else:
            user_role = session['user'][23]
            if user_role == 12:
                return render_template("search_staff.html")
            error_msg.append("権限不足のため、閲覧できません。")
            return redirect("/")
        
    if request.method == 'POST':
        s_staff_id = request.form.get('s_staff_id')
        full_name =  request.form.get('full_name')
        s_office = request.form.get('s_office')
        s_group = request.form.get('s_group')

        result = search_data(s_staff_id, full_name, s_office, s_group)        
        if result:
            return render_template("search_staff.html", result=result, error_msg=error_msg)
        else:
            error_msg.append("見つかりませんでした。")
            return render_template("search_staff.html", result=result, error_msg=error_msg)
#------------パスワード変更ページ("/user/change_password")へアクセス------------
@app.route('/user/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'GET':
        
        if  'user' in session:
            user = session['user']
            return render_template('change_password.html')
        else:
            return redirect(url_for('login'))
        
    if request.method == 'POST':
        error_msg = []

        #フォームから入力内容を取得
        o_password = request.form['o_password']
        n_password = request.form['n_password']
        n_password_r = request.form['n_password_r']
        
        with app.app_context():
            cur = mysql.connection.cursor()
            error_msg = password_change_validation(cur, o_password,n_password,n_password_r,session['user'][0])
            cur.close()
            
        if not error_msg:
            print(error_msg)
            new_password = hash_password(n_password)
            
            print(new_password)
            
            if c_password(session['user'][0],new_password):
                return redirect("/")
            else:
                print("エラー")
                return render_template("change_password.html", error_msg=error_msg)

    return render_template('change_password.html')

#------------個人設定ページ("/user/settings")へアクセス------------
@app.route('/user/settings', methods=['GET', 'POST'])
def settings():
    
    if request.method == 'GET':
        if 'user' in session:
            tel = mask_tel(session['user'][8])
            idm = hide_characters(str(session['user'][24]))
            return render_template('settings.html', tel=tel,idm=idm)
        else:
            return (url_for('login'))
    
    if request.method == 'POST':
        error_msg = []
        if 'confirm_sms' in  request.form:
            authcode = generate_authcode()
            if send_register_authcode(session['user'][0],authcode):
                session['authcode'] = authcode 
                return redirect(url_for('confirm_sms'))
            else:
                return render_template('settings.html', error_msg=error_msg)
            
        if 'change_tel' in request.form:
            return redirect(url_for('change_tel'))
        
        if 'f_settings' in request.form:
            auth_format = request.form.get('auth_format')
            if not auth_format:  # auth_format が空の場合
                error_msg.append("ログイン認証形式を選択してください。")
                return render_template("settings.html", error_msg=error_msg)
            else:
                if change_auth_format(session['user'][0],auth_format):
                    return redirect("/")
                else:
                    return render_template("settings.html",error_msg=error_msg)
                
        
        if 'scan_ic' in request.form:
            return redirect(url_for("scan_ic"))
        
        if 'change_ic' in request.form:
            return redirect(url_for("scan_ic"))
        
        if 'r_app' in request.form:
            return redirect(url_for("register_app"))
        
            
    return render_template('settings.html', error_msg=[])

#------------認証アプリ登録ページ("/user/register_app")へアクセス------------
@app.route('/user/register_app', methods=['GET', 'POST'])
def register_app():
    if request.method == 'GET':
        genarate_qr()
        return render_template("register_app.html")
    
    if request.method == 'POST':
        app_authcode = request.form['app_authcode']
        
        if f_confirm_app_authcode(app_authcode, session['user'][0]):
            return redirect(url_for("settings"))
        else:
            return render_template("register_app.html",error_msg=error_msg)

#------------電話番号登録ページ("/user/change_tel")へアクセス------------
@app.route('/user/change_tel', methods=['GET', 'POST'])
def change_tel():
    if request.method == 'GET':
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('change_tel.html')

    if request.method == 'POST':
        error_msg = [];
        tel = request.form['tel']
        authcode = generate_authcode()
        uuid =  session['user'][0] 
        
        if update_tel(uuid,tel,authcode):
            return redirect("confirm_sms")
        else:
            return render_template("change_tel.html", error_msg=error_msg)
#------------認証コード確認ページ("/user/confirm_sms")へアクセス------------       
@app.route('/user/confirm_sms', methods=['GET', 'POST'])
def confirm_sms():
    if request.method == 'GET':
        return render_template("confirm_sms.html")

    if request.method == 'POST':
        error_msg = []
        authcode = request.form['authcode']
        print(authcode)
        print(session['user'][0])
        
        if f_confirm_app_authcode(authcode,session['user'][0]):
            return redirect(url_for('settings'))
        else:
            error_msg.append("認証コードが正しくありません。再度入力してください。")
            return render_template("confirm_sms.html", error_msg=error_msg)

#------------ICカード登録ページ("/user/method_ic")へアクセス------------
@app.route('/user/scan_ic', methods=['GET', 'POST'])
def scan_ic():
    global temp_ic_idm  # グローバル変数として使用するため、関数内で参照する

    if request.method == 'GET':
        # 最初に読み込まれたときに直接 NFC カードを読み取る
        temp_ic_idm = None
        if temp_ic_idm is None:
            threading.Thread(target=nfc_reader_once).start()

    if request.method == 'POST':
        # 登録ボタンが押されたら、格納されたICカードのIDをデータベースに登録する
        if 'register_btn' in request.form:
            if temp_ic_idm:
                print(session['user'][0])
                print(temp_ic_idm)
                if register_card_uid(session['user'][0], temp_ic_idm):
                    print("登録ボタンが押されました。カードのUIDをデータベースに登録しました。")
                    return redirect(url_for('settings'))
                else:
                    print("登録ボタンが押されましたが、カードのUIDの登録に失敗しました。")
                    # 登録に失敗した場合の処理（エラーメッセージなど）
                    return redirect(url_for('method_ic'))
            else:
                print("登録ボタンが押されましたが、ICカードのIDが取得されていません。")
                # ICカードのIDが取得されていない場合の処理（エラーメッセージなど）
                return redirect(url_for('scan_ic'))

    # GETリクエストの場合は、テンプレートにtemp_ic_idmを渡す
    return render_template("scan_ic.html", ic_idm=temp_ic_idm)

#------------SocketIOイベント: カードのIDを受信したとき------------
@socketio.on('read_card')
def handle_read_card():
    if temp_ic_idm:
        emit('card_id_received', {'card_id': temp_ic_idm})
        
def nfc_reader_once():
    global temp_ic_idm  # グローバル変数として使用するため、関数内で参照する

    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("NFCリーダーを初期化しました。")
            tag = clf.connect(rdwr={'on-connect': lambda tag: False})
            ic_idm = tag.identifier.hex()
            print(f"カードのUID：{ic_idm}")

            # カードのUIDを一時的に変数に格納する
            temp_ic_idm = ic_idm

            # SocketIOを使用してクライアントにカードIDを送信
            socketio.emit('card_id_received', {'card_id': ic_idm})
    except Exception as e:
        print(f"エラー：{e}")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')