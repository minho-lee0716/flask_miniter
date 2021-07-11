from sqlalchemy import create_engine, text

from flask.json import JSONEncoder
from flask      import (
    Flask,
    request,
    jsonify,
    current_app
)

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
    def tweet():
        user_tweet = request.json
        tweet      = user_tweet['tweet']

        if len(tweet) > 300:
            return '300자를 초과했습니다', 400

        app.database.execute(text("""
            INSERT INTO tweets (
                user_id,
                tweet
            ) VALUES (
                :id,
                :tweet
            )
        """), user_tweet)

        return '', 200

    @app.route('/follow', methods=['POST'])
    def follow():
        data = request.json

        if data['user_id'] == data['follow_user_id']:
            return jsonify({'message':'Can not follow yourself'}), 400

        if check_follow(data):
            return jsonify({'message':'Already Followed'}), 400
        else:
            insert_follow(data)
            return '', 200

    @app.route('/unfollow', methods=['DELETE'])
    def unfollow():
        data = request.json

        app.database.execute(text("""
            DELETE FROM users_follow_list
            WHERE user_id = :user_id and follow_user_id = :follow_user_id
        """), data)

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
