<template>
  <div class="settings-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">账号中心</p>
        <h1>账户设置</h1>
        <p class="muted">管理您的安全信息与账户操作。</p>
      </div>
    </header>

    <section class="card">
      <div class="card-title">
        <span>安全设置</span>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>当前密码</label>
          <input v-model="securityForm.currentPassword" type="password" placeholder="请输入当前密码" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="securityForm.newPassword" type="password" placeholder="请输入新密码" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input v-model="securityForm.confirmPassword" type="password" placeholder="请再次输入新密码" />
        </div>
      </div>
      <div class="actions-row">
        <button class="primary-btn" type="button" :disabled="savingSecurity" @click="handleChangePassword">
          {{ savingSecurity ? "保存中..." : "保存安全设置" }}
        </button>
        <p v-if="securitySuccess" class="hint hint-success">{{ securitySuccess }}</p>
        <p v-if="securityError" class="hint hint-error">{{ securityError }}</p>
      </div>
    </section>

    <section class="card danger">
      <div class="card-title">
        <span>账户操作</span>
      </div>
      <div class="danger-actions">
        <button class="warn-btn" type="button" @click="handleLogout">退出登录</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { changePassword } from "@/services/authApi";

const auth = useAuthStore();
const router = useRouter();

const savingSecurity = ref(false);
const securityError = ref("");
const securitySuccess = ref("");
const securityForm = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: ""
});

const handleLogout = () => {
  auth.logout();
  router.push("/");
};

const handleChangePassword = async () => {
  if (savingSecurity.value) return;
  securityError.value = "";
  securitySuccess.value = "";

  const currentPassword = securityForm.currentPassword || "";
  const newPassword = securityForm.newPassword || "";
  const confirmPassword = securityForm.confirmPassword || "";

  if (!currentPassword || !newPassword || !confirmPassword) {
    securityError.value = "请完整填写密码信息";
    return;
  }
  if (newPassword !== confirmPassword) {
    securityError.value = "两次输入的新密码不一致";
    return;
  }
  if (newPassword === currentPassword) {
    securityError.value = "新密码不能与原密码相同";
    return;
  }
  if (newPassword.length < 6) {
    securityError.value = "密码：至少 6 位";
    return;
  }

  savingSecurity.value = true;
  try {
    await changePassword({ current_password: currentPassword, new_password: newPassword });
    securitySuccess.value = "已修改成功";
    // 清理输入，避免密码留在页面里
    securityForm.currentPassword = "";
    securityForm.newPassword = "";
    securityForm.confirmPassword = "";
  } catch (err) {
    securityError.value = err?.message || "修改失败";
  } finally {
    savingSecurity.value = false;
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
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.hint {
  margin: 0;
  font-size: 13px;
}

.hint-success {
  color: rgba(16, 185, 129, 0.95);
}

.hint-error {
  color: rgba(248, 113, 113, 0.95);
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
    gap: 12px;
  }
}
</style>
