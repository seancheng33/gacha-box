"""《欧皇运维所》—— 盲盒抽卡小游戏（Flask + SQLite）

启动：python app.py            → http://127.0.0.1:5000
管理：python app.py create-admin <用户名> <密码>
"""
import hmac
import os
import secrets
import uuid
from datetime import datetime

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import generate_password_hash

import admin as admin_module
import auth
import collection
import db
import economy
import gacha
import rank
import seed_cards

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class InsufficientCoins(Exception):
    def __init__(self, coins):
        super().__init__("金币不足")
        self.coins = coins


def _secret_key():
    """优先环境变量；否则落盘持久化，避免重启导致所有人掉线。"""
    key = os.environ.get("GACHA_SECRET_KEY")
    if key:
        return key
    path = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def bootstrap(app):
    conn = db.connect(app.config["DB_PATH"])
    try:
        db.init_schema(conn)
        if conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"] == 0:
            seed_cards.seed(conn)
        if not conn.execute("SELECT 1 FROM app_config WHERE key='weights'").fetchone():
            gacha.save_weights(conn, gacha.DEFAULT_WEIGHTS)
    finally:
        conn.close()


def create_app(db_path=None, testing=False):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=_secret_key(),
        DB_PATH=db_path or os.environ.get("GACHA_DB") or os.path.join(BASE_DIR, "gacha.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        TESTING=testing,
    )
    app.teardown_appcontext(db.close_db)
    app.register_blueprint(admin_module.bp)
    bootstrap(app)

    # ---------- 横切：CSRF、模板全局 ----------
    @app.before_request
    def ensure_csrf():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
            if not token or not hmac.compare_digest(token, session["_csrf"]):
                abort(400, description="CSRF 校验失败，请刷新页面重试")

    @app.context_processor
    def inject_globals():
        return {
            "RARITY": gacha.RARITY_META,
            "csrf_token": lambda: session.get("_csrf", ""),
            "me": auth.current_user(db.get_db()) if session.get("uid") else None,
            "SIGNIN_REWARD": economy.SIGNIN_REWARD,
            "COST_SINGLE": gacha.COST_SINGLE,
            "COST_TEN": gacha.COST_TEN,
            "PITY_LIMIT": gacha.PITY_LIMIT,
        }

    # ---------- 认证 ----------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            conn = db.get_db()
            try:
                with db.transaction(conn):
                    user = auth.register(conn, username, password, economy.REGISTER_COINS)
                session.clear()
                session["uid"] = user["id"]
                session["username"] = user["username"]
                session["is_admin"] = bool(user["is_admin"])
                session["_csrf"] = secrets.token_hex(16)
                flash("注册成功，赠送 %d 金币，祝你欧气满满" % economy.REGISTER_COINS, "ok")
                return redirect(url_for("index"))
            except ValueError as exc:
                flash(str(exc), "error")
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            conn = db.get_db()
            user, err = auth.verify(conn, request.form.get("username", ""),
                                    request.form.get("password", ""))
            if err:
                flash(err, "error")
            else:
                session.clear()
                session["uid"] = user["id"]
                session["username"] = user["username"]
                session["is_admin"] = bool(user["is_admin"])
                session["_csrf"] = secrets.token_hex(16)
                return redirect(url_for("index"))
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------- 主页与抽卡 ----------
    @app.get("/")
    @auth.login_required
    def index():
        conn = db.get_db()
        uid = session["uid"]
        recent = [dict(r) for r in conn.execute(
            "SELECT d.created_at, d.is_pity, c.name, c.emoji, c.rarity "
            "FROM draws d JOIN cards c ON c.id = d.card_id "
            "WHERE d.user_id=? ORDER BY d.id DESC LIMIT 8", (uid,))]
        got, total, pct = collection.progress(conn, uid)
        return render_template("index.html", recent=recent,
                               got=got, total=total, pct=pct,
                               weights=gacha.load_weights(conn))

    @app.post("/draw")
    @auth.login_required
    def draw():
        mode = request.form.get("mode") or (request.get_json(silent=True) or {}).get("mode", "single")
        count = 10 if mode == "ten" else 1
        cost = gacha.COST_TEN if count == 10 else gacha.COST_SINGLE
        conn = db.get_db()
        uid = session["uid"]
        batch_id = uuid.uuid4().hex
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with db.transaction(conn):
                user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
                if user["coins"] < cost:
                    raise InsufficientCoins(user["coins"])
                weights = gacha.load_weights(conn)
                owned = collection.owned_ids(conn, uid)
                results, new_pity = gacha.draw_batch(
                    conn, user["pity_count"], weights, count)
                cards = []
                for card, is_pity in results:
                    conn.execute(
                        "INSERT INTO draws(user_id, card_id, batch_id, is_pity, created_at) "
                        "VALUES(?, ?, ?, ?, ?)",
                        (uid, card["id"], batch_id, 1 if is_pity else 0, now))
                    held = collection.add_card(conn, uid, card["id"], now)
                    is_new = card["id"] not in owned
                    owned.add(card["id"])
                    cards.append({
                        "id": card["id"], "name": card["name"], "rarity": card["rarity"],
                        "rarity_name": gacha.RARITY_NAMES[card["rarity"]],
                        "emoji": card["emoji"], "description": card["description"],
                        "image": card.get("image"), "count": held,
                        "is_new": is_new, "is_pity": is_pity,
                    })
                balance = user["coins"] - cost
                conn.execute("UPDATE users SET coins=?, pity_count=? WHERE id=?",
                             (balance, new_pity, uid))
        except InsufficientCoins as exc:
            return jsonify(ok=False, coins=exc.coins,
                           error="金币不足：单抽需 %d，十连需 %d，当前 %d"
                                 % (gacha.COST_SINGLE, gacha.COST_TEN, exc.coins)), 400
        return jsonify(ok=True, cards=cards, coins=balance,
                       pity=new_pity, pity_limit=gacha.PITY_LIMIT)

    @app.post("/checkin")
    @auth.login_required
    def checkin():
        conn = db.get_db()
        with db.transaction(conn):
            ok, msg = economy.signin(conn, session["uid"])
        flash(msg, "ok" if ok else "error")
        return redirect(url_for("index"))

    # ---------- 图鉴与排行 ----------
    @app.get("/album")
    @auth.login_required
    def album():
        conn = db.get_db()
        rarity = request.args.get("rarity", type=int)
        if rarity not in (1, 2, 3, 4, 5):
            rarity = None
        cards = collection.album(conn, session["uid"], rarity)
        got, total, pct = collection.progress(conn, session["uid"])
        return render_template("album.html", cards=cards, rarity=rarity,
                               got=got, total=total, pct=pct)

    @app.get("/rank")
    @auth.login_required
    def ranking():
        conn = db.get_db()
        return render_template("rank.html",
                               by_collection=rank.by_collection(conn),
                               by_ssr=rank.by_ssr(conn),
                               by_draws=rank.by_draws(conn))

    # ---------- 错误页 ----------
    @app.errorhandler(400)
    def bad_request(err):
        return render_template("error.html", code=400,
                               message=getattr(err, "description", "请求参数有误")), 400

    @app.errorhandler(403)
    def forbidden(err):
        return render_template("error.html", code=403,
                               message="没有权限访问这里"), 403

    @app.errorhandler(404)
    def not_found(err):
        return render_template("error.html", code=404,
                               message="页面不存在"), 404

    return app


def main():
    import sys

    app = create_app()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if cmd in ("initdb", "seed", "create-admin"):
        conn = db.connect(app.config["DB_PATH"])
        db.init_schema(conn)
        if cmd == "initdb":
            print("表结构就绪：%s" % app.config["DB_PATH"])
        elif cmd == "seed":
            n = seed_cards.seed(conn, verbose=True)
            print("seed 完成，新增 %d 张卡" % n)
        else:
            if len(sys.argv) < 4:
                print("用法: python app.py create-admin <用户名> <密码>")
                sys.exit(1)
            username, password = sys.argv[2], sys.argv[3]
            _, err = auth.validate_credentials(username, password)
            if err:
                print("error: %s" % err)
                sys.exit(1)
            row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            with db.transaction(conn):
                if row:
                    conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (row["id"],))
                else:
                    conn.execute(
                        "INSERT INTO users(username, password_hash, coins, is_admin, created_at) "
                        "VALUES(?, ?, ?, 1, ?)",
                        (username, generate_password_hash(password), economy.REGISTER_COINS,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            print("管理员就绪：%s" % username)
        conn.close()
        return

    port = int(os.environ.get("PORT", 5000))
    print("《欧皇运维所》已启动 → http://127.0.0.1:%d" % port)
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
