# syntax=docker/dockerfile:1.4
# 前端生产镜像：Node 22 LTS 构建（npm run build）+ nginx 托管静态资源
# 启用 BuildKit 特性以支持缓存挂载，构建时需设置 DOCKER_BUILDKIT=1
# 内部端口统一为 3000

# ============ 构建阶段 ============
FROM node:22-slim AS builder

WORKDIR /app

# npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com

# 先复制依赖清单与 scripts（npm install 会触发 prepare 生命周期脚本 scripts/setup-git-hooks.mjs，
# 需要该文件提前就位；容器内无 .git，脚本会静默跳过）
COPY package.json ./
COPY package-lock.json ./
COPY scripts ./scripts

# 安装依赖（含 devDependencies：tsc + vite 构建时需要）
RUN npm install --legacy-peer-deps

# 复制项目代码
COPY . .

# 通过构建参数指定环境文件名（如 .env.test / .env.pre / .env.main）
# 默认使用 .env.production，构建时通过 --build-arg ENV_FILE=xxx 覆盖
ARG ENV_FILE=.env.production
RUN if [ -f "$ENV_FILE" ]; then cp "$ENV_FILE" .env; fi

# 构建生产产物：tsc 类型检查 → vite build 打包到 dist/
RUN npm run build

# ============ 运行阶段 ============
FROM nginx:alpine

# 拷贝自定义 nginx 配置（SPA history 路由兜底、内部端口 3000）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物（miaoda 预设的 outDir 是 dist/client，产物在其下）
COPY --from=builder /app/dist/client/ /usr/share/nginx/html/

# 前端内部端口统一为 3000（与 nginx.conf listen 对齐）
EXPOSE 3000

# nginx 启动命令（前台运行）
CMD ["nginx", "-g", "daemon off;"]
