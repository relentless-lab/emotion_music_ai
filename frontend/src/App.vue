<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="route.meta?.layout === 'blank' ? BlankLayout : DefaultLayout">
      <template v-if="route.meta?.keepAlive">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </template>
      <component v-else :is="Component" />
    </component>
  </RouterView>
</template>

<script setup>
import { RouterView } from "vue-router";
import { KeepAlive } from "vue";
import DefaultLayout from "./layouts/DefaultLayout.vue";
import BlankLayout from "./layouts/BlankLayout.vue";
</script>

