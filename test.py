import torch

ckpt = torch.load(r"d:\DOAN\models_weight\LicensePlateV8s.pt", map_location="cpu")
print(type(ckpt))