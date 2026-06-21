cmake_minimum_required(VERSION 3.24)

project(willow2_mod_manager)

set(UNREALSDK_FLAVOUR WILLOW)
set(EXPLICIT_PYTHON_ARCH win32)
set(EXPLICIT_PYTHON_VERSION 3.14.6)
set(EXPLICIT_PYTHON_HASH_BASE SHA256=6b3b132bd4b8520b238e57bfa2d98557fcae5b6653dfa0103fe4db5be5aeb13a)
set(EXPLICIT_PYTHON_HASH_TEST SHA256=49328bc23727a44bd4b1ec43aca4bb2a97da034c8b2967aeb6600909813495f1)
set(EXPLICIT_PYTHON_HASH_EMBEDDABLE SHA256=e5843719d78cd68b382683b16defbbc587c1c52bba758b612536bece3bdb94ab)

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
