"""
端到端演示脚本：构造 mock 数据，验证全流程稳定性。
用法:  python scripts/demo_e2e.py
前提:  uvicorn src.api.main:app --host 127.0.0.1 --port 8000 已启动
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000/api"
TIMEOUT = 60

# ── 1. Mock 数据：模拟一个典型信息茧房用户 ──────────────────────────
# 特征：娱乐/搞笑占绝对主导，立场偏正面，极少跨领域，情绪偏高
# 这会让 S1(内容多样性)低、S2(跨领域)低、S3(立场多样性)低、S4(认知覆盖)低 → 茧房指数高

MOCK_ROWS = [
    # ── 娱乐/搞笑（占 ~55%，高频互动）──
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_001", "timestamp": "2025-05-01T10:00:00", "content_type": "video", "text": "搞笑猫咪合集，笑到停不下来", "image_url": "", "video_url": "", "like": 42, "comment": 8, "share": 5, "duration": 45.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.5, "author_id": "a_funny"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_002", "timestamp": "2025-05-01T12:30:00", "content_type": "video", "text": "沙雕日常翻车现场", "image_url": "", "video_url": "", "like": 35, "comment": 12, "share": 3, "duration": 30.0, "topic": "搞笑", "stance": "positive", "emotion_score": 9.0, "author_id": "a_funny"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_003", "timestamp": "2025-05-02T09:15:00", "content_type": "video", "text": "宠物搞笑瞬间，太可爱了", "image_url": "", "video_url": "", "like": 28, "comment": 5, "share": 7, "duration": 60.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.8, "author_id": "a_cute"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_004", "timestamp": "2025-05-02T14:00:00", "content_type": "video", "text": "整蛊室友大作战", "image_url": "", "video_url": "", "like": 50, "comment": 15, "share": 8, "duration": 90.0, "topic": "搞笑", "stance": "positive", "emotion_score": 9.2, "author_id": "a_funny"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_005", "timestamp": "2025-05-03T08:00:00", "content_type": "video", "text": "方言搞笑配音合集", "image_url": "", "video_url": "", "like": 22, "comment": 3, "share": 2, "duration": 35.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.0, "author_id": "a_dub"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_006", "timestamp": "2025-05-03T20:30:00", "content_type": "video", "text": "搞笑动画短片", "image_url": "", "video_url": "", "like": 18, "comment": 2, "share": 1, "duration": 25.0, "topic": "搞笑", "stance": "positive", "emotion_score": 7.5, "author_id": "a_anim"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_007", "timestamp": "2025-05-04T11:00:00", "content_type": "video", "text": "萌娃搞笑日常", "image_url": "", "video_url": "", "like": 30, "comment": 6, "share": 4, "duration": 50.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.6, "author_id": "a_kid"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_008", "timestamp": "2025-05-04T16:45:00", "content_type": "video", "text": "街头采访搞笑回答", "image_url": "", "video_url": "", "like": 25, "comment": 4, "share": 3, "duration": 40.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.3, "author_id": "a_street"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_009", "timestamp": "2025-05-05T10:20:00", "content_type": "video", "text": "恶搞美食制作", "image_url": "", "video_url": "", "like": 38, "comment": 10, "share": 6, "duration": 55.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.9, "author_id": "a_food"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_010", "timestamp": "2025-05-05T22:00:00", "content_type": "video", "text": "办公室摸鱼搞笑瞬间", "image_url": "", "video_url": "", "like": 33, "comment": 7, "share": 4, "duration": 38.0, "topic": "搞笑", "stance": "positive", "emotion_score": 8.1, "author_id": "a_office"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_011", "timestamp": "2025-05-06T09:00:00", "content_type": "video", "text": "搞笑配音之经典电影片段", "image_url": "", "video_url": "", "like": 20, "comment": 3, "share": 2, "duration": 28.0, "topic": "搞笑", "stance": "positive", "emotion_score": 7.8, "author_id": "a_dub"},

    # ── 娱乐（占 ~18%，中频互动）──
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_012", "timestamp": "2025-05-01T18:00:00", "content_type": "video", "text": "明星八卦最新动态", "image_url": "", "video_url": "", "like": 15, "comment": 3, "share": 2, "duration": 60.0, "topic": "娱乐", "stance": "positive", "emotion_score": 7.0, "author_id": "a_gossip"},
    {"user_id": "demo_user_01", "platform": "xiaohongshu", "content_id": "xhs_001", "timestamp": "2025-05-02T19:30:00", "content_type": "image", "text": "追剧推荐：最近超好看的综艺", "image_url": "", "video_url": "", "like": 12, "comment": 2, "share": 1, "duration": 20.0, "topic": "娱乐", "stance": "positive", "emotion_score": 7.5, "author_id": "a_show"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_013", "timestamp": "2025-05-04T21:00:00", "content_type": "video", "text": "偶像舞台直拍合集", "image_url": "", "video_url": "", "like": 20, "comment": 5, "share": 3, "duration": 180.0, "topic": "娱乐", "stance": "positive", "emotion_score": 8.0, "author_id": "a_idol"},
    {"user_id": "demo_user_01", "platform": "weibo", "content_id": "wb_001", "timestamp": "2025-05-05T12:00:00", "content_type": "text", "text": "综艺名场面盘点", "image_url": "", "video_url": "", "like": 8, "comment": 1, "share": 0, "duration": 15.0, "topic": "娱乐", "stance": "positive", "emotion_score": 6.5, "author_id": "a_variety"},

    # ── 体育（占 ~9%，低频）──
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_014", "timestamp": "2025-05-02T22:00:00", "content_type": "video", "text": "NBA精彩扣篮集锦", "image_url": "", "video_url": "", "like": 10, "comment": 1, "share": 0, "duration": 45.0, "topic": "体育", "stance": "positive", "emotion_score": 7.0, "author_id": "a_nba"},
    {"user_id": "demo_user_01", "platform": "douyin", "content_id": "dy_015", "timestamp": "2025-05-05T18:00:00", "content_type": "video", "text": "足球搞笑失误合集", "image_url": "", "video_url": "", "like": 8, "comment": 0, "share": 1, "duration": 30.0, "topic": "体育", "stance": "neutral", "emotion_score": 6.0, "author_id": "a_soccer"},

    # ── 科技（占 ~9%，偶尔浏览）──
    {"user_id": "demo_user_01", "platform": "weibo", "content_id": "wb_002", "timestamp": "2025-05-03T15:00:00", "content_type": "text", "text": "新款手机发布，配置一览", "image_url": "", "video_url": "", "like": 3, "comment": 0, "share": 0, "duration": 10.0, "topic": "科技", "stance": "neutral", "emotion_score": 5.0, "author_id": "a_tech"},
    {"user_id": "demo_user_01", "platform": "xiaohongshu", "content_id": "xhs_002", "timestamp": "2025-05-06T14:00:00", "content_type": "image", "text": "数码产品开箱体验", "image_url": "", "video_url": "", "like": 2, "comment": 0, "share": 0, "duration": 8.0, "topic": "科技", "stance": "neutral", "emotion_score": 4.5, "author_id": "a_digi"},

    # ── 少量社会/时政（占 ~9%，几乎无互动）──
    {"user_id": "demo_user_01", "platform": "weibo", "content_id": "wb_003", "timestamp": "2025-05-03T08:00:00", "content_type": "text", "text": "今日社会热点新闻速览", "image_url": "", "video_url": "", "like": 0, "comment": 0, "share": 0, "duration": 5.0, "topic": "社会", "stance": "neutral", "emotion_score": 4.0, "author_id": "a_news"},
    {"user_id": "demo_user_01", "platform": "weibo", "content_id": "wb_004", "timestamp": "2025-05-06T07:30:00", "content_type": "text", "text": "政策解读：最新民生政策", "image_url": "", "video_url": "", "like": 0, "comment": 0, "share": 0, "duration": 3.0, "topic": "时政", "stance": "neutral", "emotion_score": 3.5, "author_id": "a_policy"},
]

# 对标分布：理想情况下各领域均衡
BENCHMARK = {
    "entertainment": 0.20,
    "politics": 0.15,
    "society": 0.15,
    "technology": 0.15,
    "education": 0.10,
    "finance": 0.10,
    "sports": 0.10,
    "health": 0.05,
}


# ── 工具函数 ────────────────────────────────────────────────────────

def _header(token: str | None = None) -> dict:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _post(path: str, body: dict, token: str | None = None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body, headers=_header(token), timeout=TIMEOUT)
    if r.status_code >= 400:
        print(f"  ✗ POST {path} → {r.status_code}: {r.text[:300]}")
        return {"error": True, "status": r.status_code, "detail": r.text[:500]}
    return r.json()


def _get(path: str, token: str | None = None) -> dict:
    r = requests.get(f"{BASE}{path}", headers=_header(token), timeout=TIMEOUT)
    if r.status_code >= 400:
        print(f"  ✗ GET {path} → {r.status_code}: {r.text[:300]}")
        return {"error": True, "status": r.status_code, "detail": r.text[:500]}
    return r.json()


def step(name: str) -> None:
    print(f"\n{'='*60}\n  {name}\n{'='*60}")


def ok(label: str, detail: str = "") -> None:
    msg = f"  ✓ {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)


def fail(label: str, detail: str = "") -> None:
    msg = f"  ✗ {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)


# ── 主流程 ──────────────────────────────────────────────────────────

def main() -> None:
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  茧评系统 端到端演示脚本                                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    token: str | None = None

    # ── Step 0: 健康检查 ──
    step("Step 0: 后端健康检查")
    try:
        r = _get("/llm/health")
        if r.get("ok"):
            ok("LLM 服务正常", f"provider={r.get('provider')}, model={r.get('multimodal_model')}")
        else:
            fail("LLM 服务异常", str(r))
            print("  ⚠ 后端可能未启动，请先运行: uvicorn src.api.main:app --reload")
            return
    except Exception as e:
        fail("无法连接后端", str(e))
        return

    # ── Step 1: 注册/登录（workbench 需要 admin 角色） ──
    step("Step 1: 用户认证（admin）")
    # 系统自动 seed admin 用户 admin/admin123
    login = _post("/auth/login", {"username": "admin", "password": "admin123"})
    if login.get("access_token"):
        token = login["access_token"]
        ok("Admin 登录成功", f"username={login.get('username')}, role={login.get('role')}")
    else:
        # fallback: 注册新用户
        reg = _post("/auth/register", {"username": "demo_admin", "password": "demo123456"})
        if reg.get("access_token"):
            token = reg["access_token"]
            ok("注册成功（user 角色，部分端点可能 403）", f"username={reg.get('username')}, role={reg.get('role')}")
        else:
            fail("认证失败", str(reg))
            return

    # ── Step 2: LLM 调用测试 ──
    step("Step 2: LLM 调用测试")
    llm_available = True
    t0 = time.time()
    r = _post("/llm/invoke-test", {"prompt": "请用一句话解释什么是信息茧房。", "response_mode": "text"}, token)
    if r.get("error"):
        fail("LLM 调用失败（可能账户欠费或额度不足）", str(r.get("detail", ""))[:200])
        llm_available = False
        print("  ⚠ 后续语义增强步骤将降级为本地 fallback 模式")
    else:
        ok("LLM 调用成功", f"model={r.get('model')}, latency={r.get('latency_ms')}ms")
        print(f"    回复: {r.get('content', '')[:100]}")

    # ── Step 3: 数据导入 + 语义增强 ──
    step("Step 3: 数据导入（含语义增强）")
    import io
    import json as _json

    buf = io.BytesIO(_json.dumps(MOCK_ROWS, ensure_ascii=False).encode("utf-8"))
    files = {"file": ("demo_data.json", buf, "application/json")}
    semantic_flag = "true" if llm_available else "false"
    params = {"format": "standard", "semantic_enhance": semantic_flag, "anonymize": "false"}
    if not llm_available:
        print("  ⚠ LLM 不可用，跳过语义增强，使用原始数据")
    enhance_task_id = None
    try:
        resp = requests.post(
            f"{BASE}/ingestion/import",
            files=files,
            params=params,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=TIMEOUT,
        )
        if resp.status_code >= 400:
            fail("数据导入失败", resp.text[:300])
            ingested_rows = MOCK_ROWS  # fallback
        else:
            imp = resp.json()
            enhance_task_id = imp.get("semantic_enhance_task_id")
            ok("数据导入成功", f"row_count={imp.get('row_count')}, format={imp.get('detected_format')}, semantic_enhanced={imp.get('semantic_enhanced')}, task_id={enhance_task_id}")
            ingested_rows = imp.get("rows", MOCK_ROWS)
    except Exception as e:
        fail("数据导入异常", str(e))
        ingested_rows = MOCK_ROWS

    # 等待语义增强后台任务完成
    if enhance_task_id and llm_available:
        print("  ⏳ 等待语义增强后台任务完成...")
        max_wait = 300  # 最多等5分钟
        poll_interval = 3
        waited = 0
        while waited < max_wait:
            try:
                status_resp = requests.get(
                    f"{BASE}/ingestion/enhance-status/{enhance_task_id}",
                    headers={"Authorization": f"Bearer {token}"} if token else {},
                    timeout=15,
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    st = status_data.get("status", "unknown")
                    if st == "completed":
                        ingested_rows = status_data.get("rows", ingested_rows)
                        ok("语义增强完成", f"enhanced_rows={status_data.get('row_count')}")
                        break
                    elif st == "failed":
                        fail("语义增强失败", str(status_data.get("error", ""))[:200])
                        break
                    else:
                        print(f"    状态: {st}，已等待 {waited}s...")
            except Exception as poll_err:
                print(f"    轮询异常: {poll_err}")
            time.sleep(poll_interval)
            waited += poll_interval
        if waited >= max_wait:
            fail("语义增强超时", f"等待超过 {max_wait}s")
    elif not llm_available:
        print("  ⚠ LLM 不可用，使用原始数据（无语义增强）")

    # ── Step 4: 四维度茧房评估 ──
    step("Step 4: 四维度茧房评估")
    r = _post("/workbench/plan", {"rows": ingested_rows, "benchmark": BENCHMARK}, token)
    if r.get("error"):
        fail("评估失败", str(r.get("detail", ""))[:200])
    else:
        ev = r.get("evaluation", {})
        ok("评估完成",
           f"S1={ev.get('s1_content_diversity')}, S2={ev.get('s2_cross_domain')}, "
           f"S3={ev.get('s3_stance_diversity')}, S4={ev.get('s4_cognitive_coverage')}, "
           f"C={ev.get('cocoon_index')}")
        lp = r.get("ladder_plan", [])
        ok("阶梯计划生成", f"共 {len(lp)} 个阶段")

    # ── Step 5: 风险详情 ──
    step("Step 5: 风险详情")
    r = _post("/risk/detail", {"rows": ingested_rows, "benchmark": BENCHMARK}, token)
    if r.get("error"):
        fail("风险详情失败", str(r.get("detail", ""))[:200])
    else:
        ok("风险详情", json.dumps(r, ensure_ascii=False)[:200])

    # ── Step 6: 数字孪生构建 ──
    step("Step 6: 数字孪生构建")
    r = _post("/persona/build", {"rows": ingested_rows}, token)
    if r.get("error"):
        fail("孪生构建失败", str(r.get("detail", ""))[:200])
    else:
        ok("孪生构建成功", f"profile_id={r.get('profile_id')}, user_id={r.get('user_id')}")
        profile = r.get("profile", {})
        ok("兴趣模型", f"top_topics={profile.get('interest', {}).get('top_topics', [])}")
        ok("行为模型", f"like_rate={profile.get('behavior', {}).get('like_rate', 0):.2f}, avg_duration={profile.get('behavior', {}).get('avg_duration', 0):.1f}s")
        ok("认知模型", f"mean_emotion={profile.get('cognitive', {}).get('mean_emotion', 0):.2f}")

    # ── Step 7: 模拟对比 ──
    step("Step 7: 智能体模拟对比")
    r = _post("/simulation/compare", {
        "rows": ingested_rows,
        "benchmark": BENCHMARK,
        "rounds": 5,
        "llm_enabled": False,
    }, token)
    if r.get("error"):
        fail("模拟对比失败", str(r.get("detail", ""))[:200])
    else:
        result_keys = [k for k in r.get("result", {}).keys() if not k.startswith("_")]
        ok("模拟对比完成", f"策略数={len(result_keys)}, 策略={result_keys}")
        trend = r.get("trend_option")
        if trend:
            ok("趋势图数据", "已生成")

    # ── Step 8: 阶梯破茧计划 ──
    step("Step 8: 阶梯破茧计划")
    r = _post("/simulation/ladder/plan", {
        "rows": ingested_rows,
        "benchmark": BENCHMARK,
        "user_id": "demo_user_01",
    }, token)
    if r.get("error"):
        fail("阶梯计划失败", str(r.get("detail", ""))[:200])
    else:
        exec_id = r.get("execution_id", r.get("id", ""))
        ok("阶梯计划创建", f"execution_id={exec_id}")
        # 尝试执行一步
        if exec_id:
            r2 = _post(f"/simulation/ladder/{exec_id}/execute-step", {}, token)
            if r2.get("error"):
                fail("执行步骤失败", str(r2.get("detail", ""))[:200])
            else:
                ok("执行步骤成功", f"current_step={r2.get('current_step')}, status={r2.get('status')}")

    # ── Step 9: 认知训练 ──
    step("Step 9: 认知训练")
    r = _post("/workbench/training/start", {
        "topic": "科技",
        "pro_view": "AI技术将深刻改变人类生活，带来效率革命",
        "con_view": "AI技术可能导致大规模失业和隐私危机",
    }, token)
    if r.get("error"):
        fail("训练启动失败", str(r.get("detail", ""))[:200])
    else:
        tid = r.get("training_id", "")
        ok("训练启动成功", f"training_id={tid}, topic={r.get('topic')}")
        # 提交训练
        if tid:
            r2 = _post(f"/workbench/training/{tid}/submit", {
                "summary": "AI技术既有提升效率的潜力，也需要关注就业转型和隐私保护，关键在于制度设计和技术治理的平衡。",
                "reflection": "我之前只关注了AI的便利性，忽略了社会层面的风险，需要更全面地看待技术发展。",
            }, token)
            if r2.get("error"):
                fail("训练提交失败（LLM 评阅可能不可用）", str(r2.get("detail", ""))[:200])
            else:
                ok("训练提交成功", f"score={r2.get('score')}, feedback={str(r2.get('feedback', ''))[:80]}")

    # ── Step 10: 报告导出 ──
    step("Step 10: 评估报告导出")
    r = _post("/workbench/report", {
        "rows": ingested_rows,
        "benchmark": BENCHMARK,
        "strategy_summary": "建议用户逐步增加科技、教育、财经类内容消费，每周至少阅读3篇不同立场的社会评论，参与一次跨领域话题讨论。",
        "platform_placeholder": "抖音/小红书/微博",
    }, token)
    if r.get("error"):
        fail("报告导出失败", str(r.get("detail", ""))[:200])
    else:
        ok("报告导出成功", f"path={r.get('path')}")
        ev = r.get("evaluation", {})
        if ev:
            ok("报告评估数据", f"C={ev.get('cocoon_index')}")
        lp = r.get("ladder_plan", [])
        ok("报告阶梯计划", f"{len(lp)} 阶段")

    # ── Step 11: Workflow 全流程 ──
    step("Step 11: LangGraph 工作流（全智能体协作）")
    try:
        r = _post("/workflow/run", {
            "rows": ingested_rows,
            "benchmark": BENCHMARK,
        }, token)
        if r.get("error"):
            fail("工作流失败", str(r.get("detail", ""))[:200])
        else:
            ok("工作流完成", f"row_count={r.get('row_count')}, degraded={r.get('degraded')}")
            ev = r.get("evaluation")
            if ev:
                ok("工作流评估", f"C={ev.get('cocoon_index')}")
            trace = r.get("agent_trace", [])
            ok("智能体追踪", f"{len(trace)} 步")
            for item in trace[:5]:
                agent = item.get("agent", "?")
                status = item.get("status", "?")
                print(f"    → {agent}: {status}")
    except requests.exceptions.ReadTimeout:
        fail("工作流超时（60s），LangGraph 多智能体编排耗时较长，可单独测试")
    except Exception as e:
        fail("工作流异常", str(e)[:200])

    # ── 汇总 ──
    step("演示完成")
    print(f"""
  Mock 数据: {len(MOCK_ROWS)} 条行为记录
  用户画像: demo_user_01（娱乐主导型茧房用户）
  对标分布: {len(BENCHMARK)} 个领域均衡

  演示覆盖端点:
    ✓ POST /api/auth/register|login
    ✓ GET  /api/llm/health
    ✓ POST /api/llm/invoke-test
    ✓ POST /api/ingestion/import
    ✓ POST /api/workbench/plan
    ✓ POST /api/risk/detail
    ✓ POST /api/persona/build
    ✓ POST /api/simulation/compare
    ✓ POST /api/simulation/ladder/plan
    ✓ POST /api/workbench/training/start + submit
    ✓ POST /api/workbench/report
    ✓ POST /api/workflow/run
""")


if __name__ == "__main__":
    main()
