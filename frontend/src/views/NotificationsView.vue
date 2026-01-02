<template>
  <div class="notifications-page">
    <div class="page-header">
      <div class="left">
        <RouterLink to="/" class="back-btn">← 返回首页</RouterLink>
        <div>
          <p class="eyebrow">系统公告</p>
          <h1>最新通知</h1>
          <p class="muted">查看平台最新公告与历史动态</p>
        </div>
      </div>
    </div>

    <section class="card highlight">
      <div class="card-title">最新公告</div>
      <div class="notice-list">
        <div class="notice-row">
          <div class="notice-title">
            <span class="icon">📢</span>
            系统维护通知
            <span class="badge new">NEW</span>
          </div>
          <div class="notice-desc">
            为提升系统性能，我们计划于 2025 年 2 月 3 日凌晨 02:00-04:00 进行系统维护，期间服务短暂不可用，敬请谅解。
          </div>
          <div class="notice-date">2025-02-01</div>
        </div>
        <div class="notice-row">
          <div class="notice-title">
            <span class="icon">🎵</span>
            新功能上线：AI 音乐生成优化
            <span class="badge beta">beta</span>
          </div>
          <div class="notice-desc">
            新版本增加更多音乐风格选项，提升生成质量和并发性能，欢迎体验并反馈。
          </div>
          <div class="notice-date">2025-01-28</div>
        </div>
        <div class="notice-row">
          <div class="notice-title">
            <span class="icon">🛡</span>
            账号安全提醒
          </div>
          <div class="notice-desc">
            为保障账号安全，请定期更换密码，并启用双重验证。如发现异常活动，请及时联系支持。
          </div>
          <div class="notice-date">2025-01-20</div>
        </div>
      </div>
    </section>

    <section class="card secondary">
      <div class="card-title">历史公告</div>
      <div class="notice-list">
        <div class="notice-row">
          <div class="notice-title">
            <span class="icon">🗞</span>
            版本更新 v1.2.0
          </div>
          <div class="notice-desc">
            优化了用户体验，增加了导出的格式，提升列表加载速度，修复了若干已知问题。
          </div>
          <div class="notice-date">2024-12-15</div>
        </div>
        <div class="notice-row">
          <div class="notice-title">
            <span class="icon">📅</span>
            国庆客服安排
          </div>
          <div class="notice-desc">
            节日期间客服在线时间为 9:00-18:00，如有紧急需求可通过工单提交。
          </div>
          <div class="notice-date">2024-10-01</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup >
import { RouterLink } from "vue-router";
</script>

<style scoped>
.notifications-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 32px 32px 48px;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 6px;
}

.left {
  display: flex;
  gap: 14px;
  align-items: center;
}

.back-btn {
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.07);
  color: #e5e7eb;
  text-decoration: none;
  transition: all 0.16s ease-out;
  font-weight: 600;
}

.back-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.45);
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.65);
}

h1 {
  font-size: 24px;
  margin: 4px 0 6px;
}

.muted {
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
}

.card {
  padding: 22px 24px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.7);
}

.highlight {
  border-color: rgba(94, 234, 212, 0.3);
  box-shadow: 0 22px 70px rgba(94, 234, 212, 0.2);
}

.secondary {
  background: rgba(15, 23, 42, 0.85);
}

.card-title {
  font-weight: 800;
  margin-bottom: 16px;
  letter-spacing: 0.01em;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.notice-row {
  padding: 14px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.16);
  display: grid;
  grid-template-columns: 1fr auto;
  row-gap: 8px;
}

.notice-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.notice-desc {
  grid-column: 1 / span 2;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  line-height: 1.6;
}

.notice-date {
  text-align: right;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
}

.badge {
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.badge.new {
  background: rgba(94, 234, 212, 0.18);
  color: #5eead4;
}

.badge.beta {
  background: rgba(234, 179, 8, 0.18);
  color: #facc15;
}

.icon {
  font-size: 15px;
}

@media (max-width: 900px) {
  .notifications-page {
    padding: 18px 14px 32px;
  }

  .notice-row {
    grid-template-columns: 1fr;
  }

  .notice-date {
    text-align: left;
  }
}
</style>

