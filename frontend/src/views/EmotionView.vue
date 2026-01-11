<template>
  <div class="emotion-demo">
    <h1>音乐情绪分析</h1>

    <section class="panel upload-panel">
      <!-- 上传控件：仅在非历史模式下展示 -->
      <div class="controls" v-if="!historyMode">
        <div class="file-upload-wrapper">
          <button class="primary-btn" type="button" @click="$refs.fileInput.click()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            <span>选择文件</span>
          </button>
          <input ref="fileInput" type="file" accept="audio/*" @change="onFileChange" style="display: none" />
          <span class="file-name" v-if="selectedFile">{{ selectedFile.name }}</span>
        </div>
        <button class="primary-btn analysis-btn" :disabled="!selectedFile || isAnalyzing" @click="onAnalyze">
          <span v-if="!isAnalyzing">上传并分析</span>
          <template v-else>
            <span class="loading-spinner--small"></span>
            <span>分析中...</span>
          </template>
        </button>
      </div>

      <!-- 状态提示：两种模式都显示 -->
      <span class="status">{{ statusText }}</span>

      <!-- 分析进度条 -->
      <div v-if="showProgress" class="progress-container">
        <div class="progress-bar-wrapper">
          <div class="progress-bar" :style="{ width: `${progressPercent}%` }"></div>
        </div>
        <div class="progress-text">{{ progressPercent }}%</div>
      </div>

      <!-- 播放器：始终存在，historyMode 下用后端提供的 URL -->
      <audio ref="audioEl" controls class="audio-player" :src="audioUrl"></audio>
    </section>

    <div class="row">
      <div class="col panel">
        <h3>情绪分布饼图（随播放动态变化）</h3>
        <div class="feature-card" v-if="!historyMode">
          <div class="feature-header">
            <span class="feature-badge">{{ demoMode ? "示例演示" : "功能说明" }}</span>
            <span class="feature-title">动态饼图说明</span>
          </div>
          <div class="feature-body" v-if="demoMode">
            <div class="feature-text">
              {{ demoPieExplainDisplay }}<span class="typing-cursor typing-cursor--sm" />
            </div>
          </div>
          <div class="feature-body" v-else>
            <div class="feature-text feature-text--muted">
              播放音乐时，饼图会按时间片实时更新；暂停/拖动进度条会同步刷新当前分布。
            </div>
          </div>
        </div>
        <div ref="pieChartRef" class="chart"></div>
      </div>
      <div class="col panel">
        <h3>情绪波形图</h3>
        <div class="feature-card" v-if="!historyMode">
          <div class="feature-header">
            <span class="feature-badge">{{ demoMode ? "示例演示" : "功能说明" }}</span>
            <span class="feature-title">动态波形图说明</span>
          </div>
          <div class="feature-body" v-if="demoMode">
            <div class="feature-text">
              {{ demoWaveExplainDisplay }}<span class="typing-cursor typing-cursor--sm" />
            </div>
          </div>
          <div class="feature-body" v-else>
            <div class="feature-text feature-text--muted">
              实际分析时，情绪波形将随音乐播放动态变化，反映情绪强度随时间的起伏情况。
            </div>
          </div>
        </div>
        <div ref="waveChartRef" class="chart"></div>
        <div class="metrics">
          <div>
            当前情绪强度：<span>{{ displayIntensity }}</span>
            &nbsp;&nbsp;当前强度等级：<span>{{ intensityLevel }}</span>
          </div>
          <div>
            平均情绪强度：<span>{{ avgIntensity }}</span>
            &nbsp;&nbsp;情绪变化频率：<span>{{ volatility }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <div class="col panel">
        <h3>情绪四象限分析（整体）</h3>
        <div ref="quadrantChartRef" class="chart"></div>
        <div class="metrics">
          <div>主导情绪：<span>{{ dominantEmotion }}</span></div>
          <div>
            愉悦度：<span>{{ valence }}</span>
            &nbsp;&nbsp;唤醒度：<span>{{ arousal }}</span>
          </div>
        </div>
      </div>
      <div class="col panel">
        <h3>AI 情绪分析报告</h3>
        <div class="summary-text">
          <template v-if="demoMode">
            <div class="demo-badge">示例演示</div>
            <div class="demo-text">{{ demoReportDisplay }}<span class="typing-cursor" /></div>
          </template>
          <template v-else>
            {{ summaryText }}
          </template>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <div v-if="toastMessage" :class="['toast', `toast-${toastType}`]">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { analyzeMusicTask, fetchEmotionDetail, getEmotionTaskStatus } from "@/services/emotionApi";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin))
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");
const auth = useAuthStore();
const ui = useUiStore();

const fileInput = ref(null);
const audioEl = ref(null);
const pieChartRef = ref(null);
const waveChartRef = ref(null);
const quadrantChartRef = ref(null);

const selectedFile = ref(null);
const audioUrl = ref("");
const statusText = ref("请选择一段音乐文件");
const isAnalyzing = ref(false);
const summaryText = ref("");
const analysisResult = ref(null);
const historyMode = ref(false);

// -------- 持久化（仿音乐生成页：离开再回来仍可继续/可回显）--------
// 注意：必须按用户隔离，避免“游客/其他账号”看到上一位用户的分析进度
const BASE_EMOTION_SESSION_KEY = "emotion_session_v2";
const EMOTION_SESSION_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const currentTaskId = ref("");
const currentAnalysisId = ref(null);
let emotionPollTimer = null;
let destroyed = false;

const getEmotionSessionKey = () => {
  const uid = auth?.user?.id;
  if (!auth?.isLoggedIn || !uid) return `${BASE_EMOTION_SESSION_KEY}:guest`;
  return `${BASE_EMOTION_SESSION_KEY}:user:${uid}`;
};

// demoMode: 只有在有真实分析结果时才为 false，分析等待阶段继续显示 demo
const demoMode = computed(() => !analysisResult.value);
const demoReportText = [
  "AI 情绪分析说明",
  "",
  "上传音乐后，系统将从以下维度进行分析：",
  "• 情绪类别分布（能量 / 快乐 / 治愈 / 史诗等）",
  "• 情绪强度随时间变化（随播放实时更新）",
  "• 整体情绪在「唤醒度 × 愉悦度」空间的位置",
  "• 生成可读的情绪理解与风格总结",
  "",
  "提示：此处为示例演示，实际结果将基于你的音乐生成。"
].join("\n");
const demoReportDisplay = ref("");
let demoTypingTimer = null;
let demoRestartTimer = null;
let demoCharIndex = 0;

const EMOTION_META = [
  {
    cn: "能量/励志",
    en: "energetic_inspiring",
    av: [0.8, 0.8]
  },
  { cn: "欢快/快乐", en: "happy_joyful", av: [0.9, 0.7] },
  {
    cn: "治愈/宿命",
    en: "healing_fateful",
    av: [0.65, 0.45]
  },
  {
    cn: "浪漫/温柔",
    en: "romantic_tender",
    av: [0.75, 0.4]
  },
  { cn: "平静/舒缓", en: "calm_peaceful", av: [0.7, 0.25] },
  { cn: "悲伤/遗憾", en: "sad_regretful", av: [0.25, 0.3] },
  {
    cn: "神秘/戏剧",
    en: "mysterious_drama",
    av: [0.45, 0.65]
  },
  { cn: "史诗/宏大", en: "epic_grand", av: [0.82, 0.9] }
];

const EMOTION_BY_EN = Object.fromEntries(EMOTION_META.map((e) => [e.en, e]));
const EMOTION_BY_INDEX = Object.fromEntries(EMOTION_META.map((e, idx) => [idx, e]));

const demoPieExplainText = [
  "进入页面：饼图按扇区逆时针铺满展示",
  "演示态：占比会周期性变化并循环播放",
  "实际分析：随音乐播放实时更新"
].join("\n");
const demoPieExplainDisplay = ref("");
let demoPieExplainTimer = null;
let demoPieExplainRestartTimer = null;
let demoPieExplainCharIndex = 0;

const demoWaveExplainText = [
  "示例演示",
  "实际分析时，情绪波形将随音乐播放动态变化，反映情绪强度随时间的起伏情况。"
].join("\n");
const demoWaveExplainDisplay = ref("");
let demoWaveExplainTimer = null;
let demoWaveExplainRestartTimer = null;
let demoWaveExplainCharIndex = 0;

let demoPieLoopTimer = null;
let pieIntroRaf = null;
let pieAnimationToken = 0;
let pieIntroInProgress = false;
let demoPieKeyframeIndex = 0;
let demoPieStartAngle = 90;

const displayIntensity = ref("-");
const intensityLevel = ref("-");
const avgIntensity = ref("-");
const volatility = ref("-");
const dominantEmotion = ref("-");
const valence = ref("-");
const arousal = ref("-");
const segmentPoints = ref([]);

// 进度条相关
const showProgress = ref(false);
const progressPercent = ref(0);
let progressTimer = null;
let progressInterval = null;

// Toast 提示
const toastMessage = ref("");
const toastType = ref("success");

const showToast = (message, type = "success") => {
  toastMessage.value = message;
  toastType.value = type;
  setTimeout(() => {
    toastMessage.value = "";
  }, 3000);
};

const clearEmotionSession = () => {
  try {
    localStorage.removeItem(getEmotionSessionKey());
    // 清理旧版本全局 key，避免串号（v1 没有用户隔离）
    localStorage.removeItem("emotion_session_v1");
  } catch (e) {
    // ignore
  }
};

const saveEmotionSession = () => {
  // 游客不做持久化：每次进入都应该是新的界面
  if (!auth?.isLoggedIn) {
    try {
      localStorage.removeItem(`${BASE_EMOTION_SESSION_KEY}:guest`);
    } catch {
      // ignore
    }
    return;
  }
  if (historyMode.value) return;
  const payload = {
    ts: Date.now(),
    owner_user_id: auth?.user?.id ?? null,
    taskId: currentTaskId.value || "",
    analysisId: currentAnalysisId.value || null,
    audioUrl: audioUrl.value || "",
    statusText: statusText.value || "",
    isAnalyzing: !!isAnalyzing.value,
    progress: Number(progressPercent.value) || 0
  };
  try {
    localStorage.setItem(getEmotionSessionKey(), JSON.stringify(payload));
  } catch (e) {
    // ignore
  }
};

const stopEmotionPolling = () => {
  if (emotionPollTimer) {
    clearTimeout(emotionPollTimer);
    emotionPollTimer = null;
  }
};

let pieChart = null;
let waveChart = null;
let quadrantChart = null;
let resizeHandler = null;
let timer = null;
let echartsLoading = null;

// 动态饼图丝滑：指数平滑缓存（不改变后端数据，只改变前端展示）
let smoothPieProbs = [];
let smoothPieLastTs = 0;
let lastAudioTime = -1;

// 演示波形相关
let demoWaveTimer = null;
let demoWaveTime = 0; // 演示时间（秒）
const DEMO_WAVE_DURATION = 60; // 演示波形总时长（秒）
const DEMO_WAVE_UPDATE_INTERVAL = 400; // 更新间隔（毫秒）
const DEMO_WAVE_DATA_POINTS = 120; // 固定数据点数量（滑动窗口）
let demoWaveData = []; // 存储演示波形数据

const getEmotionMeta = (idx, labelEn) => {
  if (labelEn && EMOTION_BY_EN[labelEn]) return EMOTION_BY_EN[labelEn];
  return EMOTION_BY_INDEX[idx] || null;
};

const getEmotionArousal = (idx, labelEn) => getEmotionMeta(idx, labelEn)?.av?.[1] ?? 0;

const calculateSegmentPoints = () => {
  if (!analysisResult.value || !analysisResult.value.segments) return [];
  const segments = analysisResult.value.segments;
  const labelsEn = analysisResult.value.labels_en || [];

  return segments
    .map((seg, idx) => {
      const probs = seg.probs || [];
      if (!probs.length) return null;

      let seg_valence = 0;
      let seg_arousal = 0;
      const sum = probs.reduce((a, b) => a + b, 0) || 1;
      const normProbs = probs.map((p) => p / sum);

      normProbs.forEach((p, i) => {
        const meta = getEmotionMeta(i, labelsEn[i]);
        if (meta && meta.av) {
          seg_valence += p * meta.av[0];
          seg_arousal += p * meta.av[1];
        }
      });

      const vx = seg_valence * 2 - 1;
      const vy = seg_arousal * 2 - 1;

      // 估算 start/end：用相邻 center 的中点
      let startTime = 0;
      let endTime = 0;
      if (idx === 0) {
        startTime = 0;
        endTime = segments.length > 1 ? (segments[0].center + segments[1].center) / 2 : segments[0].center + 1.5;
      } else if (idx === segments.length - 1) {
        startTime = (segments[idx - 1].center + segments[idx].center) / 2;
        endTime = audioEl.value?.duration || segments[idx].center + 1.5;
      } else {
        startTime = (segments[idx - 1].center + segments[idx].center) / 2;
        endTime = (segments[idx].center + segments[idx + 1].center) / 2;
      }

      return {
        value: [vx, vy],
        segmentIdx: idx + 1,
        startTime,
        endTime,
        center: seg.center,
        valence: seg_valence,
        arousal: seg_arousal
      };
    })
    .filter((p) => p !== null);
};

const intensityToLevel = (x) => {
  if (x < 0.2) return "低";
  if (x < 0.4) return "中低";
  if (x < 0.6) return "中";
  if (x < 0.8) return "中高";
  return "高";
};

const resetDisplay = () => {
  displayIntensity.value = "-";
  intensityLevel.value = "-";
  avgIntensity.value = "-";
  volatility.value = "-";
  dominantEmotion.value = "-";
  valence.value = "-";
  arousal.value = "-";
  summaryText.value = "";
  segmentPoints.value = [];
};

const stopDemoTyping = () => {
  if (demoTypingTimer) clearInterval(demoTypingTimer);
  if (demoRestartTimer) clearTimeout(demoRestartTimer);
  demoTypingTimer = null;
  demoRestartTimer = null;
};

const stopDemoPieExplainTyping = () => {
  if (demoPieExplainTimer) clearInterval(demoPieExplainTimer);
  if (demoPieExplainRestartTimer) clearTimeout(demoPieExplainRestartTimer);
  demoPieExplainTimer = null;
  demoPieExplainRestartTimer = null;
};

const stopDemoWaveExplainTyping = () => {
  if (demoWaveExplainTimer) clearInterval(demoWaveExplainTimer);
  if (demoWaveExplainRestartTimer) clearTimeout(demoWaveExplainRestartTimer);
  demoWaveExplainTimer = null;
  demoWaveExplainRestartTimer = null;
};

const startDemoPieExplainTyping = () => {
  stopDemoPieExplainTyping();
  demoPieExplainDisplay.value = "";
  demoPieExplainCharIndex = 0;

  const speedMs = 24;
  const pauseAfterMs = 1800;

  demoPieExplainTimer = setInterval(() => {
    if (!demoMode.value) {
      stopDemoPieExplainTyping();
      return;
    }
    demoPieExplainCharIndex += 1;
    demoPieExplainDisplay.value = demoPieExplainText.slice(0, demoPieExplainCharIndex);
    if (demoPieExplainCharIndex >= demoPieExplainText.length) {
      stopDemoPieExplainTyping();
      demoPieExplainRestartTimer = setTimeout(() => {
        if (demoMode.value) startDemoPieExplainTyping();
      }, pauseAfterMs);
    }
  }, speedMs);
};

const startDemoWaveExplainTyping = () => {
  stopDemoWaveExplainTyping();
  demoWaveExplainDisplay.value = "";
  demoWaveExplainCharIndex = 0;

  const speedMs = 30;
  const pauseAfterMs = 2000;

  demoWaveExplainTimer = setInterval(() => {
    if (!demoMode.value) {
      stopDemoWaveExplainTyping();
      return;
    }
    demoWaveExplainCharIndex += 1;
    demoWaveExplainDisplay.value = demoWaveExplainText.slice(0, demoWaveExplainCharIndex);
    if (demoWaveExplainCharIndex >= demoWaveExplainText.length) {
      stopDemoWaveExplainTyping();
      demoWaveExplainRestartTimer = setTimeout(() => {
        if (demoMode.value) startDemoWaveExplainTyping();
      }, pauseAfterMs);
    }
  }, speedMs);
};

const cancelPieAnimation = () => {
  pieAnimationToken += 1;
  if (pieIntroRaf) cancelAnimationFrame(pieIntroRaf);
  pieIntroRaf = null;
  pieIntroInProgress = false;
};

const stopDemoPie = () => {
  cancelPieAnimation();
  if (demoPieLoopTimer) clearInterval(demoPieLoopTimer);
  demoPieLoopTimer = null;
};

// 生成演示波形数据点
const generateDemoWavePoint = (time) => {
  // 使用多个正弦波叠加，加上随机噪声，创造有节奏、有生命感的效果
  const base = 0.5; // 基础强度
  const amplitude1 = 0.25; // 主波振幅
  const amplitude2 = 0.15; // 次波振幅
  const amplitude3 = 0.08; // 细节波振幅
  
  // 不同频率的正弦波
  const wave1 = Math.sin(time * 0.1) * amplitude1; // 缓慢变化
  const wave2 = Math.sin(time * 0.3) * amplitude2; // 中等频率
  const wave3 = Math.sin(time * 0.7) * amplitude3; // 快速细节
  
  // 添加轻微的随机噪声（不要剧烈抖动）
  const noise = (Math.random() - 0.5) * 0.05;
  
  // 计算最终强度，限制在 0-1 之间
  let intensity = base + wave1 + wave2 + wave3 + noise;
  intensity = Math.max(0.1, Math.min(0.95, intensity));
  
  return [time, intensity];
};

// 更新演示波形数据
const updateDemoWave = () => {
  if (!waveChart || !demoMode.value) return;
  
  // 添加新数据点
  const newPoint = generateDemoWavePoint(demoWaveTime);
  demoWaveData.push(newPoint);
  
  // 保持固定长度（滑动窗口）
  if (demoWaveData.length > DEMO_WAVE_DATA_POINTS) {
    demoWaveData.shift();
  }
  
  // 更新时间（模拟播放进度）
  demoWaveTime += DEMO_WAVE_UPDATE_INTERVAL / 1000;
  
  // 循环播放：当超过总时长时，重置时间并清空数据重新开始
  if (demoWaveTime >= DEMO_WAVE_DURATION) {
    demoWaveTime = 0;
    demoWaveData = [];
  }
  
  // 更新图表
  waveChart.setOption({
    series: [
      {
        name: "情绪强度",
        type: "line",
        smooth: true, // 演示模式使用平滑曲线，看起来更自然
        showSymbol: false,
        lineStyle: {
          color: "#3b82f6",
          width: 2
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(59, 130, 246, 0.25)" },
              { offset: 1, color: "rgba(59, 130, 246, 0.03)" }
            ]
          }
        },
        data: demoWaveData
      },
      {
        name: "当前播放位置",
        type: "scatter",
        symbolSize: 14,
        z: 10,
        itemStyle: {
          color: "#ffeb3b",
          borderColor: "#ffffff",
          borderWidth: 3,
          shadowBlur: 12,
          shadowColor: "rgba(255, 235, 59, 0.8)"
        },
        data: demoWaveData.length > 0 ? [[demoWaveTime, demoWaveData[demoWaveData.length - 1][1]]] : []
      }
    ],
    graphic: [
      {
        type: "text",
        right: 12,
        top: 10,
        style: {
          text: "示例演示",
          fill: "rgba(255,255,255,0.55)",
          fontSize: 12
        }
      }
    ]
  });
  
  // 更新指标显示（演示模式下的模拟值）
  if (demoWaveData.length > 0) {
    const currentIntensity = demoWaveData[demoWaveData.length - 1][1];
    displayIntensity.value = `${(currentIntensity * 100).toFixed(1)}%`;
    intensityLevel.value = intensityToLevel(currentIntensity);
    
    // 计算平均值
    const avg = demoWaveData.reduce((sum, point) => sum + point[1], 0) / demoWaveData.length;
    avgIntensity.value = `${(avg * 100).toFixed(1)}%`;
    
    // 计算变化频率（简化：基于数据点间的变化）
    if (demoWaveData.length > 1) {
      let changes = 0;
      for (let i = 1; i < demoWaveData.length; i++) {
        if (Math.abs(demoWaveData[i][1] - demoWaveData[i - 1][1]) > 0.05) {
          changes++;
        }
      }
      volatility.value = `${changes}次`;
    } else {
      volatility.value = "-";
    }
  }
};

const startDemoWave = () => {
  stopDemoWave();
  demoWaveTime = 0;
  demoWaveData = [];
  
  // 初始化图表（演示模式样式）
  if (waveChart) {
    waveChart.setOption({
      series: [
        {
          name: "情绪强度",
          type: "line",
          smooth: true,
          showSymbol: false,
          lineStyle: {
            color: "#3b82f6",
            width: 2
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(59, 130, 246, 0.25)" },
                { offset: 1, color: "rgba(59, 130, 246, 0.03)" }
              ]
            }
          },
          data: []
        },
        {
          name: "当前播放位置",
          type: "scatter",
          symbolSize: 14,
          z: 10,
          itemStyle: {
            color: "#ffeb3b",
            borderColor: "#ffffff",
            borderWidth: 3,
            shadowBlur: 12,
            shadowColor: "rgba(255, 235, 59, 0.8)"
          },
          data: []
        }
      ],
      graphic: [
        {
          type: "text",
          right: 12,
          top: 10,
          style: {
            text: "示例演示",
            fill: "rgba(255,255,255,0.55)",
            fontSize: 12
          }
        }
      ]
    });
  }
  
  // 立即更新一次
  updateDemoWave();
  
  // 定时更新
  demoWaveTimer = setInterval(() => {
    if (!demoMode.value) {
      stopDemoWave();
      return;
    }
    updateDemoWave();
  }, DEMO_WAVE_UPDATE_INTERVAL);
};

const stopDemoWave = () => {
  if (demoWaveTimer) {
    clearInterval(demoWaveTimer);
    demoWaveTimer = null;
  }
  demoWaveTime = 0;
  demoWaveData = [];
  
  // 清除演示标记
  if (waveChart) {
    waveChart.setOption({ graphic: [] });
  }
};

const normalizeWeights = (arr = []) => {
  const safe = arr.map((v) => Math.max(0, Number(v) || 0));
  const sum = safe.reduce((a, b) => a + b, 0) || 1;
  return safe.map((v) => v / sum);
};

const weightsToPieData = (weights, labelsCn = [], labelsEn = []) => {
  const w = normalizeWeights(weights);
  return w.map((v, idx) => {
    const cn = labelsCn[idx];
    const en = labelsEn[idx];
    const name = [cn, en].filter(Boolean).join(" ");
    const stableId = en || cn || String(idx);
    return {
      id: stableId,
      name: name || `情绪${idx + 1}`,
      value: +v.toFixed(4)
    };
  });
};

const animatePieReveal = ({
  targetWeights,
  labelsCn,
  labelsEn,
  startAngle = 90,
  clockwise = false,
  sliceMs = 240,
  gapMs = 30
}) => {
  if (!pieChart) return;
  cancelPieAnimation();
  pieIntroInProgress = true;
  const token = (pieAnimationToken += 1);

  const targets = normalizeWeights(targetWeights);
  const n = targets.length || 0;
  if (!n) {
    pieIntroInProgress = false;
    return;
  }

  const eps = 0.0001;
  const current = Array.from({ length: n }, () => eps);
  let activeIdx = 0;
  let sliceStart = performance.now();

  const render = () => {
    if (token !== pieAnimationToken) return;
    pieChart.setOption(
      {
        series: [
          {
            startAngle,
            clockwise,
            animation: false,
            data: weightsToPieData(current, labelsCn, labelsEn)
          }
        ]
      },
      { lazyUpdate: true }
    );
  };

  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

  const step = (now) => {
    if (token !== pieAnimationToken) return;
    const t = Math.min(1, (now - sliceStart) / sliceMs);
    const eased = easeOutCubic(t);

    for (let i = 0; i < n; i += 1) {
      if (i < activeIdx) current[i] = targets[i];
      else if (i > activeIdx) current[i] = eps;
      else current[i] = eps + (targets[i] - eps) * eased;
    }

    render();

    if (t >= 1) {
      activeIdx += 1;
      if (activeIdx >= n) {
        pieIntroInProgress = false;
        pieChart.setOption({ series: [{ animation: true, data: weightsToPieData(targets, labelsCn, labelsEn) }] });
        return;
      }
      sliceStart = now + gapMs;
    }

    pieIntroRaf = requestAnimationFrame(step);
  };

  render();
  pieIntroRaf = requestAnimationFrame(step);
};

const demoPieKeyframes = [
  [0.26, 0.11, 0.11, 0.07, 0.07, 0.05, 0.11, 0.22],
  [0.05, 0.12, 0.22, 0.16, 0.26, 0.12, 0.05, 0.02],
  [0.12, 0.05, 0.1, 0.06, 0.07, 0.26, 0.2, 0.14],
  [0.18, 0.3, 0.12, 0.14, 0.1, 0.03, 0.05, 0.08]
];

const startDemoPie = () => {
  if (!pieChart) return;
  stopDemoPie();
  demoPieKeyframeIndex = 0;
  demoPieStartAngle = 90;

  const labelsCn = EMOTION_META.map((e) => e.cn);
  const labelsEn = EMOTION_META.map((e) => e.en);

  pieChart.setOption({
    graphic: [
      {
        type: "text",
        right: 12,
        top: 10,
        style: {
          text: "示例演示",
          fill: "rgba(255,255,255,0.55)",
          fontSize: 12
        }
      }
    ]
  });

  animatePieReveal({
    targetWeights: demoPieKeyframes[0],
    labelsCn,
    labelsEn,
    startAngle: demoPieStartAngle,
    clockwise: false,
    sliceMs: 240,
    gapMs: 30
  });

  demoPieLoopTimer = setInterval(() => {
    if (!demoMode.value) {
      stopDemoPie();
      return;
    }
    if (pieIntroInProgress) return;
    demoPieKeyframeIndex = (demoPieKeyframeIndex + 1) % demoPieKeyframes.length;
    demoPieStartAngle -= 28;
    pieChart?.setOption({
      series: [
        {
          startAngle: demoPieStartAngle,
          clockwise: false,
          universalTransition: true,
          animationDuration: 1100,
          animationEasing: "cubicInOut",
          data: weightsToPieData(demoPieKeyframes[demoPieKeyframeIndex], labelsCn, labelsEn)
        }
      ]
    });
  }, 2200);
};

const startDemoTyping = () => {
  stopDemoTyping();
  demoReportDisplay.value = "";
  demoCharIndex = 0;

  const speedMs = 35;
  const pauseAfterMs = 2200;

  demoTypingTimer = setInterval(() => {
    if (!demoMode.value) {
      stopDemoTyping();
      return;
    }
    demoCharIndex += 1;
    demoReportDisplay.value = demoReportText.slice(0, demoCharIndex);
    if (demoCharIndex >= demoReportText.length) {
      stopDemoTyping();
      demoRestartTimer = setTimeout(() => {
        if (demoMode.value) startDemoTyping();
      }, pauseAfterMs);
    }
  }, speedMs);
};

const clearCharts = () => {
  pieChart?.setOption({ series: [{ data: [] }] });
  waveChart?.setOption({ series: [{ data: [] }, { data: [] }] });
  quadrantChart?.setOption({ series: [{ data: [] }, { data: [] }] });
};

const toAbsoluteUrl = (path) => {
  if (!path) return "";
  if (/^(https?:)?\/\//i.test(path) || path.startsWith("blob:") || path.startsWith("data:")) return path;
  const base = API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "");
  try {
    return new URL(path, base).toString();
  } catch {
    return path;
  }
};

const ensureEcharts = () => {
  if (typeof window === "undefined") return Promise.resolve(null);
  if (window.echarts) return Promise.resolve(window.echarts);
  if (echartsLoading) return echartsLoading;
  echartsLoading = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js";
    script.onload = () => resolve(window.echarts);
    script.onerror = () => reject(new Error("ECharts 加载失败"));
    document.head.appendChild(script);
  });
  return echartsLoading;
};

const initCharts = () => {
  const echarts = window.echarts;
  if (!echarts) return;
  pieChart = echarts.init(pieChartRef.value);
  waveChart = echarts.init(waveChartRef.value);
  quadrantChart = echarts.init(quadrantChartRef.value);

  pieChart.setOption({
    tooltip: { trigger: "item" },
    series: [
      {
        id: "emotionPie",
        name: "情绪分布",
        type: "pie",
        radius: "70%",
        startAngle: 90,
        clockwise: false,
        universalTransition: true,
        animationDuration: 500,
        animationEasing: "cubicOut",
        animationDurationUpdate: 260,
        animationEasingUpdate: "cubicOut",
        data: [],
        label: { color: "#fff" }
      }
    ]
  });

  waveChart.setOption({
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        if (!params.length) return "";
        const p = params[0];
        return `时间: ${p.data[0].toFixed(1)} s<br/>情绪强度: ${(p.data[1] * 100).toFixed(1)} %`;
      }
    },
    xAxis: {
      type: "value",
      name: "时间 (s)",
      axisLine: { lineStyle: { color: "#fff" } },
      axisLabel: { color: "#fff" }
    },
    yAxis: {
      type: "value",
      name: "情绪强度",
      min: 0,
      max: 1,
      axisLine: { lineStyle: { color: "#fff" } },
      axisLabel: {
        color: "#fff",
        formatter: (v) => `${(v * 100).toFixed(0)}%`
      }
    },
    series: [
      {
        name: "情绪强度",
        type: "line",
        smooth: false,
        showSymbol: true,
        data: []
      },
      {
        name: "当前播放位置",
        type: "scatter",
        symbolSize: 14,
        z: 10,
        itemStyle: {
          color: "#ffeb3b",
          borderColor: "#ffffff",
          borderWidth: 3,
          shadowBlur: 12,
          shadowColor: "rgba(255, 235, 59, 0.8)"
        },
        data: []
      }
    ]
  });

  quadrantChart.setOption({
    tooltip: {
      backgroundColor: "rgba(10, 25, 48, 0.9)",
      borderColor: "rgba(30, 128, 255, 0.5)",
      textStyle: { color: "#fff" },
      formatter: (params) => {
        const d = params.data;
        if (d.segmentIdx) {
          return `
            <div style="font-weight:bold;margin-bottom:4px;color:#1e80ff">片段 #${d.segmentIdx}</div>
            时间: ${d.startTime.toFixed(1)}s ~ ${d.endTime.toFixed(1)}s<br/>
            中心: ${d.center.toFixed(1)}s<br/>
            愉悦度: ${(d.valence * 100).toFixed(1)}% (vx: ${d.value[0].toFixed(2)})<br/>
            唤醒度: ${(d.arousal * 100).toFixed(1)}% (vy: ${d.value[1].toFixed(2)})
          `;
        }
        return `
          <div style="font-weight:bold;margin-bottom:4px;color:#ffeb3b">整体情绪</div>
          愉悦度: ${(d.valence ? d.valence * 100 : ((d.value[0] + 1) / 2) * 100).toFixed(1)}%<br/>
          唤醒度: ${(d.arousal ? d.arousal * 100 : ((d.value[1] + 1) / 2) * 100).toFixed(1)}%
        `;
      }
    },
    xAxis: {
      type: "value",
      min: -1,
      max: 1,
      name: "愉悦度",
      nameLocation: "end",
      nameTextStyle: { color: "rgba(255,255,255,0.7)", padding: [0, 0, 0, 10] },
      axisLabel: {
        color: "rgba(255,255,255,0.6)",
        formatter: (v) => `${(v * 100).toFixed(0)}%`
      },
      axisLine: { onZero: true, lineStyle: { color: "rgba(255,255,255,0.8)", width: 2 } },
      splitLine: {
        show: true,
        lineStyle: { type: "dashed", color: "rgba(255,255,255,0.15)" }
      }
    },
    yAxis: {
      type: "value",
      min: -1,
      max: 1,
      name: "唤醒度",
      nameLocation: "end",
      nameTextStyle: { color: "rgba(255,255,255,0.7)", padding: [0, 0, 10, 0] },
      axisLabel: {
        color: "rgba(255,255,255,0.6)",
        formatter: (v) => `${(v * 100).toFixed(0)}%`
      },
      axisLine: { onZero: true, lineStyle: { color: "rgba(255,255,255,0.8)", width: 2 } },
      splitLine: {
        show: true,
        lineStyle: { type: "dashed", color: "rgba(255,255,255,0.15)" }
      }
    },
    series: [
      {
        name: "分段轨迹",
        type: "scatter",
        symbolSize: 8,
        itemStyle: {
          color: "rgba(30, 128, 255, 0.4)",
          borderColor: "rgba(255,255,255,0.2)",
          borderWidth: 1
        },
        emphasis: {
          scale: 2,
          itemStyle: {
            color: "#ffeb3b",
            shadowBlur: 15,
            shadowColor: "rgba(255, 235, 59, 0.9)",
            borderColor: "#fff",
            borderWidth: 2
          }
        },
        data: []
      },
      {
        name: "整体位置",
        type: "scatter",
        symbolSize: 20,
        z: 10,
        itemStyle: {
          color: "#ff5722",
          borderColor: "#fff",
          borderWidth: 3,
          shadowBlur: 20,
          shadowColor: "rgba(255, 87, 34, 0.6)"
        },
        data: []
      }
    ],
    graphic: [
      // 背景象限底色
      {
        type: "group",
        silent: true,
        children: [
          {
            type: "rect",
            left: "50%",
            top: "10%",
            shape: { width: "40%", height: "40%" },
            style: { fill: "rgba(130, 144, 255, 0.05)" }
          },
          {
            type: "rect",
            left: "10%",
            top: "10%",
            shape: { width: "40%", height: "40%" },
            style: { fill: "rgba(100, 100, 255, 0.02)" }
          },
          {
            type: "rect",
            left: "10%",
            top: "50%",
            shape: { width: "40%", height: "40%" },
            style: { fill: "rgba(255, 100, 100, 0.03)" }
          },
          {
            type: "rect",
            left: "50%",
            top: "50%",
            shape: { width: "40%", height: "40%" },
            style: { fill: "rgba(100, 255, 100, 0.03)" }
          }
        ]
      },
      // 象限文字（水印风格）
      {
        type: "text",
        left: "15%",
        top: "15%",
        style: { text: "神秘/戏剧", fill: "rgba(255,255,255,0.15)", fontSize: 20, fontWeight: "bold" }
      },
      {
        type: "text",
        right: "15%",
        top: "15%",
        style: { text: "史诗/宏大", fill: "rgba(255,255,255,0.15)", fontSize: 20, fontWeight: "bold" }
      },
      {
        type: "text",
        left: "15%",
        bottom: "15%",
        style: { text: "悲伤/遗憾", fill: "rgba(255,255,255,0.15)", fontSize: 20, fontWeight: "bold" }
      },
      {
        type: "text",
        right: "15%",
        bottom: "15%",
        style: { text: "平静/舒缓", fill: "rgba(255,255,255,0.15)", fontSize: 20, fontWeight: "bold" }
      }
    ]
  });
};

const updateStaticViews = () => {
  if (!analysisResult.value) return;
  
  // 当有真实分析结果时，demoMode 会自动变为 false，watch 会处理停止 demo
  // 这里只需要确保清除演示标记即可
  
  const segments = analysisResult.value.segments || [];
  if (segments.length) {
    const waveData = segmentsToWaveData(segments, audioEl.value?.duration);
    waveChart?.setOption({
      series: [{ data: waveData }, { data: [] }],
      graphic: [] // 清除演示标记
    });
  }

  // 初始化饼图为「起始时刻」的分布，避免刚分析完仍显示演示态/空数据
  const firstProbs = segments.find((s) => Array.isArray(s?.probs) && s.probs.length)?.probs;
  if (firstProbs?.length) {
    const labelsCn = analysisResult.value.labels_cn || [];
    const labelsEn = analysisResult.value.labels_en || [];
    pieChart?.setOption({ graphic: [] });
    animatePieReveal({
      targetWeights: firstProbs,
      labelsCn,
      labelsEn,
      startAngle: 90,
      clockwise: false,
      sliceMs: 180,
      gapMs: 18
    });
    // 平滑缓存与首帧对齐，避免随后动态更新出现“跳变”
    smoothPieProbs = normalizeWeights(firstProbs);
    smoothPieLastTs = performance.now();
    lastAudioTime = -1;
  }

  const q = analysisResult.value.quadrant || {};
  const vx = typeof q.valence === "number" ? q.valence * 2 - 1 : 0;
  const vy = typeof q.arousal === "number" ? q.arousal * 2 - 1 : 0;

  segmentPoints.value = calculateSegmentPoints();
  quadrantChart?.setOption({
    series: [
      { data: segmentPoints.value },
      {
        data: [
          {
            value: [vx, vy],
            valence: q.valence,
            arousal: q.arousal
          }
        ]
      }
    ]
  });

  dominantEmotion.value = q.dominant_label_cn
    ? `${q.dominant_label_cn}${q.dominant_label_en ? ` (${q.dominant_label_en})` : ""}`
    : "-";
  valence.value = typeof q.valence === "number" ? `${(q.valence * 100).toFixed(1)}%` : "-";
  arousal.value = typeof q.arousal === "number" ? `${(q.arousal * 100).toFixed(1)}%` : "-";

  const stats = analysisResult.value.stats || {};
  avgIntensity.value = typeof stats.avg_intensity === "number" ? `${(stats.avg_intensity * 100).toFixed(1)}%` : "-";
  volatility.value = stats.intensity_volatility ?? "-";
};

const probsToPieData = (probs, labelsCn = [], labelsEn = []) =>
  (probs || []).map((v, idx) => {
    const cn = labelsCn[idx];
    const en = labelsEn[idx];
    const name = [cn, en].filter(Boolean).join(" ");
    const stableId = en || cn || String(idx);
    return { id: stableId, value: v, name: name || `情绪${idx + 1}` };
  });

const interpolateDistribution = (t, segments) => {
  const valid = (segments || [])
    .filter((seg) => typeof seg?.center === "number" && Array.isArray(seg?.probs))
    .sort((a, b) => a.center - b.center);
  if (!valid.length) return [];

  const centers = valid.map((s) => s.center);
  const probsList = valid.map((s) => s.probs);

  if (t <= centers[0]) return probsList[0];
  if (t >= centers[centers.length - 1]) return probsList[probsList.length - 1];

  let idx = centers.findIndex((c) => c > t) - 1;
  if (idx < 0) idx = 0;
  const t1 = centers[idx];
  const t2 = centers[idx + 1];
  const p1 = probsList[idx] || [];
  const p2 = probsList[idx + 1] || [];
  const alpha = (t - t1) / (t2 - t1 || 1);

  const len = Math.max(p1.length, p2.length);
  return Array.from({ length: len }, (_, i) => (1 - alpha) * (p1[i] ?? 0) + alpha * (p2[i] ?? 0));
};

const probsToIntensity = (probs = [], labelsEn = []) => {
  if (!probs.length) return 0;
  const sum = probs.reduce((a, b) => a + b, 0) || 1;
  const norm = probs.map((p) => p / sum);
  return norm.reduce((acc, cur, idx) => acc + cur * getEmotionArousal(idx, labelsEn?.[idx]), 0);
};

const segmentsToWaveData = (segments = [], durationSec) => {
  const points = segments
    .filter((seg) => typeof seg?.center === "number")
    .sort((a, b) => a.center - b.center)
    .map((seg) => {
      if (Array.isArray(seg.probs) && seg.probs.length) return [seg.center, probsToIntensity(seg.probs)];
      if (typeof seg.intensity === "number") return [seg.center, seg.intensity];
      return [seg.center, 0];
    });

  if (!points.length) return points;

  const firstX = points[0][0];
  const lastX = points[points.length - 1][0];
  const startX = 0;
  const endX = Number.isFinite(durationSec) && durationSec > 0 ? durationSec : lastX;

  if (firstX > startX) points.unshift([startX, points[0][1]]);
  if (endX > lastX) points.push([endX, points[points.length - 1][1]]);
  return points;
};

const updateDynamicViews = () => {
  if (!analysisResult.value || !audioEl.value || Number.isNaN(audioEl.value.currentTime)) return;
  if (pieIntroInProgress) return;
  const segments = analysisResult.value.segments || [];
  if (!segments.length) return;

  const t = audioEl.value.currentTime;
  // 避免暂停/卡住时重复 setOption 带来的“顿挫感”
  if (Math.abs(t - lastAudioTime) < 0.03) return;
  lastAudioTime = t;

  const probs = interpolateDistribution(t, segments);
  if (!probs.length) return;

  const labelsCn = analysisResult.value.labels_cn || [];
  const labelsEn = analysisResult.value.labels_en || [];
  // 归一化 + 指数平滑，视觉更丝滑（不改变后端数据逻辑）
  const sum = probs.reduce((a, b) => a + b, 0) || 1;
  const target = probs.map((p) => Math.max(0, (Number(p) || 0) / sum));

  const now = performance.now();
  const dt = smoothPieLastTs ? Math.max(0, now - smoothPieLastTs) : 0;
  smoothPieLastTs = now;

  // 时间常数越小越“跟手”，越大越“顺滑”
  const tau = 220; // ms
  const alpha = dt > 0 ? 1 - Math.exp(-dt / tau) : 1;

  if (!smoothPieProbs.length) {
    smoothPieProbs = target.slice();
  } else {
    const len = Math.max(smoothPieProbs.length, target.length);
    for (let i = 0; i < len; i += 1) {
      const cur = Number(smoothPieProbs[i] ?? 0) || 0;
      const to = Number(target[i] ?? 0) || 0;
      smoothPieProbs[i] = cur + alpha * (to - cur);
    }
  }

  // 重新归一化，避免累积误差导致总和不为 1
  const smoothSum = smoothPieProbs.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
  const smooth = smoothPieProbs.map((p) => Math.max(0, (Number(p) || 0) / smoothSum));

  const pieData = probsToPieData(smooth, labelsCn, labelsEn);

  pieChart?.setOption(
    {
      series: [
        {
          id: "emotionPie",
          universalTransition: true,
          animationDurationUpdate: 260,
          animationEasingUpdate: "cubicOut",
          data: pieData
        }
      ]
    },
    { lazyUpdate: true }
  );

  const intensity = probsToIntensity(target, labelsEn);
  displayIntensity.value = `${(intensity * 100).toFixed(1)}%`;
  intensityLevel.value = intensityToLevel(intensity);

  waveChart?.setOption({
    series: [{}, { data: [[t, intensity]] }]
  });

  // 四象限图高亮：方案 C
  if (segmentPoints.value.length > 0) {
    const curIdx = segmentPoints.value.findIndex((p) => t >= p.startTime && t < p.endTime);
    if (curIdx !== -1) {
      quadrantChart?.dispatchAction({
        type: "downplay",
        seriesIndex: 0
      });
      quadrantChart?.dispatchAction({
        type: "highlight",
        seriesIndex: 0,
        dataIndex: curIdx
      });
      quadrantChart?.dispatchAction({
        type: "showTip",
        seriesIndex: 0,
        dataIndex: curIdx
      });
    }
  }
};

const onFileChange = (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    selectedFile.value = null;
    statusText.value = "请选择一段音乐文件";
    clearCharts();
    resetDisplay();
    if (audioUrl.value) {
      URL.revokeObjectURL(audioUrl.value);
      audioUrl.value = "";
    }
    smoothPieProbs = [];
    smoothPieLastTs = 0;
    lastAudioTime = -1;
    return;
  }

  if (!file.type.startsWith("audio/")) {
    statusText.value = "请选择音频文件";
    return;
  }

  selectedFile.value = file;
  statusText.value = `已选择文件：${file.name}`;
  analysisResult.value = null;
  resetDisplay();
  clearCharts();
  smoothPieProbs = [];
  smoothPieLastTs = 0;
  lastAudioTime = -1;

  // 选择新文件意味着开启新分析：清理上一轮会话/任务
  currentTaskId.value = "";
  currentAnalysisId.value = null;
  clearEmotionSession();

  if (audioUrl.value && audioUrl.value.startsWith("blob:")) URL.revokeObjectURL(audioUrl.value);
  audioUrl.value = URL.createObjectURL(file);
};

// 进度条控制函数
const startProgress = () => {
  resetProgress();
  showProgress.value = true;
  progressPercent.value = 0;
  
  let currentPercent = 0;
  let isPhase2 = false;
  
  // 第一阶段：0% → 85%，每 120ms 增加 1-3%
  // 第二阶段：85% → 95%，放慢速度
  const progressUpdate = setInterval(() => {
    if (currentPercent >= 95) {
      clearInterval(progressUpdate);
      progressTimer = null;
      return;
    }
    
    if (currentPercent < 85) {
      // 第一阶段：快速增长
      const increment = Math.min(Math.random() * 2 + 1, 85 - currentPercent);
      currentPercent = Math.min(currentPercent + increment, 85);
    } else if (!isPhase2) {
      // 刚进入第二阶段
      isPhase2 = true;
      currentPercent = 85;
    } else {
      // 第二阶段：慢速增长
      const increment = Math.min(Math.random() * 0.5 + 0.3, 95 - currentPercent);
      currentPercent = Math.min(currentPercent + increment, 95);
    }
    
    progressPercent.value = Math.floor(currentPercent);
  }, 120);
  
  // 保存定时器以便清理
  progressTimer = progressUpdate;
};

const finishProgress = () => {
  // 清理所有进度定时器
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
  
  // 快速补齐到 100%
  const target = 100;
  const current = progressPercent.value;
  const duration = 300; // 300ms 内完成
  const steps = 20;
  const stepTime = duration / steps;
  const increment = (target - current) / steps;
  
  let step = 0;
  const finishInterval = setInterval(() => {
    step++;
    progressPercent.value = Math.min(Math.floor(current + increment * step), target);
    
    if (step >= steps || progressPercent.value >= target) {
      clearInterval(finishInterval);
      progressPercent.value = 100;
      
      // 延迟隐藏进度条并显示完成提示
      setTimeout(() => {
        showProgress.value = false;
        showToast("分析完成 ✅", "success");
      }, 500);
    }
  }, stepTime);
};

const resetProgress = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  showProgress.value = false;
  progressPercent.value = 0;
};

const loadAnalysisDetail = async (analysisId, { setAsHistory = false } = {}) => {
  if (!analysisId) return;
  isAnalyzing.value = true;
  if (setAsHistory) historyMode.value = true;
  resetDisplay();
  analysisResult.value = null;
  statusText.value = setAsHistory ? "正在加载历史记录..." : "正在加载情绪分析结果...";
  try {
    const detail = await fetchEmotionDetail(analysisId);
    const raw = detail?.raw_result || detail || {};
    analysisResult.value = raw;
    summaryText.value = detail?.summary || raw.summary || raw.extra?.summary || "";

    const nextAudio = detail?.audio_url ? toAbsoluteUrl(detail.audio_url) : "";
    if (audioUrl.value && audioUrl.value.startsWith("blob:")) {
      URL.revokeObjectURL(audioUrl.value);
    }
    audioUrl.value = nextAudio;

    statusText.value = setAsHistory
      ? "已加载历史情绪分析记录，可以播放音乐查看动态图表。"
      : "分析完成，可以播放音乐查看动态图表。";
    updateStaticViews();
  } catch (err) {
    console.error(err);
    statusText.value = `${setAsHistory ? "加载历史记录失败" : "加载失败"}：${err?.message || "请检查接口"}`;
  } finally {
    isAnalyzing.value = false;
  }
};

const pollEmotionTaskStatus = async (taskId) => {
  if (!taskId || destroyed) return;
  stopEmotionPolling();
  try {
    const task = await getEmotionTaskStatus(taskId);
    const status = task?.status;
    if (status === "completed") {
      const analysisId = task?.result?.analysis_id;
      currentAnalysisId.value = analysisId || null;
      currentTaskId.value = "";
      // 完成进度条
      finishProgress();
      saveEmotionSession();
      if (analysisId) {
        await loadAnalysisDetail(analysisId, { setAsHistory: false });
      } else if (task?.result?.extra) {
        analysisResult.value = task.result.extra;
        summaryText.value = task.result.summary || task.result.extra?.summary || "";
        statusText.value = "分析完成，可以播放音乐查看动态图表。";
        updateStaticViews();
      }
      isAnalyzing.value = false;
      saveEmotionSession();
      return;
    }
    if (status === "failed") {
      resetProgress();
      isAnalyzing.value = false;
      statusText.value = `分析失败：${task?.message || "请重试"}`;
      showToast("分析失败，请重试", "error");
      currentTaskId.value = "";
      clearEmotionSession();
      return;
    }
    // pending / processing：继续轮询
    isAnalyzing.value = true;
    statusText.value = "正在上传并分析，请稍候...";
    saveEmotionSession();
  } catch (err) {
    // 网络抖动时不要立即失败，稍后重试
  }
  emotionPollTimer = setTimeout(() => pollEmotionTaskStatus(taskId), 1500);
};

const restoreEmotionSession = async () => {
  if (historyMode.value) return;
  // 游客不恢复：每次进入都是新的界面
  if (!auth?.isLoggedIn) return;
  let raw = null;
  try {
    // 清理旧版本全局 key，避免串号（v1 没有用户隔离）
    localStorage.removeItem("emotion_session_v1");
    raw = localStorage.getItem(getEmotionSessionKey());
  } catch (e) {
    raw = null;
  }
  if (!raw) return;

  let data = null;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    clearEmotionSession();
    return;
  }

  // 安全校验：必须是当前用户自己的会话
  if ((data?.owner_user_id ?? null) !== (auth?.user?.id ?? null)) {
    clearEmotionSession();
    return;
  }

  const ts = Number(data?.ts) || 0;
  if (!ts || Date.now() - ts > EMOTION_SESSION_MAX_AGE_MS) {
    clearEmotionSession();
    return;
  }

  currentTaskId.value = data?.taskId || "";
  currentAnalysisId.value = data?.analysisId || null;
  if (data?.audioUrl) audioUrl.value = data.audioUrl;
  if (data?.statusText) statusText.value = data.statusText;

  if (currentAnalysisId.value) {
    await loadAnalysisDetail(currentAnalysisId.value, { setAsHistory: false });
    return;
  }

  if (currentTaskId.value) {
    isAnalyzing.value = true;
    startProgress();
    await pollEmotionTaskStatus(currentTaskId.value);
  }
};

const resetEmotionState = () => {
  stopEmotionPolling();
  resetProgress();
  currentTaskId.value = "";
  currentAnalysisId.value = null;
  selectedFile.value = null;
  if (audioUrl.value && audioUrl.value.startsWith("blob:")) {
    try {
      URL.revokeObjectURL(audioUrl.value);
    } catch {
      // ignore
    }
  }
  audioUrl.value = "";
  statusText.value = "请选择一段音乐文件";
  isAnalyzing.value = false;
  summaryText.value = "";
  analysisResult.value = null;
  progressPercent.value = 0;
  showProgress.value = false;
};

const onAnalyze = async () => {
  if (!selectedFile.value) return;
  
  // 检查登录状态
  if (!auth.isLoggedIn) {
    statusText.value = "请先登录后再使用情绪分析功能";
    showToast("请先登录", "error");
    ui.openLoginPanel();
    return;
  }
  
  isAnalyzing.value = true;
  summaryText.value = "";
  statusText.value = "正在上传并分析，请稍候...";
  
  // 启动进度条
  startProgress();

  try {
    const created = await analyzeMusicTask(selectedFile.value);
    const taskId = created?.task_id || created?.taskId || created?.id;
    currentTaskId.value = taskId || "";
    currentAnalysisId.value = null;

    // 用后端可访问的音频 URL 替换 blob，这样离开页面也能持续播放/恢复
    const nextAudio = created?.audio_url ? toAbsoluteUrl(created.audio_url) : "";
    if (nextAudio) {
      if (audioUrl.value && audioUrl.value.startsWith("blob:")) URL.revokeObjectURL(audioUrl.value);
      audioUrl.value = nextAudio;
    }

    saveEmotionSession();

    if (!taskId) {
      throw new Error("后端未返回任务 ID");
    }
    await pollEmotionTaskStatus(taskId);
  } catch (err) {
    console.error(err);
    // 停止进度条
    resetProgress();
    
    // 处理 401 未授权错误
    if (err?.status === 401 || err?.message?.includes("401") || err?.message?.includes("Unauthorized")) {
      statusText.value = "分析失败：请先登录后再使用情绪分析功能";
      showToast("请先登录", "error");
    } else {
      statusText.value = `分析失败：${err?.message || "请检查后端服务是否已启动。"}`;
      showToast("分析失败，请重试", "error");
    }
  } finally {
    isAnalyzing.value = false;
    saveEmotionSession();
  }
};

const loadHistoryDetail = async (historyId) => {
  if (!historyId) return;
  await loadAnalysisDetail(historyId, { setAsHistory: true });
};

onMounted(async () => {
  try {
    await ensureEcharts();
    initCharts();
    const historyId = route?.query?.historyId;
    historyMode.value = Boolean(historyId);
    // 优先恢复“最近一次情绪识别会话”（非 history 模式）
    if (!historyId) {
      await restoreEmotionSession();
    }
    if (!historyId && demoMode.value) startDemoPie();
    resizeHandler = () => {
      pieChart?.resize();
      waveChart?.resize();
      quadrantChart?.resize();
    };
    window.addEventListener("resize", resizeHandler);
    // 动态刷新更密一点，配合指数平滑与 ECharts 动画，让饼图变化更丝滑
    timer = setInterval(updateDynamicViews, 120);
    if (historyId) {
      await loadHistoryDetail(historyId);
    }
  } catch (err) {
    console.error(err);
    statusText.value = err?.message || "图表初始化失败";
  }
});

// 自动保存会话（仅非 history 模式）
watch([currentTaskId, currentAnalysisId, audioUrl, statusText, isAnalyzing, progressPercent], () => saveEmotionSession());

// 账号切换时：不允许串号，直接重置并恢复当前用户自己的分析进度
watch(
  () => (auth?.isLoggedIn ? auth?.user?.id : null),
  async () => {
    // history 模式由 query 控制，不参与会话恢复
    if (historyMode.value) return;
    resetEmotionState();
    await restoreEmotionSession();
  }
);

watch(
  demoMode,
  (enabled) => {
    if (enabled) {
      startDemoTyping();
      startDemoPieExplainTyping();
      startDemoWaveExplainTyping();
      startDemoPie();
      startDemoWave();
    } else {
      stopDemoTyping();
      stopDemoPieExplainTyping();
      stopDemoWaveExplainTyping();
      stopDemoPie();
      stopDemoWave();
      pieChart?.setOption({ graphic: [] });
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  destroyed = true;
  stopEmotionPolling();
  if (timer) clearInterval(timer);
  if (resizeHandler) window.removeEventListener("resize", resizeHandler);
  resetProgress(); // 清理进度条定时器
  stopDemoTyping();
  stopDemoPieExplainTyping();
  stopDemoWaveExplainTyping();
  stopDemoPie();
  stopDemoWave();
  pieChart?.dispose();
  waveChart?.dispose();
  quadrantChart?.dispose();
  if (audioUrl.value && audioUrl.value.startsWith("blob:")) URL.revokeObjectURL(audioUrl.value);
});
</script>

<style scoped>
.emotion-demo {
  position: relative;
  padding: 8px 4px 24px;
  color: #fff;
}

h1 {
  margin: 0 0 12px;
  text-align: center;
}

.panel {
  background: rgba(9, 33, 68, 0.9);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.file-upload-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.primary-btn {
  padding: 0 16px;
  height: 38px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #3b82f6;
  color: #fff;
  border: none;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.primary-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.primary-btn:active:not(:disabled) {
  transform: translateY(0);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.analysis-btn {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
}

.loading-spinner--small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-panel {
  margin-bottom: 16px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.btn {
  background: #1e80ff;
  border: none;
  border-radius: 20px;
  color: #fff;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

.audio-player {
  width: 100%;
  margin-top: 8px;
}

.progress-container {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar-wrapper {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #3b82f6, #6366f1, #8b5cf6);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.5);
  transition: width 0.1s linear;
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  min-width: 40px;
  text-align: right;
  font-feature-settings: "tnum";
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.col {
  flex: 1;
  min-width: 320px;
}

.chart {
  width: 100%;
  height: 320px;
}

.feature-card {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
}

.feature-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.feature-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
}

.feature-title {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.feature-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.88);
  min-height: 56px;
}

.feature-text--muted {
  min-height: auto;
  color: rgba(255, 255, 255, 0.8);
}

.metrics {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.summary-text {
  margin-top: 12px;
  padding: 12px;
  min-height: 96px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  white-space: pre-wrap;
  line-height: 1.6;
}

.demo-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  margin-bottom: 10px;
}

.demo-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.88);
  min-height: 56px;
}

.typing-cursor {
  display: inline-block;
  width: 8px;
  height: 1.05em;
  margin-left: 2px;
  border-radius: 2px;
  background: rgba(255, 235, 59, 0.95);
  box-shadow: 0 0 10px rgba(255, 235, 59, 0.9);
  vertical-align: -0.15em;
  animation: blink 0.95s step-end infinite;
}

.typing-cursor--sm {
  width: 6px;
  height: 0.95em;
  background: rgba(96, 165, 250, 0.95);
  box-shadow: 0 0 10px rgba(96, 165, 250, 0.85);
  vertical-align: -0.12em;
}

@keyframes blink {
  0%,
  100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  z-index: 3000;
  animation: toastSlideIn 0.3s ease;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(12px);
}

.toast-success {
  background: rgba(34, 197, 94, 0.9);
  color: #fff;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.toast-error {
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

@keyframes toastSlideIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@media (max-width: 900px) {
  .chart {
    height: 280px;
  }
}
</style>
