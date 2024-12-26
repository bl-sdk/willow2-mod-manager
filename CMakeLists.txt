cmake_minimum_required(VERSION 3.24)

project(willow_mod_manager)

set(UNREALSDK_ARCH x86)
set(UNREALSDK_UE_VERSION UE3)
set(EXPLICIT_PYTHON_ARCH win32)
set(EXPLICIT_PYTHON_VERSION 3.13.1)

add_subdirectory(libs/pyunrealsdk)

add_subdirectory(libs/pluginloader EXCLUDE_FROM_ALL)
set_target_properties(pluginloader_no_proxy PROPERTIES
    EXCLUDE_FROM_ALL false
    OUTPUT_NAME ddraw
)

install(
    TARGETS
        pluginloader_no_proxy
    RUNTIME DESTINATION
        .exe_folder
)
