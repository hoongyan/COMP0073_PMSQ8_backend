.PHONY: install setup preload test clean init load

install:
	@echo "Installing Python dependencies from requirements.txt..."
	pip install -r requirements.txt

setup:
	@echo "Setting up Docker, initializing schema, and loading data..."
	./scripts/setup/setup.sh
	python scripts/setup/init_db.py
	python scripts/setup/load_data.py
		python scripts/setup/seed_loader.py

preload:  
	@echo "Preloading data into existing database..."
	python scripts/setup/init_db.py
	python scripts/setup/load_data.py
	python scripts/setup/seed_loader.py

init:
	@echo "Initializing database schema..."
	python scripts/setup/init_db.py

load:
	@echo "Loading data into database..."
	python scripts/setup/load_data.py

test:
	@echo "Testing RAG retrieval..."
	python tests/test_retrieval.py

clean:
	@echo "Cleaning up Docker containers and volumes..."
	docker-compose down -v
	@echo "Removing logs..."
	rm -f logs/preprocessing/preprocess.log logs/database/database.log logs/setup/setup.log