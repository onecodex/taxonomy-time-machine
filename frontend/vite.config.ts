import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vite.dev/config/
export default defineConfig(({ command, mode, isSsrBuild, isPreview }) => {
  return {
    define: {
      __API_BASE__:
        command === "serve"
          ? JSON.stringify("http://localhost:5000")
          : JSON.stringify(null),
    },
    plugins: [vue()],
  };
});
