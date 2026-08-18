find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_TRANSPORT gnuradio-transport)

FIND_PATH(
    GR_TRANSPORT_INCLUDE_DIRS
    NAMES gnuradio/transport/api.h
    HINTS $ENV{TRANSPORT_DIR}/include
        ${PC_TRANSPORT_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_TRANSPORT_LIBRARIES
    NAMES gnuradio-transport
    HINTS $ENV{TRANSPORT_DIR}/lib
        ${PC_TRANSPORT_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-transportTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_TRANSPORT DEFAULT_MSG GR_TRANSPORT_LIBRARIES GR_TRANSPORT_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_TRANSPORT_LIBRARIES GR_TRANSPORT_INCLUDE_DIRS)
