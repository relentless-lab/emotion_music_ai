import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    showLoginPanel: false,
    authMode: "login",
    // Mobile/zoom-friendly sidebar drawer (Suno-like): hide fixed sidebar at narrow widths,
    // and open it via a topbar menu button.
    sidebarOpen: false
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
    },
    openSidebar() {
      this.sidebarOpen = true;
    },
    closeSidebar() {
      this.sidebarOpen = false;
    },
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    }
  }
});
