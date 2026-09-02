include_guard(GLOBAL)

# Pedigree exposes POSIX interfaces through libc and uses the standard ELF
# shared-library model, but does not split dlopen into a separate libdl.
set(PEDIGREE 1)
set(UNIX 1)
set(CMAKE_DL_LIBS "")
set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")
set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")
set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "\$ORIGIN")
set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")
set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")
set(CMAKE_EXE_EXPORTS_C_FLAG "-Wl,--export-dynamic")
set(CMAKE_SHARED_LIBRARY_SUFFIX ".so")

set(CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME 1)

foreach(type SHARED_LIBRARY SHARED_MODULE EXE)
  set(CMAKE_${type}_LINK_STATIC_C_FLAGS "-Wl,-Bstatic")
  set(CMAKE_${type}_LINK_DYNAMIC_C_FLAGS "-Wl,-Bdynamic")
endforeach()

set(_PEDIGREE_PAGE_FLAGS
  " -Wl,-z,max-page-size=4096 -Wl,-z,common-page-size=4096")
string(APPEND CMAKE_EXE_LINKER_FLAGS_INIT "${_PEDIGREE_PAGE_FLAGS}")
string(APPEND CMAKE_SHARED_LINKER_FLAGS_INIT "${_PEDIGREE_PAGE_FLAGS}")
string(APPEND CMAKE_MODULE_LINKER_FLAGS_INIT "${_PEDIGREE_PAGE_FLAGS}")
unset(_PEDIGREE_PAGE_FLAGS)

include(Platform/UnixPaths)
