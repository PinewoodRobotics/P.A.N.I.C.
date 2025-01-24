export PYTHONPATH := $(shell pwd)

initiate-project:
	python -m venv .venv
	pip install -r requirements.txt
	pip install -e .

generate-proto: prepare
	protoc --python_out=project/generated --pyi_out=project/generated project/common/proto/*.proto

run-multiprocess-2-test:
	python project/test/april/april_tag_mlti_process_2.py

run-multiprocess:
	python project/test/april/april_tag_mult_process.py

autobahn:
	cd project/autobahn/autobahn-rust && cargo run

ai-server:
	cd project/recognition/detection/image-recognition && python src/main.py

april-server:
	cd project/recognition/position/april && python src/main.py

prepare:
	if [ ! -d "project/generated" ]; then mkdir project/generated; fi

generate-proto-cpp-navx2:
	mkdir -p project/hardware/navx2/include/proto
	protoc --cpp_out=project/hardware/navx2/include/proto project/common/proto/*.proto

position-extrapolator:
	cd project/recognition/position/pos_extrapolator/ && python src/main.py