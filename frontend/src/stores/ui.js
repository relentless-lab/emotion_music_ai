import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    showLoginPanel: false,
    authMode: "login"
  }),
  actions: {
    openLoginPanel() {
      this.authMode = "login";
      this.showLoginPanel = true;
    },
    openRegisterPanel() {
      this.authMode = "register";
      this.showLoginPanel = true;
    },
    setAuthMode(mode) {
      this.authMode = mode;
    },
    closeLoginPanel() {
      this.showLoginPanel = false;
      this.authMode = "login";
    }
  }
});
