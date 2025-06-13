import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vite.dev/config/
export default defineConfig(({ command }) => {
  return {
    define: {
      "import.meta.env.VITE_API_BASE":
        command === "serve"
          ? JSON.stringify("http://localhost:9606")
          : JSON.stringify(null),
    },
    plugins: [vue()],
    server: {
      proxy: {
        // Proxy API requests to the backend server (matches nginx config)
        "/api/": {
          target: "http://localhost:9606/",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\//, "/"),
        },
        // Proxy documentation endpoints without rewriting (matches nginx config)
        "^/(openapi|openapi\\.json|swagger-ui|redoc)": {
          target: "http://localhost:9606",
          changeOrigin: true,
        },
      },
    },
  };
});
