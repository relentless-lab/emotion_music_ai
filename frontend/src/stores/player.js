import { defineStore } from "pinia";
import { recordWorkPlay } from "../services/workApi";

const VOLUME_KEY = "player_volume";
const MUTED_KEY = "player_muted";
const REPEAT_KEY = "player_repeat";

const fallbackPlaylist = [
  {
    id: 1,
    title: "Neon Skyline",
    artist: "AI Composer",
    album: "Midnight Drive",
    cover: "https://images.unsplash.com/photo-1464375117522-1311d6a5b81f?auto=format&w=400&q=80",
    url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    duration: 0
  },
  {
    id: 2,
    title: "Electric Bloom",
    artist: "Synth Lab",
    album: "Pulse",
    cover: "https://images.unsplash.com/photo-1470229538611-16ba8c7ffbd7?auto=format&w=400&q=80",
    url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    duration: 0
  },
  {
    id: 3,
    title: "Glacier Light",
    artist: "Ambient Field",
    album: "Northbound",
    cover: "https://images.unsplash.com/photo-1483412033650-1015ddeb83d1?auto=format&w=400&q=80",
    url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    duration: 0
  }
];

export const usePlayerStore = defineStore("player", {
  state: () => ({
    audio: null,
    playlist: fallbackPlaylist,
    currentIndex: 0,
    isPlaying: false,
    isMuted: JSON.parse(localStorage.getItem(MUTED_KEY) || "false"),
    shuffle: false,
    repeatMode: localStorage.getItem(REPEAT_KEY) || "all", // all | one | off
    volume: parseFloat(localStorage.getItem(VOLUME_KEY) || "0.8"),
    currentTime: 0,
    duration: 0,
    likedTrackIds: [],
    // 防止暂停/继续或重复点击导致多次上报
    _lastPlayReportAtByWorkId: {}
  }),
  getters: {
    currentTrack(state) {
      return state.playlist[state.currentIndex] ?? null;
    }
  },
  actions: {
    initAudio() {
      if (this.audio || typeof Audio === "undefined") return;
      this.audio = new Audio();
      this.audio.preload = "auto";
      this.audio.volume = this.volume;
      this.audio.playbackRate = 1;

      const updateTime = () => {
        this.currentTime = this.audio?.currentTime ?? 0;
        this.duration = this.audio?.duration || this.duration;
      };
      const handleLoaded = () => {
        this.duration = this.audio?.duration || 0;
        if (this.currentTrack && this.duration) {
          this.playlist[this.currentIndex] = {
            ...this.currentTrack,
            duration: this.duration
          };
        }
      };
      const handleEnded = () => {
        this.handleEnded();
      };

      this.audio.addEventListener("timeupdate", updateTime);
      this.audio.addEventListener("loadedmetadata", handleLoaded);
      this.audio.addEventListener("ended", handleEnded);

      if (this.currentTrack?.url) {
        this.audio.src = this.currentTrack.url;
      }
    },
    setPlaylist(list, startIndex = 0) {
      this.playlist = list;
      if (!list.length) {
        this.currentIndex = 0;
        this.currentTime = 0;
        this.duration = 0;
        this.isPlaying = false;
        if (this.audio) {
          this.audio.pause();
          this.audio.removeAttribute("src");
        }
        return;
      }
      this.currentIndex = Math.min(startIndex, list.length - 1);
      this.currentTime = 0;
      this.duration = 0;
      if (this.audio && this.currentTrack?.url) {
        this.audio.src = this.currentTrack.url;
      }
    },
    async playTrack(index = this.currentIndex) {
      if (!this.playlist.length) return;
      if (!this.audio) this.initAudio();
      const prevIndex = this.currentIndex;
      const normalized = ((index % this.playlist.length) + this.playlist.length) % this.playlist.length;
      if (normalized !== this.currentIndex || this.audio.src !== this.currentTrack?.url) {
        this.currentIndex = normalized;
        this.currentTime = 0;
        this.duration = 0;
        if (this.currentTrack?.url) {
          this.audio.src = this.currentTrack.url;
        }
      }
      try {
        await this.audio.play();
        this.isPlaying = true;
        this._reportPlayIfNeeded(this.currentTrack, prevIndex !== this.currentIndex);
      } catch (err) {
        console.error("播放失败", err);
        this.isPlaying = false;
      }
    },
    _reportPlayIfNeeded(track, changedTrack = false) {
      try {
        if (!track) return;
        const id = track.id;
        if (!id) return;
        // 仅统计“公开发布作品”的播放；生成中 track / 未发布作品不计入榜单
        if (track.status !== "published") return;
        if (track.visibility && track.visibility !== "public") return;
        if (!(track.url || track.audio_url || track.audioUrl)) return;

        const now = Date.now();
        const lastAt = this._lastPlayReportAtByWorkId?.[id] || 0;
        // 去抖：同一作品 30s 内只上报一次（防止暂停/继续、重复点击）
        if (!changedTrack && now - lastAt < 30 * 1000) return;
        if (now - lastAt < 30 * 1000) return;

        this._lastPlayReportAtByWorkId = {
          ...(this._lastPlayReportAtByWorkId || {}),
          [id]: now
        };

        // best-effort：不上报成功与否不影响播放
        recordWorkPlay(id, { source: "player" }).catch(() => {});
      } catch {
        // ignore
      }
    },
    async togglePlay() {
      if (!this.audio) this.initAudio();
      if (!this.audio) return;
      if (this.isPlaying) {
        this.audio.pause();
        this.isPlaying = false;
        return;
      }
      await this.playTrack(this.currentIndex);
    },
    next() {
      if (!this.playlist.length) return;
      if (this.shuffle) {
        const randomIndex = this.getRandomIndex();
        this.playTrack(randomIndex);
        return;
      }
      const nextIndex = (this.currentIndex + 1) % this.playlist.length;
      this.playTrack(nextIndex);
    },
    prev() {
      if (!this.playlist.length) return;
      if (this.audio && this.audio.currentTime > 3) {
        this.seekTo(0);
        return;
      }
      if (this.shuffle) {
        const randomIndex = this.getRandomIndex();
        this.playTrack(randomIndex);
        return;
      }
      const prevIndex = (this.currentIndex - 1 + this.playlist.length) % this.playlist.length;
      this.playTrack(prevIndex);
    },
    handleEnded() {
      if (this.repeatMode === "one") {
        this.seekTo(0);
        this.playTrack(this.currentIndex);
        return;
      }
      if (this.repeatMode === "off") {
        this.isPlaying = false;
        return;
      }
      this.next();
    },
    seekTo(percent) {
      if (!this.audio || !this.duration) return;
      const target = this.duration * Math.min(Math.max(percent, 0), 1);
      this.audio.currentTime = target;
      this.currentTime = target;
    },
    setVolume(value) {
      const clamped = Math.min(Math.max(value, 0), 1);
      this.volume = clamped;
      this.isMuted = clamped === 0;
      
      localStorage.setItem(VOLUME_KEY, clamped);
      localStorage.setItem(MUTED_KEY, this.isMuted);

      if (this.audio) {
        this.audio.volume = clamped;
        this.audio.muted = this.isMuted;
      }
    },
    toggleMute() {
      this.isMuted = !this.isMuted;
      localStorage.setItem(MUTED_KEY, this.isMuted);
      
      if (this.audio) {
        this.audio.muted = this.isMuted;
      }
    },
    toggleShuffle() {
      this.shuffle = !this.shuffle;
    },
    cycleRepeatMode() {
      if (this.repeatMode === "all") {
        this.repeatMode = "one";
      } else if (this.repeatMode === "one") {
        this.repeatMode = "off";
      } else {
        this.repeatMode = "all";
      }
      localStorage.setItem(REPEAT_KEY, this.repeatMode);
    },
    getRandomIndex() {
      if (this.playlist.length <= 1) return this.currentIndex;
      let nextIndex = this.currentIndex;
      while (nextIndex === this.currentIndex) {
        nextIndex = Math.floor(Math.random() * this.playlist.length);
      }
      return nextIndex;
    },
    toggleLike(id) {
      if (!id) return;
      if (this.likedTrackIds.includes(id)) {
        this.likedTrackIds = this.likedTrackIds.filter((item) => item !== id);
      } else {
        this.likedTrackIds.push(id);
      }
    }
  }
});
