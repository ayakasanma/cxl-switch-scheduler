# Manual cocotb entry point; reviewed evidence uses scripts/run_revision_experiments.py.
.DEFAULT_GOAL := sim
TOPLEVEL_LANG = verilog
SIM ?= verilator
COCOTB_TOPLEVEL ?= switch_experiment_top
COCOTB_TEST_MODULES ?= test_experiment_top
VERILOG_SOURCES := $(addprefix ../../,$(shell sed -e '/^[[:space:]]*\/\//d' -e '/^[[:space:]]*$$/d' ../../rtl/experimental/filelist.f))
COMPILE_ARGS += -Wall -Wpedantic -Werror-IMPLICIT --public-flat-rw
export PYTHONDONTWRITEBYTECODE := 1
include $(shell cocotb-config --makefiles)/Makefile.sim
