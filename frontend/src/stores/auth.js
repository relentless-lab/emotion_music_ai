import { defineStore } from "pinia";
import { deleteAccount, fetchProfile, login, register, updateProfile } from "@/services/authApi";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
    loading: false,
    error: ""
  }),
  getters: {
    isLoggedIn: state => !!state.token
  },
  actions: {
    async loginAction(credentials) {
      this.loading = true;
      this.error = "";
      try {
        const { token, user } = await login(credentials);
        this.token = token;
        this.user = user;
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      } catch (err) {
        this.error = err?.message || "登录失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async registerAction(payload) {
      this.loading = true;
      this.error = "";
      try {
        const res = await register(payload);
        return res;
      } catch (err) {
        this.error = err?.message || "注册失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async refreshProfile() {
      if (!this.token) return;
      try {
        const profile = await fetchProfile();
        // 保留登录态里拿到的 id 等关键字段（后端旧版 profile 可能不含 id）
        const merged = {
          ...(this.user || {}),
          ...(profile || {})
        };
        this.user = merged;
        localStorage.setItem(USER_KEY, JSON.stringify(merged));
      } catch (err) {
        // token 失效时清理状态，避免反复报错
        this.logout();
      }
    },
    async updateProfileAction(payload) {
      this.loading = true;
      this.error = "";
      try {
        const profile = await updateProfile(payload);
        const merged = {
          ...(this.user || {}),
          ...(profile || {})
        };
        this.user = merged;
        localStorage.setItem(USER_KEY, JSON.stringify(merged));
        return merged;
      } catch (err) {
        this.error = err?.message || "更新失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async deleteAccountAction() {
      this.loading = true;
      this.error = "";
      try {
        await deleteAccount();
        this.logout();
      } catch (err) {
        this.error = err?.message || "删除失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }
});
