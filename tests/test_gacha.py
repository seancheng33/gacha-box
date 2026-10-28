"""功能测试：概率分布、双保底、事务回滚、认证、收集、排行榜、后台、CSRF。

运行： .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
import os
import random
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
import collection
import db
import gacha
from app import create_app

CARD_COUNT = 30


class FixedRng:
    """确定性随机源：random() 恒返回 v，choice() 恒取第一个。"""

    def __init__(self, v):
        self.v = v

    def random(self):
        return self.v

    def choice(self, seq):
        return seq[0]


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gacha_test_")
        self.db_path = os.path.join(self.tmp, "test.db")
        self.app = create_app(db_path=self.db_path, testing=True)
        self.client = self.app.test_client()
        auth.reset_rate_limit()
        self.client.get("/login")
        self.refresh_csrf()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def refresh_csrf(self):
        with self.client.session_transaction() as s:
            self.csrf = s.get("_csrf", "")

    def post(self, path, **data):
        data["_csrf"] = self.csrf
        resp = self.client.post(path, data=data)
        self.refresh_csrf()
        return resp

    def register(self, username="alice", password="secret123"):
        resp = self.post("/register", username=username, password=password)
        return resp

    def sql(self, query, params=()):
        conn = db.connect(self.db_path)
        try:
            cur = conn.execute(query, params)
            return cur.fetchall()
        finally:
            conn.close()

    def execute(self, query, params=()):
        conn = db.connect(self.db_path)
        try:
            conn.execute(query, params)
        finally:
            conn.close()

    def conn(self):
        return db.connect(self.db_path)

    def login(self, username="alice", password="secret123"):
        return self.post("/login", username=username, password=password)

    def logout(self):
        """退出后会话被清空，需重新取一次 token（模拟浏览器跳到登录页）。"""
        self.post("/logout")
        self.client.get("/login")
        self.refresh_csrf()

    def make_admin(self, username="alice"):
        self.execute("UPDATE users SET is_admin=1 WHERE username=?", (username,))
        self.login(username)
        self.refresh_csrf()
        with self.client.session_transaction() as s:
            s["is_admin"] = True


class ProbabilityTests(BaseCase):
    def test_distribution_within_tolerance(self):
        weights = dict(gacha.DEFAULT_WEIGHTS)
        rng = random.Random(42)
        n = 100000
        counts = {k: 0 for k in weights}
        for _ in range(n):
            counts[gacha.pick_rarity(weights, rng)] += 1
        for rarity, expected in weights.items():
            actual = counts[rarity] * 100.0 / n
            self.assertLess(abs(actual - expected), 0.6,
                            "等级 %d 实测 %.2f%% 偏离预期 %.2f%%" % (rarity, actual, expected))

    def test_zero_weight_never_drawn(self):
        weights = {1: 0, 2: 40, 3: 30, 4: 20, 5: 10}
        rng = random.Random(7)
        seen = {gacha.pick_rarity(weights, rng) for _ in range(20000)}
        self.assertNotIn(1, seen)

    def test_all_weight_on_ssr(self):
        weights = {1: 0, 2: 0, 3: 0, 4: 0, 5: 100}
        rng = random.Random(1)
        for _ in range(200):
            self.assertEqual(5, gacha.pick_rarity(weights, rng))


class PityTests(BaseCase):
    def test_forced_ssr_on_60th_draw(self):
        conn = self.conn()
        try:
            card, pity, is_pity = gacha.draw_one(conn, 59, dict(gacha.DEFAULT_WEIGHTS), FixedRng(0.0))
            self.assertEqual(5, card["rarity"])
            self.assertTrue(is_pity)
            self.assertEqual(0, pity)
        finally:
            conn.close()

    def test_pity_accumulates_before_limit(self):
        conn = self.conn()
        try:
            card, pity, is_pity = gacha.draw_one(conn, 0, dict(gacha.DEFAULT_WEIGHTS), FixedRng(0.0))
            self.assertEqual(1, card["rarity"])
            self.assertFalse(is_pity)
            self.assertEqual(1, pity)
        finally:
            conn.close()

    def test_pity_resets_on_natural_ssr(self):
        conn = self.conn()
        try:
            card, pity, is_pity = gacha.draw_one(conn, 12, dict(gacha.DEFAULT_WEIGHTS), FixedRng(0.999))
            self.assertEqual(5, card["rarity"])
            self.assertFalse(is_pity)
            self.assertEqual(0, pity)
        finally:
            conn.close()

    def test_ten_pull_guarantees_epic_when_all_low(self):
        conn = self.conn()
        try:
            results, pity = gacha.draw_batch(conn, 0, dict(gacha.DEFAULT_WEIGHTS), 10, FixedRng(0.0))
            self.assertEqual(10, len(results))
            self.assertEqual(3, results[0][0]["rarity"], "十连保底应把第一张替换为史诗")
            self.assertTrue(any(card["rarity"] >= 3 for card, _ in results))
            self.assertEqual(10, pity)
        finally:
            conn.close()

    def test_ten_pull_no_replacement_when_epic_present(self):
        conn = self.conn()
        try:
            results, _ = gacha.draw_batch(conn, 0, dict(gacha.DEFAULT_WEIGHTS), 10, FixedRng(0.9))
            self.assertTrue(all(card["rarity"] == 3 for card, _ in results))
        finally:
            conn.close()


class DrawApiTests(BaseCase):
    def test_unauthenticated_redirect(self):
        resp = self.client.get("/")
        self.assertEqual(302, resp.status_code)
        self.assertIn("/login", resp.headers["Location"])

    def test_csrf_required(self):
        self.register()
        resp = self.client.post("/draw", data={"mode": "single"})
        self.assertEqual(400, resp.status_code)

    def test_single_draw_costs_and_records(self):
        self.register()
        resp = self.post("/draw", mode="single")
        self.assertEqual(200, resp.status_code)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(1, len(data["cards"]))
        self.assertEqual(900, data["coins"])
        self.assertEqual(1, len(self.sql("SELECT id FROM draws")))
        self.assertEqual(1, len(self.sql("SELECT card_id FROM collections")))

    def test_insufficient_coins_rolls_back(self):
        self.register()
        self.execute("UPDATE users SET coins=50 WHERE username='alice'")
        resp = self.post("/draw", mode="single")
        self.assertEqual(400, resp.status_code)
        body = resp.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(0, len(self.sql("SELECT id FROM draws")))
        self.assertEqual(0, len(self.sql("SELECT card_id FROM collections")))
        self.assertEqual(50, self.sql("SELECT coins FROM users")[0]["coins"])

    def test_ten_draw_cost_and_guarantee(self):
        self.register()
        resp = self.post("/draw", mode="ten")
        self.assertEqual(200, resp.status_code)
        data = resp.get_json()
        self.assertEqual(10, len(data["cards"]))
        self.assertEqual(100, data["coins"])
        self.assertTrue(any(c["rarity"] >= 3 for c in data["cards"]),
                        "十连必须至少一张史诗及以上")

    def test_repeat_card_count_increases(self):
        self.register()
        uid = self.sql("SELECT id FROM users")[0]["id"]
        conn = self.conn()
        try:
            card_id = conn.execute("SELECT id FROM cards WHERE rarity=1 LIMIT 1").fetchone()["id"]
            collection.add_card(conn, uid, card_id)
            second = collection.add_card(conn, uid, card_id)
        finally:
            conn.close()
        self.assertEqual(2, second)


class AuthTests(BaseCase):
    def test_register_and_login(self):
        self.register()
        self.assertEqual(1, len(self.sql("SELECT id FROM users")))
        self.assertEqual(1000, self.sql("SELECT coins FROM users")[0]["coins"])

    def test_duplicate_username_rejected(self):
        self.register()
        self.logout()
        resp = self.register(username="alice", password="another123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(self.sql("SELECT id FROM users")))

    def test_short_password_rejected(self):
        self.register(username="bob", password="123")
        self.assertEqual(0, len(self.sql("SELECT id FROM users WHERE username='bob'")))

    def test_login_rate_limit(self):
        self.register()
        self.logout()
        for _ in range(5):
            self.login(password="wrongpass")
        resp = self.login(password="secret123")
        self.assertEqual(200, resp.status_code)
        with self.client.session_transaction() as s:
            self.assertNotIn("uid", s)
        auth.reset_rate_limit()

    def test_checkin_once_per_day(self):
        self.register()
        self.post("/checkin")
        coins_after_first = self.sql("SELECT coins FROM users")[0]["coins"]
        self.assertEqual(1100, coins_after_first)
        self.post("/checkin")
        self.assertEqual(1100, self.sql("SELECT coins FROM users")[0]["coins"])


class AlbumRankTests(BaseCase):
    def test_album_total_and_locked_cards(self):
        self.register()
        resp = self.client.get("/album")
        html = resp.get_data(as_text=True)
        self.assertEqual(200, resp.status_code)
        self.assertIn("未收集", html)

    def test_progress_counts_distinct_cards(self):
        self.register()
        uid = self.sql("SELECT id FROM users")[0]["id"]
        conn = self.conn()
        try:
            ids = [r["id"] for r in conn.execute("SELECT id FROM cards WHERE rarity=1 LIMIT 3")]
            for cid in ids:
                collection.add_card(conn, uid, cid)
            got, total, pct = collection.progress(conn, uid)
        finally:
            conn.close()
        self.assertEqual(3, got)
        self.assertEqual(CARD_COUNT, total)
        self.assertAlmostEqual(10.0, pct, places=1)

    def test_leaderboards_include_user(self):
        self.register()
        self.post("/draw", mode="ten")
        resp = self.client.get("/rank")
        self.assertIn("alice", resp.get_data(as_text=True))

    def test_rank_lists_user_without_ssr(self):
        self.register()
        html = self.client.get("/rank").get_data(as_text=True)
        self.assertIn("alice", html, "没有 SSR 的用户也应出现在 SSR 榜（显示 0）")

    def test_album_filter_by_rarity(self):
        self.register()
        html = self.client.get("/album?rarity=5").get_data(as_text=True)
        self.assertEqual(6, html.count("未收集"), "SSR 筛选应只显示 6 张未收集")


class AdminTests(BaseCase):
    def test_admin_requires_permission(self):
        self.register()
        resp = self.client.get("/admin/")
        self.assertEqual(403, resp.status_code)

    def test_admin_page_renders(self):
        self.register()
        self.make_admin()
        resp = self.client.get("/admin/")
        self.assertEqual(200, resp.status_code)
        html = resp.get_data(as_text=True)
        self.assertIn("概率表", html)
        self.assertIn("卡池", html)

    def test_weights_validation_rejects_non_100(self):
        self.register()
        self.make_admin()
        resp = self.post("/admin/weights", w1=50, w2=20, w3=10, w4=10, w5=9)
        self.assertEqual(302, resp.status_code)
        conn = self.conn()
        try:
            weights = gacha.load_weights(conn)
        finally:
            conn.close()
        self.assertEqual(55.0, weights[1], "非法概率不应保存")

    def test_weights_update_applies(self):
        self.register()
        self.make_admin()
        self.post("/admin/weights", w1=46, w2=28, w3=12, w4=4, w5=10)
        conn = self.conn()
        try:
            weights = gacha.load_weights(conn)
        finally:
            conn.close()
        self.assertEqual(10.0, weights[5])

    def test_add_card_extends_pool(self):
        self.register()
        self.make_admin()
        self.post("/admin/cards/add", name="新增测试卡", rarity=5, emoji="🧪", description="测试用")
        rows = self.sql("SELECT id, rarity FROM cards WHERE name='新增测试卡'")
        self.assertEqual(1, len(rows))
        self.assertEqual(5, rows[0]["rarity"])
        self.assertEqual(CARD_COUNT + 1, self.sql("SELECT COUNT(*) c FROM cards")[0]["c"])

    def test_give_coins(self):
        self.register()
        self.make_admin()
        self.post("/admin/give", username="alice", amount=500)
        self.assertEqual(1500, self.sql("SELECT coins FROM users")[0]["coins"])


class SeedTests(BaseCase):
    def test_seed_idempotent(self):
        import seed_cards
        conn = self.conn()
        try:
            added = seed_cards.seed(conn)
            total = conn.execute("SELECT COUNT(*) c FROM cards").fetchone()["c"]
        finally:
            conn.close()
        self.assertEqual(0, added, "重复 seed 不应新增卡")
        self.assertEqual(CARD_COUNT, total)

    def test_rarity_distribution_of_pool(self):
        rows = self.sql("SELECT rarity, COUNT(*) c FROM cards GROUP BY rarity")
        self.assertEqual({1: 6, 2: 6, 3: 6, 4: 6, 5: 6}, {r["rarity"]: r["c"] for r in rows})


class ThemeTests(BaseCase):
    """双主题：深色默认 + 浅色可切换，且稀有度配色走 CSS 变量。"""

    def setUp(self):
        super().setUp()
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, *parts):
        with open(os.path.join(self.root, *parts), encoding="utf-8") as f:
            return f.read()

    def test_login_page_has_theme_bootstrap(self):
        html = self.client.get("/login").get_data(as_text=True)
        self.assertIn('data-theme="dark"', html, "默认主题应为深色")
        self.assertIn('id="themeToggle"', html, "未登录页也应有切换按钮")
        self.assertIn("gacha-theme", html, "应把选择写入 localStorage")

    def test_bootstrap_runs_before_stylesheet(self):
        html = self.client.get("/login").get_data(as_text=True)
        self.assertLess(
            html.index("gacha-theme"), html.index("style.css"),
            "主题引导脚本必须在样式表之前执行，否则刷新会闪一下深色",
        )

    def test_logged_in_page_has_toggle(self):
        self.register()
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="themeToggle"', html)
        self.assertIn("topbar-right", html)

    def test_css_defines_light_theme(self):
        css = self._read("static", "style.css")
        self.assertIn('html[data-theme="light"]', css)
        for token in ("--bg", "--panel", "--text", "--gold", "--rar-5", "--overlay"):
            self.assertGreaterEqual(
                css.count(token + ":"), 2, "%s 需要深色/浅色两套取值" % token
            )
        self.assertIn("color-scheme:light", css.replace(" ", ""))

    def test_templates_do_not_inline_rarity_colors(self):
        self.register()
        for path in ("/", "/album", "/rank"):
            html = self.client.get(path).get_data(as_text=True)
            self.assertNotIn('style="--c:', html, "%s 仍有内联稀有度色，浅色主题会失效" % path)
        self.assertNotIn("--c:'", self._read("static", "app.js"))

    def test_rarity_classes_rendered(self):
        self.register()
        html = self.client.get("/album").get_data(as_text=True)
        self.assertIn('class="card r5', html.replace("  ", " "))
        self.assertIn('class="chip r5', html.replace("  ", " "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
