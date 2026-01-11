<template>
  <div v-if="showLoginPanel" class="login-modal">
    <section class="panel login-panel" :class="{ register: ui.authMode === 'register' }">
      <div class="login-header">
        <div class="login-title">
          {{ ui.authMode === "login" ? "登录您的账户" : "注册新用户账户" }}
        </div>
        <button class="close-btn" type="button" @click="close()">关闭</button>
      </div>

      <form
        v-if="ui.authMode === 'login'"
        class="auth-form"
        @submit.prevent="handleLogin"
      >
        <label class="field">
          <span>请输入用户名</span>
          <input
            v-model="loginForm.username"
            type="text"
            placeholder="请输入用户名"
            required
          />
        </label>
        <label class="field">
          <span>密码</span>
          <div class="password-input-wrapper">
            <input
              v-model="loginForm.password"
              :type="showLoginPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              required
            />
            <button
              type="button"
              class="password-toggle"
              @click="showLoginPassword = !showLoginPassword"
              :title="showLoginPassword ? '隐藏密码' : '显示密码'"
            >
              <!-- 睁眼 -->
              <svg v-if="showLoginPassword" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <!-- 闭眼 -->
              <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </label>

        <button class="cta primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? "登录中..." : "登录" }}
        </button>
        <p v-if="registerSuccess && ui.authMode === 'login'" class="success-text">{{ registerSuccess }}</p>
        <p v-if="auth.error" class="error-text">{{ auth.error }}</p>
      </form>

      <form
        v-else
        class="auth-form register-form"
        @submit.prevent="handleRegister"
      >
        <label class="field">
          <span>用户名</span>
          <input v-model="registerForm.username" type="text" placeholder="请输入用户名" required />
        </label>
        <label class="field">
          <span>电子邮箱</span>
          <input v-model="registerForm.email" type="email" placeholder="请输入电子邮箱" required />
        </label>
        <label class="field code-field">
          <span>验证码</span>
          <div class="code-row">
            <input v-model="registerForm.code" type="text" placeholder="请输入邮箱验证码" required />
            <button
              class="ghost-btn"
              type="button"
              :disabled="countdown > 0 || isSendingCode || !registerForm.email"
              @click="handleGetVerificationCode"
            >
              {{ countdown > 0 ? `${countdown}秒后重新获取` : isSendingCode ? "发送中..." : "获取验证码" }}
            </button>
          </div>
        </label>
        <label class="field">
          <span>密码</span>
          <div class="password-input-wrapper">
            <input
              v-model="registerForm.password"
              :type="showRegisterPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              required
            />
            <button
              type="button"
              class="password-toggle"
              @click="showRegisterPassword = !showRegisterPassword"
              :title="showRegisterPassword ? '隐藏密码' : '显示密码'"
            >
              <svg v-if="showRegisterPassword" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </label>
        <label class="field">
          <span>确认密码</span>
          <div class="password-input-wrapper">
            <input
              v-model="registerForm.confirm"
              :type="showConfirmPassword ? 'text' : 'password'"
              placeholder="再次输入密码"
              required
            />
            <button
              type="button"
              class="password-toggle"
              @click="showConfirmPassword = !showConfirmPassword"
              :title="showConfirmPassword ? '隐藏密码' : '显示密码'"
            >
              <svg v-if="showConfirmPassword" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </label>

        <div class="terms">
          <input type="checkbox" required />
          <span>我同意服务条款和隐私政策</span>
        </div>

        <button class="cta primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? "注册中..." : "注册" }}
        </button>
        <p v-if="auth.error && ui.authMode === 'register'" class="error-text">{{ auth.error }}</p>
      </form>

      <div class="register-row">
        <span
          v-if="ui.authMode === 'login'"
          class="register-link"
          @click="ui.openRegisterPanel()"
        >
          还没有账号？立即注册
        </span>
        <span
          v-else
          class="register-link"
          @click="ui.openLoginPanel()"
        >
          已有账号？立即登录
        </span>
      </div>
    </section>
  </div>

  <div v-if="showLoginSuccessToast" class="toast success-toast">登录成功</div>
  <div v-if="showCodeSuccessToast" class="toast success-toast">验证码已发送</div>
</template>

<script setup>
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { sendVerificationCode } from "@/services/authApi";

const auth = useAuthStore();
const ui = useUiStore();

const loginForm = reactive({
  username: "",
  password: ""
});

const registerForm = reactive({
  username: "",
  email: "",
  code: "",
  password: "",
  confirm: ""
});

const registerSuccess = ref("");

// 密码可见性控制
const showLoginPassword = ref(false);
const showRegisterPassword = ref(false);
const showConfirmPassword = ref(false);

// toast
const showLoginSuccessToast = ref(false);
const showCodeSuccessToast = ref(false);
let loginSuccessTimer;
let codeSuccessTimer;

// 验证码倒计时
const countdown = ref(0);
const isSendingCode = ref(false);
let countdownTimer;

const showLoginPanel = computed(() => ui.showLoginPanel && !auth.isLoggedIn);

const triggerLoginSuccessToast = () => {
  if (loginSuccessTimer) clearTimeout(loginSuccessTimer);
  showLoginSuccessToast.value = true;
  loginSuccessTimer = setTimeout(() => {
    showLoginSuccessToast.value = false;
  }, 1000);
};

const triggerCodeSuccessToast = () => {
  if (codeSuccessTimer) clearTimeout(codeSuccessTimer);
  showCodeSuccessToast.value = true;
  codeSuccessTimer = setTimeout(() => {
    showCodeSuccessToast.value = false;
  }, 2000);
};

const close = () => {
  ui.closeLoginPanel();
};

const handleLogin = async () => {
  auth.error = "";
  registerSuccess.value = "";
  const username = loginForm.username.trim();
  const password = loginForm.password;
  if (!username || !password) {
    auth.error = "请填写用户名和密码";
    return;
  }
  try {
    await auth.loginAction({ username, password });
    triggerLoginSuccessToast();
    loginForm.password = "";
    close();
  } catch (err) {
    // error 已写入 store
  }
};

const handleGetVerificationCode = async () => {
  const email = registerForm.email.trim();
  if (!email) {
    auth.error = "请先输入邮箱地址";
    return;
  }

  // 简单的邮箱格式验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    auth.error = "请输入有效的邮箱地址";
    return;
  }

  isSendingCode.value = true;
  auth.error = "";

  try {
    await sendVerificationCode(email);
    triggerCodeSuccessToast();

    // 开始倒计时
    countdown.value = 60;
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
    }, 1000);
  } catch (err) {
    // api.js 会把 message 写入 Error，这里兜底
    auth.error = err?.message || "验证码发送失败，请稍后重试";
  } finally {
    isSendingCode.value = false;
  }
};

const handleRegister = async () => {
  auth.error = "";
  registerSuccess.value = "";
  const username = registerForm.username.trim();
  const email = registerForm.email.trim();
  const password = registerForm.password;
  const confirm = registerForm.confirm;

  if (!username || !email || !password || !confirm) {
    auth.error = "请完整填写注册信息";
    return;
  }
  if (password !== confirm) {
    auth.error = "两次密码不一致";
    return;
  }
  if (!registerForm.code) {
    auth.error = "请输入验证码";
    return;
  }

  try {
    await auth.registerAction({
      username,
      email,
      code: registerForm.code,
      password
    });
    registerSuccess.value = "注册成功，请登录";
    loginForm.username = username;
    ui.setAuthMode("login");
  } catch (err) {
    // error 已写入 store
  }
};

// 防止弹窗打开时背景滚动 + ESC 关闭（更稳定，避免误触“闪退”）
let previousBodyOverflow = "";
const onKeyDown = e => {
  if (e.key === "Escape") {
    close();
  }
};

watch(showLoginPanel, open => {
  if (typeof document === "undefined") return;
  if (open) {
    previousBodyOverflow = document.body.style.overflow || "";
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
  } else {
    document.body.style.overflow = previousBodyOverflow;
    window.removeEventListener("keydown", onKeyDown);
  }
});

onBeforeUnmount(() => {
  if (loginSuccessTimer) clearTimeout(loginSuccessTimer);
  if (codeSuccessTimer) clearTimeout(codeSuccessTimer);
  if (countdownTimer) clearInterval(countdownTimer);
  if (typeof window !== "undefined") {
    window.removeEventListener("keydown", onKeyDown);
  }
  if (typeof document !== "undefined") {
    document.body.style.overflow = previousBodyOverflow;
  }
});
</script>

<style scoped>
.panel {
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.6);
  padding: 20px;
  backdrop-filter: blur(8px);
}

.login-modal {
  position: fixed;
  inset: 0;
  background: rgba(3, 7, 18, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.login-panel {
  padding: 24px 24px 28px;
  max-width: 420px;
  width: 100%;
  margin-left: -20px;
}

.login-panel.register {
  max-width: 420px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 18px;
}

.auth-form .field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-form .field span {
  color: #f9fafb;
  font-weight: 600;
  font-size: 14px;
}

.auth-form input {
  height: 40px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(12, 16, 26, 0.95);
  color: #f3f4f6;
  padding: 0 12px;
  outline: none;
}

.auth-form input:focus {
  border-color: rgba(79, 133, 255, 0.9);
  box-shadow: 0 0 0 2px rgba(79, 133, 255, 0.35);
}

.password-input-wrapper {
  position: relative;
  width: 100%;
}

.password-input-wrapper input {
  width: 100%;
  padding-right: 40px;
}

.password-toggle {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
  z-index: 2;
}

.password-toggle:hover {
  color: rgba(255, 255, 255, 0.8);
}

.register-form {
  gap: 10px;
}

.code-field .code-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

.ghost-btn {
  height: 40px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  cursor: pointer;
  font-weight: 600;
}

.ghost-btn:hover:not(:disabled) {
  border-color: rgba(79, 133, 255, 0.8);
}

.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cta {
  height: 42px;
  padding: 0 14px;
  border-radius: 10px;
  border: none;
  color: #f8fafc;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.3);
}

.cta.primary {
  background: #4f85ff;
}

.cta:hover {
  transform: translateY(-1px);
}

.login-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.login-title {
  text-align: center;
  font-weight: 700;
}

.error-text {
  color: #f87171;
  font-size: 13px;
}

.success-text {
  color: #10b981;
  font-size: 13px;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(229, 231, 235, 0.9);
  cursor: pointer;
  font-weight: 600;
  padding: 6px 8px;
  border-radius: 8px;
  transition: background 0.15s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.04);
}

.register-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.register-link {
  cursor: pointer;
}

.register-link:hover {
  color: #9cbcff;
}

.terms {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(229, 231, 235, 0.85);
}

.terms input {
  width: 14px;
  height: 14px;
}

.toast {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 700;
  color: #071c12;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.96), rgba(52, 211, 153, 0.96));
  border: 1px solid rgba(74, 222, 128, 0.4);
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.3);
  z-index: 10000;
  animation: toast-in 0.18s ease;
  letter-spacing: 0.02em;
}

.toast.success-toast {
  color: #071c12;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.96), rgba(52, 211, 153, 0.96));
  border: 1px solid rgba(74, 222, 128, 0.4);
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.3);
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translate(-50%, -6px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>





