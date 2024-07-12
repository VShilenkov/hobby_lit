cmake_minimum_required(VERSION 3.12)

find_package(Sphinx REQUIRED COMPONENTS build)
set(format html)

set(docs_root_path    "${CMAKE_SOURCE_DIR}")
set(docs_conf_path    "${CMAKE_CURRENT_SOURCE_DIR}")
set(docs_conf_version "${PROJECT_VERSION}") 
set(docs_conf_release "${docs_conf_version}")

configure_file(conf.py.in conf.py @ONLY)

add_custom_target(documentation_generate)

add_custom_target(documentation_generate_${format}
    COMMAND 
        ${Sphinx-build_COMMAND}
            -c ${CMAKE_CURRENT_BINARY_DIR}
            -d ${CMAKE_CURRENT_BINARY_DIR}/doctrees
            -b ${format}
            ${docs_root_path}
            ${CMAKE_CURRENT_BINARY_DIR}/${format}
    COMMENT "Documentation: Generate: ${Sphinx-build_COMMAND} ${format}"
    VERBATIM
)
add_dependencies(documentation_generate documentation_generate_${format})

add_custom_target(documentation_clean
    COMMAND 
        ${CMAKE_COMMAND} 
            -E remove_directory 
                "${CMAKE_CURRENT_BINARY_DIR}/doctrees"
    COMMENT "Documentation: Clean"
)

add_custom_target(documentation_clean_${format}
    COMMAND 
        ${CMAKE_COMMAND} 
            -E remove_directory 
                "${CMAKE_CURRENT_BINARY_DIR}/${format}"
    COMMENT "Documentation: Clean: ${format}"
)

add_dependencies(documentation_clean documentation_clean_${format})
