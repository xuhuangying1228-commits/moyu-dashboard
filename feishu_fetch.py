#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拉取飞书多维表中达人的「主页链接 / 蒲公英链接 / 稿件链接」三列，
按"达人昵称"字段匹配，输出 feishu_inf.json 供网页加载填格。

配置（通过环境变量，切勿硬编码密钥）：
  FEISHU_APP_ID      飞书自建应用 App ID（cli_ 开头）
  FEISHU_APP_SECRET  应用密钥
  FEISHU_NICK_FIELD  飞书表里"达人昵称"字段名（默认"小红书昵称"，不对就改这个）
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.parse
import urllib.error

# ===== 常量：来自多维表链接 base/ 后 + ?table= =====
APP_TOKEN = "TTmEb8JYhacQUIsMTNxchMMAnte"
TABLE_ID = "tbl4MwhsLVskmCpl"
NICK_FIELD = os.environ.get("FEISHU_NICK_FIELD", "小红书昵称")
FIELDS = ["主页链接", "蒲公英链接", "稿件链接"]


def get_token():
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        sys.exit("❌ 缺少环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
    except urllib.error.URLError as e:
        sys.exit(f"❌ 获取 token 网络错误: {e}")
    if d.get("code") != 0:
        sys.exit(f"❌ 获取 token 失败: {d}")
    return d["tenant_access_token"]


def norm(v):
    """飞书字段值可能是 str / {'text':..,'link':..} / [{'text':..,'link':..}] 等"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        if not v:
            return ""
        v = v[0]
    if isinstance(v, dict):
        return (v.get("link") or v.get("text") or v.get("url") or "").strip()
    return str(v).strip()


def get_records(token):
    items = []
    page_token = None
    while True:
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}"
            f"/tables/{TABLE_ID}/records?page_size=100"
        )
        if page_token:
            url += "&page_token=" + urllib.parse.quote(page_token)
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.load(r)
        except urllib.error.URLError as e:
            sys.exit(f"❌ 拉取记录网络错误: {e}")
        if d.get("code") != 0:
            sys.exit(f"❌ 拉取记录失败: {d}")
        data = d.get("data", {})
        items.extend(data.get("items", []))
        page_token = data.get("page_token")
        if not data.get("has_more") or not page_token:
            break
    return items


def main():
    book = {}
    token = get_token()
    records = get_records(token)
    skipped = 0
    for rec in records:
        f = rec.get("fields", {})
        nick = norm(f.get(NICK_FIELD))
        if not nick:
            skipped += 1
            continue
        book[nick] = {k: norm(f.get(k)) for k in FIELDS}
    out = {
        "app_token": APP_TOKEN,
        "table_id": TABLE_ID,
        "nick_field": NICK_FIELD,
        "updated": datetime.datetime.now().isoformat(timespec="seconds"),
        "count": len(book),
        "data": book,
    }
    with open("feishu_inf.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print(f"✅ 导出 {len(book)} 位达人 → feishu_inf.json（跳过无昵称记录 {skipped} 条）")


if __name__ == "__main__":
    main()
