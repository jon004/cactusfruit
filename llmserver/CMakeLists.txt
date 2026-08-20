cmake_minimum_required(VERSION 3.24)
project(llmserver LANGUAGES C CXX)

# Ensure C++ standard requirements are set globally
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---------------------------------------------------------------------------
# SPEED OPTIMIZATION: COMPILER ACCELERATION CACHE TRACKING
# ---------------------------------------------------------------------------
find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    message(STATUS "[localdoby] Compiler acceleration cache found: ${CCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER   "${CCACHE_PROGRAM}")
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    if(USE_CUDA)
        set(CMAKE_CUDA_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    endif()
endif()

# ---------------------------------------------------------------------------
# DEPENDENCY RESOLUTION: CURL (SYSTEM LOOKUP WITH SOURCE FALLBACK)
# ---------------------------------------------------------------------------
find_package(CURL QUIET)

if(NOT CURL_FOUND)
    message(STATUS "[localdoby] System CURL dev headers not found. Provisioning statically via FetchContent...")
    
    include(FetchContent)
    
    # Platform-specific Fetch arguments for CURL
    if(WIN32)
        set(CURL_PLATFORM_ARGS -DCMAKE_USE_SCHANNEL=ON)
    else()
        set(CURL_PLATFORM_ARGS -DCMAKE_USE_OPENSSL=OFF)
    endif()

    FetchContent_Declare(
        CURL
        GIT_REPOSITORY https://github.com/curl/curl.git
        GIT_TAG        curl-8_8_0
        CMAKE_ARGS     -DBUILD_CURL_EXE=OFF 
                       -DBUILD_SHARED_LIBS=OFF 
                       -DHTTP_ONLY=ON 
                       ${CURL_PLATFORM_ARGS}
    )
    FetchContent_MakeAvailable(CURL)

    set(CURL_FOUND TRUE)
    set(CURL_INCLUDE_DIRS ${curl_SOURCE_DIR}/include)
    set(CURL_LIBRARIES libcurl)
    
    if(NOT TARGET CURL::libcurl)
        if(TARGET libcurl)
            add_library(CURL::libcurl INTERFACE IMPORTED)
            target_link_libraries(CURL::libcurl INTERFACE libcurl)
            target_include_directories(CURL::libcurl INTERFACE ${CURL_INCLUDE_DIRS})
        endif()
    endif()
endif()

# ---------------------------------------------------------------------------
# EXTERNAL BACKEND SUBSYSTEM: LLAMA.CPP
# ---------------------------------------------------------------------------
set(LLAMA_FATAL_WARNINGS OFF CACHE BOOL "Disable strict warning traps within external codebases" FORCE)
set(LLAMA_ALL_WARNINGS OFF CACHE BOOL "Mute verbose compilation warnings" FORCE)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "Enforce static linkage rules across third-party extensions" FORCE)
set(LLAMA_SERVER OFF CACHE BOOL "Disable upstream native server bin matching" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "Disable example applications binary compilation" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "Disable testing framework dependencies" FORCE)

# === SPEED OPTIMIZATION: PRUNE CUDA TEMPLATE MATRIX ===
set(GGML_CUDA_FORCE_F16 ON CACHE BOOL "Compile optimized FP16 paths" FORCE)
set(GGML_CUDA_FORCE_MMQ OFF CACHE BOOL "Disable legacy multi-quant kernels if not using old quants" FORCE)

if(USE_CUDA)
    message(STATUS "[localdoby] Propagating backend flags down to llama.cpp modules...")
    set(GGML_CUDA ON CACHE BOOL "Enable GGML CUDA backend compilation" FORCE)
    set(GGML_CUDA_FORCE_SET ON CACHE BOOL "" FORCE)
    
    # Restrict compilation to modern local architectures (Ampere + Ada) to skip computing unneeded targets
    set(CMAKE_CUDA_ARCHITECTURES "86;89" CACHE STRING "Target hardware generation" FORCE)
endif()

add_subdirectory(external/llama.cpp)

# ---------------------------------------------------------------------------
# MAIN TARGET BUILD DEFINITION
# ---------------------------------------------------------------------------
set(SERVER_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/core/LlamaEmbedder.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/core/LlamaGenerator.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/core/ModelMemoryManager.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/core/Prompter.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/core/Server.cpp"
)

file(GLOB_RECURSE H_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/include/**/*.h")

add_executable(llm-server ${SERVER_SOURCES} ${H_SOURCES})

# Target-specific compile options
if(USE_CUDA)
    set_target_properties(llm-server PROPERTIES 
        CUDA_SEPARABLE_COMPILATION ON
    )
endif()

# Link dependencies
target_link_libraries(llm-server 
    PRIVATE 
    llama
    ggml
    CURL::libcurl
)

# Handle platform-specific low-level network and system configurations
if(WIN32)
    target_compile_definitions(llm-server PRIVATE _WIN32_WINNT=0x0A00)
    target_link_libraries(llm-server PRIVATE ws2_32 wsock32 crypt32 secur32)
    
    if(MSVC)
        target_compile_options(llm-server PRIVATE /W1 /EHsc /MP)
        set_target_properties(llm-server PROPERTIES
            MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL"
            LINK_FLAGS "/SUBSYSTEM:CONSOLE"
        )
    endif()
elseif(APPLE)
    target_link_libraries(llm-server PRIVATE pthread "-framework CoreFoundation" "-framework Security")
else()
    target_link_libraries(llm-server PRIVATE pthread)
endif()

# Explicitly map inclusion directories
target_include_directories(llm-server 
    PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/external/json/include
    ${CMAKE_CURRENT_SOURCE_DIR}/external/cpp-httplib
    ${CMAKE_CURRENT_SOURCE_DIR}/external/llama.cpp/include
    ${CMAKE_CURRENT_SOURCE_DIR}/external/llama.cpp/ggml/include
)
