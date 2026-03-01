run:
	python -m src.transport.simulation

report:
	quarto render report/

clean:
	rm -rf figures/* data/*
