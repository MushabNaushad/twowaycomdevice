# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT DLC_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT DLC_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################
list(APPEND DLC_python_files
    addFlags_python.cc
    removeFlags_python.cc
    bitStuffing_python.cc python_bindings.cc)

gr_pybind_make_oot(DLC ../../.. gr::DLC "${DLC_python_files}")

target_include_directories(DLC_python PRIVATE ${PROJECT_SOURCE_DIR}/include/gnuradio)

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET DLC_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:DLC_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/DLC/)

install(
    TARGETS DLC_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/DLC
    COMPONENT pythonapi)
