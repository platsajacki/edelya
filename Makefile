export PYTHONPATH := src
export DJANGO_SETTINGS_MODULE := app.settings

install-hooks:
	@$(if $(wildcard .git/hooks/pre-commit), \
			echo pre-commit hook already exists, \
			pre-commit install && echo pre-commit hooks installed)

dev-install:
	pip install -r src/requirements.txt
	pip install -r src/requirements-dev.txt
	make install-hooks

prod-install:
	pip install -r requirements.txt

fmt:
	ruff format src --check || true && ruff format src

lint:
	ruff check src --show-fixes

fmt+lint:
	make fmt
	make lint

lint-unsafe:
	ruff check src --show-fixes --unsafe-fixes

mypy:
	mypy src

check:
	python src/manage.py check
	make install-hooks
	ruff check src --no-fix
	make mypy

tag:
	make check
	make test
	./tags-pretty.sh

superuser:
	python src/manage.py createsuperuser

runserver:
	python src/manage.py runserver

static:
	python src/manage.py collectstatic

makemigrations:
	python src/manage.py makemigrations

migrate:
	python src/manage.py migrate

shell:
	python src/manage.py shell

TEST ?= src/_tests
COVERAGE ?= --cov=src --cov-report=term-missing

test:
	make install-hooks
	pytest $(TEST) --create-db $(COVERAGE) -q

tag-win:
	make check
	make test
	powershell -File .\tag-win.ps1