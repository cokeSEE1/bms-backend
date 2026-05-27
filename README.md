# FastAPI Starter

一个最小可运行的 FastAPI 工程。

## 1. 创建并激活虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后访问：
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
