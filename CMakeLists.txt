cmake_minimum_required(VERSION 3.12)
project(hobby-literature
    VERSION      0.0.1
    DESCRIPTION  "Home library"
    HOMEPAGE_URL "https://github.com/VShilenkov/hobby_lit"
    LANGUAGES    NONE
)

find_package(CMakeFramework REQUIRED)

add_subdirectory(docs)
