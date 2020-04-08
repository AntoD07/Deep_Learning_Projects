# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 08:59:45 2020

@author: Martin
"""

import torch
from torch import nn
from torch.nn import functional as F

class ResNetBlock(nn.Module):
    '''
    Input Nx1x14x14
    Output N   
    '''
    def __init__(self, nb_channels, kernel_size,
                 skip_connections = True, batch_normalization = True):
        super(ResNetBlock, self).__init__()       

        self.conv1 = nn.Conv2d(nb_channels, nb_channels,
                               kernel_size = kernel_size,
                               padding = (kernel_size - 1) // 2)

        self.bn1 = nn.BatchNorm2d(nb_channels)

        self.conv2 = nn.Conv2d(nb_channels, nb_channels,
                               kernel_size = kernel_size,
                               padding = (kernel_size - 1) // 2)

        self.bn2 = nn.BatchNorm2d(nb_channels)

        self.skip_connections = skip_connections
        self.batch_normalization = batch_normalization

    def forward(self, x):
        y = self.conv1(x)
        if self.batch_normalization: y = self.bn1(y)
        y = F.relu(y)
        y = self.conv2(y)
        if self.batch_normalization: y = self.bn2(y)
        if self.skip_connections: y = y + x
        y = F.relu(y)

        return y
    
class ResNet(nn.Module):

    def __init__(self, nb_residual_blocks, nb_channels = 10,
                 kernel_size = 3, nb_classes = 10,
                 skip_connections = True, batch_normalization = True):
        super(ResNet, self).__init__()
        

        self.conv = nn.Conv2d(1, nb_channels,
                              kernel_size = kernel_size,
                              padding = (kernel_size - 1) // 2)
        self.bn = nn.BatchNorm2d(nb_channels)

        self.resnet_blocks = nn.Sequential(
            *(ResNetBlock(nb_channels, kernel_size, skip_connections,
                          batch_normalization)
              for _ in range(nb_residual_blocks))
        )

        self.fc = nn.Linear(nb_channels*14*14, nb_classes)

    def forward(self, x):
        x = F.relu(self.bn(self.conv(x)))
        x = self.resnet_blocks(x)
        #print(x.size()) torch.Size([5, 1, 14, 14])
        x = x.view(x.size(0), -1)
        #print(x.size()) torch.Size([5, 196])
        x = self.fc(x)
        x = F.softmax(x, dim = 1)
        return x
    
class PairSetsModel(nn.Module):

    def __init__(self, weight_sharing = True, 
                 nb_residual_blocks = 5,
                 kernel_size = 3, nb_classes = 10,
                 skip_connections = True, batch_normalization = True):
        super(PairSetsModel, self).__init__()
        
        build_resnet = lambda : \
            ResNet(nb_residual_blocks = nb_residual_blocks,
                   nb_channels = 1,
                   kernel_size = kernel_size,
                   nb_classes = nb_classes,
                   skip_connections = skip_connections,
                   batch_normalization = batch_normalization)
            
        self.resnet1 = build_resnet()
        self.resnet2 = self.resnet1 if weight_sharing else build_resnet()
        
        self.fc = nn.Linear(2*nb_classes, 1)

    def forward(self, x):
        a,b,c,d = x.size()
        x1 = x[:,0,:,:].view((a, 1, c, d))
        x2 = x[:,1,:,:].view((a, 1, c, d))
        x1_p = self.resnet1(x1)
        x2_p = self.resnet2(x2)
        # print (x1_p.size()) torch.Size([5, 10])
        x_p = torch.cat((x1_p, x2_p), dim = 1)
        # print (x_p.size()) torch.Size([5, 20])
        p = self.fc(x_p)
        return p, x1_p, x2_p