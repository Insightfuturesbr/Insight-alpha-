
.PHONY: dev prod deps docker-build docker-run docker-stop docker-rm docker-logs docker-shell init-env smoke simulate-start simulate-restart simulate-status simulate-stop simulate-tail help

# Run Flask in dev mode (with sudo)
dev:    
		PYTHONPATH=$$(pwd) \
		FLASK_APP=main.py \
		FLASK_ENV=development \
		venv/bin/flask run --debug

# Run production locally with Gunicorn (no Docker)
prod: init-env
	PYTHONPATH=$$(pwd) \
	ENV=production \
	FLASK_ENV=production \
	PORT=$(PORT) \
	WORKERS=$(WORKERS) \
	THREADS=$(THREADS) \
	venv/bin/gunicorn -b 0.0.0.0:$(PORT) -w $(WORKERS) -k gthread --threads $(THREADS) app.webserver:create_app()

# Collect dependencies for a given file (with sudo)
PYTHON := python3
LIST_FILE := dependencies_list.txt
TARGET_DIR := $(CURDIR)/../dependencies

collect:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make collect FILE=path/to/file.py"; \
		exit 1; \
	fi
	@echo "→ adding $(FILE) to $(LIST_FILE)"
	@$(PYTHON) -c "from pathlib import Path; f=Path('$(LIST_FILE)'); \
txt = f.read_text() if f.exists() else ''; \
f.write_text(txt + str(Path('$(FILE)').resolve()) + '\n')"

copy:
	@if [ ! -f $(LIST_FILE) ]; then \
		echo 'No $(LIST_FILE) found'; \
		exit 1; \
	fi
	@mkdir -p "$(TARGET_DIR)"
	@echo "→ copying files into $(TARGET_DIR)"
	@while IFS= read -r file; do \
		if [ -f "$$file" ]; then \
			cp -v "$$file" "$(TARGET_DIR)/$$(basename "$$file")"; \
		else \
			echo "skipping missing $$file"; \
		fi; \
	done < $(LIST_FILE)

# -------------------------
# Production / Docker tasks
# -------------------------

IMAGE ?= insight-futures:latest
CONTAINER ?= insight-futures
PORT ?= 8000
WORKERS ?= 2
THREADS ?= 2
ENV_FILE_OPT := $(shell [ -f .env ] && echo --env-file .env)

help:
	@echo "Make targets:"
	@echo "  dev                - Run Flask in dev mode"
	@echo "  prod               - Run Gunicorn locally (no Docker)"
	@echo "  init-env           - Generate .env with random SECRET_KEY"
	@echo "  smoke              - Run local /health smoke test"
	@echo "  simulate-start     - Start deploy via /bin/bash with cache"
	@echo "  simulate-restart   - Killbug restart cycle until healthy"
	@echo "  simulate-status    - Show status of a RUN_ID"
	@echo "  simulate-stop      - Stop a RUN_ID"
	@echo "  simulate-tail      - Tail logs of a RUN_ID"
	@echo "  docker-build       - Build production Docker image ($(IMAGE))"
	@echo "  docker-run         - Run container on port $(PORT) with volumes"
	@echo "  docker-stop        - Stop running container"
	@echo "  docker-rm          - Remove stopped container"
	@echo "  docker-logs        - Tail container logs"
	@echo "  docker-shell       - Open a shell inside the container"
	@echo "Environment vars: IMAGE, CONTAINER, PORT, WORKERS, THREADS"

docker-build:
	docker build -t $(IMAGE) .

docker-run: init-env
	@mkdir -p uploads outputs
	@if [ "$$(docker ps -q -f name=$(CONTAINER))" ]; then \
		echo "Container $(CONTAINER) already running"; exit 0; \
	fi
	@if [ "$$(docker ps -aq -f status=exited -f name=$(CONTAINER))" ]; then \
		echo "Removing exited container $(CONTAINER)"; docker rm $(CONTAINER); \
	fi
	docker run -d --name $(CONTAINER) \
		-p $(PORT):8000 \
		--env PORT=8000 \
		--env ENV=production \
		--env FLASK_ENV=production \
		--env WORKERS=$(WORKERS) \
		--env THREADS=$(THREADS) \
		$(ENV_FILE_OPT) \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/outputs:/app/outputs \
		$(IMAGE)
	@echo "App running at http://localhost:$(PORT)"

docker-stop:
	-@docker stop $(CONTAINER) >/dev/null 2>&1 || true

docker-rm:
	-@docker rm $(CONTAINER) >/dev/null 2>&1 || true

docker-logs:
	docker logs -f $(CONTAINER)

docker-shell:
	docker exec -it $(CONTAINER) /bin/bash

init-env:
	@python3 scripts/gen_env.py

smoke:
	@python3 scripts/smoke_test.py

simulate-start:
	@bash scripts/deployctl.sh start

simulate-restart:
	@bash scripts/deployctl.sh restart

simulate-status:
	@bash scripts/deployctl.sh status $(RUN_ID)

simulate-stop:
	@bash scripts/deployctl.sh stop $(RUN_ID)

simulate-tail:
	@bash scripts/deployctl.sh tail $(RUN_ID)