# fAIth

If using CUDA, use:
```
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo nvidia-ctk config --in-place --set nvidia-container-runtime.mode=cdi && systemctl restart docker
```
The current version of Nvidia 580.XX breaks and no longer supports legacy mode. Use the CDI runtime instead