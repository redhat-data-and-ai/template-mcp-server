.PHONY: dev

clean:
	rm -rf .mypy_cache .ruff_cache .venv __pycache__

dev:
	export PODMAN_COMPOSE_SILENT=true
	podman-compose --no-ansi up --build --force-recreate --remove-orphans  --timeout=60

test:
	python3 -m pytest
