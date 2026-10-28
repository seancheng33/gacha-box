"""真实 HTTP 端到端冒烟：注册 → 签到 → 十连 → 图鉴 → 排行榜 → 退出登录。

用法：先启动服务（GACHA_DB=smoke.db PORT=5055 python app.py），再运行本脚本。
"""
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:5055"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("User-Agent", "gacha-smoke/1.0")]

steps = []


def get(path):
    with opener.open(BASE + path, timeout=10) as r:
        return r.status, r.read().decode()


def post(path, data, csrf=None):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"X-CSRF-Token": csrf or ""})
    try:
        with opener.open(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def csrf_of(html):
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return m.group(1) if m else ""


def check(name, cond, detail=""):
    steps.append(("PASS" if cond else "FAIL", name, detail))
    return cond


def main():
    status, html = get("/register")
    token = csrf_of(html)
    check("注册页可访问", status == 200 and bool(token), "status=%s" % status)

    status, html = post("/register", {"_csrf": token, "username": "冒烟测试员", "password": "smoke123"})
    check("注册成功", status == 200 and "拆盲盒" in html, "status=%s" % status)
    token = csrf_of(html)

    status, html = get("/")
    check("主页渲染", status == 200 and "单抽" in html and "出率公示" in html, "status=%s" % status)
    token = csrf_of(html)

    status, body = post("/draw", {"_csrf": token, "mode": "ten"})
    ok = status == 200
    data = json.loads(body) if ok else {}
    cards = data.get("cards", [])
    check("十连成功", ok and len(cards) == 10, "status=%s cards=%d" % (status, len(cards)))
    check("十连保底生效", any(c["rarity"] >= 3 for c in cards),
          "稀有度=%s" % [c["rarity"] for c in cards])
    check("扣费正确", data.get("coins") == 100, "coins=%s" % data.get("coins"))

    status, body = post("/draw", {"_csrf": token, "mode": "ten"})
    check("余额不足被拒", status == 400, "status=%s body=%s" % (status, body[:80]))

    status, html = get("/album")
    owned = [c for c in cards]
    check("图鉴可访问", status == 200 and "已收集" in html, "status=%s" % status)
    check("抽到的卡入册", all(c["name"] in html for c in owned[:3]), "抽查前3张")

    status, html = get("/rank?")
    check("排行榜可访问", status == 200 and "冒烟测试员" in html, "status=%s" % status)

    status, html = get("/")
    token = csrf_of(html)
    status, html = post("/checkin", {"_csrf": token})
    check("签到成功", status == 200 and "签到成功" in html, "status=%s" % status)

    status, html = get("/")
    token = csrf_of(html)
    status, html = post("/logout", {"_csrf": token})
    check("退出成功", status == 200 and "登录" in html, "status=%s" % status)

    status, html = get("/login")
    token = csrf_of(html)
    status, html = post("/login", {"_csrf": token, "username": "冒烟测试员", "password": "smoke123"})
    check("重新登录成功", status == 200 and "拆盲盒" in html, "status=%s" % status)

    passed = sum(1 for s in steps if s[0] == "PASS")
    lines = ["%-4s %-14s %s" % s for s in steps]
    lines.append("")
    lines.append("冒烟结果：%d/%d 通过" % (passed, len(steps)))
    out = "\n".join(lines)
    print(out)
    with open("smoke_out.txt", "w", encoding="utf-8") as f:
        f.write(out)
    return 0 if passed == len(steps) else 1


if __name__ == "__main__":
    sys.exit(main())
