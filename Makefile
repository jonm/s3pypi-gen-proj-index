# Copyright 2019 Jonathan T. Moore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

PROJECT=s3pypi-gen-proj-index

SOURCES=handler.py

all: $(PROJECT)-$(VERSION).zip

.dep: requirements.txt
	pip install -r requirements.txt -t .
	touch .dep

$(PROJECT)-$(VERSION).zip: .dep $(SOURCES)
	python -m compileall .
	rm -f $(PROJECT)-$(VERSION).zip
	zip -r $(PROJECT)-$(VERSION).zip . -x .git/\* -x \.* -x \*~ -x Makefile -x ci/\*

clean:
	rm -f *.pyc $(PROJECT)-$(VERSION).zip *~

distclean: clean
	rm -f .dep

depend: .dep
