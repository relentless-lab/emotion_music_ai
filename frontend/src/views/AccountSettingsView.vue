<template>
  <div class="settings-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">账号中心</p>
        <h1>账户设置</h1>
        <p class="muted">管理安全信息、通知偏好与隐私设置。</p>
      </div>
      <div class="header-actions">
        <button class="ghost-btn">重置</button>
        <button class="primary-btn">保存更改</button>
      </div>
    </header>

    <section class="card">
      <div class="card-title">
        <span>安全设置</span>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>当前密码</label>
          <input type="password" placeholder="请输入当前密码" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input type="password" placeholder="请输入新密码" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input type="password" placeholder="请再次输入新密码" />
        </div>
      </div>
      <div class="actions-row">
        <button class="primary-btn">保存安全设置</button>
      </div>
    </section>

    <section class="card">
      <div class="card-title">
        <span>通知设置</span>
      </div>
      <div class="list">
        <label class="list-item">
          <input type="checkbox" checked />
          <span>邮件通知</span>
        </label>
        <label class="list-item">
          <input type="checkbox" checked />
          <span>推送通知</span>
        </label>
        <label class="list-item">
          <input type="checkbox" checked />
          <span>系统更新通知</span>
        </label>
        <label class="list-item">
          <input type="checkbox" />
          <span>促销活动通知</span>
        </label>
      </div>
    </section>

    <section class="card">
      <div class="card-title">
        <span>隐私设置</span>
      </div>
      <div class="list">
        <label class="list-item">
          <input type="radio" name="privacy" checked />
          <span>公开：所有人可以看到我的作品</span>
        </label>
        <label class="list-item">
          <input type="radio" name="privacy" />
          <span>仅好友：只有获批的好友可查看我的作品</span>
        </label>
        <label class="list-item">
          <input type="radio" name="privacy" />
          <span>私密：只有我自己可以看到我的作品</span>
        </label>
      </div>
    </section>

    <section class="card danger">
      <div class="card-title">
        <span>账户操作</span>
      </div>
      <div class="danger-actions">
        <button class="ghost-btn">导出数据备份</button>
        <button class="warn-btn" type="button" @click="handleLogout">退出登录</button>
        <button class="danger-btn" type="button" @click="handleDelete" :disabled="deleting">
          {{ deleting ? "删除中..." : "删除账户" }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const deleting = ref(false);

const handleLogout = () => {
  auth.logout();
  router.push("/");
};

const handleDelete = async () => {
  if (deleting.value) return;
  const confirmed = window.confirm("确定要删除账户吗？此操作不可撤销（演示环境将清空本地登录状态）");
  if (!confirmed) return;
  deleting.value = true;
  try {
    await auth.deleteAccountAction();
    router.push("/");
    window.alert("账户已删除（本地登录信息已清理）");
  } catch (err) {
    window.alert(err?.message || "删除失败");
  } finally {
    deleting.value = false;
  }
};
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(23, 37, 84, 0.4), rgba(8, 20, 46, 0.8));
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 4px;
}

h1 {
  font-size: 20px;
  margin: 0;
}

.muted {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.card {
  padding: 18px 20px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 50px rgba(15, 23, 42, 0.7);
}

.card.danger {
  border-color: rgba(248, 113, 113, 0.35);
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  font-weight: 600;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.field input {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #e5e7eb;
}

.field input:focus {
  outline: 1px solid rgba(59, 130, 246, 0.6);
  border-color: rgba(59, 130, 246, 0.6);
}

.actions-row {
  margin-top: 10px;
}

.list {
  display: grid;
  gap: 10px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
}

.list-item input {
  width: 16px;
  height: 16px;
}

.danger-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.ghost-btn,
.primary-btn,
.warn-btn,
.danger-btn {
  height: 34px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.16s ease-out;
}

.primary-btn {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  box-shadow: 0 12px 30px rgba(59, 130, 246, 0.25);
}

.warn-btn {
  border-color: rgba(234, 179, 8, 0.5);
  color: #facc15;
  background: rgba(250, 204, 21, 0.1);
}

.danger-btn {
  border-color: rgba(248, 113, 113, 0.6);
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.ghost-btn:hover,
.primary-btn:hover,
.warn-btn:hover,
.danger-btn:hover {
  transform: translateY(-1px);
}

.danger-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-actions {
    width: 100%;
  }
}
</style>
