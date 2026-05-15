.PHONY: install lint test run check-connection list-projects clean

install:
	poetry install

lint:
	poetry run flake8 qfield_checker tests

test:
	poetry run pytest tests

check-connection:
	poetry run qfield-checker check-connection

list-projects:
	poetry run qfield-checker list-projects

run:
	poetry run qfield-checker run

clean:
	rm -rf .pytest_cache .workdir dist build
	find . -type d -name "__pycache__" -exec rm -rf {} +
