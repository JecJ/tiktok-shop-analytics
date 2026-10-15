import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from datetime import date
from pathlib import Path

import streamlit as st

from ui.common import (MARKET_LABELS, export_db_bytes, get_db, get_settings, require_password,
                       reset_db_cache, run_full_analysis, setup_env)
from ui.github_actions import sync_daily_settings

st.set_page_config(page_title="数据快照", page_icon="💾", layout="wide")
setup_env()
require_password()

st.title("💾 数据快照")
st.caption("数据库、EchoTik 凭证和本地采集配置保存在项目 data 目录；换电脑/账户时备份并迁移 data 文件夹。GitHub Actions 的每日采集配置保存在 GitHub 仓库。")

db = get_db()
settings = get_settings()


st.subheader("① 每日采集配置（GitHub Actions）")
st.caption(f"当前左侧市场：{MARKET_LABELS.get(settings.region, settings.region)}。填写英文关键词后同步到 GitHub，下一次每日任务将按此市场采集并生成独立快照。GitHub runner 使用云端 IP，IP 所在地不保证等于所选市场；市场由 EchoTik 请求参数决定。")
config_path = ROOT / "data" / "daily_collection.json"
try:
    import json
    local_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
except (OSError, ValueError):
    local_config = {}
default_keywords = local_config.get("keywords", "yoga mat, massage gun, air fryer")
keywords = st.text_input("每日采集关键词（英文逗号分隔）", value=default_keywords,
                         help="关键词会用于当前所选市场；例如 bra, sports bra, lingerie。")
token = st.text_input("GitHub Fine-grained Token（仅本次会话使用）", type="password",
                      help="需要此仓库 Actions: write 权限。不会写入本地文件。")
if st.button("同步当前市场和关键词到 GitHub Actions"):
    try:
        sync_daily_settings(token, settings.region, keywords)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"region": settings.region, "keywords": keywords}, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success(f"已同步：{MARKET_LABELS.get(settings.region, settings.region)}；每日任务将使用这组关键词。")
    except Exception as exc:
        st.error(f"同步失败：{exc}")
st.link_button("打开 GitHub Actions 手动运行/查看状态", "https://github.com/JecJ/tiktok-shop-analytics/actions/workflows/daily-report.yml")

st.subheader("② 加载所选市场的最新每日快照")
st.caption("快照按市场分开发布；只会下载并覆盖当前左侧市场对应的本地数据库。")
if st.button("一键加载最新每日采集数据"):
    import urllib.request
    url = f"https://JecJ.github.io/tiktok-shop-analytics/tiktok_shop_{settings.region}.db"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        if len(data) < 1024:
            st.warning("下载的数据太小，可能还没有每日采集结果。")
        else:
            db_path = Path(settings.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            for suffix in ("", "-wal", "-shm"):
                fp = Path(str(db_path) + suffix)
                if fp.exists():
                    fp.unlink()
            db_path.write_bytes(data)
            reset_db_cache()
            st.success(f"已加载 {len(data)/1024:.0f} KB 数据，可到总览页查看，或点上方「重新生成分析报告」。")
    except Exception as exc:
        st.error(f"加载 {settings.region} 市场快照失败：{exc}。该市场可能尚未成功运行每日 Actions。")

st.subheader("③ 导出数据快照")
if st.button("打包当前数据库"):
    try:
        data = export_db_bytes(db)
        st.session_state["snapshot_bytes"] = data
        st.session_state["snapshot_name"] = f"tiktok_shop_{date.today().isoformat()}.db"
        st.success("打包完成，点击下方按钮下载。")
    except Exception as exc:
        st.error(f"打包失败：{exc}")
if st.session_state.get("snapshot_bytes"):
    st.download_button("⬇️ 下载快照 (.db)", st.session_state["snapshot_bytes"],
                       file_name=st.session_state["snapshot_name"],
                       mime="application/octet-stream")

st.subheader("④ 导入数据快照")
uploaded = st.file_uploader("上传之前导出的 .db 快照", type=["db"])
if uploaded is not None and st.button("恢复数据（将覆盖当前数据库）"):
    try:
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        db_path.write_bytes(uploaded.getvalue())
        reset_db_cache()
        st.success("已恢复。可到「总览」页查看数据规模，或先重新生成分析报告。")
    except Exception as exc:
        st.error(f"恢复失败：{exc}")

st.subheader("⑤ 分析报告")
report_path = Path(settings.report_dir) / "tiktok_shop_report.html"
if st.button("重新生成分析报告"):
    with st.spinner("正在计算选品评分 / 毛利 / 趋势 / 竞品 / 异动……"):
        try:
            run_full_analysis(db, settings)
            st.success("分析完成，报告已刷新。")
        except Exception as exc:
            st.error(f"分析失败：{exc}")

if report_path.exists():
    st.download_button("⬇️ 下载分析报告 (HTML)", report_path.read_bytes(),
                       file_name="tiktok_shop_report.html", mime="text/html")
    top_csv = report_path.parent / "top_products.csv"
    if top_csv.exists():
        st.download_button("⬇️ 下载 Top 商品 CSV", top_csv.read_bytes(),
                           file_name="top_products.csv", mime="text/csv")
else:
    st.info("还没有报告，点上面「重新生成分析报告」。")

st.divider()
st.caption("切换 Windows 用户/设备时，迁移项目目录下 data 文件夹即可保留本地数据库与 EchoTik 凭证；也可逐市场使用上面的导出/导入快照。不要把 data/api_key.txt 或 GitHub Token 提交到仓库。")
