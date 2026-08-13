# Aigility SDK (ADK) 使用文档

Aigility SDK 使用文档网站，基于 React 19 + TypeScript + Tailwind CSS + shadcn/ui 构建。

## 环境要求

- Node.js >= 20.19 或 >= 22.12（推荐使用 Node.js 22 LTS）

## 打开方式

```bash
# 1. 切换 Node.js 版本（以 nvm 为例）
nvm use lts/jod

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

启动后在浏览器中访问 `http://localhost:8001/` 即可查看网站。

> **注意**：如果遇到 `nvm: command not found`，先执行 `source ~/.zshrc`（或 `source ~/.bashrc`）加载 nvm。

## 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist/` 目录。
