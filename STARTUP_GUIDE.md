# DBCSRC 项目启动指南

## 快速启动

### 1. 启动后端服务器

```bash
# 进入后端目录
cd backend

# 安装依赖（首次运行）
pip install -r requirements.txt

# 启动后端服务器
python main.py
```

后端服务器将在 `http://localhost:8000` 启动。

### 2. 启动前端服务器

```bash
# 进入前端目录
cd nextjs-frontend

# 安装依赖（首次运行）
npm install

# 启动前端开发服务器
npm run dev
```

前端服务器将在 `http://localhost:3000` 启动。

## 常见问题

### Network Error 错误

如果在前端看到 "Network Error" 或 "后端服务器未启动" 的错误信息，请确保：

1. 后端服务器正在运行（在 `backend` 目录运行 `python main.py`）
2. 后端服务器在端口 8000 上监听
3. 没有防火墙阻止本地连接

### 环境配置

#### 后端环境变量（可选）

复制 `backend/.env.example` 到 `backend/.env` 并根据需要修改配置：

```bash
cd backend
cp .env.example .env
```

#### 前端环境变量（可选）

如果需要自定义 API 地址，可以在 `nextjs-frontend` 目录创建 `.env.local` 文件：

```bash
# nextjs-frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 项目结构

```
dbcsrc/
├── backend/          # FastAPI 后端服务
├── nextjs-frontend/  # Next.js 前端应用
├── frontend/         # 旧版 Streamlit 前端（可选）
└── monitoring/       # 监控配置
```

## 开发模式

1. 确保后端服务器运行在 `http://localhost:8000`
2. 前端开发服务器运行在 `http://localhost:3000`
3. 前端会自动代理 API 请求到后端服务器

## 生产部署

请参考各目录下的 README.md 文件获取详细的部署说明。