# SPDX-License-Identifier: MPL-2.0
# My App for NBT Manager. Targets:
#   host              build/nbt-myapp-host (Linux, X11)
#   test              the Python tests (the host build started as NBT Manager
#                     starts it, the package, the notices)
#   test-asan         the launches under AddressSanitizer and UBSan
#   check-static-init nothing of ours runs before main
#   notice            legal/NOTICE.txt (notice-check: it is current)
# For the head unit, with the NBT toolchain, in the form FORM names:
#   module            build/nbt-myapp.so, loaded into NBT Manager's nbt-runner
#   guest             build/nbt-myapp.guest, nbt-runner's child process: the
#                     form GPL or LGPL code needs
#   native            build/nbt-myapp-native, a program of its own, without
#                     the runner; native-check: its imports exist on the car
#   vm-test           FORM's payload in the SDK's VM
#   package           FORM's signed package (APP_KEY; APP_VERSION, APP_SEQ)
#   format, clean
SHELL := /bin/bash

# The application's id, as in release/package.args.
APP := myapp
# The form the package carries: module, guest or native (README, "The form").
FORM ?= module

BUILD_DIR ?= build
OBJ_DIR := $(BUILD_DIR)/obj

APP_VERSION ?= 0.0.1
APP_SEQ ?= 1
APP_KEY ?=
# Sibling NBTFoundry checkouts; override as needed. The SDK is built into
# $(BUILD_DIR)/sdk; the manager is only needed for packaging.
NBT_SDK_DIR ?= ../sdk
NBT_MGR_DIR ?= ../manager
CXX ?= g++
PYTHON ?= python3

NBT_SDK_BUILD_DIR := $(abspath $(BUILD_DIR))/sdk
include $(NBT_SDK_DIR)/nbt-sdk.mk
# Each kind of object rebuilds when its compile command changes (the SDK's
# nbt-stamp.mk; the stamps are written at the end of this file).
stamp = $(OBJ_DIR)/$(1).stamp
ifeq ($(value nbt_stamp),)
$(error $(NBT_SDK_ROOT) has no nbt-stamp.mk: update that SDK checkout)
endif

# --- Our sources. An upstream project goes in third_party/ as a submodule,
# unmodified, compiled from its own source list with -w. ---
APP_SRC := src/main.cpp
APP_INC := $(NBT_SDK_INC) -Isrc
APP_CXXFLAGS := -std=c++11 -O2 -Wall -Wextra -Werror -fno-exceptions -fno-rtti $(CXXFLAGS)
ASAN_FLAGS := -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer
objs = $(patsubst %.cpp,$(OBJ_DIR)/$(1)/%.o,$(2))

HOST_COMPILE = $(CXX) $(APP_INC) $(APP_CXXFLAGS)
ASAN_COMPILE = $(HOST_COMPILE) $(ASAN_FLAGS)

HOST_APP := $(BUILD_DIR)/nbt-$(APP)-host
ASAN_APP := $(BUILD_DIR)/nbt-$(APP)-asan
# The tests name the build they start in NBT_<APP>_APP.
APP_ENV := NBT_$(shell echo $(APP) | tr a-z- A-Z_)_APP

.PHONY: all host test test-asan check-static-init format module guest native native-check vm-test package \
	notice notice-check clean

all: host test

# --- Host (Linux, X11) ---
$(OBJ_DIR)/host/%.o: %.cpp $(call stamp,host)
	@mkdir -p $(dir $@)
	$(HOST_COMPILE) -MMD -MP -c $< -o $@

$(HOST_APP): $(call objs,host,$(APP_SRC)) $(NBT_SDK_FRONT_HOST_LIBS)
	$(CXX) $^ $(LDFLAGS) $(NBT_SDK_HOST_LDLIBS) -o $@

host: $(HOST_APP)

# --- Sanitizer build ---
$(OBJ_DIR)/asan/%.o: %.cpp $(call stamp,asan)
	@mkdir -p $(dir $@)
	$(ASAN_COMPILE) -MMD -MP -c $< -o $@

$(ASAN_APP): $(call objs,asan,$(APP_SRC)) $(NBT_SDK_FRONT_ASAN_LIBS)
	$(CXX) $(ASAN_FLAGS) $^ $(LDFLAGS) $(NBT_SDK_HOST_LDLIBS) -o $@

# --- Tests ---
test: host
	$(APP_ENV)=$(abspath $(HOST_APP)) NBT_MGR_DIR=$(abspath $(NBT_MGR_DIR)) NBT_SDK_DIR=$(NBT_SDK_ROOT) \
		NBT_APP_FORM=$(FORM) $(PYTHON) -m unittest discover -s tests -v

test-asan: $(ASAN_APP)
	ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
		$(APP_ENV)=$(abspath $(ASAN_APP)) $(PYTHON) -m unittest discover -s tests -v -k Launch

# Our objects only: upstream's static constructors are its business.
check-static-init: $(call objs,host,$(APP_SRC))
	@set -e; \
	for obj in $^; do \
		ctors="$$(readelf -S "$$obj" | awk '/\.init_array|\.ctors/ {print $$2}')"; \
		if test -n "$$ctors"; then \
			echo "ERROR: static constructor section in $$obj: $$ctors"; exit 1; \
		fi; \
	done; \
	echo "OK: no .init_array/.ctors in our objects"
	+@$(NBT_SDK_MAKE) check-static-init

format:
	clang-format -i src/*.cpp

# --- The head unit: built with the NBT toolchain ("make -C ../sdk toolchain"
# once; sdk/docs/native-apps.md). ---

# With the runner: the same objects link as a module, loaded into NBT
# Manager's nbt-runner, or as a guest, the runner's child process.
MOD_APP := $(BUILD_DIR)/nbt-$(APP).so
GUEST_APP := $(BUILD_DIR)/nbt-$(APP).guest
# The SPDX licence of every linked object, upstream's and ours ("LicenseRef-X
# AND MPL-2.0"): the link checks it, and refuses GPL or LGPL code in a module.
APP_LICENSE := MPL-2.0
MOD_COMPILE = $(NBT_MOD_CXX) $(NBT_MOD_CXXFLAGS) -O2 -std=c++11 -Wall -Wextra -Werror -fno-exceptions \
	-fno-rtti $(APP_INC)

$(OBJ_DIR)/mod/%.o: %.cpp $(call stamp,mod) | nbt-sdk-mod
	@mkdir -p $(dir $@)
	$(MOD_COMPILE) -MMD -MP -c $< -o $@

MOD_OBJ := $(call objs,mod,$(APP_SRC))

$(MOD_APP): $(MOD_OBJ) $(NBT_SDK_MOD_DEPS)
	$(call nbt_module_link,$@,$(MOD_OBJ),$(APP_LICENSE))

$(GUEST_APP): $(MOD_OBJ) $(NBT_SDK_MOD_DEPS)
	$(call nbt_guest_link,$@,$(MOD_OBJ),$(APP_LICENSE))

module: $(MOD_APP)
guest: $(GUEST_APP)

# Without the runner: the toolchain's target for the head unit's own system.
# The car's libraries come as link stubs; the program links the real ones
# when it starts.
NATIVE_APP := $(BUILD_DIR)/nbt-$(APP)-native
NATIVE_COMPILE = $(NBT_QNX_CXX) $(NBT_QNX_CXXFLAGS) $(NBT_QNX_SDK_INC) $(APP_INC) $(APP_CXXFLAGS)

$(OBJ_DIR)/native/%.o: %.cpp $(call stamp,native)
	@mkdir -p $(dir $@)
	$(NATIVE_COMPILE) -MMD -MP -c $< -o $@

$(NATIVE_APP)-unstripped: $(call objs,native,$(APP_SRC)) $(NBT_SDK_FRONT_QNX_LIBS)
	$(call nbt_qnx_link,$@,$(filter %.o %.a,$^),$(NBT_SDK_QNX_LDLIBS))

$(NATIVE_APP): $(NATIVE_APP)-unstripped
	$(NBT_LLVM_BIN)/llvm-strip -o $@ $<

native: $(NATIVE_APP)

# The program's imports must exist on the car (CAR_SYSROOT: a sysroot of the
# release the car runs; skipped without); its window library calls its kdMain.
# (A module or a guest was checked when it was linked.)
CAR_SYSROOT ?=
native-check: native
	@$(NBT_LLVM_BIN)/llvm-nm -D --defined-only $(NATIVE_APP)-unstripped | grep -qw kdMain \
		|| { echo "$(NATIVE_APP): kdMain is not exported"; exit 1; }
	@if test -d "$(CAR_SYSROOT)"; then \
		$(PYTHON) $(NBT_SDK_ROOT)/tools/check_qnx_imports.py --sysroot "$(CAR_SYSROOT)" \
			--readelf $(NBT_MOD_READELF) $(NATIVE_APP)-unstripped; \
	else echo "skipped: CAR_SYSROOT names no sysroot of the car's system"; fi

PAYLOAD_module := $(MOD_APP)
PAYLOAD_guest := $(GUEST_APP)
PAYLOAD_native := $(NATIVE_APP)
PAYLOAD := $(PAYLOAD_$(FORM))
ifeq ($(PAYLOAD),)
$(error FORM is module, guest or native, not "$(FORM)")
endif

# --- The payload in the SDK's VM under QEMU (no GPU, no sound;
# sdk/docs/native-apps.md for what it needs): the health check, and with the
# runner (which fakes both) a user launch that must draw frames and stop
# cleanly. ---
ifeq ($(FORM),native)
VM_DIR := $(BUILD_DIR)/vm
vm-test: $(NATIVE_APP)
	@mkdir -p $(VM_DIR)
	cp $(NATIVE_APP) $(VM_DIR)/nbt-$(APP)
	QEMU_RUN_SECS=60 $(NBT_SDK_VM_RUN) \
		-c "NBT_LAUNCH=check NBT_DATA_DIR=/dev/shmem nbt-$(APP) &" -c "waitfor /none 10" \
		-c "slay -s TERM nbt-$(APP)" -c "waitfor /none 2" \
		-x 'ready, 1280x480' \
		$(VM_DIR)/nbt-$(APP)
else
VM_RUN := NBT_DATA_DIR=/dev/shmem nbt-runner --nbt-payload /proc/boot/$(notdir $(PAYLOAD))
vm-test: $(NBT_SDK_RUNNER) $(PAYLOAD)
	QEMU_RUN_SECS=120 $(NBT_SDK_VM_RUN) \
		-c "NBT_LAUNCH=check $(VM_RUN) &" \
		-c "waitfor /none 10" -c "slay -s TERM nbt-runner" -c "waitfor /none 3" \
		-c "NBT_LAUNCH=user NBT_SURFACE=5 NBT_RUNNER_FAKE_GL=1 NBT_RUNNER_FAKE_AUDIO=1 $(VM_RUN) &" \
		-c "waitfor /none 20" -c "slay -s TERM nbt-runner" -c "waitfor /none 3" \
		-x 'ready, 1280x480' -x 'fake-gl: closed: [1-9][0-9]* frames' \
		$^
endif

# --- The signed package: release/package.args describes it; a native
# program declares no runner (release/native.args, read after it). ---
PACKAGE_INPUT ?= $(PAYLOAD)
PACKAGE := $(BUILD_DIR)/$(APP)-$(APP_VERSION).nbt
PACKAGE_ARGS := @release/package.args $(if $(filter native,$(FORM)),@release/native.args)

package: $(PACKAGE_INPUT)
	@test -f "$(APP_KEY)" || { echo "APP_KEY must name the RSA signing key"; exit 1; }
	@test -f "$(NBT_MGR_DIR)/tools/package.py" || { echo "NBT_MGR_DIR=$(NBT_MGR_DIR) has no tools/package.py"; exit 1; }
	rm -f $(PACKAGE)
	$(PYTHON) $(NBT_MGR_DIR)/tools/package.py $(PACKAGE_ARGS) \
		--version "$(APP_VERSION)" \
		--sequence "$(APP_SEQ)" \
		--key "$(APP_KEY)" \
		--output $(PACKAGE) \
		$(PACKAGE_INPUT)

# legal/NOTICE.txt (tools/make_notice.py): again when a dependency, the SDK
# or the toolchain changes; `make test` fails until then.
notice:
	NBT_SDK_DIR=$(NBT_SDK_ROOT) NBT_TOOLCHAIN=$(NBT_TOOLCHAIN) $(PYTHON) tools/make_notice.py

notice-check:
	NBT_SDK_DIR=$(NBT_SDK_ROOT) NBT_TOOLCHAIN=$(NBT_TOOLCHAIN) $(PYTHON) tools/make_notice.py --check

clean:
	rm -rf $(BUILD_DIR)

DEPS := $(shell find $(OBJ_DIR) -name '*.d' 2>/dev/null)
-include $(DEPS)

$(call nbt_stamp,$(call stamp,host),$(HOST_COMPILE),$(CXX))
$(call nbt_stamp,$(call stamp,asan),$(ASAN_COMPILE),$(CXX))
$(call nbt_stamp,$(call stamp,mod),$(MOD_COMPILE),,$(NBT_TOOLCHAIN)/VERSION)
$(call nbt_stamp,$(call stamp,native),$(NATIVE_COMPILE),,$(NBT_TOOLCHAIN)/VERSION)
