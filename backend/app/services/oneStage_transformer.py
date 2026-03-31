import torch
import torch.nn as nn


class POP909Transformer(nn.Module):
    def __init__(
        self,
        vocab_size,  # 這個值應該是 len(pipeline.tokenizer)
        d_model=256,
        nhead=8,
        num_encoder_layers=4,
        num_decoder_layers=4,
        dim_feedforward=1024,
        dropout=0.1,
        max_len=2048,
    ):
        super().__init__()
        self.d_model = d_model

        # 1. 詞嵌入與位置編碼 (Learnable)
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_len, d_model)  # max_len=2048

        # 2. Transformer 本體
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=False,  # ✅ 改回 Post-LN
            # enable_nested_tensor 預設 True，不用寫
        )

        self.fc_out = nn.Linear(d_model, vocab_size)
        self.dropout = nn.Dropout(dropout)

    def generate_causal_mask(self, sz, device):
        return torch.triu(
            torch.ones(sz, sz, device=device, dtype=torch.bool), diagonal=1
        )

    def forward(self, src, tgt, src_padding_mask=None, tgt_padding_mask=None):
        # src: (batch, src_len), tgt: (batch, tgt_len)
        src_len = src.size(1)
        tgt_len = tgt.size(1)

        # 建立位置索引並送入 GPU
        src_pos = torch.arange(src_len, device=src.device).unsqueeze(0)
        tgt_pos = torch.arange(tgt_len, device=tgt.device).unsqueeze(0)

        # Embedding + Position
        src_emb = self.dropout(self.embedding(src) + self.pos_emb(src_pos))
        tgt_emb = self.dropout(self.embedding(tgt) + self.pos_emb(tgt_pos))

        # 建立自回歸遮罩 (Decoder 專用)
        tgt_mask = self.generate_causal_mask(tgt_len, tgt.device)

        # 執行核心運算
        output = self.transformer(
            src_emb,
            tgt_emb,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask,
            memory_key_padding_mask=src_padding_mask,
        )

        return self.fc_out(output)
