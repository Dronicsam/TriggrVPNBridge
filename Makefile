.PHONY: build package check install clean
build:
	bash scripts/build.sh
package: build
	python3 scripts/package.py --binary build/TriggrVPNBridge.dylib
check:
	python3 -m unittest discover -s tests -v
	bash -n scripts/build.sh scripts/install.sh
install:
	bash scripts/install.sh "$(DEVICE)"
clean:
	rm -rf build dist
