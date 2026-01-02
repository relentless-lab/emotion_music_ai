import { createRouter, createWebHistory } from "vue-router";

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
    component: () => import("../views/AccountSettingsView.vue")
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

export default router;
