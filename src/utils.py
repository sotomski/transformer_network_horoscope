import math
import numpy as np
import copy
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as F

def clones(module, N):
    """
    Produce N identical layers.
    """
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])

def subsequent_mask(size, k = 1):
    """
    Mask out subsequent positions.
    """
    attn_shape      = (1, size, size)
    subsequent_mask = np.triu(
        np.ones(attn_shape),
        k = k
    ).astype('uint8')

    return torch.from_numpy(subsequent_mask) == 0

def attention(query, key, value, mask = None, dropout = None):
    """
    Compute 'Scaled Dot Product Attention'.
    """
    # Size of network connections
    d_k    = query.size(-1)
    # Attention scores
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)

    # If mask is set, we use it to prevent the network attenting
    # to future positions in the sequence. It is mainly used in the
    # decoder.
    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)

    # We then use the softmax activitation to mainly focus the attention
    # output on a single value.
    p_attn = F.softmax(scores, dim = -1)

    if dropout is not None:
        p_attn = dropout(p_attn)

    return torch.matmul(p_attn, value), p_attn
