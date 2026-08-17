find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_DLC gnuradio-DLC)

FIND_PATH(
    GR_DLC_INCLUDE_DIRS
    NAMES gnuradio/DLC/api.h
    HINTS $ENV{DLC_DIR}/include
        ${PC_DLC_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_DLC_LIBRARIES
    NAMES gnuradio-DLC
    HINTS $ENV{DLC_DIR}/lib
        ${PC_DLC_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-DLCTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_DLC DEFAULT_MSG GR_DLC_LIBRARIES GR_DLC_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_DLC_LIBRARIES GR_DLC_INCLUDE_DIRS)
