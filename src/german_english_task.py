import torch
import torch.nn as nn
from torchtext import datasets
from torchtext import data
import spacy
from model_utils import make_model
from model_utils import greedy_decode
from optimizer import LabelSmoothing
from optimizer import NoamOpt
from train import MyIterator
from train import MultiGPULossCompute
from train import batch_size_fn
from train import run_epoch
from train import rebatch


spacy_de = spacy.load('de')
spacy_en = spacy.load('en')

def tokenize_de(text):
    return [tok.text for tok in spacy_de.tokenizer(text)]

def tokenize_en(text):
    return [tok.text for tok in spacy_en.tokenizer(text)]

if __name__ == '__main__':
    BOS_WORD   = '<s>'
    EOS_WORD   = '</s>'
    BLANK_WORD = '<blank>'

    SRC = data.Field(
        tokenize  = tokenize_de,
        pad_token = BLANK_WORD
    )
    TGT = data.Field(
        tokenize   = tokenize_en,
        init_token = BOS_WORD,
        eos_token  = EOS_WORD,
        pad_token  = BLANK_WORD
    )

    MAX_LEN = 100

    train, val, test = datasets.IWSLT.splits(
        exts = ('.de', '.en'),
        fields = (SRC, TGT),
        filter_pred = lambda x: len(vars(x)['src']) <= MAX_LEN and \
                                 len(vars(x)['trg']) <= MAX_LEN
    )
    MIN_FREQ = 2
    SRC.build_vocab(train.src, min_freq = MIN_FREQ)
    TGT.build_vocab(train.trg, min_freq = MIN_FREQ)

    devices = [0]
    if True:
        pad_idx = TGT.vocab.stoi['<blank>']
        model = make_model(
            len(SRC.vocab),
            len(TGT.vocab),
            N = 6
        )
        model.cuda()
        criterion = LabelSmoothing(
            size        = len(TGT.vocab),
            padding_idx = pad_idx,
            smoothing   = 0.1
        )
        criterion.cuda()
        BATCH_SIZE = 1500
        train_iter = MyIterator(
            train,
            batch_size    = BATCH_SIZE,
            device        = 0,
            repeat        = False,
            sort_key      = lambda x: (len(x.src), len(x.trg)),
            batch_size_fn = batch_size_fn,
            train         = True
        )
        valid_iter = MyIterator(
            val,
            batch_size    = BATCH_SIZE,
            device        = 0,
            repeat        = False,
            sort_key      = lambda x: (len(x.src), len(x.trg)),
            batch_size_fn = batch_size_fn,
            train         = False
        )
        model_par = nn.DataParallel(model, device_ids = devices)

    if True:
        model_opt = NoamOpt(
            model.src_embed[0].d_model,
            1,
            2000,
            torch.optim.Adam(
                model.parameters(),
                lr    = 0,
                betas = (0.9, 0.988),
                eps   = 1e-9
            )
        )

        # TODO: rework the code to be able to use SimpleLossCompute
        # instead of MultiGPULossCompute.
        for epoch in range(2):
            model_par.train()
            run_epoch(
                (rebatch(pad_idx, b) for b in train_iter),
                model_par,
                MultiGPULossCompute(
                    model.generator,
                    criterion,
                    devices = devices,
                    opt     = model_opt
                )
            )
            model_par.eval()
            loss = run_epoch(
                (rebatch(pad_idx, b) for b in valid_iter),
                model_par,
                MultiGPULossCompute(
                    model.generator,
                    criterion,
                    devices = devices,
                    opt     = None
                )
            )
            print(loss)
    else:
        model = torch.load('iwslt.pt')

    for batch_idx, batch in enumerate(valid_iter):
        src = batch.src.transpose(0, 1)[:1]
        src_mask = (src != SRC.vocab.stoi["<blank>"]).unsqueeze(-2)
        out = greedy_decode(
            model,
            src,
            src_mask,
            max_len = 60,
            start_symbol = TGT.vocab.stoi['<s>']
        )

        print('Translation:', end = '\t')

        for i in range(1, out.size(1)):
            sym = TGT.vocab.itos[out[0, i]]
            if sym == '</s>':
                break
            print(sym, end = ' ')
        print()
        print('Target:', end = '\t')
        for i in range(1, batch.trg.size(0)):
            sym = TGT.vocab.itos[batch.trg.data[i, 0]]
            if sym == '</s>':
                break
            print(sym, end = ' ')
        print()
        if batch_idx == 5:
            break
