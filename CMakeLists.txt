cmake_minimum_required(VERSION 2.8)
find_package(OpenCV REQUIRED)
add_executable(main test.cpp)
target_link_libraries(main ${OpenCV_LIBS})
