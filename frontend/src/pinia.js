import { createPinia } from "pinia";

// 全局 Pinia 实例：供 main.js 和 router 守卫共享使用（避免循环依赖）
export const pinia = createPinia();


