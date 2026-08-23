# CMake generated Testfile for 
# Source directory: /home/methalabeywickrama/Documents/CDP Project/twowaycomdevice/blocks/gr-transport/python/transport
# Build directory: /home/methalabeywickrama/Documents/CDP Project/twowaycomdevice/blocks/gr-transport/build/python/transport
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(qa_transport_layer "/usr/bin/sh" "qa_transport_layer_test.sh")
set_tests_properties(qa_transport_layer PROPERTIES  _BACKTRACE_TRIPLES "/usr/lib64/cmake/gnuradio/GrTest.cmake;119;add_test;/home/methalabeywickrama/Documents/CDP Project/twowaycomdevice/blocks/gr-transport/python/transport/CMakeLists.txt;37;GR_ADD_TEST;/home/methalabeywickrama/Documents/CDP Project/twowaycomdevice/blocks/gr-transport/python/transport/CMakeLists.txt;0;")
subdirs("bindings")
