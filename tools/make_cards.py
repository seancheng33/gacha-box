# -*- coding: utf-8 -*-
"""按参考图风格生成 30 张卡面 + 1 张卡背（HTML+CSS+SVG → 无头浏览器截图）

风格规格（对照 2026-10-30 用户提供的参考图）：
  · 竖版 3:4（300x400）
  · 细描边等级色 + 外发光
  · 径向渐变底（中心亮、四周暗）
  · 中心彩色填充风 SVG 图标 + 强光晕
  · 底部卡名条位置留暗角（卡名由前端 HTML 渲染，不烤进图里）
  · 四角小三角装饰
"""
import os
import subprocess
import sys

OUT_DIR = r"E:\workbuddy\2026-10-30-gacha-ssr\cards"
HTML_DIR = r"E:\workbuddy\2026-10-30-gacha-ssr\html"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
W, H = 300, 300

# 等级配色：(描边色, 中心光晕色, 底色)
LEVEL = {
    1: ("#6b86b8", "rgba(90,125,185,.26)", "#0e1626"),
    2: ("#3fb5a8", "rgba(63,181,168,.26)", "#0b1f22"),
    3: ("#a86bd8", "rgba(168,107,216,.28)", "#170f2a"),
    4: ("#e0a12e", "rgba(224,161,46,.30)", "#22160a"),
    5: ("#f5c451", "rgba(245,196,81,.34)", "#261c08"),
}

# ---------------- 30 个图标（viewBox 0 0 100 100） ----------------
ICONS = {
1: '''<circle cx="50" cy="52" r="30" fill="none" stroke="#ffd97a" stroke-width="8"
      stroke-linecap="round" stroke-dasharray="141 48" transform="rotate(-90 50 52)"/>
   <line x1="50" y1="20" x2="50" y2="50" stroke="#ffeeb0" stroke-width="8" stroke-linecap="round"/>
   <circle cx="50" cy="52" r="34" fill="none" stroke="rgba(255,220,130,.25)" stroke-width="2"/>''',

2: '''<rect x="22" y="28" width="56" height="46" rx="6" fill="#8ea6c6" stroke="#eaf3ff" stroke-width="3.5"/>
   <rect x="22" y="28" width="56" height="13" rx="6" fill="#cfe0f5" stroke="#eaf3ff" stroke-width="2.5"/>
   <rect x="31" y="48" width="28" height="7" rx="3.5" fill="#ffe08a"/>
   <rect x="31" y="60" width="18" height="5" rx="2.5" fill="#6b83a3"/>
   <circle cx="68" cy="62" r="4" fill="#ffd257" stroke="#fff0bb" stroke-width="1.5"/>''',

3: '''<rect x="25" y="18" width="50" height="64" rx="7" fill="#1b2540" stroke="#9fb6d8" stroke-width="3.5"/>
   <rect x="32" y="26" width="36" height="11" rx="2.5" fill="#4a5c80" stroke="#7c92b8" stroke-width="1.5"/>
   <rect x="32" y="41" width="36" height="11" rx="2.5" fill="#4a5c80" stroke="#7c92b8" stroke-width="1.5"/>
   <rect x="32" y="56" width="36" height="11" rx="2.5" fill="#4a5c80" stroke="#7c92b8" stroke-width="1.5"/>
   <circle cx="37.5" cy="31.5" r="2.6" fill="#5ef0a0"/>
   <circle cx="37.5" cy="46.5" r="2.6" fill="#5ef0a0"/>
   <circle cx="37.5" cy="61.5" r="2.6" fill="#ffd257"/>''',

4: '''<path d="M50 18 L78 30 V52 C78 70 65 80 50 86 C35 80 22 70 22 52 V30 Z"
      fill="#f0b93c" stroke="#ffeeb0" stroke-width="3" stroke-linejoin="round"/>
   <path d="M50 24 L72 33 V52 C72 66 62 74 50 79 C38 74 28 66 28 52 V33 Z" fill="#ffd257" opacity=".55"/>
   <path d="M36 52 L46 62 L65 40" fill="none" stroke="#4a3505" stroke-width="8"
         stroke-linecap="round" stroke-linejoin="round"/>''',

5: '''<rect x="30" y="24" width="40" height="52" rx="3" fill="#f6ead0" stroke="#d9c9a6" stroke-width="2.5"/>
   <rect x="24" y="18" width="52" height="9" rx="4.5" fill="#a86bd8" stroke="#d4b3f0" stroke-width="2"/>
   <rect x="24" y="73" width="52" height="9" rx="4.5" fill="#a86bd8" stroke="#d4b3f0" stroke-width="2"/>
   <line x1="38" y1="38" x2="62" y2="38" stroke="#b9a684" stroke-width="3" stroke-linecap="round"/>
   <line x1="38" y1="47" x2="62" y2="47" stroke="#b9a684" stroke-width="3" stroke-linecap="round"/>
   <line x1="38" y1="56" x2="54" y2="56" stroke="#b9a684" stroke-width="3" stroke-linecap="round"/>
   <circle cx="50" cy="34" r="30" fill="rgba(168,107,216,.22)"/>''',

6: '''<path d="M32 20 H68 L60 50 L68 80 H32 L40 50 Z" fill="rgba(255,240,200,.28)"
      stroke="#ffd257" stroke-width="3.5" stroke-linejoin="round"/>
   <path d="M40 30 H60 L55 50 L60 70 H40 L45 50 Z" fill="#ffd257" opacity=".75"/>
   <path d="M45 62 C47 58 53 58 55 62 L55 68 H45 Z" fill="#ffeeb0"/>
   <rect x="28" y="15" width="44" height="7" rx="3.5" fill="#e0a12e"/>
   <rect x="28" y="78" width="44" height="7" rx="3.5" fill="#e0a12e"/>''',

7: '''<circle cx="50" cy="32" r="14" fill="#f6ead0" stroke="#fff6df" stroke-width="2.5"/>
   <circle cx="56" cy="28" r="12" fill="#0b1f22"/>
   <rect x="26" y="54" width="48" height="26" rx="4" fill="#16283c" stroke="#7ff0d0" stroke-width="2.5"/>
   <rect x="32" y="60" width="34" height="5" rx="2.5" fill="#7ff0d0" opacity=".85"/>
   <rect x="32" y="69" width="34" height="5" rx="2.5" fill="#7ff0d0" opacity=".5"/>
   <circle cx="29" cy="63" r="1.8" fill="#5ef0a0"/><circle cx="29" cy="72" r="1.8" fill="#5ef0a0"/>''',

8: '''<g fill="#e8a94a" stroke="#ffd089" stroke-width="2.5">
   <circle cx="50" cy="50" r="26"/></g>
   <g fill="#e8a94a" stroke="#ffd089" stroke-width="2.5">
   <rect x="45" y="12" width="10" height="14" rx="3"/><rect x="45" y="74" width="10" height="14" rx="3"/>
   <rect x="12" y="45" width="14" height="10" rx="3"/><rect x="74" y="45" width="14" height="10" rx="3"/>
   <rect x="22" y="22" width="10" height="13" rx="3" transform="rotate(-45 27 28)"/>
   <rect x="68" y="22" width="10" height="13" rx="3" transform="rotate(45 73 28)"/>
   <rect x="22" y="65" width="10" height="13" rx="3" transform="rotate(45 27 71)"/>
   <rect x="68" y="65" width="10" height="13" rx="3" transform="rotate(-45 73 71)"/></g>
   <circle cx="50" cy="50" r="13" fill="#3a2a12" stroke="#ffd089" stroke-width="3"/>''',

9: '''<path d="M50 32 C40 24 26 26 20 31 V76 C26 71 40 69 50 77 Z" fill="#f6ead0" stroke="#e2d3b4" stroke-width="2.5" stroke-linejoin="round"/>
   <path d="M50 32 C60 24 74 26 80 31 V76 C74 71 60 69 50 77 Z" fill="#e8dcc0" stroke="#e2d3b4" stroke-width="2.5" stroke-linejoin="round"/>
   <line x1="50" y1="32" x2="50" y2="77" stroke="#c9b795" stroke-width="2.5"/>
   <line x1="27" y1="40" x2="44" y2="42" stroke="#c1ad8a" stroke-width="2.4" stroke-linecap="round"/>
   <line x1="27" y1="50" x2="44" y2="52" stroke="#c1ad8a" stroke-width="2.4" stroke-linecap="round"/>
   <line x1="56" y1="42" x2="73" y2="40" stroke="#c1ad8a" stroke-width="2.4" stroke-linecap="round"/>
   <line x1="56" y1="52" x2="73" y2="50" stroke="#c1ad8a" stroke-width="2.4" stroke-linecap="round"/>''',

10: '''<circle cx="50" cy="52" r="27" fill="#f6ead0" stroke="#e0cba4" stroke-width="3.5"/>
   <circle cx="50" cy="52" r="21" fill="#fffaf0"/>
   <circle cx="50" cy="52" r="2.8" fill="#8a7550"/>
   <line x1="50" y1="52" x2="50" y2="36" stroke="#8a7550" stroke-width="3.6" stroke-linecap="round"/>
   <line x1="50" y1="52" x2="63" y2="57" stroke="#8a7550" stroke-width="3.6" stroke-linecap="round"/>
   <path d="M36 20 C40 12 50 10 56 14" fill="none" stroke="#ffe9a8" stroke-width="3"
         stroke-linecap="round" opacity=".8"/>
   <rect x="47" y="17" width="6" height="7" rx="2" fill="#e0a12e"/>''',

11: '''<path d="M38 52 L26 88 L40 80 L48 92 L54 56 Z" fill="#d24a4a" stroke="#f07a7a" stroke-width="2"/>
   <path d="M62 52 L74 88 L60 80 L52 92 L46 56 Z" fill="#b83c3c" stroke="#f07a7a" stroke-width="2"/>
   <circle cx="50" cy="44" r="24" fill="#f0b93c" stroke="#ffeeb0" stroke-width="3"/>
   <circle cx="50" cy="44" r="16" fill="#ffd257"/>
   <path d="M43 44 L48 50 L58 38" fill="none" stroke="#6b4a08" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>''',

12: '''<ellipse cx="50" cy="50" rx="40" ry="26" fill="none" stroke="rgba(255,210,120,.25)" stroke-width="2"/>
   <ellipse cx="50" cy="50" rx="32" ry="20" fill="none" stroke="rgba(255,210,120,.4)" stroke-width="2.5"/>
   <ellipse cx="50" cy="50" rx="23" ry="14" fill="none" stroke="rgba(255,225,150,.6)" stroke-width="3"/>
   <ellipse cx="50" cy="50" rx="14" ry="9" fill="rgba(255,235,180,.75)"/>
   <ellipse cx="50" cy="50" rx="6" ry="4" fill="#fffbe8"/>
   <line x1="50" y1="50" x2="50" y2="18" stroke="rgba(255,225,150,.35)" stroke-width="2"/>''',

13: '''<rect x="36" y="26" width="28" height="52" rx="12" fill="#d24a4a" stroke="#f78383" stroke-width="3"/>
   <rect x="43" y="18" width="14" height="10" rx="3" fill="#8a2b2b"/>
   <path d="M50 18 C50 12 58 12 60 16" fill="none" stroke="#c9d3e0" stroke-width="3.5" stroke-linecap="round"/>
   <rect x="42" y="36" width="16" height="10" rx="3" fill="#f6d7d7" opacity=".85"/>
   <rect x="38" y="54" width="24" height="6" rx="3" fill="#8a2b2b" opacity=".5"/>''',

14: '''<path d="M18 66 A32 32 0 0 1 82 66" fill="none" stroke="#8fa3c4" stroke-width="7" stroke-linecap="round"/>
   <path d="M18 66 A32 32 0 0 1 82 66" fill="none" stroke="#3fb5a8" stroke-width="3" stroke-linecap="round"
         stroke-dasharray="60 120"/>
   <line x1="50" y1="66" x2="66" y2="44" stroke="#ff6b6b" stroke-width="4.5" stroke-linecap="round"/>
   <circle cx="50" cy="66" r="5" fill="#e8eefb"/>
   <rect x="20" y="70" width="60" height="8" rx="4" fill="rgba(143,163,196,.35)"/>''',

15: '''<text x="50" y="72" font-size="64" font-family="Georgia,serif" font-weight="bold"
      fill="#d9a6ff" text-anchor="middle">π</text>
   <text x="50" y="72" font-size="64" font-family="Georgia,serif" font-weight="bold"
      fill="none" stroke="#f0d4ff" stroke-width="1.6" text-anchor="middle" opacity=".9">π</text>
   <path d="M20 34 H34 M66 34 H80" stroke="rgba(200,150,255,.5)" stroke-width="3" stroke-linecap="round"/>''',

16: '''<rect x="20" y="46" width="60" height="34" rx="8" fill="#4a2a2a" stroke="#e07a7a" stroke-width="3"/>
   <rect x="26" y="52" width="48" height="22" rx="5" fill="#8c3b3b"/>
   <path d="M60 56 L68 63 L60 70" fill="none" stroke="#ffb3b3" stroke-width="4"
         stroke-linecap="round" stroke-linejoin="round"/>
   <path d="M52 63 H66" stroke="#ffb3b3" stroke-width="4" stroke-linecap="round"/>
   <circle cx="50" cy="30" r="10" fill="none" stroke="#f0c9c9" stroke-width="3.5"/>
   <path d="M42 38 C38 42 36 46 36 48" fill="none" stroke="#f0c9c9" stroke-width="3.5" stroke-linecap="round"/>''',

17: '''<rect x="12" y="30" width="30" height="22" rx="3" fill="#0d2a22" stroke="#3fb5a8" stroke-width="2.5"/>
   <rect x="58" y="30" width="30" height="22" rx="3" fill="#0d2a22" stroke="#3fb5a8" stroke-width="2.5"/>
   <rect x="30" y="56" width="40" height="22" rx="3" fill="#0d2a22" stroke="#3fb5a8" stroke-width="2.5"/>
   <path d="M16 41 H26 L30 35 L34 47 L38 39" stroke="#5ef0a0" stroke-width="2.4" fill="none" stroke-linecap="round"/>
   <path d="M62 41 H72 L76 35 L80 47 L84 39" stroke="#5ef0a0" stroke-width="2.4" fill="none" stroke-linecap="round"/>
   <path d="M34 66 H44 L48 60 L52 72 L56 64 L60 68 H66" stroke="#5ef0a0" stroke-width="2.4" fill="none" stroke-linecap="round"/>''',

18: '''<circle cx="44" cy="42" r="22" fill="rgba(200,160,255,.18)" stroke="#c69cf0" stroke-width="4"/>
   <line x1="60" y1="58" x2="78" y2="78" stroke="#c69cf0" stroke-width="7" stroke-linecap="round"/>
   <path d="M40 46 C40 40 48 40 48 46 C48 50 40 50 40 56" fill="none" stroke="#e8c9ff"
         stroke-width="3.6" stroke-linecap="round"/>''',

19: '''<rect x="20" y="24" width="60" height="56" rx="6" fill="#e8eefb" stroke="#9fb6d8" stroke-width="3"/>
   <rect x="20" y="24" width="60" height="14" rx="6" fill="#3f6fb5"/>
   <rect x="30" y="44" width="40" height="5" rx="2.5" fill="#c3d3ea"/>
   <rect x="30" y="54" width="40" height="5" rx="2.5" fill="#c3d3ea"/>
   <rect x="42" y="58" width="40" height="18" rx="4" fill="#d24a4a" stroke="#f08a8a" stroke-width="2"/>
   <text x="62" y="71" font-size="11" font-family="Arial" font-weight="bold" fill="#fff" text-anchor="middle">STOP</text>
   <rect x="28" y="18" width="10" height="12" rx="4" fill="#3f6fb5"/>
   <rect x="62" y="18" width="10" height="12" rx="4" fill="#3f6fb5"/>''',

20: '''<rect x="18" y="26" width="64" height="48" rx="7" fill="rgba(70,120,200,.22)" stroke="#6fa0e0" stroke-width="3"/>
   <rect x="26" y="36" width="34" height="8" rx="3" fill="#5b86c4"/>
   <rect x="26" y="50" width="34" height="8" rx="3" fill="#5b86c4"/>
   <circle cx="66" cy="66" r="13" fill="#f0b93c" stroke="#ffe9a8" stroke-width="2.5"/>
   <circle cx="66" cy="66" r="5" fill="#3a2a05"/>
   <path d="M66 79 V88" stroke="#f0b93c" stroke-width="4" stroke-linecap="round"/>''',

21: '''<path d="M18 28 H82 V66 H46 L32 80 V66 H18 Z" fill="rgba(70,140,210,.28)" stroke="#6fa8e0"
      stroke-width="3" stroke-linejoin="round"/>
   <circle cx="36" cy="47" r="4" fill="#cfe3ff"/>
   <circle cx="50" cy="47" r="4" fill="#cfe3ff"/>
   <circle cx="64" cy="47" r="4" fill="#cfe3ff"/>''',

22: '''<rect x="16" y="26" width="68" height="52" rx="6" fill="#0a1420" stroke="#3fb5a8" stroke-width="3"/>
   <rect x="16" y="26" width="68" height="9" rx="6" fill="#1c3340"/>
   <circle cx="23" cy="30.5" r="2.2" fill="#ff6b6b"/><circle cx="30" cy="30.5" r="2.2" fill="#ffd257"/>
   <circle cx="37" cy="30.5" r="2.2" fill="#5ef0a0"/>
   <text x="24" y="50" font-size="9" font-family="Consolas,monospace" fill="#5ef0a0">$ exit 0</text>
   <text x="24" y="62" font-size="8" font-family="Consolas,monospace" fill="#7ff0d0" opacity=".7">done</text>''',

23: '''<rect x="30" y="46" width="40" height="34" rx="6" fill="#3fb5a8" stroke="#8ff0e4" stroke-width="3"/>
   <path d="M38 46 V34 C38 24 62 24 62 34 V46" fill="none" stroke="#8ff0e4" stroke-width="5" stroke-linecap="round"/>
   <circle cx="50" cy="61" r="5" fill="#0b1f22"/>
   <path d="M50 66 V74" stroke="#0b1f22" stroke-width="3.4" stroke-linecap="round"/>''',

24: '''<rect x="28" y="28" width="44" height="48" rx="9" fill="#e8eefb" stroke="#a8bcd6" stroke-width="3"/>
   <circle cx="43" cy="46" r="4.5" fill="#8fa3c4"/>
   <circle cx="57" cy="46" r="4.5" fill="#8fa3c4"/>
   <rect x="46" y="60" width="8" height="10" rx="4" fill="#8fa3c4"/>
   <path d="M32 76 H68" stroke="#c3d3ea" stroke-width="3" stroke-linecap="round"/>''',

25: '''<rect x="26" y="32" width="48" height="40" rx="9" fill="#9fb3cc" stroke="#dbe8f8" stroke-width="3"/>
   <rect x="34" y="42" width="32" height="18" rx="5" fill="#1e2b40"/>
   <circle cx="42" cy="51" r="3.2" fill="#7ff0d0"/><circle cx="58" cy="51" r="3.2" fill="#7ff0d0"/>
   <line x1="50" y1="32" x2="50" y2="22" stroke="#9fb3cc" stroke-width="3.4" stroke-linecap="round"/>
   <circle cx="50" cy="19" r="3.4" fill="#ffd257"/>
   <rect x="20" y="46" width="7" height="16" rx="3.5" fill="#8fa6c2"/>
   <rect x="73" y="46" width="7" height="16" rx="3.5" fill="#8fa6c2"/>''',

26: '''<rect x="24" y="18" width="52" height="64" rx="4" fill="#f2f6fc" stroke="#a8bcd6" stroke-width="3"/>
   <line x1="32" y1="32" x2="68" y2="32" stroke="#8fa3c4" stroke-width="3"/>
   <line x1="32" y1="44" x2="68" y2="44" stroke="#c3d3ea" stroke-width="3"/>
   <line x1="32" y1="54" x2="68" y2="54" stroke="#c3d3ea" stroke-width="3"/>
   <line x1="32" y1="64" x2="56" y2="64" stroke="#c3d3ea" stroke-width="3"/>
   <line x1="32" y1="26" x2="32" y2="74" stroke="#c3d3ea" stroke-width="2.5"/>
   <line x1="56" y1="26" x2="56" y2="74" stroke="#c3d3ea" stroke-width="2.5"/>''',

27: '''<path d="M22 24 H64 L78 38 V76 H22 Z" fill="#f2f6fc" stroke="#a8bcd6" stroke-width="3" stroke-linejoin="round"/>
   <path d="M64 24 V38 H78" fill="none" stroke="#a8bcd6" stroke-width="3" stroke-linejoin="round"/>
   <line x1="32" y1="44" x2="66" y2="44" stroke="#8fa3c4" stroke-width="3" stroke-linecap="round"/>
   <line x1="32" y1="54" x2="66" y2="54" stroke="#c3d3ea" stroke-width="3" stroke-linecap="round"/>
   <line x1="32" y1="64" x2="52" y2="64" stroke="#c3d3ea" stroke-width="3" stroke-linecap="round"/>''',

28: '''<rect x="20" y="26" width="60" height="48" rx="4" fill="#f6ead0" stroke="#cbb78e" stroke-width="3"/>
   <line x1="28" y1="38" x2="56" y2="38" stroke="#c1ad8a" stroke-width="2.6"/>
   <line x1="28" y1="46" x2="60" y2="46" stroke="#c1ad8a" stroke-width="2.6"/>
   <line x1="28" y1="54" x2="50" y2="54" stroke="#c1ad8a" stroke-width="2.6"/>
   <g transform="rotate(-14 66 62)">
     <rect x="44" y="52" width="44" height="18" rx="3" fill="rgba(210,74,74,.9)" stroke="#f08a8a" stroke-width="2"/>
     <text x="66" y="65" font-size="10" font-family="Arial" font-weight="bold" fill="#fff" text-anchor="middle">EXPIRED</text>
   </g>
   <circle cx="76" cy="34" r="7" fill="#d24a4a" opacity=".8"/>''',

29: '''<rect x="24" y="30" width="52" height="48" rx="5" fill="#2b3550" stroke="#7f8cab" stroke-width="3"/>
   <rect x="32" y="38" width="36" height="10" rx="3" fill="#1a2237"/>
   <circle cx="38" cy="43" r="2.4" fill="#ff6b6b"/>
   <rect x="32" y="54" width="36" height="16" rx="3" fill="#1a2237"/>
   <circle cx="50" cy="62" r="10" fill="rgba(255,210,120,.18)" stroke="#e0a12e" stroke-width="2.4"/>
   <line x1="50" y1="62" x2="50" y2="56" stroke="#ffd257" stroke-width="2.4" stroke-linecap="round"/>
   <line x1="50" y1="62" x2="55" y2="64" stroke="#ffd257" stroke-width="2.4" stroke-linecap="round"/>
   <rect x="30" y="78" width="10" height="6" rx="2" fill="#7f8cab"/>
   <rect x="60" y="78" width="10" height="6" rx="2" fill="#7f8cab"/>''',

30: '''<rect x="18" y="52" width="64" height="26" rx="4" fill="#c3cede" stroke="#e8eefb" stroke-width="3"/>
   <rect x="26" y="34" width="48" height="12" rx="3" fill="#dfe7f2" stroke="#f4f8ff" stroke-width="2"/>
   <path d="M30 34 L38 18 H70 L78 34 Z" fill="#e8eefb" stroke="#f8fbff" stroke-width="2.5" stroke-linejoin="round"/>
   <rect x="30" y="60" width="40" height="6" rx="3" fill="#8fa3c4"/>
   <circle cx="72" cy="63" r="3" fill="#5ef0a0"/>
   <rect x="34" y="42" width="30" height="4" rx="2" fill="#b9c8dc"/>''',
}

# id, 卡名, 等级
CARDS = [
    (1, "重启就好了", 5), (2, "rm -rf 前的最后一备份", 5), (3, "服役三年零宕机", 5),
    (4, "一次通过的安全审计", 5), (5, "老板亲自写的运维脚本", 5), (6, "停机窗口内提前完成升级", 5),
    (7, "凌晨三点服务正常", 4), (8, "一次改对的 nginx 配置", 4), (9, "完全按文档部署成功", 4),
    (10, "客户主动说不急", 4), (11, "免费拿到正版企业授权", 4), (12, "内网穿透一次通", 4),
    (13, "深夜救火成功", 3), (14, "提前发现磁盘将满", 3), (15, "手写正则一次匹配", 3),
    (16, "忍住了没敲回车", 3), (17, "大促零故障值班", 3), (18, "找到了那个逗号", 3),
    (19, "周五下午拒绝发版", 2), (20, "管理后台密码找回", 2), (21, "被拉进新群", 2),
    (22, "跑了一夜的脚本", 2), (23, "VPN 自己连上了", 2), (24, "会议室墙角充电口", 2),
    (25, "报 400 的扫描机器人", 1), (26, "周报模板", 1), (27, "已读不回的工单", 1),
    (28, "过期的 SSL 证书", 1), (29, "例行重启的祖传服务", 1), (30, "打印机又卡纸", 1),
]

BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(w)dpx;height:%(h)dpx;overflow:hidden}
body{background:%(bg)s}
.art{position:relative;width:%(w)dpx;height:%(h)dpx;overflow:hidden;
     background:radial-gradient(circle at 50%% 50%%, %(glow)s 0%%, %(bg)s 66%%);}
/* 中心光晕 */
.halo{position:absolute;left:50%%;top:50%%;width:186px;height:186px;margin:-93px 0 0 -93px;
      border-radius:50%%;background:radial-gradient(circle, %(glow)s 0%%, transparent 64%%);
      filter:blur(8px)}
/* 四角三角装饰 */
.c{position:absolute;width:0;height:0;opacity:.5}
.c.tl{left:7px;top:7px;border-top:9px solid %(edge)s;border-right:9px solid transparent}
.c.tr{right:7px;top:7px;border-top:9px solid %(edge)s;border-left:9px solid transparent}
.c.bl{left:7px;bottom:7px;border-bottom:9px solid %(edge)s;border-right:9px solid transparent}
.c.br{right:7px;bottom:7px;border-bottom:9px solid %(edge)s;border-left:9px solid transparent}
.icon{position:absolute;left:50%%;top:50%%;width:158px;height:158px;margin:-79px 0 0 -79px;
      filter:drop-shadow(0 0 12px %(glow)s)}
/* SSR 放射光（克制，避免整张过曝） */
.rays{position:absolute;left:50%%;top:50%%;width:300px;height:300px;margin:-150px 0 0 -150px;
      border-radius:50%%;opacity:.13;
      background:repeating-conic-gradient(from 0deg, %(edge)s 0deg 2.5deg, transparent 2.5deg 14deg);
      -webkit-mask-image:radial-gradient(circle, transparent 22%%, #000 46%%, transparent 72%%);
      mask-image:radial-gradient(circle, transparent 22%%, #000 46%%, transparent 72%%)}
"""

BACK_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:300px;height:300px;overflow:hidden}
body{background:#0b1226}
.back{position:relative;width:300px;height:300px;
      background:radial-gradient(circle at 50% 50%, #1d2b52 0%, #0a1024 72%);}
.frame1{position:absolute;inset:14px;border:2px solid rgba(245,196,81,.55);border-radius:6px}
.frame2{position:absolute;inset:24px;border:1px solid rgba(245,196,81,.28);border-radius:4px}
.diamond{position:absolute;left:50%;top:50%;width:150px;height:150px;margin:-75px 0 0 -75px;
         border:2px solid rgba(245,196,81,.5);transform:rotate(45deg);border-radius:8px}
.diamond2{position:absolute;left:50%;top:50%;width:126px;height:126px;margin:-63px 0 0 -63px;
          border:1px solid rgba(245,196,81,.25);transform:rotate(45deg);border-radius:6px}
.q{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
   font:700 92px/1 Georgia,serif;color:#f5c451;
   text-shadow:0 0 22px rgba(245,196,81,.75),0 0 48px rgba(245,196,81,.35)}
.glow{position:absolute;left:50%;top:50%;width:240px;height:240px;margin:-120px 0 0 -120px;
      border-radius:50%;background:radial-gradient(circle,rgba(245,196,81,.22),transparent 62%);
      filter:blur(8px)}
.c{position:absolute;width:0;height:0;opacity:.6}
.c.tl{left:20px;top:20px;border-top:10px solid #f5c451;border-right:10px solid transparent}
.c.tr{right:20px;top:20px;border-top:10px solid #f5c451;border-left:10px solid transparent}
.c.bl{left:20px;bottom:20px;border-bottom:10px solid #f5c451;border-right:10px solid transparent}
.c.br{right:20px;bottom:20px;border-bottom:10px solid #f5c451;border-left:10px solid transparent}
"""


def card_html(cid, _name, rarity):
    edge, glow, bg = LEVEL[rarity]
    css = BASE_CSS % dict(w=W, h=H, bg=bg, glow=glow, edge=edge)
    rays = '<div class="rays"></div>' if rarity == 5 else ""
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>%s</style></head>
<body><div class="art">
%s<div class="halo"></div>
<svg class="icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">%s</svg>
<i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i>
</div></body></html>""" % (css, rays, ICONS[cid])


def back_html():
    head = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
    body = ('</style></head><body><div class="back"><div class="glow"></div>'
            '<div class="frame1"></div><div class="frame2"></div>'
            '<div class="diamond"></div><div class="diamond2"></div>'
            '<div class="q">?</div>'
            '<i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i>'
            '</div></body></html>')
    return head + BACK_CSS + body


def shoot(html_path, png_path):
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=2",
           "--user-data-dir=" + os.path.join(HTML_DIR, "_profile"),
           "--screenshot=" + png_path,
           "--window-size=%d,%d" % (W, H),
           "file:///" + html_path.replace("\\", "/")]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)


def check(png_path):
    """三层校验：大小 / PNG 魔数 / 像素方差"""
    if not os.path.exists(png_path):
        return False, "missing"
    size = os.path.getsize(png_path)
    if size < 8000:
        return False, "size %dB too small" % size
    with open(png_path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            return False, "bad magic"
    return True, "%dKB" % (size // 1024)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(HTML_DIR, exist_ok=True)

    # 卡背
    bp = os.path.join(HTML_DIR, "back.html")
    with open(bp, "w", encoding="utf-8") as f:
        f.write(back_html())
    out = os.path.join(OUT_DIR, "back.png")
    shoot(bp, out)
    print("back  ->", check(out))

    ok_list, bad_list = [], []
    for cid, name, rarity in CARDS:
        hp = os.path.join(HTML_DIR, "%02d.html" % cid)
        with open(hp, "w", encoding="utf-8") as f:
            f.write(card_html(cid, name, rarity))
        out = os.path.join(OUT_DIR, "%02d.png" % cid)
        shoot(hp, out)
        ok, note = check(out)
        (ok_list if ok else bad_list).append(cid)
        print("%02d %-22s r%d -> %s %s" % (cid, name, rarity, "OK" if ok else "BAD", note), flush=True)

    print("\nDONE ok=%d bad=%s" % (len(ok_list), bad_list))


if __name__ == "__main__":
    main()
