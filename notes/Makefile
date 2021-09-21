TARGETS = workflow_schema.png

.PHONY: all
all: $(TARGETS)

%.png: %.dot
	dot -Tpng $^ > $@

.PHONY: clean
clean:
	rm -rf $(TARGETS)
