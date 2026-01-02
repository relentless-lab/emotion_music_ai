<template>
  <div class="carousel">
    <div class="carousel-container" @mouseenter="pauseAutoPlay" @mouseleave="startAutoPlay">
      <div class="carousel-track" :style="{ transform: `translateX(-${currentIndex * 100}%)` }">
        <div
          v-for="(slide, index) in slides"
          :key="index"
          class="carousel-slide"
          @click="handleSlideClick(slide, index)"
        >
          <img :src="slide.image" :alt="slide.title" class="slide-image" />
          <div class="slide-content">
            <h3 class="slide-title">{{ slide.title }}</h3>
            <p class="slide-description">{{ slide.description }}</p>
          </div>
        </div>
      </div>

      <button class="carousel-btn carousel-btn--prev" @click="prevSlide">
        <span>&lsaquo;</span>
      </button>
      <button class="carousel-btn carousel-btn--next" @click="nextSlide">
        <span>&rsaquo;</span>
      </button>

      <div class="carousel-indicators">
        <button
          v-for="(slide, index) in slides"
          :key="index"
          class="indicator"
          :class="{ active: currentIndex === index }"
          @click="goToSlide(index)"
        >
          <span class="sr-only">Slide {{ index + 1 }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const props = defineProps({
  slides: {
    type: Array,
    required: true,
    default: () => []
  },
  autoPlay: {
    type: Boolean,
    default: true
  },
  interval: {
    type: Number,
    default: 4000
  }
});

const emit = defineEmits(["slide-click"]);

const currentIndex = ref(0);
let autoPlayTimer = null;

const nextSlide = () => {
  if (!props.slides.length) return;
  currentIndex.value = (currentIndex.value + 1) % props.slides.length;
};

const prevSlide = () => {
  if (!props.slides.length) return;
  currentIndex.value = currentIndex.value === 0 ? props.slides.length - 1 : currentIndex.value - 1;
};

const goToSlide = index => {
  currentIndex.value = index;
};

const handleSlideClick = (slide, index) => {
  emit("slide-click", { slide, index });
};

const startAutoPlay = () => {
  if (props.autoPlay && props.slides.length) {
    stopAutoPlay();
    autoPlayTimer = setInterval(nextSlide, props.interval);
  }
};

const pauseAutoPlay = () => {
  stopAutoPlay();
};

const stopAutoPlay = () => {
  if (autoPlayTimer) {
    clearInterval(autoPlayTimer);
    autoPlayTimer = null;
  }
};

onMounted(() => {
  startAutoPlay();
});

onUnmounted(() => {
  stopAutoPlay();
});
</script>

<style scoped>
.carousel {
  width: 100%;
  height: 400px;
}

.carousel-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.carousel-track {
  display: flex;
  transition: transform 0.5s ease-in-out;
  height: 100%;
}

.carousel-slide {
  flex: 0 0 100%;
  position: relative;
  height: 100%;
  cursor: pointer;
}

.slide-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.slide-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  color: white;
  padding: 30px 40px;
}

.slide-title {
  font-size: 2rem;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.slide-description {
  font-size: 1.1rem;
  margin: 0;
  opacity: 0.9;
}

.carousel-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.9);
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.carousel-btn:hover {
  background: white;
  transform: translateY(-50%) scale(1.1);
}

.carousel-btn--prev {
  left: 20px;
}

.carousel-btn--next {
  right: 20px;
}

.carousel-indicators {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
}

.indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.3s ease;
}

.indicator.active {
  background: white;
  transform: scale(1.2);
}

.indicator:hover {
  background: rgba(255, 255, 255, 0.8);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 768px) {
  .carousel {
    height: 300px;
  }

  .slide-title {
    font-size: 1.5rem;
  }

  .slide-description {
    font-size: 1rem;
  }

  .carousel-btn {
    width: 40px;
    height: 40px;
    font-size: 1.25rem;
  }
}

@media (max-width: 480px) {
  .carousel {
    height: 250px;
  }

  .slide-content {
    padding: 20px;
  }

  .slide-title {
    font-size: 1.25rem;
  }

  .slide-description {
    font-size: 0.9rem;
  }
}
</style>
