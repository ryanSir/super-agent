.PHONY: help dev dev-backend dev-frontend install install-backend install-frontend build lint

help:
	@echo "可用命令："
	@echo "  make install          安装前后端依赖"
	@echo "  make dev              同时启动前后端开发服务器"
	@echo "  make dev-backend      仅启动后端 (port 9001)"
	@echo "  make dev-frontend     仅启动前端 (port 5173)"
	@echo "  make build            构建前端生产包"
	@echo "  make lint             运行后端代码检查"
	@echo "  make install-backend  仅安装后端依赖"
	@echo "  make install-frontend 仅安装前端依赖"

install: install-backend install-frontend

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd frontend-deepagent && npm install

dev:
	@echo "启动后端和前端..."
	@trap 'kill 0' INT; \
	python run_deepagent.py & \
	cd frontend-deepagent && npm run dev & \
	wait

dev-backend:
	python run_deepagent.py

dev-frontend:
	cd frontend-deepagent && npm run dev

build:
	cd frontend-deepagent && npm run build

lint:
	ruff check src_deepagent/
