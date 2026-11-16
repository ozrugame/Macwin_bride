.PHONY: test build package privacy-check

privacy-check:
	python3 scripts/privacy_check.py --history

test:
	bash scripts/swift.sh test
	python3 -m unittest discover -s Tests -p 'test_*.py'
	mkdir -p .build/checks
	clang -Wall -Wextra -Werror Tests/window_watch_test.c -o .build/checks/window-watch-test
	.build/checks/window-watch-test

build:
	python3 scripts/distribution.py build

package:
	python3 scripts/distribution.py package
