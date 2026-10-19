"""CPU 실행 가능한 소형 U-Net. U-Net++는 아직 구현하지 않았다."""
import torch
from torch import nn


class TinyUNet(nn.Module):
    def __init__(self, channels, classes=9):
        super().__init__()
        def block(a, b):
            return nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.ReLU())
        self.enc1, self.enc2 = block(channels,8), block(8,16)
        self.middle = block(16,32)
        self.dec2, self.dec1 = block(48,16), block(24,8)
        self.head = nn.Conv2d(8,classes,1)

    def forward(self, x):
        a = self.enc1(x)
        b = self.enc2(nn.functional.max_pool2d(a,2))
        c = self.middle(nn.functional.max_pool2d(b,2))
        d = self.dec2(torch.cat([nn.functional.interpolate(c,size=b.shape[-2:],mode='bilinear',align_corners=False),b],1))
        e = self.dec1(torch.cat([nn.functional.interpolate(d,size=a.shape[-2:],mode='bilinear',align_corners=False),a],1))
        return self.head(e)
