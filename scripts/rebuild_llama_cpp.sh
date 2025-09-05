#! /bin/bash

echo "Attempting to rebuild llama-cpp-python..."
pip uninstall llama-cpp-python -y || true
pip cache remove llama_cpp_python || true

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi detected and working. Building with CUDA support (GGML_CUDA=on)..."
    CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
else
    echo "nvidia-smi not available or failed. Installing without CUDA..."
    pip install llama-cpp-python
fi
echo "Rebuilt llama-cpp-python"