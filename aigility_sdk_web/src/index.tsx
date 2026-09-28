import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ErrorBoundary } from "react-error-boundary";
import { ErrorRender } from "@lark-apaas/client-toolkit-lite";
import App from "./app";
import "./index.css";

// miaoda 预设构建时会将 CLIENT_BASE_PATH 注入为含 {{basename}} 模板占位符的值
// （供飞书 miaoda 云平台部署时替换）。自托管部署无人替换，Router 会因 URL 不匹配
// basename 而拒绝渲染（白屏），这里剔除未替换的占位符；云平台替换后此处理为空操作
const basename =
  (process.env.CLIENT_BASE_PATH || "/").replace(/\{\{[^}]+\}\}/g, "") || "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <ErrorBoundary
        fallbackRender={({ error, resetErrorBoundary }) => (
          <ErrorRender error={error} resetErrorBoundary={resetErrorBoundary} />
        )}
      >
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
);
