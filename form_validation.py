from app_function import *
from db_process import *
import re
def form_register_validation(cursor, first_name, last_name, first_name_kana, last_name_kana, tel, mail, sex, b_year, b_month, b_day, postcode, add1, add2, add3, office, group,j_year,j_month,j_day):
    error_msg = []

    # 以下は既存のバリデーションルール
    if not first_name:
        error_msg.append("※苗字を入力してください.")

    if not last_name:
        error_msg.append("※名前を入力してください.")

    if not first_name_kana:
        error_msg.append("※苗字（カナ）を入力してください.")

    if not last_name_kana:
        error_msg.append("※名前（カナ）を入力してください.")

    if not tel:
        error_msg.append("※電話番号を入力してください.")

    if not mail:
        error_msg.append("※メールアドレスを入力してください.")
    else:
        cursor.execute('SELECT COUNT(*) as count FROM staff_list WHERE mail = %s', (mail,))

        count = cursor.fetchone()[0]
        if count > 0:
            error_msg.append("※既に登録されているメールアドレスです.")

    if not sex:
        error_msg.append("※性別を選択してください.")

    if not b_year or not b_month or not b_day:
        error_msg.append("※生年月日を入力してください.")
    elif not (1900 <= int(b_year) <= 2024) or not (1 <= int(b_month) <= 12) or not (1 <= int(b_day) <= 31):
        error_msg.append("※正しい形式で生年月日を入力してください.")

    if not postcode:
        error_msg.append("※郵便番号を入力してください.")

    if not add1:
        error_msg.append("※都道府県を入力してください.")

    if not add2:
        error_msg.append("※市区町村を入力してください.")
        
    if not add3:
        error_msg.append("※町名・番地を入力してください.")        

    if not office:
        error_msg.append("※所属オフィスを入力してください.")

    if not group:
        error_msg.append("※所属部署を選択してください.")
        
    if j_year == '-' or j_month == '-' or j_day == '-':
        error_msg.append("※入社年月日を入力してください.")
    return error_msg


def password_change_validation(cur, o_password, n_password, r_new_password, uuid):
    error_msg = []

    # 現在のパスワードが入力されているかどうかをチェック
    if not o_password:
        #print("現在のパスワードを入力してください。")
        error_msg.append("現在のパスワードを入力してください。")
    else:
        # データベースからユーザーの情報を取得
        cur = mysql.connection.cursor()
        sql_query = "SELECT * FROM staff_list WHERE uuid = %s"
        cur.execute(sql_query, (uuid,))
        result = cur.fetchone()
        
        if result:
            stored_salt = result[4][:29].encode('utf-8')
            hashed_input_password = bcrypt.hashpw(o_password.encode('utf-8'), stored_salt)
            if hashed_input_password != result[4].encode('utf-8'):
                #print("現在のパスワードが一致しません。")
                error_msg.append("現在のパスワードが一致しません。")

    # 新しいパスワードが入力されているかどうかをチェック
    if not n_password:
        #print("新しいパスワードを入力してください。")
        error_msg.append("新しいパスワードを入力してください。")
    else:
        # パスワードの強度をチェック
        password_errors = password_strong_tester(n_password)
        if password_errors:
            print("\n".join(password_errors))
            error_msg.extend(password_errors)

    # 新しいパスワード（確認用）が入力されているかどうかをチェック
    if not r_new_password:
        #print("新しいパスワード（確認用）を入力してください。")
        error_msg.append("新しいパスワード（確認用）を入力してください。")
    else:
        # 新しいパスワードと確認用のパスワードが一致しているかどうかをチェック
        if n_password != r_new_password:
            #print("新しいパスワードが一致しません。")
            error_msg.append("新しいパスワードが一致しません。")
            
    return error_msg

def password_strong_tester(password):
    error_msg = []

    # パスワードの長さが8文字以上であることを確認
    if len(password) < 8:
        error_msg.append("パスワードは8文字以上でなければなりません")
    
    # 大文字、小文字、数字、特殊文字のいずれかを含むかどうかをチェック
    if not re.search(r"[A-Z]", password):
        error_msg.append("パスワードには少なくとも1つの大文字を含めてください")
    if not re.search(r"[a-z]", password):
        error_msg.append("パスワードには少なくとも1つの小文字を含めてください")
    if not re.search(r"\d", password):
        error_msg.append("パスワードには少なくとも1つの数字を含めてください")
    if not re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~@]", password):
        error_msg.append("パスワードには少なくとも1つの記号を含めてください")

    return error_msg

