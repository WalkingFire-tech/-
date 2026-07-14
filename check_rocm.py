#!/usr/bin/env python
"""检查ROCm支持"""
import torch

print(f'ROCm版本: {torch.version.hip if hasattr(torch.version, "hip") else "不可用"}')