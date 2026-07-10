# CellScribe -> ROBOT -> OWL, ODK-style round-trip. Requires Java + ../.tools/robot.jar.
#
# make term NAME="striatal PV interneuron" MARKERS="GAD1,GAD2,PVALB" \
#           LOCATION="striatum" FUNCTIONS="GABA biosynthetic process"
ROBOT ?= java -jar ../.tools/robot.jar
BUILD := build
NAME ?=
MARKERS ?=
LOCATION ?=
FUNCTIONS ?=

$(BUILD):
	mkdir -p $(BUILD)

# 1) CellScribe drafts + ROBOT materialises the candidate OWL; 2) ELK classifies it.
term: $(BUILD)
	cd .. && python -m cellscribe.cli curate --name "$(NAME)" --markers "$(MARKERS)" \
	    --location "$(LOCATION)" --functions "$(FUNCTIONS)" \
	    --robot-owl odk/$(BUILD)/candidate.owl
	$(ROBOT) reason --reasoner ELK \
	    --input $(BUILD)/candidate.owl --output $(BUILD)/candidate.reasoned.owl
	@echo ""
	@echo "Candidate term: $(BUILD)/candidate.reasoned.owl"
	@echo "Review it, then in your ODK repo:"
	@echo "  robot merge --input src/ontology/cl-edit.owl --input $(BUILD)/candidate.owl \\"
	@echo "              --output src/ontology/cl-edit.owl   # then open a PR"

clean:
	rm -rf $(BUILD)

.PHONY: term clean
