<template>
  <div class="blank">
    <slot />
  </div>
</template>

<style scoped>
.blank {
  height: 100vh;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: radial-gradient(circle at top left, #283a6f 0, #050816 45%, #000 100%);
  color: #fff;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
}
</style>

