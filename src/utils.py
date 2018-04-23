import torch.nn as nn
import copy
import numpy as np

class Batch():
    """
    Object for holding a batch of data with mask during training.
    """
    def __init__(self, src, trg = None, pad = 0):
        self.src      = src
        self.src_mask = (src != pad).unsqueeze(-2)

        if trg is not None:
            self.trg      = trg[:, :-1]
            self.trg_y    = trg[:, 1:]
            self.trg_mask = self.make_std_mask(self.trg, pad)
            self.ntokens  = (self.trg_y != pad).data.sum()

    @staticmethod
    def make_std_mask(tgt, pad):
        """
        Create a mask to hide padding and future words.
        """
        tgt_mask = (tgt != pad).unsqueeze(-2)
        tgt_mask = tgt_mask & Variable(subsequent_mask(tgt.size(-1)).type_as(tgt_mask.data))

        return tgt_mask

def clones(module, N):
    """
    Produce N identical layers.
    """
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])

def subsequent_mask(size):
    """
    Mask out subsequent positions.
    """
    attn_shape      = (1, size, size)
    subsequent_mask = np.triu(
        np.ones(attn_shape),
        k = 1
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