import { createRouter, createWebHistory } from "vue-router";
import { pinia } from "@/pinia";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const routes = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/HomeView.vue")
  },
  {
    path: "/generate",
    name: "generate",
    component: () => import("../views/GenerateView.vue"),
    meta: { keepAlive: true }
  },
  {
    path: "/emotion",
    name: "emotion",
    component: () => import("../views/EmotionView.vue"),
    meta: { keepAlive: true }
  },
  {
    path: "/works",
    name: "works",
    component: () => import("../views/WorksView.vue")
  },
  {
    path: "/search",
    name: "search",
    component: () => import("../views/SearchView.vue")
  },
  {
    path: "/song/:id",
    name: "songDetail",
    component: () => import("../views/SongDetailView.vue")
  },
  {
    path: "/user/:id",
    name: "userPublic",
    component: () => import("../views/UserDetailView.vue")
  },
  {
    path: "/history",
    name: "history",
    component: () => import("../views/HistoryView.vue")
  },
  {
    path: "/notifications",
    name: "notifications",
    component: () => import("../views/NotificationsView.vue"),
    meta: { layout: "blank" }
  },
  {
    path: "/account",
    name: "account",
    component: () => import("../views/AccountSettingsView.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/profile",
    name: "profile",
    component: () => import("../views/ProfileView.vue")
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

router.beforeEach((to, from) => {
  if (!to.meta?.requiresAuth) return true;

  const auth = useAuthStore(pinia);
  const ui = useUiStore(pinia);
  if (auth.isLoggedIn) return true;

  // 在登录弹窗中展示提示
  auth.error = "请先进行登录";
  ui.openLoginPanel();

  // 首次进入（直接输入 /account）时，强制回首页；其它情况保持在当前页
  const isInitialNavigation = !from.name && from.fullPath === "/";
  return isInitialNavigation ? { name: "home" } : false;
});

export default router;
