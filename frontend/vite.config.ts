import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vite.dev/config/
export default defineConfig(({ command }) => {
  return {
    define: {
      "import.meta.env.VITE_API_BASE":
        command === "serve"
          ? JSON.stringify("http://localhost:5000")
          : JSON.stringify(null),
    },
    plugins: [vue()],
  };
});
