"""30 张种子卡（运维梗）。以 name 为唯一键 INSERT OR IGNORE，可重复执行、不覆盖人工改动。"""
from datetime import datetime

CARDS = [
    # (name, rarity, emoji, description, image)
    # ---- SSR ----
    ("重启就好了", 5, "🔄", "全宇宙最强运维法术，成功率存疑但信仰坚定", "/static/cards/01.png"),
    ("rm -rf 前的最后一备份", 5, "💾", "传说中的保命符，持有者从未后悔", "/static/cards/02.png"),
    ("服役三年零宕机", 5, "📈", "SLA 神话，监控曲线平得让人怀疑探针挂了", "/static/cards/03.png"),
    ("一次通过的安全审计", 5, "🛡️", "藏在人类历史角落的未解之谜", "/static/cards/04.png"),
    ("老板亲自写的运维脚本", 5, "🧙", "出自号称不写代码的老板之手，而且真的能跑", "/static/cards/05.png"),
    ("停机窗口内提前完成升级", 5, "⏱️", "DBA 圈的都市传说，没人亲眼见过但人人都信", "/static/cards/06.png"),
    # ---- 传说 ----
    ("凌晨三点服务正常", 4, "🌙", "监控全绿你反而睡不着，这本身就是一种故障", "/static/cards/07.png"),
    ("一次改对的 nginx 配置", 4, "⚙️", "reload 零 warning，此刻值得截图裱起来", "/static/cards/08.png"),
    ("完全按文档部署成功", 4, "📖", "文档没骗人，这在云计算时代近乎玄学", "/static/cards/09.png"),
    ("客户主动说不急", 4, "🕊️", "稀有度堪比陨石，请先确认对方是否身体不适", "/static/cards/10.png"),
    ("免费拿到正版企业授权", 4, "🎫", "销售喝多了签的字，第二天没敢承认", "/static/cards/11.png"),
    ("内网穿透一次通", 4, "🚇", "防火墙、安全组、路由，全都没拦你", "/static/cards/12.png"),
    # ---- 史诗 ----
    ("深夜救火成功", 3, "🧯", "一个人、一盏灯、一条 tail -f，天亮前恢复", "/static/cards/13.png"),
    ("提前发现磁盘将满", 3, "💿", "巡检脚本凌晨发的告警，你恰好在打游戏看到", "/static/cards/14.png"),
    ("手写正则一次匹配", 3, "🔤", "没上测试网站直接进生产，居然真匹配对了", "/static/cards/15.png"),
    ("忍住了没敲回车", 3, "🛑", "rm -rf 输到一半，悬停三秒，最终 Ctrl+C", "/static/cards/16.png"),
    ("大促零故障值班", 3, "🎯", "整夜无事发生，你获得了带薪发呆", "/static/cards/17.png"),
    ("找到了那个逗号", 3, "🔍", "三小时排查，真凶是配置里一个全角逗号", "/static/cards/18.png"),
    # ---- 稀有 ----
    ("周五下午拒绝发版", 2, "🙅", "「这版下周一再上」，你做出了本周最正确的决定", "/static/cards/19.png"),
    ("管理后台密码找回", 2, "🔑", "三个月没登录，重置邮件一直在垃圾箱躺着", "/static/cards/20.png"),
    ("被拉进新群", 2, "💬", "刚进群就看到 @你 两个字，预感不妙", "/static/cards/21.png"),
    ("跑了一夜的脚本", 2, "🌅", "早上来一看 exit code 0，输出文件完好", "/static/cards/22.png"),
    ("VPN 自己连上了", 2, "🔐", "不是你修的，它自己好的，但功劳算你的", "/static/cards/23.png"),
    ("会议室墙角充电口", 2, "🔌", "演示前电量 1%，靠它续命", "/static/cards/24.png"),
    # ---- 普通 ----
    ("报 400 的扫描机器人", 1, "🤖", "今天第 47 次尝试访问 .env，热情可嘉", "/static/cards/25.png"),
    ("周报模板", 1, "📋", "每周复制一次改三个数字，没人发现", "/static/cards/26.png"),
    ("已读不回的工单", 1, "🎫", "「处理中」挂了两周，用户已自行放弃", "/static/cards/27.png"),
    ("过期的 SSL 证书", 1, "📜", "浏览器标红那天才想起三个月前的告警邮件", "/static/cards/28.png"),
    ("例行重启的祖传服务", 1, "⏰", "每晚四点重启，没人知道为什么，也没人敢停", "/static/cards/29.png"),
    ("打印机又卡纸", 1, "🖨️", "IT 三件套：重启、拍两下、抽纸对齐", "/static/cards/30.png"),
]


def seed(conn, verbose=False):
    """幂等灌入：已存在的卡名跳过；老库里 image 为空的补齐图片路径。返回新插入数量。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    before = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
    conn.executemany(
        "INSERT OR IGNORE INTO cards(name, rarity, emoji, description, image, enabled, created_at) "
        "VALUES(?, ?, ?, ?, ?, 1, ?)",
        [(name, rarity, emoji, desc, img, now) for name, rarity, emoji, desc, img in CARDS],
    )
    # 兼容早期无图的库：只补空值，不覆盖后台人工改过的图
    conn.executemany(
        "UPDATE cards SET image = ? WHERE name = ? AND (image IS NULL OR image = '')",
        [(img, name) for name, _, _, _, img in CARDS],
    )
    after = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
    if verbose:
        print("seed: %d -> %d (新增 %d 张)" % (before, after, after - before))
    return after - before
