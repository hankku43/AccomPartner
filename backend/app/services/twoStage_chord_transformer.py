import torch
import torch.nn as nn

class POP909ChordPredictor(nn.Module):
    def __init__(
        self,
        src_vocab_size,
        tgt_vocab_size,
        d_model=256,
        nhead=8,
        num_encoder_layers=4,
        num_decoder_layers=2,  # 和弦序列很短，Decoder 可輕量化
        dim_feedforward=1024,
        dropout=0.1,
        max_len=2048,
    ):
        super().__init__()
        self.d_model = d_model

        # 1. 雙辭典嵌入
        self.src_embedding = nn.Embedding(src_vocab_size, d_model)
        self.tgt_embedding = nn.Embedding(tgt_vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_len, d_model)

        # 2. Transformer
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=False,
        )

        self.fc_out = nn.Linear(d_model, tgt_vocab_size)
        self.dropout = nn.Dropout(dropout)

    def generate_causal_mask(self, sz, device):
        return torch.triu(
            torch.ones(sz, sz, device=device, dtype=torch.bool), diagonal=1
        )

    def forward(self, src, tgt, src_padding_mask=None, tgt_padding_mask=None, is_nar=False):
        src_len = src.size(1)
        tgt_len = tgt.size(1)

        src_pos = torch.arange(src_len, device=src.device).unsqueeze(0)
        tgt_pos = torch.arange(tgt_len, device=tgt.device).unsqueeze(0)

        src_emb = self.dropout(self.src_embedding(src) + self.pos_emb(src_pos))
        tgt_emb = self.dropout(self.tgt_embedding(tgt) + self.pos_emb(tgt_pos))

        tgt_mask = None if is_nar else self.generate_causal_mask(tgt_len, tgt.device)

        output = self.transformer(
            src_emb,
            tgt_emb,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask,
            memory_key_padding_mask=src_padding_mask,
        )

        return self.fc_out(output)
