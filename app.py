from sqlalchemy import create_engine, text

from flask.json import JSONEncoder
from flask      import (
    Flask,
    request,
    Response,
    jsonify,
    current_app
)

import bcrypt, jwt
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                payload = None

            if payload is None: return Response(status=401)

            user_id = payload['user_id']
            g.user_id = user_id
            g.user = get_user_info(user_id) if user_id else None

        else:
            return Response(status=401)

        return f(*args, **kwargs)
    return decorated_function

'''
Default JSON encoder는 set를 JSON으로 변환할 수 없다.
그러므로 커스텀 엔코더를 작성해서 set을 list로 변환하여
JSON으로 변환 가능하게 해주어야 한다.
'''
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return JSONEncoder.default(self, obj)

def check_follow(data):
    check_follow_table = current_app.database.execute(text("""
        SELECT user_id, follow_user_id
        FROM users_follow_list
        WHERE user_id = :user_id and follow_user_id = :follow_user_id
    """), data).fetchone()

    return True if check_follow_table else False

def insert_follow(data):
    return current_app.database.execute(text("""
        INSERT INTO  users_follow_list (
            user_id,
            follow_user_id
        ) VALUES (
            :user_id,
            :follow_user_id
        )
    """), data)

def create_app(test_config=None):
    app = Flask(__name__)

    app.json_encoder = CustomJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding='utf-8', max_overflow=0)
    app.database = database

    @app.route("/ping", methods=['GET'])
    def ping():
        return "pong"

    @app.route("/sign-up", methods=['POST'])
    def sign_up():
        # 정보 받아오기
        new_user    = request.json
        new_user['password'] = bcrypt.hashpw(
            new_user['password'].encode('utf-8'),
            bcrypt.gensalt()
        )



        # 받아온 정보로 사용자 생성
        # new_user_id에는 생성된 사용자의 id가 저장
        new_user_id = app.database.execute(text("""
            INSERT INTO users (
                name,
                email,
                profile,
                hashed_password
            ) VALUES (
                :name,
                :email,
                :profile,
                :password
            )
        """), new_user).lastrowid
        new_user_info = get_user(new_user_id) 

        return jsonify(new_user_info)

        # row는 생성된 사용자의 정보를 읽음
        row = current_app.database.execute(text("""
            SELECT
                id,
                name,
                email,
                profile
            FROM users
            WHERE id = :user_id
        """), {
            'user_id' : new_user_id
        }).fetchone()


        # 읽어 들인 사용자의 정보를 created_user라는 변수에 저장
        # created_user라는 변수를 json으로 리턴 할 수 있도록 딕셔너리 형태로..
        created_user = {
            'id'      : row['id'],
            'name'    : row['name'],
            'email'   : row['email'],
            'profile' : row['profile']
        } if row else None

        return jsonify(created_user)

    @app.route('/tweet', methods=['POST'])
    @login_required
    def tweet():
        user_tweet = request.json
        tweet      = user_tweet['tweet']

        if len(tweet) > 300:
            return '300자를 초과했습니다', 400

        insert_tweet(user_tweet)
        return '', 200

    @app.route('/follow', methods=['POST'])
    @login_required
    def follow():
        payload = request.json
        insert_follow(payload)

        return '', 200

    @app.route('/unfollow', methods=['DELETE'])
    @login_required
    def unfollow():
        payload = request.json
        insert_unfollow(payload)

        return '', 200

    @app.route('/timeline/<int:user_id>', methods=['GET'])
    def timeline(user_id):
        rows = app.database.execute(text("""
            SELECT
                t.user_id,
                t.tweet
            FROM tweets t
            LEFT JOIN users_follow_list ufl
            ON ufl.user_id = :user_id
            WHERE t.user_id = :user_id
            OR t.user_id = ufl.follow_user_id
        """), {'user_id':user_id}
        ).fetchall()

        timeline = [{
            'user_id' : row['user_id'],
            'tweet'   : row['tweet']
        } for row in rows]

        return jsonify({
            'user_id' : user_id,
            'timeline' : timeline
        })

    return app

    @app.route('/test'), methods=['GET'])
    def testapi():
        return 'Hello World'
