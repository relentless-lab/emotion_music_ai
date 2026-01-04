import { globalIgnores } from 'eslint/config'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

const asFlatConfigArray = (maybeArray) => (Array.isArray(maybeArray) ? maybeArray : [maybeArray])

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{js,mjs,jsx,vue}'],
  },
  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),
  ...asFlatConfigArray(pluginVue.configs['flat/essential']),
  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  {
    ...asFlatConfigArray(pluginPlaywright.configs['flat/recommended'])[0],
    files: ['e2e/**/*.{test,spec}.{js,jsx}'],
  },
  skipFormatting,
]
