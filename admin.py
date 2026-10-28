"""管理员后台：卡池增改与下架、概率调整、金币发放。"""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

import economy
import gacha
from auth import admin_required
from db import get_db, transaction

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@admin_required
def index():
    conn = get_db()
    cards = [dict(r) for r in conn.execute("SELECT * FROM cards ORDER BY rarity DESC, id")]
    weights = gacha.load_weights(conn)
    users = [dict(r) for r in conn.execute(
        "SELECT id, username, coins, is_admin, pity_count FROM users ORDER BY id LIMIT 200")]
    return render_template("admin.html", cards=cards, weights=weights, users=users)


@bp.post("/weights")
@admin_required
def update_weights():
    try:
        weights = {i: float(request.form.get("w%d" % i) or 0) for i in range(1, 6)}
    except ValueError:
        flash("概率必须是数字", "error")
        return redirect(url_for("admin.index"))
    err = gacha.validate_weights(weights)
    if err:
        flash(err, "error")
        return redirect(url_for("admin.index"))
    conn = get_db()
    with transaction(conn):
        gacha.save_weights(conn, weights)
    flash("概率表已更新，立即生效", "ok")
    return redirect(url_for("admin.index"))


@bp.post("/cards/add")
@admin_required
def add_card():
    name = (request.form.get("name") or "").strip()
    emoji = (request.form.get("emoji") or "").strip() or "🎴"
    rarity = request.form.get("rarity", type=int)
    desc = (request.form.get("description") or "").strip()
    if not name or rarity not in (1, 2, 3, 4, 5):
        flash("卡名不能为空，等级需为 1~5", "error")
        return redirect(url_for("admin.index"))
    conn = get_db()
    try:
        with transaction(conn):
            conn.execute(
                "INSERT INTO cards(name, rarity, emoji, image, description, enabled, created_at) "
                "VALUES(?, ?, ?, NULL, ?, 1, ?)",
                (name, rarity, emoji, desc,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        flash("已新增卡牌「%s」，已自动进入卡池" % name, "ok")
    except Exception as exc:  # 卡名唯一约束
        flash("新增失败：%s" % exc, "error")
    return redirect(url_for("admin.index"))


@bp.post("/cards/<int:card_id>/edit")
@admin_required
def edit_card(card_id):
    name = (request.form.get("name") or "").strip()
    emoji = (request.form.get("emoji") or "").strip()
    desc = (request.form.get("description") or "").strip()
    rarity = request.form.get("rarity", type=int)
    if not name or rarity not in (1, 2, 3, 4, 5):
        flash("卡名不能为空，等级需为 1~5", "error")
        return redirect(url_for("admin.index"))
    conn = get_db()
    try:
        with transaction(conn):
            conn.execute(
                "UPDATE cards SET name=?, emoji=?, description=?, rarity=? WHERE id=?",
                (name, emoji, desc, rarity, card_id),
            )
        flash("卡牌 #%d 已更新" % card_id, "ok")
    except Exception as exc:
        flash("更新失败：%s" % exc, "error")
    return redirect(url_for("admin.index"))


@bp.post("/cards/<int:card_id>/toggle")
@admin_required
def toggle_card(card_id):
    conn = get_db()
    with transaction(conn):
        row = conn.execute("SELECT enabled FROM cards WHERE id=?", (card_id,)).fetchone()
        if not row:
            flash("卡牌不存在", "error")
            return redirect(url_for("admin.index"))
        new_state = 0 if row["enabled"] else 1
        conn.execute("UPDATE cards SET enabled=? WHERE id=?", (new_state, card_id))
    flash("卡牌 #%d 已%s" % (card_id, "上架" if new_state else "下架"), "ok")
    return redirect(url_for("admin.index"))


@bp.post("/give")
@admin_required
def give_coins():
    username = (request.form.get("username") or "").strip()
    amount = request.form.get("amount", type=int)
    if not amount:
        flash("金币数量需为整数", "error")
        return redirect(url_for("admin.index"))
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        flash("用户不存在：%s" % username, "error")
        return redirect(url_for("admin.index"))
    with transaction(conn):
        economy.grant(conn, user["id"], amount)
    flash("已向 %s 发放 %d 金币" % (username, amount), "ok")
    return redirect(url_for("admin.index"))
